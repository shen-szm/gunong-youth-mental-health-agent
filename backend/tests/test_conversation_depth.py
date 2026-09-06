import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.chat import _derive_student_turn_features, _student_support_bridge, _render_model_selected_student_reply, StudentTurnModelOutput, generated_content_violations


class ConversationDepthTests(unittest.TestCase):
    def test_theme_and_support_need_change_the_actual_response(self):
        candidate = StudentTurnModelOutput(emotion="焦虑", intensity="明显", evidence=["焦虑"], support_need="整理任务", response_style="温和映照", question_focus="最难的部分")
        features = [_derive_student_turn_features("考试让我焦虑", 1)]
        reply = _render_model_selected_student_reply(candidate, "routine", turn_features=features)
        self.assertIn("学习", reply)
        self.assertIn("现在能做", reply)
        self.assertGreater(len(reply), 100)
        self.assertFalse(generated_content_violations(reply))
        other = _render_model_selected_student_reply(candidate.model_copy(update={"support_need": "被倾听"}), "routine", turn_features=features)
        self.assertNotEqual(reply, other)

    def test_feature_context_never_interpolates_arbitrary_personal_or_model_text(self):
        marker = "张某某住在某路123号"
        reply = _student_support_bridge(marker, [{"support_theme": marker}], 0)
        self.assertNotIn(marker, reply)

    def test_explicit_listening_preference_and_recent_theme_are_retained(self):
        features = [_derive_student_turn_features("和同学相处让我焦虑", 1), _derive_student_turn_features("先听我说，不用给建议", 2)]
        self.assertEqual(features[-1]["conversation_preference"], "先倾听")
        self.assertIn("同伴", _student_support_bridge("被倾听", features, 0))
