import asyncio
import json
import sys
import unittest
from secrets import token_urlsafe
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import guardian_engine
from config import settings
from database import Base
from guardian_engine import (
    build_review,
    classify_risk,
    ensure_agent_runs,
    generated_content_violations,
    process_case,
)
from guardian_pdf import generate_guardian_pdf
from guardian_schemas import GuardianCaseCreate, InterventionOutput, KnowledgeOutput, ResourceOutput, SupportPlanOutput
from models import AgentRun, EvidenceSource, FollowUpTask, GuardianCase, SafetyEvent, SupportPlan, User
from security import get_password_hash


class GuardianWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.old_session_local = guardian_engine.SessionLocal
        self.old_available = guardian_engine.is_spark_available
        self.old_delay = settings.AGENT_STEP_DELAY_MS
        guardian_engine.SessionLocal = self.Session
        guardian_engine.is_spark_available = lambda: False
        settings.AGENT_STEP_DELAY_MS = 0
        user = User(username="guardian_test", password_hash=get_password_hash(token_urlsafe(18)), nickname="测试守护者", is_admin=0)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user = user

    def tearDown(self):
        guardian_engine.SessionLocal = self.old_session_local
        guardian_engine.is_spark_available = self.old_available
        settings.AGENT_STEP_DELAY_MS = self.old_delay
        self.db.close()
        self.engine.dispose()

    def create_case(self, *, signals, context="", duration="2_4_weeks", impact="partial"):
        case = GuardianCase(
            case_code=guardian_engine.create_case_code(),
            owner_user_id=self.user.id,
            reporter_role="parent",
            age_band="15-18",
            signals_json=json.dumps(signals, ensure_ascii=False),
            duration=duration,
            functional_impact=impact,
            district="南城街道",
            context=context,
            guardian_may_be_source=0,
            consent_version="guardian-support-v1",
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def test_negated_or_quoted_language_does_not_create_false_urgent(self):
        case = self.create_case(signals=["mood_low"], context="孩子明确否认不想活，也说那只是新闻里别人说的话。", duration="under_1_week", impact="none")
        risk, trigger = classify_risk(case)
        self.assertEqual(risk, "watch")
        self.assertEqual(trigger, "observed_change")

    def test_explicit_danger_signal_forces_urgent_and_skips_normal_plan(self):
        case = self.create_case(signals=["self_harm_sign"], context="发现合成个案中的自伤痕迹")
        ensure_agent_runs(self.db, case)
        asyncio.run(process_case(case.id))
        self.db.expire_all()
        completed = self.db.query(GuardianCase).filter(GuardianCase.id == case.id).first()
        self.assertEqual(completed.risk_level, "urgent")
        self.assertEqual(completed.status, "completed")
        self.assertEqual(self.db.query(FollowUpTask).filter(FollowUpTask.case_id == case.id).count(), 0)
        self.assertEqual(self.db.query(SafetyEvent).filter(SafetyEvent.case_id == case.id).count(), 1)
        skipped = self.db.query(AgentRun).filter(AgentRun.case_id == case.id, AgentRun.status == "skipped_for_safety").count()
        self.assertGreaterEqual(skipped, 4)
        plan = SupportPlanOutput.model_validate(json.loads(self.db.query(SupportPlan).filter(SupportPlan.case_id == case.id).one().plan_json))
        self.assertNotIn("PHQ", plan.observation_summary)
        self.assertIn("12356", json.dumps(plan.model_dump(), ensure_ascii=False))

    def test_indirect_crisis_language_and_unsafe_guardian_force_urgent(self):
        for text in ["最近总说想死", "想结束生命", "准备烧炭", "把药藏起来准备一次吃掉", "想从楼上跳下去", "提到轻生"]:
            with self.subTest(text=text):
                case = self.create_case(signals=["mood_low"], context=text)
                self.assertEqual(classify_risk(case)[0], "urgent")
        family_case = self.create_case(signals=["family_conflict"], context="家庭环境现在不安全")
        family_case.guardian_may_be_source = 1
        self.assertEqual(classify_risk(family_case), ("urgent", "family_harm_or_unsafe_guardian"))

    def test_generated_diagnosis_and_treatment_language_is_rejected(self):
        violations = generated_content_violations("孩子可能患有抑郁，需要药物治疗，PHQ-9得分18分。")
        self.assertIn("diagnostic_label", violations)
        self.assertIn("treatment_instruction", violations)
        self.assertIn("fabricated_scale_score", violations)

    def test_review_marks_missing_evidence_and_resources_unavailable(self):
        case = self.create_case(signals=["mood_low"])
        case.risk_level = "watch"
        intervention = InterventionOutput(
            immediate_actions=["保持支持"], seven_day_actions=[], conversation_prompts=["我愿意听"],
            avoid_actions=["不贴标签"], tailored_note="待人工审核", generated_by="reviewed_template",
        )
        review = build_review(
            case,
            intervention,
            KnowledgeOutput(evidence_codes=[], evidence_summary=[], evidence_limit="当前不可用"),
            ResourceOutput(resources=[], selection_note="当前不可用"),
        )
        self.assertEqual(review.evidence_coverage, "unavailable")
        self.assertTrue(review.disagreements)

    def test_context_schema_rejects_phone_school_id_and_precise_address(self):
        base = {
            "reporter_role": "parent", "age_band": "15-18", "signals": ["mood_low"],
            "duration": "under_1_week", "functional_impact": "none", "district": "南城街道",
            "guardian_may_be_source": False, "consent_version": "guardian-support-v1", "deidentified_confirmed": True,
        }
        for text in ["电话13800138000", "身份证440101200001011234", "张三在东莞中学", "住在鸿福路88号2栋"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                GuardianCaseCreate.model_validate({**base, "context": text})

    def test_professional_support_flow_creates_evidence_followups_and_pdf(self):
        case = self.create_case(signals=["mood_low", "social_withdrawal", "performance_drop"])
        ensure_agent_runs(self.db, case)
        asyncio.run(process_case(case.id))
        self.db.expire_all()
        completed = self.db.query(GuardianCase).filter(GuardianCase.id == case.id).first()
        self.assertEqual(completed.risk_level, "professional")
        self.assertEqual(completed.status, "completed")
        self.assertEqual(self.db.query(FollowUpTask).filter(FollowUpTask.case_id == case.id).count(), 3)
        self.assertEqual(self.db.query(AgentRun).filter(AgentRun.case_id == case.id, AgentRun.status == "completed").count(), 7)
        plan = SupportPlanOutput.model_validate(json.loads(self.db.query(SupportPlan).filter(SupportPlan.case_id == case.id).one().plan_json))
        self.assertFalse(any(term in json.dumps(plan.model_dump(), ensure_ascii=False) for term in ["抑郁症", "焦虑症", "确诊"]))
        evidence = self.db.query(EvidenceSource).filter(EvidenceSource.source_code.in_(plan.evidence_codes)).all()
        pdf = generate_guardian_pdf(completed, plan, evidence)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertGreater(len(pdf), 5_000)


if __name__ == "__main__":
    unittest.main()
