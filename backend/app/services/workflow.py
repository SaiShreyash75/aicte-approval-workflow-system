import json
from pathlib import Path
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import Application, StageTransition, EVC, User, Undertaking, Document
from app.services.clock import get_system_time
from app.services.audit import record_audit

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "workflow_rules.json"

def load_workflow_rules() -> dict:
    if not RULES_PATH.exists():
        raise RuntimeError(f"Workflow rules file not found at {RULES_PATH}")
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_stage_config(route_name: str, stage_name: str) -> dict:
    rules = load_workflow_rules()
    routes = rules.get("routes", {})
    route = routes.get(route_name)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route '{route_name}' not defined in workflow_rules.json",
        )
    stage = route.get("stages", {}).get(stage_name)
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stage '{stage_name}' not defined in route '{route_name}'",
        )
    return stage

def generate_case_summary(db: Session, application: Application, action: str, actor: User, remarks: str) -> str:
    """
    Auto-generates a standardized statutory case summary from template.
    """
    sys_time = get_system_time(db)
    inst_name = application.institution.name if application.institution else "N/A"
    inst_code = application.institution.code if application.institution else "N/A"
    region_name = application.institution.region.name if (application.institution and application.institution.region) else "N/A"

    pending_undertakings = db.query(Undertaking).filter(
        Undertaking.application_id == application.id,
        Undertaking.status.in_(["PENDING", "SUBMITTED", "OVERDUE"])
    ).count()

    expiring_docs = db.query(Document).filter(
        Document.institution_id == application.institution_id,
        Document.status.in_(["EXPIRING_SOON", "EXPIRED"])
    ).count()

    summary = (
        f"=====================================================================\n"
        f"AICTE STATUTORY SCRUTINY CASE SUMMARY\n"
        f"=====================================================================\n"
        f"Application Number : {application.application_no}\n"
        f"Institution        : {inst_name} [{inst_code}]\n"
        f"Regional Office    : {region_name}\n"
        f"Application Route  : {application.route_name}\n"
        f"Priority Status    : {application.priority}\n"
        f"Current Stage      : {application.current_stage}\n"
        f"Overall Status     : {application.status}\n"
        f"Stage Due Date     : {application.stage_due_date.strftime('%Y-%m-%d %H:%M UTC') if application.stage_due_date else 'N/A'}\n"
        f"---------------------------------------------------------------------\n"
        f"Latest Action      : {action}\n"
        f"Officer / Member   : {actor.full_name} ({actor.role})\n"
        f"Action Timestamp   : {sys_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Mandatory Remarks  : {remarks}\n"
        f"---------------------------------------------------------------------\n"
        f"Active Undertakings: {pending_undertakings} requiring compliance\n"
        f"Document Alerts    : {expiring_docs} expiring/expired statutory certificates\n"
        f"Statutory Note     : Automated alerts support, but do not replace, statutory\n"
        f"                     scrutiny and decisions of the competent authority.\n"
        f"====================================================================="
    )
    return summary

def auto_queue_evc_if_needed(db: Session, application: Application, actor: User):
    """
    Auto-queues an EVC record if the application enters an EVC stage and has no EVC yet.
    Sets high priority if new institution.
    """
    existing_evc = db.query(EVC).filter(EVC.application_id == application.id).first()
    if not existing_evc:
        is_new = application.institution.is_new_institution if application.institution else False
        evc = EVC(
            application_id=application.id,
            status="QUEUED",
            scheduled_date=None,
            committee_members=None,
            created_at=get_system_time(db)
        )
        db.add(evc)
        db.flush()

        record_audit(
            db=db,
            action="EVC_AUTO_QUEUED",
            entity_type="EVC",
            entity_id=evc.id,
            role=actor.role,
            user_id=actor.id,
            old_state="NONE",
            new_state="QUEUED",
            remarks=f"EVC auto-queued for application {application.application_no} (New Institution Priority: {is_new})"
        )

def execute_stage_transition(
    db: Session,
    application: Application,
    action: str,  # APPROVE, REVERT, REJECT
    actor: User,
    remarks: str
) -> Application:
    """
    Executes a workflow action enforcing:
    1. Role authorization checks (raises 403 Forbidden)
    2. Mandatory remarks validation
    3. Stage progression, SLA due date updates, or status changes
    4. Auto-queuing of EVC
    5. Immutable StageTransition row and AuditLog row creation
    6. Case summary auto-generation
    """
    remarks = (remarks or "").strip()
    if not remarks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mandatory remarks/reason required for this workflow action.",
        )

    current_stage_name = application.current_stage
    stage_cfg = get_stage_config(application.route_name, current_stage_name)
    allowed_roles = stage_cfg.get("allowed_roles", [])

    # Enforce role permission (Admin can override)
    if actor.role not in allowed_roles and actor.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{actor.role}' is not authorized to perform actions at stage '{current_stage_name}'. Allowed: {allowed_roles}",
        )

    sys_time = get_system_time(db)
    old_stage = application.current_stage
    old_status = application.status

    if action == "APPROVE":
        next_stage_name = stage_cfg.get("next_stage")
        if next_stage_name:
            next_cfg = get_stage_config(application.route_name, next_stage_name)
            application.current_stage = next_stage_name
            application.status = "IN_PROGRESS"
            application.stage_entered_at = sys_time
            application.stage_due_date = sys_time + timedelta(days=next_cfg.get("sla_days", 7))
            
            # Check if next stage requires EVC
            if "EVC" in next_stage_name:
                auto_queue_evc_if_needed(db, application, actor)
        else:
            # Final terminal approval
            application.status = "APPROVED"
            application.stage_due_date = None

    elif action == "REVERT":
        target_stage = stage_cfg.get("can_revert_to")
        if not target_stage:
            target_stage = "Re-Scrutiny"
        
        target_cfg = get_stage_config(application.route_name, target_stage)
        application.current_stage = target_stage
        application.status = "REVERTED"
        application.stage_entered_at = sys_time
        application.stage_due_date = sys_time + timedelta(days=target_cfg.get("sla_days", 5))

    elif action == "REJECT":
        application.status = "REJECTED"
        application.stage_due_date = None

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported workflow action '{action}'. Allowed: APPROVE, REVERT, REJECT.",
        )

    application.updated_at = sys_time

    # Record StageTransition row
    transition = StageTransition(
        application_id=application.id,
        from_stage=old_stage,
        to_stage=application.current_stage,
        action=action,
        performed_by_user_id=actor.id,
        remarks=remarks,
        created_at=sys_time
    )
    db.add(transition)

    # Record AuditLog row
    record_audit(
        db=db,
        action=f"WORKFLOW_{action}",
        entity_type="APPLICATION",
        entity_id=application.id,
        role=actor.role,
        user_id=actor.id,
        old_state=f"{old_stage} ({old_status})",
        new_state=f"{application.current_stage} ({application.status})",
        remarks=remarks
    )

    # Auto-generate Case Summary
    application.case_summary = generate_case_summary(db, application, action, actor, remarks)

    db.commit()
    db.refresh(application)
    return application
