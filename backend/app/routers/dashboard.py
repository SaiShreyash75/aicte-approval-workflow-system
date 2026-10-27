from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import timezone
from app.database import get_db
from app.models.models import Application, Institution, Region, User, EVC, Undertaking, Document
from app.auth.dependencies import get_current_user
from app.services.clock import get_system_time
from app.services.reports import get_ageing_bucket

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard & Pendency Analytics"])

@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sys_time = get_system_time(db)
    sys_date = sys_time.date()

    app_query = db.query(Application).join(Institution, Application.institution_id == Institution.id)
    u_query = db.query(Undertaking).join(Application, Undertaking.application_id == Application.id).join(Institution, Application.institution_id == Institution.id)
    doc_query = db.query(Document).join(Institution, Document.institution_id == Institution.id)
    evc_query = db.query(EVC).join(Application, EVC.application_id == Application.id).join(Institution, Application.institution_id == Institution.id)

    # Scoping by Role
    if current_user.role == "Institution":
        if current_user.institution_id:
            app_query = app_query.filter(Application.institution_id == current_user.institution_id)
            u_query = u_query.filter(Institution.id == current_user.institution_id)
            doc_query = doc_query.filter(Document.institution_id == current_user.institution_id)
            evc_query = evc_query.filter(Institution.id == current_user.institution_id)
        else:
            app_query = app_query.filter(Application.id == -1)
    elif current_user.role == "Regional Officer":
        if current_user.region_id:
            app_query = app_query.filter(Institution.region_id == current_user.region_id)
            u_query = u_query.filter(Institution.region_id == current_user.region_id)
            doc_query = doc_query.filter(Institution.region_id == current_user.region_id)
            evc_query = evc_query.filter(Institution.region_id == current_user.region_id)
    elif current_user.role == "Committee Member":
        app_query = app_query.join(EVC, Application.id == EVC.application_id).filter(
            EVC.assigned_user_id == current_user.id
        )
        evc_query = evc_query.filter(
            EVC.assigned_user_id == current_user.id
        )

    apps = app_query.all()
    undertakings = u_query.all()
    docs = doc_query.all()
    evcs = evc_query.all()

    # KPI counts
    total_apps = len(apps)
    pending_apps = sum(1 for a in apps if a.status in ("IN_PROGRESS", "REVERTED"))
    approved_apps = sum(1 for a in apps if a.status == "APPROVED")
    rejected_apps = sum(1 for a in apps if a.status == "REJECTED")

    sla_red_count = 0
    sla_amber_count = 0
    ageing = {"0-7 days": 0, "8-15 days": 0, "16-30 days": 0, "30+ days": 0}
    by_stage = {}
    by_region = {}
    by_status = {}
    stage_overdue_counts = {}

    for a in apps:
        stage = a.current_stage
        by_stage[stage] = by_stage.get(stage, 0) + 1
        by_status[a.status] = by_status.get(a.status, 0) + 1

        reg_name = a.institution.region.name if (a.institution and a.institution.region) else "Unknown"
        by_region[reg_name] = by_region.get(reg_name, 0) + 1

        if a.status in ("IN_PROGRESS", "REVERTED"):
            # Ageing
            entered_dt = a.stage_entered_at.replace(tzinfo=timezone.utc) if a.stage_entered_at.tzinfo is None else a.stage_entered_at
            days_pending = max(0, (sys_time - entered_dt).days)
            bucket = get_ageing_bucket(days_pending)
            ageing[bucket] += 1

            # SLA state
            if a.stage_due_date:
                due_dt = a.stage_due_date.replace(tzinfo=timezone.utc) if a.stage_due_date.tzinfo is None else a.stage_due_date
                diff = due_dt - sys_time
                if diff.total_seconds() < 0:
                    sla_red_count += 1
                    stage_overdue_counts[stage] = stage_overdue_counts.get(stage, 0) + 1
                elif 0 <= diff.days <= 2:
                    sla_amber_count += 1

    # Overdue undertakings
    overdue_undertakings_count = 0
    for u in undertakings:
        if u.status in ("PENDING", "SUBMITTED", "OVERDUE"):
            due = u.due_date.replace(tzinfo=timezone.utc) if u.due_date.tzinfo is None else u.due_date
            if due < sys_time:
                overdue_undertakings_count += 1

    # Expiring documents (<30 days or expired)
    expiring_docs_count = 0
    for d in docs:
        if d.status != "VERIFIED":
            if d.expiry_date < sys_date or (d.expiry_date - sys_date).days <= 30:
                expiring_docs_count += 1

    # Overdue EVCs
    overdue_evcs_count = 0
    for e in evcs:
        if e.status == "SCHEDULED" and e.scheduled_date:
            sched = e.scheduled_date.replace(tzinfo=timezone.utc) if e.scheduled_date.tzinfo is None else e.scheduled_date
            if sched < sys_time:
                overdue_evcs_count += 1
        elif e.status == "QUEUED" and e.application and e.application.stage_due_date:
            due = e.application.stage_due_date.replace(tzinfo=timezone.utc) if e.application.stage_due_date.tzinfo is None else e.application.stage_due_date
            if due < sys_time:
                overdue_evcs_count += 1

    # Bottleneck stage identification
    bottleneck_stages = sorted(
        [{"stage": st, "overdue_count": cnt} for st, cnt in stage_overdue_counts.items()],
        key=lambda x: x["overdue_count"],
        reverse=True
    )
    primary_bottleneck = bottleneck_stages[0]["stage"] if bottleneck_stages else "None"

    # Officer Workload
    officer_workload = []
    officers = db.query(User).filter(User.role.in_(["Regional Officer", "Bureau Officer"])).all()
    for off in officers:
        if off.role == "Regional Officer" and off.region_id:
            active_count = db.query(Application).join(Institution).filter(
                Institution.region_id == off.region_id,
                Application.status.in_(["IN_PROGRESS", "REVERTED"])
            ).count()
        else:
            # Bureau officers handle committee reviews and apex approvals
            active_count = db.query(Application).filter(
                Application.current_stage.in_(["Scrutiny Committee Review", "Regional Committee Review", "SAC/SHC Review", "Final Approval"]),
                Application.status.in_(["IN_PROGRESS", "REVERTED"])
            ).count()
        officer_workload.append({
            "officer_name": off.full_name,
            "role": off.role,
            "region": off.region.name if off.region else "National Bureau",
            "active_cases": active_count
        })

    return {
        "user_role": current_user.role,
        "user_name": current_user.full_name,
        "kpi": {
            "total_applications": total_apps,
            "pending_applications": pending_apps,
            "approved_applications": approved_apps,
            "rejected_applications": rejected_apps,
            "sla_red_count": sla_red_count,
            "sla_amber_count": sla_amber_count,
            "overdue_sla_count": sla_red_count,
            "approaching_sla_count": sla_amber_count,
            "overdue_undertakings_count": overdue_undertakings_count,
            "expiring_documents_count": expiring_docs_count,
            "overdue_evcs_count": overdue_evcs_count,
            "primary_bottleneck": primary_bottleneck
        },
        "by_stage": [{"stage": k, "count": v} for k, v in by_stage.items()],
        "by_region": [{"region": k, "count": v} for k, v in by_region.items()],
        "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
        "ageing_buckets": [{"bucket": k, "count": v} for k, v in ageing.items()],
        "officer_workload": officer_workload,
        "bottleneck_stages": bottleneck_stages,
        "disclaimer": "Automated alerts support, but do not replace, statutory scrutiny and decisions of the competent authority."
    }
