from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import EVC, Application, User
from app.services.clock import get_system_time
from app.services.audit import record_audit

def get_evc_by_application(db: Session, application_id: int) -> EVC:
    evc = db.query(EVC).filter(EVC.application_id == application_id).first()
    if not evc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No EVC inspection found for application ID {application_id}"
        )
    return evc

def schedule_evc(
    db: Session,
    application_id: int,
    scheduled_date: datetime,
    committee_members: str,
    actor: User
) -> EVC:
    evc = db.query(EVC).filter(EVC.application_id == application_id).first()
    if not evc:
        # Create queued first if not existing
        evc = EVC(
            application_id=application_id,
            status="QUEUED",
            created_at=get_system_time(db)
        )
        db.add(evc)
        db.flush()

    if scheduled_date.tzinfo is None:
        scheduled_date = scheduled_date.replace(tzinfo=timezone.utc)

    old_state = f"{evc.status} ({evc.scheduled_date})"
    evc.scheduled_date = scheduled_date
    evc.committee_members = committee_members
    evc.status = "SCHEDULED"

    record_audit(
        db=db,
        action="EVC_SCHEDULED",
        entity_type="EVC",
        entity_id=evc.id,
        role=actor.role,
        user_id=actor.id,
        old_state=old_state,
        new_state=f"SCHEDULED for {scheduled_date.isoformat()}",
        remarks=f"Committee allocated: {committee_members}"
    )

    db.commit()
    db.refresh(evc)
    return evc

def complete_evc(
    db: Session,
    application_id: int,
    recommendations: str,
    report_summary: str,
    actor: User
) -> EVC:
    evc = get_evc_by_application(db, application_id)
    if not report_summary.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report summary is mandatory to complete EVC.",
        )

    sys_time = get_system_time(db)
    old_state = evc.status
    evc.status = "COMPLETED"
    evc.recommendations = recommendations
    evc.report_summary = report_summary
    evc.completed_at = sys_time

    record_audit(
        db=db,
        action="EVC_COMPLETED",
        entity_type="EVC",
        entity_id=evc.id,
        role=actor.role,
        user_id=actor.id,
        old_state=old_state,
        new_state=f"COMPLETED ({recommendations})",
        remarks=f"EVC Report finalized: {report_summary[:100]}..."
    )

    from app.services.escalation import close_alerts_for_entity
    close_alerts_for_entity(
        db=db,
        entity_type="EVC",
        entity_id=evc.id,
        resolution_reason="EVC inspection report submitted and completed",
        actor_role=actor.role,
        actor_user_id=actor.id
    )

    db.commit()
    db.refresh(evc)
    return evc

def check_evc_status_overdue(db: Session, evc: EVC) -> dict:
    """
    Checks if an EVC is due or overdue based on virtual SystemClock.
    """
    sys_time = get_system_time(db)
    is_overdue = False
    days_diff = None

    if evc.status == "SCHEDULED" and evc.scheduled_date:
        sched = evc.scheduled_date
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        if sched < sys_time:
            is_overdue = True
            days_diff = (sys_time - sched).days
    elif evc.status == "QUEUED" and evc.application and evc.application.stage_due_date:
        due = evc.application.stage_due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < sys_time:
            is_overdue = True
            days_diff = (sys_time - due).days

    return {
        "is_overdue": is_overdue,
        "days_overdue": days_diff if is_overdue else 0,
        "status": evc.status,
        "priority": evc.application.priority if evc.application else "NORMAL"
    }
