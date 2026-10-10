import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import test_teacher_case_access as fixture_module
from api.teacher_tasks import router, durable_store
from teacher_task_runtime import DurableTeacherPlans
from models import TeacherReviewReport, TeacherStudentAssignment


class RealCaseWorkflowApiTests(unittest.TestCase):
    def test_clarification_receipt_is_scope_bound_and_never_approves_execution(self):
        client = self.fixture.admin_client
        url = '/api/teacher/tasks/clarifications'
        payload = {'request_id': str(uuid4()), 'student_id': self.fixture.student_id,
                   'goal': '30天授权资料沟通报告，不要发送消息', 'confirmed': True}
        for confirmed in (False, 'true'):
            self.assertEqual(client.post(url, json={**payload, 'confirmed': confirmed}).status_code, 422)
        self.assertEqual(self.fixture.student_client.post(url, json=payload).status_code, 403)
        self.assertEqual(self.fixture.teacher_client.post(url, json=payload).status_code, 403)
        result = client.post(url, json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        receipt = result.json()
        detail = url + '/' + receipt['clarification_id']
        self.assertEqual(client.get(detail).json(), receipt)
        self.assertEqual(self.fixture.teacher_client.get(detail).status_code, 404)
        decision = {'goal': payload['goal'], 'confirmed': True, 'decisions': {'external_delivery': 'prohibited'}}
        self.assertEqual(client.post(detail + '/decision', json={**decision, 'goal': '换成没有风险的要求'}).status_code, 409)
        response = client.post(detail + '/decision', json=decision)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'review_recorded_blocked')
        self.assertFalse(response.json()['can_prepare'])
        self.assertNotIn('goal', response.json())
        self.model.assert_not_awaited()
        # Current role is checked again, not trusted from the stored receipt.
        from models import User
        with self.fixture.Session() as db:
            db.query(User).filter(User.id == self.fixture.admin_id).update({'is_admin': 0})
            db.commit()
        self.assertEqual(client.get(detail).status_code, 403)
        self.assertEqual(client.post(detail + '/decision', json=decision).status_code, 403)

    def test_history_requires_current_scope_and_excludes_other_owners(self):
        client = self.fixture.admin_client
        task = client.post("/api/teacher/tasks/case-plans", json=self.payload).json()
        query = {"student_id": self.fixture.student_id}
        response = client.get("/api/teacher/tasks/case-history", params=query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([x["task_id"] for x in response.json()["items"]], [task["task_id"]])
        self.assertEqual(self.fixture.teacher_client.get("/api/teacher/tasks/case-history", params=query).status_code, 403)
        self.assertEqual(self.fixture.student_client.get("/api/teacher/tasks/case-history", params=query).status_code, 403)
        self.assertEqual(client.get("/api/teacher/tasks/case-history", params={"student_id": 0}).status_code, 422)

    def test_terminate_failed_task_preserves_report_and_blocks_execution(self):
        from teacher_task_runtime import TaskConflict
        client = self.fixture.admin_client
        task = client.post("/api/teacher/tasks/case-plans", json=self.payload).json()
        url = "/api/teacher/tasks/durable-plans/" + task["task_id"]
        payload = {"digest": task["digest"], "confirmed": True, "reason": "retry_exhausted"}
        self.assertEqual(client.post(url + "/terminate", json={**payload, "confirmed": False}).status_code, 422)
        self.assertEqual(client.post(url + "/terminate", json={**payload, "confirmed": "true"}).status_code, 422)
        client.post(url + "/decision", json={"digest": task["digest"], "approved": True})
        with patch("teacher_case_workflow.TeacherCaseTools.verify", side_effect=TaskConflict("verification failed")):
            result = client.post(url + "/execute")
            self.assertEqual(result.json()["status"], "failed", result.text)
        reread = client.get(url + "/execution").json()
        self.assertEqual(reread["error"], "source_or_artifact_changed")
        self.assertEqual(reread["last_failure"], result.json()["last_failure"])
        self.assertNotIn("verification failed", str(reread))
        stopped = client.post(url + "/terminate", json=payload)
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()["status"], "terminated")
        self.assertEqual(client.post(url + "/terminate", json=payload).json(), stopped.json())
        self.assertEqual(client.post(url + "/execute").status_code, 409)
        self.assertEqual(client.post(url + "/revision-plans").status_code, 409)
        self.assertEqual(self.fixture.student_client.post(url + "/terminate", json=payload).status_code, 403)
        with self.fixture.Session() as db:
            report = db.query(TeacherReviewReport).one()
            report_id = report.report_id
        self.assertEqual(client.get(f"/api/teacher/students/{self.fixture.student_id}/review-reports/{report_id}/detail").status_code, 200)

    def setUp(self):
        self.fixture = fixture_module.TeacherCaseAccessTests()
        self.fixture.setUp()
        self.temp = tempfile.TemporaryDirectory()
        app = self.fixture.admin_client.app
        app.include_router(router)
        app.dependency_overrides[durable_store] = lambda: DurableTeacherPlans(self.temp.name, lambda owner: owner in {self.fixture.admin_id, self.fixture.teacher_id})
        self.model_patch = patch("teacher_review_engine.ask_spark", new_callable=AsyncMock)
        self.model = self.model_patch.start()
        self.ai_patch = patch("config.settings.ALLOW_EXTERNAL_AI", False)
        self.ai_patch.start()
        self.payload = {"request_id": str(uuid4()), "contract": {"objective": "conversation_preparation", "period_days": 30}, "student_id": self.fixture.student_id}

    def tearDown(self):
        self.ai_patch.stop()
        self.model_patch.stop()
        self.fixture.tearDown()
        self.temp.cleanup()

    def test_real_report_pdf_and_idempotency_without_checkpoint_prose(self):
        client = self.fixture.admin_client
        response = client.post("/api/teacher/tasks/case-plans", json=self.payload)
        self.assertEqual(response.status_code, 200, response.text)
        task = response.json()
        url = "/api/teacher/tasks/durable-plans/" + task["task_id"]
        self.assertEqual(client.post(url + "/execute").status_code, 409)
        self.assertEqual(client.post(url + "/decision", json={"digest": task["digest"], "approved": True}).status_code, 200)
        result = client.post(url + "/execute")
        self.assertEqual(result.status_code, 200, result.text)
        receipt = result.json()
        self.assertEqual(client.post(url + "/terminate", json={"digest": task["digest"], "confirmed": True}).status_code, 409)
        self.assertEqual(receipt["status"], "awaiting_report_review", receipt)
        report_id = receipt["report_id"]
        self.assertEqual(client.post(url + "/execute").json()["report_id"], report_id)
        pdf = client.get(f"/api/teacher/students/{self.fixture.student_id}/review-reports/{report_id}.pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.model.assert_not_awaited()
        with self.fixture.Session() as db:
            self.assertEqual(db.query(TeacherReviewReport).count(), 1)
            row = db.query(TeacherReviewReport).one()
            row.content_hash = "0" * 64
            db.commit()
        self.assertEqual(client.get(url + "/execution").status_code, 409)
        data = (Path(self.temp.name) / "checkpoints.sqlite").read_bytes()
        self.assertNotIn("我和同学相处得有点累".encode(), data)
        self.assertNotIn("最近早上不太想去学校".encode(), data)
        self.assertEqual(client.delete(url).status_code, 204)
        self.assertEqual(client.get(url + "/execution").status_code, 404)

    def test_ordinary_teacher_requires_access_and_rechecks_assignment(self):
        client = self.fixture.teacher_client
        self.assertEqual(client.post("/api/teacher/tasks/case-plans", json=self.payload).status_code, 403)
        request = client.post(f"/api/teacher/students/{self.fixture.student_id}/access-requests", json={"reason": "准备个案沟通工作需要查看授权范围内的资料"})
        self.assertEqual(request.status_code, 201, request.text)
        request_id = request.json()["request_id"]
        approved = self.fixture.admin_client.post(f"/api/teacher/access-requests/{request_id}/decision", json={"decision": "approved", "note": "核对职责后批准"})
        self.assertEqual(approved.status_code, 200, approved.text)
        response = client.post("/api/teacher/tasks/case-plans", json={**self.payload, "access_request_id": request_id})
        self.assertEqual(response.status_code, 200, response.text)
        task = response.json()
        url = "/api/teacher/tasks/durable-plans/" + task["task_id"]
        client.post(url + "/decision", json={"digest": task["digest"], "approved": True})
        self.assertEqual(client.post(url + "/execute").json()["status"], "awaiting_report_review")
        receipt = client.get(url + "/execution").json()
        client.post(f"/api/teacher/students/{self.fixture.student_id}/review-reports/{receipt['report_id']}/decision?request_id={request_id}", json={"decision": "revision_requested", "note": "需要补充学生意愿", "checklist_confirmed": False})
        from models import MoodRecord
        from app_time import china_now_naive
        from datetime import timedelta
        with self.fixture.Session() as db:
            db.add(MoodRecord(user_id=self.fixture.student_id, mood_score=3, mood_label="平静", content="审批之后的新记录不在原授权内", created_at=china_now_naive() + timedelta(seconds=1)))
            db.commit()
        self.assertEqual(client.post(url + "/revision-check").json()["status"], "waiting_for_material")
        with self.fixture.Session() as db:
            db.query(TeacherStudentAssignment).filter_by(teacher_user_id=self.fixture.teacher_id).update({"active": 0})
            db.commit()
        self.assertEqual(client.get(url + "/execution").status_code, 403)
        self.assertEqual(client.post(url + "/execute").status_code, 403)
        self.assertEqual(client.post(url + "/revision-check").status_code, 403)

    def test_unsupported_format_and_student_role_are_rejected(self):
        payload = {**self.payload, "contract": {**self.payload["contract"], "output_format": "one_page_brief"}}
        self.assertEqual(self.fixture.admin_client.post("/api/teacher/tasks/case-plans", json=payload).status_code, 422)
        self.assertEqual(self.fixture.student_client.post("/api/teacher/tasks/case-plans", json=self.payload).status_code, 403)

    def test_capabilities_are_teacher_only_and_follow_feature_flag(self):
        with patch("config.settings.ENABLE_TEACHER_DURABLE_PLANS", False):
            self.assertEqual(self.fixture.admin_client.get("/api/teacher/tasks/capabilities").json(), {"durable_case_execution": False})
        with patch("config.settings.ENABLE_TEACHER_DURABLE_PLANS", True):
            self.assertTrue(self.fixture.teacher_client.get("/api/teacher/tasks/capabilities").json()["durable_case_execution"])
        self.assertEqual(self.fixture.student_client.get("/api/teacher/tasks/capabilities").status_code, 403)

    def test_exact_report_review_stays_bound_when_new_revision_exists(self):
        client = self.fixture.admin_client
        task = client.post("/api/teacher/tasks/case-plans", json=self.payload).json()
        task_url = "/api/teacher/tasks/durable-plans/" + task["task_id"]
        client.post(task_url + "/decision", json={"digest": task["digest"], "approved": True})
        receipt = client.post(task_url + "/execute").json()
        base = f"/api/teacher/students/{self.fixture.student_id}/review-reports"
        report_url = base + "/" + receipt["report_id"]
        exact = client.get(report_url + "/detail")
        self.assertEqual(exact.status_code, 200, exact.text)
        self.assertEqual(exact.json()["content_hash"], receipt["report_hash"])
        self.assertEqual(client.get(task_url + "/execution").json()["report_status"], "draft")
        decision = {"decision": "revision_requested", "note": "需要补充具体沟通意愿与线下核对安排", "checklist_confirmed": False}
        self.assertEqual(client.post(report_url + "/decision", json=decision).status_code, 200)
        self.assertEqual(client.post(report_url + "/decision", json=decision).status_code, 200)
        revised = client.post(base).json()
        self.assertNotEqual(revised["report_id"], receipt["report_id"])
        self.assertEqual(client.get(base + "/latest").json()["report_id"], revised["report_id"])
        self.assertEqual(client.get(report_url + "/detail").json()["status"], "revision_requested")
        restored = client.get(task_url + "/execution").json()
        self.assertEqual(restored["report_id"], receipt["report_id"])
        self.assertEqual(restored["report_status"], "revision_requested")
        self.assertFalse(restored["human_followup_completed"])
        self.assertEqual(self.fixture.teacher_client.get(report_url + "/detail").status_code, 403)
        self.assertEqual(self.fixture.student_client.get(report_url + "/detail").status_code, 403)
        wrong = f"/api/teacher/students/{self.fixture.unassigned_student_id}/review-reports/{receipt['report_id']}/detail"
        self.assertEqual(client.get(wrong).status_code, 404)
        with self.fixture.Session() as db:
            from models import TeacherReviewReportDecision
            self.assertEqual(db.query(TeacherReviewReportDecision).filter_by(report_id=receipt["report_id"]).count(), 1)
            row = db.query(TeacherReviewReport).filter_by(report_id=revised["report_id"]).one()
            row.content_hash = "0" * 64
            db.commit()
        corrupted = base + "/" + revised["report_id"]
        self.assertEqual(client.get(corrupted + "/detail").status_code, 409)
        self.assertEqual(client.get(corrupted + ".pdf").status_code, 409)
        self.assertEqual(client.post(corrupted + "/decision", json=decision).status_code, 409)

    def test_revision_check_waits_for_new_authorized_material_without_generating(self):
        from models import MoodRecord
        from app_time import china_now_naive
        from datetime import timedelta
        client = self.fixture.admin_client
        task = client.post("/api/teacher/tasks/case-plans", json=self.payload).json()
        url = "/api/teacher/tasks/durable-plans/" + task["task_id"]
        self.assertEqual(client.post(url + "/revision-check").status_code, 409)
        client.post(url + "/decision", json={"digest": task["digest"], "approved": True})
        receipt = client.post(url + "/execute").json()
        self.assertEqual(client.post(url + "/revision-check").status_code, 409)
        report_url = f"/api/teacher/students/{self.fixture.student_id}/review-reports/{receipt['report_id']}"
        client.post(report_url + "/decision", json={"decision": "revision_requested", "note": "请补充学生意愿后再核对", "checklist_confirmed": False})
        first = client.post(url + "/revision-check")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["status"], "waiting_for_material")
        self.assertEqual(first.json()["added_record_count"], 0)
        self.assertEqual(client.post(url + "/revision-plans").status_code, 409)
        self.assertEqual(client.post(url + "/revision-check").json(), first.json())
        with self.fixture.Session() as db:
            db.add(MoodRecord(user_id=self.fixture.student_id, mood_score=3, mood_label="平静", content="补充资料唯一标记", created_at=china_now_naive() - timedelta(milliseconds=1)))
            db.commit()
        result = client.post(url + "/revision-check")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["status"], "ready_for_plan_review")
        self.assertEqual(result.json()["added_record_count"], 1)
        self.assertFalse(result.json()["new_plan_created"])
        self.assertNotIn("补充资料唯一标记", result.text)
        with self.fixture.Session() as db:
            self.assertEqual(db.query(TeacherReviewReport).count(), 1)
        self.assertEqual(self.fixture.student_client.post(url + "/revision-check").status_code, 403)
        self.assertEqual(self.fixture.teacher_client.post(url + "/revision-check").status_code, 404)
        self.model.assert_not_awaited()
        data = (Path(self.temp.name) / "checkpoints.sqlite").read_bytes()
        self.assertNotIn("补充资料唯一标记".encode(), data)
        child_response = client.post(url + "/revision-plans")
        self.assertEqual(child_response.status_code, 200, child_response.text)
        child = child_response.json()
        self.assertEqual(child["status"], "waiting_approval")
        self.assertEqual(child["revision"]["parent_report_id"], receipt["report_id"])
        self.assertEqual(client.post(url + "/revision-plans").json()["task_id"], child["task_id"])
        child_url = "/api/teacher/tasks/durable-plans/" + child["task_id"]
        self.assertEqual(client.post(child_url + "/execute").status_code, 409)
        self.assertEqual(client.post(child_url + "/decision", json={"digest": task["digest"], "approved": True}).status_code, 409)
        client.post(child_url + "/decision", json={"digest": child["digest"], "approved": True})
        # Even an in-place edit of the confirmed record invalidates its fingerprint.
        with self.fixture.Session() as db:
            db.query(MoodRecord).filter_by(content="补充资料唯一标记").update({"content": "补充资料发生变化"})
            db.commit()
        self.assertEqual(client.post(child_url + "/execute").status_code, 409)
        with self.fixture.Session() as db:
            self.assertEqual(db.query(TeacherReviewReport).count(), 1)
        replacement = client.post(url + "/revision-plans").json()
        self.assertNotEqual(replacement["task_id"], child["task_id"])
        replacement_url = "/api/teacher/tasks/durable-plans/" + replacement["task_id"]
        client.post(replacement_url + "/decision", json={"digest": replacement["digest"], "approved": True})
        executed = client.post(replacement_url + "/execute")
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(executed.json()["status"], "awaiting_report_review", executed.text)
        self.assertNotEqual(executed.json()["report_id"], receipt["report_id"])
        self.assertEqual(client.get(url + "/execution").json()["report_id"], receipt["report_id"])
        self.assertEqual(client.post(replacement_url + "/execute").json()["report_id"], executed.json()["report_id"])
        with self.fixture.Session() as db:
            self.assertEqual(db.query(TeacherReviewReport).count(), 2)
        self.model.assert_not_awaited()
