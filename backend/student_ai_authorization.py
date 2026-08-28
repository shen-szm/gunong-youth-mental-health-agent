from datetime import datetime

from sqlalchemy.orm import Session

from config import settings
from models import StudentExternalAiAuthorization


AUTHORIZATION_VERSION = "teacher-ai-authorization-v1"


def get_student_ai_authorization(db: Session, student_user_id: int) -> StudentExternalAiAuthorization | None:
    return db.query(StudentExternalAiAuthorization).filter(
        StudentExternalAiAuthorization.student_user_id == student_user_id,
    ).first()


def student_ai_authorization_payload(db: Session, student_user_id: int) -> dict:
    row = get_student_ai_authorization(db, student_user_id)
    active = bool(row and row.status == "active" and row.expires_at > datetime.now())
    return {
        "active": active,
        "status": "active" if active else "expired" if row and row.status == "active" else row.status if row else "not_configured",
        "authorized_by_user_id": row.authorized_by_user_id if row else None,
        "basis": row.basis if row else None,
        "statement_version": row.statement_version if row else AUTHORIZATION_VERSION,
        "purpose": row.purpose if row else "student_support_agents",
        "expires_at": row.expires_at.isoformat() if row else None,
    }


def student_external_ai_allowed(db: Session, student_user_id: int) -> bool:
    return bool(
        settings.ALLOW_EXTERNAL_AI
        and settings.ALLOW_STUDENT_EXTERNAL_AI
        and student_ai_authorization_payload(db, student_user_id)["active"]
    )
