import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import _migrate_assessment_created_at_to_china_time, _migrate_legacy_sensitive_access_logs


class DatabaseMigrationTests(unittest.TestCase):
    def test_assessment_utc_created_at_is_shifted_once_to_china_time(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE student_wellbeing_assessments (
                    id INTEGER PRIMARY KEY,
                    created_at DATETIME
                )
            """))
            connection.execute(text("""
                INSERT INTO student_wellbeing_assessments (id, created_at)
                VALUES (1, '2026-08-30 16:30:00')
            """))

        _migrate_assessment_created_at_to_china_time(engine)
        _migrate_assessment_created_at_to_china_time(engine)

        with engine.connect() as connection:
            created_at = connection.execute(text(
                "SELECT created_at FROM student_wellbeing_assessments WHERE id = 1"
            )).scalar_one()
            migration_count = connection.execute(text(
                "SELECT COUNT(*) FROM app_data_migrations WHERE migration_key = 'alpha29_assessment_created_at_china_time'"
            )).scalar_one()
        self.assertEqual(str(created_at), "2026-08-31 00:30:00")
        self.assertEqual(migration_count, 1)

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
