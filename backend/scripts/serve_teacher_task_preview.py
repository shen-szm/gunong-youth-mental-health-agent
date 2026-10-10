"""Loopback-only UI acceptance fixture. Synthetic data, temporary DB, no external AI.

Run: backend/venv/Scripts/python backend/scripts/serve_teacher_task_preview.py
Never use this test harness as a production server.
"""
import sys
import argparse
import tempfile
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import test_teacher_case_access as fixtures
from api.teacher_tasks import router, durable_store
from config import settings
from models import User
from teacher_task_runtime import DurableTeacherPlans
import uvicorn


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8018)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    fixture = fixtures.TeacherCaseAccessTests()
    fixture.setUp()
    settings.ALLOW_EXTERNAL_AI = False
    settings.ALLOW_TEACHER_TASK_PLANNER_AI = False
    settings.ENABLE_TEACHER_DURABLE_PLANS = True
    app = fixture.admin_client.app
    app.include_router(router)

    def authorize(owner):
        with fixture.Session() as db:
            row = db.get(User, owner)
            return bool(row and int(row.is_admin or 0) >= 1)

    with tempfile.TemporaryDirectory(prefix="shengyu-case-ui-") as directory:
        # Unit fixtures use one in-memory connection. Browser requests are
        # concurrent, so copy seed data into a real temporary SQLite database.
        db_path = Path(directory) / "fixture.db"
        source = fixture.engine.raw_connection()
        try:
            with sqlite3.connect(db_path) as destination:
                source.driver_connection.backup(destination)
        finally:
            source.close()
        fixture.engine.dispose()
        fixture.engine = create_engine("sqlite:///" + db_path.as_posix(), connect_args={"check_same_thread": False})
        fixture.Session = sessionmaker(bind=fixture.engine)
        try:
            app.dependency_overrides[durable_store] = lambda: DurableTeacherPlans(directory, authorize)
            uvicorn.run(app, host="127.0.0.1", port=args.port)
        finally:
            fixture.tearDown()
