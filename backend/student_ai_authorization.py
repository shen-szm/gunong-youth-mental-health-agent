from sqlalchemy.orm import Session

from app_time import china_now_naive
from config import settings
from models import StudentExternalAiAuthorization


AUTHORIZATION_VERSION = "teacher-ai-authorization-v1"
PLATFORM_DIRECT_VERSION = "platform-direct-deidentified-v1"


def get_student_ai_authorization(db: Session, student_user_id: int) -> StudentExternalAiAuthorization | None:
    return db.query(StudentExternalAiAuthorization).filter(
        StudentExternalAiAuthorization.student_user_id == student_user_id,
    ).first()


def student_ai_authorization_payload(db: Session, student_user_id: int) -> dict:
    if settings.STUDENT_AI_ACCESS_MODE == "platform_direct":
        active = bool(
            settings.ALLOW_EXTERNAL_AI
            and settings.ALLOW_STUDENT_EXTERNAL_AI
            and settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK
        )
        return {
            "active": active,
            "status": "platform_direct" if active else "disabled",
            "authorized_by_user_id": None,
            "basis": "platform_governance",
            "statement_version": PLATFORM_DIRECT_VERSION,
            "purpose": "student_support_agents_deidentified",
            "expires_at": None,
        }
    row = get_student_ai_authorization(db, student_user_id)
    return _authorization_payload_from_row(row)


def _authorization_payload_from_row(row: StudentExternalAiAuthorization | None) -> dict:
    active = bool(row and row.status == "active" and row.expires_at > china_now_naive())
    return {
        "active": active,
        "status": "active" if active else "expired" if row and row.status == "active" else row.status if row else "not_configured",
        "authorized_by_user_id": row.authorized_by_user_id if row else None,
        "basis": row.basis if row else None,
        "statement_version": row.statement_version if row else AUTHORIZATION_VERSION,
        "purpose": row.purpose if row else "student_support_agents",
        "expires_at": row.expires_at.isoformat() if row else None,
    }


def student_ai_authorization_payloads(db: Session, student_user_ids: list[int]) -> dict[int, dict]:
    if settings.STUDENT_AI_ACCESS_MODE == "platform_direct":
        return {student_id: student_ai_authorization_payload(db, student_id) for student_id in student_user_ids}
    rows = db.query(StudentExternalAiAuthorization).filter(
        StudentExternalAiAuthorization.student_user_id.in_(student_user_ids)
    ).all() if student_user_ids else []
    by_student = {row.student_user_id: row for row in rows}
    return {
        student_id: _authorization_payload_from_row(by_student.get(student_id))
        for student_id in student_user_ids
    }


def student_external_ai_allowed(db: Session, student_user_id: int) -> bool:
    if not settings.ALLOW_EXTERNAL_AI or not settings.ALLOW_STUDENT_EXTERNAL_AI:
        return False
    if settings.STUDENT_AI_ACCESS_MODE == "platform_direct":
        return bool(settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK)
    return bool(student_ai_authorization_payload(db, student_user_id)["active"])


def student_ai_governance_version(db: Session, student_user_id: int) -> str | None:
    payload = student_ai_authorization_payload(db, student_user_id)
    return payload["statement_version"] if payload["active"] else None


def student_ai_audit_basis() -> str:
    return "platform_direct_deidentified" if settings.STUDENT_AI_ACCESS_MODE == "platform_direct" else "teacher_authorized"
