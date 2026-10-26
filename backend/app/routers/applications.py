from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Application, Institution, User, StageTransition
from app.auth.dependencies import get_current_user
from app.services.workflow import get_stage_config, execute_stage_transition
from app.services.evc_service import check_evc_status_overdue
from app.services.compliance import evaluate_undertaking_status, evaluate_document_validity
from app.services.clock import get_system_time
from app.schemas.schemas import (
    ApplicationMinimalResponse,
    ApplicationDetailResponse,
    WorkflowActionRequest,
    StageTransitionResponse,
    EVCResponse,
    UndertakingResponse,
    DocumentResponse,
    EvidenceResponse
)

router = APIRouter(prefix="/api/applications", tags=["Applications & Workflow"])

@router.get("", response_model=List[ApplicationMinimalResponse])
def get_applications(
    region_id: Optional[int] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Application).join(Institution, Application.institution_id == Institution.id)

    # Scoping by role
    if current_user.role == "Institution":
        if current_user.institution_id:
            query = query.filter(Application.institution_id == current_user.institution_id)
        else:
            return []
    elif current_user.role == "Regional Officer":
        if current_user.region_id:
            query = query.filter(Institution.region_id == current_user.region_id)
    elif current_user.role == "Committee Member":
        from app.models.models import EVC
        cleaned_name = current_user.full_name.split('(')[0].strip()
        name_parts = cleaned_name.split()
        key_fragment = name_parts[-1] if len(name_parts) > 1 else cleaned_name
        query = query.join(EVC, Application.id == EVC.application_id).filter(
            (EVC.committee_members.ilike(f"%{key_fragment}%")) |
            (EVC.committee_members.ilike(f"%{current_user.email}%"))
        )

    if region_id and current_user.role in ("Bureau Officer", "Admin"):
        query = query.filter(Institution.region_id == region_id)
    if stage:
        query = query.filter(Application.current_stage == stage)
    if status:
        query = query.filter(Application.status == status)

    apps = query.order_by(Application.id.desc()).all()

    result = []
    for app in apps:
        result.append(ApplicationMinimalResponse(
            id=app.id,
            application_no=app.application_no,
            institution_id=app.institution_id,
            institution_name=app.institution.name if app.institution else None,
            route_name=app.route_name,
            current_stage=app.current_stage,
            status=app.status,
            priority=app.priority,
            submitted_at=app.submitted_at,
            stage_due_date=app.stage_due_date
        ))
    return result

@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID {application_id} not found"
        )

    # Check RBAC access
    if current_user.role == "Institution" and current_user.institution_id != app.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view applications of other institutions."
        )
    if current_user.role == "Regional Officer" and current_user.region_id and app.institution:
        if current_user.region_id != app.institution.region_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view applications outside your regional jurisdiction."
            )

    # Read config for current stage
    stage_cfg = {}
    try:
        stage_cfg = get_stage_config(app.route_name, app.current_stage)
    except Exception:
        pass

    # Build Stage transitions
    transitions = []
    for t in app.stage_transitions:
        transitions.append(StageTransitionResponse(
            id=t.id,
            application_id=t.application_id,
            from_stage=t.from_stage,
            to_stage=t.to_stage,
            action=t.action,
            performed_by_user_id=t.performed_by_user_id,
            performed_by_name=t.performed_by.full_name if t.performed_by else "Officer",
            performed_by_role=t.performed_by.role if t.performed_by else "Officer",
            remarks=t.remarks,
            created_at=t.created_at
        ))

    # Build EVC
    evc_resp = None
    if app.evc:
        overdue_meta = check_evc_status_overdue(db, app.evc)
        evc_resp = EVCResponse(
            id=app.evc.id,
            application_id=app.id,
            application_no=app.application_no,
            institution_name=app.institution.name if app.institution else None,
            scheduled_date=app.evc.scheduled_date,
            committee_members=app.evc.committee_members,
            status=app.evc.status,
            report_summary=app.evc.report_summary,
            recommendations=app.evc.recommendations,
            completed_at=app.evc.completed_at,
            is_overdue=overdue_meta["is_overdue"],
            days_overdue=overdue_meta["days_overdue"],
            priority=app.priority
        )

    # Build Undertakings
    undertakings_resp = []
    for u in app.undertakings:
        current_status = evaluate_undertaking_status(db, u)
        ev_list = [
            EvidenceResponse(
                id=ev.id,
                undertaking_id=ev.undertaking_id,
                file_name=ev.file_name,
                file_size=ev.file_size,
                mime_type=ev.mime_type,
                uploaded_at=ev.uploaded_at
            ) for ev in u.evidence_files
        ]
        undertakings_resp.append(UndertakingResponse(
            id=u.id,
            application_id=u.application_id,
            condition_title=u.condition_title,
            description=u.description,
            due_date=u.due_date,
            status=current_status,
            officer_remarks=u.officer_remarks,
            evidence_files=ev_list,
            created_at=u.created_at
        ))

    # Build Documents
    docs_resp = []
    sys_date = get_system_time(db).date()
    for d in app.documents:
        current_status = evaluate_document_validity(db, d)
        days_left = (d.expiry_date - sys_date).days
        docs_resp.append(DocumentResponse(
            id=d.id,
            institution_id=d.institution_id,
            application_id=d.application_id,
            document_type=d.document_type,
            title=d.title,
            issue_date=d.issue_date,
            expiry_date=d.expiry_date,
            file_name=d.file_name,
            status=current_status,
            days_to_expiry=days_left,
            remarks=d.remarks,
            created_at=d.created_at
        ))

    return ApplicationDetailResponse(
        id=app.id,
        application_no=app.application_no,
        institution_id=app.institution_id,
        institution_name=app.institution.name if app.institution else None,
        institution_code=app.institution.code if app.institution else None,
        region_name=app.institution.region.name if (app.institution and app.institution.region) else None,
        program_type=app.program_type,
        application_type=app.application_type,
        route_name=app.route_name,
        current_stage=app.current_stage,
        status=app.status,
        priority=app.priority,
        submitted_at=app.submitted_at,
        stage_entered_at=app.stage_entered_at,
        stage_due_date=app.stage_due_date,
        case_summary=app.case_summary,
        allowed_roles=stage_cfg.get("allowed_roles", []),
        can_revert_to=stage_cfg.get("can_revert_to"),
        next_stage=stage_cfg.get("next_stage"),
        stage_transitions=transitions,
        evc=evc_resp,
        undertakings=undertakings_resp,
        documents=docs_resp
    )

@router.post("/{application_id}/transition", response_model=ApplicationDetailResponse)
def transition_application(
    application_id: int,
    req: WorkflowActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID {application_id} not found"
        )

    # Check Regional jurisdiction if RO
    if current_user.role == "Regional Officer" and current_user.region_id and app.institution:
        if current_user.region_id != app.institution.region_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Regional Officers can only process applications belonging to their assigned region."
            )

    execute_stage_transition(
        db=db,
        application=app,
        action=req.action.upper(),
        actor=current_user,
        remarks=req.remarks
    )

    return get_application_detail(application_id, db, current_user)
