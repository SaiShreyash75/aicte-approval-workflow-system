from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import Undertaking, Evidence, Document, User
from app.services.clock import get_system_time
from app.services.audit import record_audit

def evaluate_undertaking_status(db: Session, undertaking: Undertaking) -> str:
    """
    Evaluates current status dynamically against virtual SystemClock.
    """
    if undertaking.status in ("VERIFIED", "REJECTED"):
        return undertaking.status

    sys_time = get_system_time(db)
    due_dt = undertaking.due_date
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=sys_time.tzinfo)

    if due_dt < sys_time and undertaking.status != "SUBMITTED":
        return "OVERDUE"
    return undertaking.status

def verify_undertaking(
    db: Session,
    undertaking_id: int,
    action: str,  # VERIFY or REJECT
    remarks: str,
    actor: User
) -> Undertaking:
    undertaking = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
    if not undertaking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Undertaking ID {undertaking_id} not found",
        )

    remarks = (remarks or "").strip()
    if not remarks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Officer remarks are mandatory when verifying/rejecting an undertaking compliance submission.",
        )

    sys_time = get_system_time(db)
    old_status = undertaking.status

    if action == "VERIFY":
        undertaking.status = "VERIFIED"
    elif action == "REJECT":
        undertaking.status = "REJECTED"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification action '{action}'. Use VERIFY or REJECT.",
        )

    undertaking.officer_remarks = remarks
    undertaking.verified_by_user_id = actor.id
    undertaking.updated_at = sys_time

    record_audit(
        db=db,
        action=f"UNDERTAKING_{undertaking.status}",
        entity_type="UNDERTAKING",
        entity_id=undertaking.id,
        role=actor.role,
        user_id=actor.id,
        old_state=old_status,
        new_state=undertaking.status,
        remarks=remarks
    )

    if action == "VERIFY":
        from app.services.escalation import close_alerts_for_entity
        close_alerts_for_entity(
            db=db,
            entity_type="UNDERTAKING",
            entity_id=undertaking.id,
            resolution_reason="Undertaking compliance verified by authorized officer",
            actor_role=actor.role,
            actor_user_id=actor.id
        )

    db.commit()
    db.refresh(undertaking)
    return undertaking

def evaluate_document_validity(db: Session, doc: Document) -> str:
    """
    Evaluates document status against virtual SystemClock.
    Returns: VALID, EXPIRING_SOON, EXPIRED, RENEWAL_SUBMITTED, VERIFIED
    """
    if doc.status in ("RENEWAL_SUBMITTED", "VERIFIED"):
        return doc.status

    sys_date = get_system_time(db).date()
    if doc.expiry_date < sys_date:
        return "EXPIRED"
    elif (doc.expiry_date - sys_date).days <= 30:
        return "EXPIRING_SOON"
    return "VALID"

def verify_document_renewal(
    db: Session,
    document_id: int,
    action: str,  # VERIFY or REJECT
    remarks: str,
    new_expiry_date: date | None,
    actor: User
) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document ID {document_id} not found",
        )

    remarks = (remarks or "").strip()
    if not remarks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Officer remarks are mandatory for document renewal verification.",
        )

    sys_time = get_system_time(db)
    old_state = f"{doc.status} (exp: {doc.expiry_date})"

    if action == "VERIFY":
        doc.status = "VERIFIED"
        if new_expiry_date:
            doc.expiry_date = new_expiry_date
    elif action == "REJECT":
        doc.status = "REJECTED"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification action '{action}'. Use VERIFY or REJECT.",
        )

    doc.verified_by_user_id = actor.id
    doc.remarks = remarks
    doc.updated_at = sys_time

    record_audit(
        db=db,
        action=f"DOCUMENT_{doc.status}",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        role=actor.role,
        user_id=actor.id,
        old_state=old_state,
        new_state=f"{doc.status} (exp: {doc.expiry_date})",
        remarks=remarks
    )

    if action == "VERIFY":
        from app.services.escalation import close_alerts_for_entity
        close_alerts_for_entity(
            db=db,
            entity_type="DOCUMENT",
            entity_id=doc.id,
            resolution_reason="Document renewal verified by authorized officer",
            actor_role=actor.role,
            actor_user_id=actor.id
        )

    db.commit()
    db.refresh(doc)
    return doc
