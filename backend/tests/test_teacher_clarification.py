import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_clarification import ClarificationStore, ClarificationConflict


class ClarificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1000
        self.allowed = True
        self.target = {'student_id': 7, 'access_request_id': None}
        def authorize(owner, target):
            if not self.allowed or owner not in (1, 2) or target != self.target:
                raise PermissionError()
        self.store = ClarificationStore(self.temp.name, authorize, lambda: self.now)
        self.goal = '使用30天授权记录准备沟通报告。不要发送消息。'
        self.key = str(uuid4())
        self.receipt = self.store.create(1, self.key, self.goal, self.target)

    def test_reopen_owner_scope_and_original_fingerprint(self):
        self.assertEqual(self.store.get(1, self.receipt['clarification_id']), self.receipt)
        reopened = ClarificationStore(self.temp.name, self.store.authorize, lambda: self.now)
        self.assertEqual(reopened.get(1, self.receipt['clarification_id']), self.receipt)
        with self.assertRaises(LookupError):
            self.store.get(2, self.receipt['clarification_id'])
        with self.assertRaises(ClarificationConflict):
            self.store.create(1, self.key, self.goal + '新增要求', self.target)
        self.assertEqual(self.store.create(1, self.key, self.goal, self.target), self.receipt)
        self.allowed = False
        with self.assertRaises(PermissionError):
            self.store.get(1, self.receipt['clarification_id'])
        with self.assertRaises(PermissionError):
            self.store.decide(1, self.receipt['clarification_id'], self.goal, {'external_delivery': 'prohibited'})

    def test_recorded_classification_never_unlocks_and_is_immutable(self):
        receipt_id = self.receipt['clarification_id']
        for wrong in ({}, {'external_delivery': 'safe'}, {'external_delivery': 'prohibited', 'unknown': 'quoted'}):
            with self.assertRaises(ClarificationConflict):
                self.store.decide(1, receipt_id, self.goal, wrong)
        with self.assertRaises(ClarificationConflict):
            self.store.decide(1, receipt_id, self.goal.replace('不要', ''), {'external_delivery': 'prohibited'})
        result = self.store.decide(1, receipt_id, self.goal, {'external_delivery': 'prohibited'})
        self.assertEqual(result['status'], 'review_recorded_blocked')
        self.assertFalse(result['can_prepare'])
        self.assertFalse(result['execution_started'])
        self.assertEqual(self.store.decide(1, receipt_id, self.goal, {'external_delivery': 'prohibited'}), result)
        with self.assertRaises(ClarificationConflict):
            self.store.decide(1, receipt_id, self.goal, {'external_delivery': 'requested'})
        self.assertNotIn(self.goal.encode(), (Path(self.temp.name) / 'clarifications.sqlite').read_bytes())

    def test_expiry_and_no_unnecessary_records(self):
        with self.assertRaises(ClarificationConflict):
            self.store.create(1, str(uuid4()), '30天授权内沟通报告不检索', self.target)
        self.now += 86400
        with self.assertRaises(LookupError):
            self.store.get(1, self.receipt['clarification_id'])
        with self.assertRaises(LookupError):
            self.store.decide(1, self.receipt['clarification_id'], self.goal, {'external_delivery': 'prohibited'})
