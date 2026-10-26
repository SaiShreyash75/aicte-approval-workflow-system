from sqlalchemy.orm import Session
from app.models.models import AuditLog
from app.services.clock import get_system_time

def record_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None,
    role: str,
    user_id: int | None = None,
    old_state: str | None = None,
    new_state: str | None = None,
    remarks: str | None = None,
    ip_address: str | None = None
) -> AuditLog:
    """
    Append-only audit trail logger.
    Direct updates and deletes are prevented both at application API level
    and by the SQLite database trigger.
    """
    audit = AuditLog(
        user_id=user_id,
        role=role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_state=old_state,
        new_state=new_state,
        remarks=remarks,
        ip_address=ip_address,
        created_at=get_system_time(db)
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
