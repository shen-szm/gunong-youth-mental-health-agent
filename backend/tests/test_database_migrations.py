import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import _migrate_legacy_sensitive_access_logs


class DatabaseMigrationTests(unittest.TestCase):
    def test_legacy_sensitive_access_log_is_preserved_in_new_schema(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO users (id) VALUES (7)"))
            connection.execute(text("""
                CREATE TABLE sensitive_access_logs (
                    id INTEGER PRIMARY KEY,
                    teacher_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    reason VARCHAR(255) NOT NULL,
                    accessed_at DATETIME
                )
            """))
            connection.execute(text("""
                INSERT INTO sensitive_access_logs
                    (id, teacher_id, student_id, reason, accessed_at)
                VALUES (3, 7, 21, 'old reason', '2026-08-01 09:30:00')
            """))

        _migrate_legacy_sensitive_access_logs(engine)

        columns = {column["name"] for column in inspect(engine).get_columns("sensitive_access_logs")}
        self.assertIn("actor_user_id", columns)
        self.assertNotIn("teacher_id", columns)
        with engine.connect() as connection:
            row = connection.execute(text("""
                SELECT id, actor_user_id, action, resource_type, resource_id, result, created_at
                FROM sensitive_access_logs
            """)).one()
        self.assertEqual(row[:6], (3, 7, "legacy_teacher_access", "student", "21", "legacy_imported"))
        self.assertEqual(str(row[6]), "2026-08-01 09:30:00")

        _migrate_legacy_sensitive_access_logs(engine)
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM sensitive_access_logs")).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()
