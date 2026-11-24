import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import companion_engine as companion


class CompanionEngineTests(unittest.TestCase):
    def test_parse_marker_reply_and_state(self):
        parsed = companion.parse_companion_output(
            '嗯，我在听。\n[[XM_STATE]]{"scores": {"3": 2}, "crisis": false}'
        )
        self.assertEqual(parsed["reply"], "嗯，我在听。")
        self.assertEqual(parsed["scores"], {"3": 2})
        self.assertFalse(parsed["crisis"])
        self.assertNotIn(companion.STATE_MARKER, parsed["reply"])

    def test_parse_legacy_json_reply(self):
        parsed = companion.parse_companion_output(
            '{"reply": "旧格式也能接住。", "scores": {"2": 1}, "crisis": false}'
        )
        self.assertEqual(parsed["reply"], "旧格式也能接住。")
        self.assertEqual(parsed["scores"], {"2": 1})

    def test_parse_without_marker_keeps_whole_reply(self):
        parsed = companion.parse_companion_output("就是一句普通回复。")
        self.assertEqual(parsed["reply"], "就是一句普通回复。")
        self.assertIsNone(parsed["scores"])

    def test_parse_ignores_out_of_range_scores(self):
        parsed = companion.parse_companion_output(
            'reply\n[[XM_STATE]]{"scores": {"1": 9, "2": -1, "99": 2, "3": 1}}'
        )
        self.assertEqual(parsed["scores"], {"3": 1})

    def test_apply_turn_scores_each_topic_once(self):
        state = companion.default_state()
        companion.apply_turn(state, 1, {"1": 2}, False)
        companion.apply_turn(state, 2, {"1": 3, "3": 1}, False)
        self.assertEqual(state["scored"], {"1": 2, "3": 1})
        self.assertEqual(companion.current_focus(state), 2)

    def test_topic_moves_to_unclear_after_four_followups(self):
        state = companion.default_state()
        for _ in range(4):
            companion.apply_turn(state, 1, None, False)
        self.assertEqual(state["unclear"], [1])
        self.assertEqual(companion.current_focus(state), 2)

    def test_crisis_sets_summary_signal(self):
        state = companion.default_state()
        companion.apply_turn(state, 1, {}, True)
        self.assertTrue(state["crisisActive"])

    def test_build_history_accepts_legacy_json_assistant_messages(self):
        history = companion.build_history([
            {"role": "user", "content": "最近很累"},
            {"role": "assistant", "content": '{"reply": "嗯，我在。", "scores": {}, "crisis": false}'},
            {"role": "system", "content": "ignored"},
        ])
        self.assertEqual(history, [
            {"role": "user", "content": "最近很累"},
            {"role": "assistant", "content": "嗯，我在。"},
        ])

    def test_build_history_caps_count_and_total_characters(self):
        messages = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": "x" * 700}
            for index in range(40)
        ]
        history = companion.build_history(messages, limit=24, max_chars=2000)
        self.assertLessEqual(len(history), 24)
        self.assertLessEqual(sum(len(item["content"]) for item in history), 2700)
        self.assertEqual(history[-1]["content"], "x" * 700)

    def test_fallback_is_never_empty(self):
        for text in ["", "嗯", "你觉得我这样正常吗？", "今天真的好累，什么都不想做"]:
            self.assertTrue(companion.in_character_fallback(text).strip())

    def test_forbidden_clinical_language_is_detected(self):
        self.assertTrue(companion.has_forbidden_clinical_language("你的量表得分是 12 分"))
        self.assertTrue(companion.has_forbidden_clinical_language("这可能是一个症状"))
        self.assertFalse(companion.has_forbidden_clinical_language("听起来今天真的很累。"))

    def test_sanitize_strips_marker_and_caps_length(self):
        reply = "嗯。" + "今天真的辛苦了。" * 30 + companion.STATE_MARKER + "{}"
        cleaned = companion.sanitize_reply(reply)
        self.assertNotIn(companion.STATE_MARKER, cleaned)
        self.assertLessEqual(len(cleaned), companion.MAX_REPLY_CHARS + 1)

    def test_parse_memory_from_state_marker(self):
        parsed = companion.parse_companion_output(
            '嗯，团子听起来好黏人。\n[[XM_STATE]]{"scores": {}, "crisis": false, '
            '"memory": {"content": "养了一只叫团子的猫", "category": "近况", "quote": "我家猫叫团子"}}'
        )
        self.assertEqual(parsed["memory"]["content"], "养了一只叫团子的猫")
        self.assertEqual(parsed["memory"]["category"], "近况")

    def test_memory_candidate_must_be_grounded_in_latest_message(self):
        candidate = companion.clean_memory_candidate(
            {"content": "养了一只叫团子的猫", "category": "近况", "quote": "我家猫叫团子"},
            "我家猫叫团子，最近总在半夜跑酷。",
        )
        self.assertEqual(candidate, {"content": "养了一只叫团子的猫", "category": "近况"})
        self.assertIsNone(companion.clean_memory_candidate(
            {"content": "养了一只叫团子的猫", "category": "近况", "quote": "我家猫叫团子"},
            "今天有点累。",
        ))
        self.assertIsNone(companion.clean_memory_candidate(
            {"content": "喜欢篮球", "category": "喜好", "quote": "我喜欢看电影"},
            "我喜欢看电影。",
        ))

    def test_memory_candidate_rejects_clinical_crisis_and_contact_content(self):
        for content in ("最近量表得分 12 分", "有过轻生的念头", "手机号 13800138000", "微信 abc12345"):
            self.assertIsNone(companion.clean_memory_candidate(
                {"content": content, "category": "近况", "quote": content},
                content,
            ), content)

    def test_memory_candidate_caps_length_and_normalizes_category(self):
        too_long = "喜欢" + "很" * companion.MAX_MEMORY_CHARS
        self.assertIsNone(companion.clean_memory_candidate(
            {"content": too_long, "category": "近况", "quote": too_long}, too_long))
        candidate = companion.clean_memory_candidate(
            {"content": "喜欢打篮球", "category": "不存在的分类", "quote": "我挺喜欢打篮球的"},
            "我挺喜欢打篮球的。",
        )
        self.assertEqual(candidate, {"content": "喜欢打篮球", "category": "其他"})

    def test_build_memory_instruction_is_bounded_and_deduplicated(self):
        self.assertEqual(companion.build_memory_instruction([]), "")
        instruction = companion.build_memory_instruction(
            ["喜欢打篮球", "喜欢打篮球。", "养了一只叫团子的猫"]
        )
        self.assertIn("喜欢打篮球", instruction)
        self.assertIn("养了一只叫团子的猫", instruction)
        self.assertEqual(instruction.count("喜欢打篮球"), 1)
        long_list = companion.build_memory_instruction(
            [f"小事{index}" for index in range(30)]
        )
        self.assertEqual(long_list.count("- "), companion.MAX_MEMORIES_IN_PROMPT)


if __name__ == "__main__":
    unittest.main()
