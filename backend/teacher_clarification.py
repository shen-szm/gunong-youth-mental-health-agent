"""Owner/scope-bound clarification receipts; never an execution authorization.

No raw requirement or student material is stored. Original text must be supplied
again for a decision and match its fingerprint. Logical expiry is 24 hours;
expired rows are physically removed on the next store operation.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import UUID, uuid5, NAMESPACE_URL

from teacher_intent_guard import GUARD_VERSION, assess_intent_risk


class ClarificationConflict(ValueError):
    pass


class ClarificationStore:
    def __init__(self, directory, authorize, clock=time.time):
        self.directory = Path(directory)
        self.authorize = authorize
        self.clock = clock

    @staticmethod
    def fingerprint(goal):
        return hashlib.sha256(goal.encode('utf-8')).hexdigest()

    def _connection(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.directory / 'clarifications.sqlite', timeout=2)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS clarifications (id TEXT PRIMARY KEY, owner INTEGER NOT NULL, body TEXT NOT NULL, expires REAL NOT NULL)')
            db.execute('DELETE FROM clarifications WHERE expires <= ?', (self.clock(),))
            db.commit()
            return db
        except BaseException:
            db.close()
            raise

    def _owned(self, db, owner, receipt_id):
        row = db.execute('SELECT body, expires FROM clarifications WHERE id=? AND owner=?', (str(UUID(receipt_id)), owner)).fetchone()
        if not row or row[1] <= self.clock():
            raise LookupError('clarification not found')
        body = json.loads(row[0])
        self.authorize(owner, body['target'])
        return body

    def create(self, owner, request_id, goal, target):
        self.authorize(owner, target)
        categories = assess_intent_risk(goal)
        if not categories:
            raise ClarificationConflict('no local review required')
        receipt_id = str(uuid5(NAMESPACE_URL, f'teacher-clarification:{owner}:{UUID(request_id)}'))
        body = {'clarification_id': receipt_id, 'goal_sha256': self.fingerprint(goal),
                'guard_version': GUARD_VERSION, 'target': target, 'categories': categories,
                'status': 'pending_review', 'decisions': None, 'can_prepare': False,
                'execution_started': False, 'expires_at': self.clock() + 86400}
        with closing(self._connection()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT body FROM clarifications WHERE id=? AND owner=?', (receipt_id, owner)).fetchone()
            if existing:
                previous = self._owned(db, owner, receipt_id)
                if previous['goal_sha256'] != body['goal_sha256'] or previous['target'] != target:
                    raise ClarificationConflict('request ID reused with different intent')
                return previous
            self.authorize(owner, target)
            db.execute('INSERT INTO clarifications VALUES (?, ?, ?, ?)', (receipt_id, owner, json.dumps(body), body['expires_at']))
        return body

    def get(self, owner, receipt_id):
        with closing(self._connection()) as db:
            return self._owned(db, owner, receipt_id)

    def decide(self, owner, receipt_id, original_goal, decisions):
        with closing(self._connection()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            body = self._owned(db, owner, receipt_id)
            if self.fingerprint(original_goal) != body['goal_sha256'] or body['guard_version'] != GUARD_VERSION:
                raise ClarificationConflict('original requirement or policy changed')
            if set(decisions) != set(body['categories']) or any(value not in {'prohibited', 'requested', 'quoted', 'uncertain'} for value in decisions.values()):
                raise ClarificationConflict('every category needs an explicit classification')
            if body['decisions'] is not None:
                if body['decisions'] != decisions:
                    raise ClarificationConflict('decision already recorded')
                return body
            # Classification is evidence only. Even "prohibited" never lifts
            # the block; semantic validation and execution binding are pending.
            body.update(status='review_recorded_blocked', decisions=decisions, reviewed_at=self.clock())
            self.authorize(owner, body['target'])
            db.execute('UPDATE clarifications SET body=? WHERE id=? AND owner=?', (json.dumps(body), str(UUID(receipt_id)), owner))
        return body
