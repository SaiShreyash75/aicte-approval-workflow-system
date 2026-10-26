from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import EVC, Application, Institution, User
from app.auth.dependencies import get_current_user, require_roles
from app.services.evc_service import schedule_evc, complete_evc, check_evc_status_overdue
from app.schemas.schemas import EVCResponse, EVCScheduleRequest, EVCCompleteRequest

router = APIRouter(prefix="/api/evc", tags=["EVC Inspections"])

@router.get("", response_model=List[EVCResponse])
def get_evcs(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(EVC).join(Application, EVC.application_id == Application.id).join(Institution, Application.institution_id == Institution.id)

    # Scoping
    if current_user.role == "Institution":
        if current_user.institution_id:
            query = query.filter(Institution.id == current_user.institution_id)
        else:
            return []
    elif current_user.role == "Regional Officer":
        if current_user.region_id:
            query = query.filter(Institution.region_id == current_user.region_id)

    if status_filter:
        query = query.filter(EVC.status == status_filter)

    evcs = query.order_by(EVC.id.desc()).all()
    result = []
    for evc in evcs:
        overdue_meta = check_evc_status_overdue(db, evc)
        result.append(EVCResponse(
            id=evc.id,
            application_id=evc.application_id,
            application_no=evc.application.application_no if evc.application else None,
            institution_name=evc.application.institution.name if (evc.application and evc.application.institution) else None,
            scheduled_date=evc.scheduled_date,
            committee_members=evc.committee_members,
            status=evc.status,
            report_summary=evc.report_summary,
            recommendations=evc.recommendations,
            completed_at=evc.completed_at,
            is_overdue=overdue_meta["is_overdue"],
            days_overdue=overdue_meta["days_overdue"],
            priority=evc.application.priority if evc.application else "NORMAL"
        ))
    return result

@router.post("/{application_id}/schedule", response_model=EVCResponse)
def schedule_inspection(
    application_id: int,
    req: EVCScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Regional Officer", "Bureau Officer", "Admin"))
):
    evc = schedule_evc(
        db=db,
        application_id=application_id,
        scheduled_date=req.scheduled_date,
        committee_members=req.committee_members,
        actor=current_user
    )
    overdue_meta = check_evc_status_overdue(db, evc)
    return EVCResponse(
        id=evc.id,
        application_id=evc.application_id,
        application_no=evc.application.application_no if evc.application else None,
        institution_name=evc.application.institution.name if (evc.application and evc.application.institution) else None,
        scheduled_date=evc.scheduled_date,
        committee_members=evc.committee_members,
        status=evc.status,
        report_summary=evc.report_summary,
        recommendations=evc.recommendations,
        completed_at=evc.completed_at,
        is_overdue=overdue_meta["is_overdue"],
        days_overdue=overdue_meta["days_overdue"],
        priority=evc.application.priority if evc.application else "NORMAL"
    )

@router.post("/{application_id}/complete", response_model=EVCResponse)
def complete_inspection(
    application_id: int,
    req: EVCCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Committee Member", "Regional Officer", "Bureau Officer", "Admin"))
):
    evc = complete_evc(
        db=db,
        application_id=application_id,
        recommendations=req.recommendations,
        report_summary=req.report_summary,
        actor=current_user
    )
    overdue_meta = check_evc_status_overdue(db, evc)
    return EVCResponse(
        id=evc.id,
        application_id=evc.application_id,
        application_no=evc.application.application_no if evc.application else None,
        institution_name=evc.application.institution.name if (evc.application and evc.application.institution) else None,
        scheduled_date=evc.scheduled_date,
        committee_members=evc.committee_members,
        status=evc.status,
        report_summary=evc.report_summary,
        recommendations=evc.recommendations,
        completed_at=evc.completed_at,
        is_overdue=overdue_meta["is_overdue"],
        days_overdue=overdue_meta["days_overdue"],
        priority=evc.application.priority if evc.application else "NORMAL"
    )
