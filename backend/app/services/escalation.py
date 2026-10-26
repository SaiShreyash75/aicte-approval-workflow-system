import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.models import (
    Notification, EscalationRule, Application, Undertaking, Document, EVC, User, Institution
)
from app.services.clock import get_system_time
from app.services.audit import record_audit

logger = logging.getLogger("aicte.escalation")
RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "escalation_rules.json"
EMAIL_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "simulated_emails.log"

def load_escalation_rules_file() -> list[dict]:
    if not RULES_PATH.exists():
        return []
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("rules", [])

def sync_escalation_rules_to_db(db: Session):
    file_rules = load_escalation_rules_file()
    for r in file_rules:
        existing = db.query(EscalationRule).filter(EscalationRule.rule_code == r["rule_code"]).first()
        if not existing:
            new_rule = EscalationRule(
                rule_code=r["rule_code"],
                trigger_type=r["trigger_type"],
                days_offset=r["days_offset"],
                recipient_role=r["recipient_role"],
                escalation_level=r.get("escalation_level", 1),
                channel=r.get("channel", "IN_APP"),
                description=r.get("description", ""),
                is_active=True
            )
            db.add(new_rule)
    db.commit()

def send_simulated_email(recipient_role: str, title: str, message: str, timestamp: datetime):
    line = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}] [SIMULATED EMAIL TO: {recipient_role}] SUBJECT: {title} | BODY: {message}\n"
    try:
        with open(EMAIL_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"Could not write simulated email to log: {e}")
    print(f"\n>> [EMAIL SIMULATION] To: {recipient_role} | Subject: {title}")

def create_notification_if_not_exists(
    db: Session,
    recipient_role: str,
    recipient_user_id: int | None,
    title: str,
    message: str,
    entity_type: str,
    entity_id: int,
    trigger_key: str,
    escalation_level: int,
    rule_code: str,
    channel: str = "IN_APP"
) -> bool:
    """
    Idempotent notification creation using uq_notification_idempotency constraint.
    Writes AuditLog row for every alert/escalation.
    Returns True if notification was newly created, False if already exists.
    """
    rule = db.query(EscalationRule).filter(EscalationRule.rule_code == rule_code).first()
    rule_id = rule.id if rule else None

    # Check if notification already exists
    existing = db.query(Notification).filter(
        Notification.entity_type == entity_type,
        Notification.entity_id == entity_id,
        Notification.rule_id == rule_id,
        Notification.trigger_key == trigger_key
    ).first()
    if existing:
        return False

    sys_time = get_system_time(db)
    notif = Notification(
        recipient_role=recipient_role,
        recipient_user_id=recipient_user_id,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        rule_id=rule_id,
        trigger_key=trigger_key,
        escalation_level=escalation_level,
        channel=channel,
        is_read=False,
        is_closed=False,
        created_at=sys_time
    )
    db.add(notif)
    try:
        db.commit()
        db.refresh(notif)
    except IntegrityError:
        db.rollback()
        return False

    # Audit the alert creation / escalation
    action_name = "ALERT_CREATED" if escalation_level == 1 else f"ALERT_ESCALATED_L{escalation_level}"
    record_audit(
        db=db,
        action=action_name,
        entity_type="NOTIFICATION",
        entity_id=notif.id,
        role="SYSTEM_SCHEDULER",
        user_id=None,
        new_state=f"Level {escalation_level} alert sent to {recipient_role} (Key: {trigger_key})",
        remarks=f"{title}: {message}"
    )

    if channel in ("EMAIL", "ALL"):
        send_simulated_email(recipient_role, title, message, sys_time)

    return True

def close_alerts_for_entity(
    db: Session,
    entity_type: str,
    entity_id: int,
    resolution_reason: str,
    actor_role: str = "SYSTEM_SCHEDULER",
    actor_user_id: int | None = None
) -> int:
    """
    Closes open alerts for an entity when the underlying compliance issue is resolved.
    Writes AuditLog entry for every closure.
    """
    sys_time = get_system_time(db)
    active_alerts = db.query(Notification).filter(
        Notification.entity_type == entity_type,
        Notification.entity_id == entity_id,
        Notification.is_closed == False
    ).all()

    closed_count = 0
    for notif in active_alerts:
        notif.is_closed = True
        notif.closed_at = sys_time
        closed_count += 1

        record_audit(
            db=db,
            action="ALERT_CLOSED",
            entity_type="NOTIFICATION",
            entity_id=notif.id,
            role=actor_role,
            user_id=actor_user_id,
            old_state="ACTIVE",
            new_state="CLOSED",
            remarks=f"Alert '{notif.title}' closed. Reason: {resolution_reason}"
        )

    if closed_count > 0:
        db.commit()
    return closed_count

def has_notification_at_level(db: Session, entity_type: str, entity_id: int, level: int) -> bool:
    return db.query(Notification).filter(
        Notification.entity_type == entity_type,
        Notification.entity_id == entity_id,
        Notification.escalation_level == level
    ).first() is not None

def scan_and_generate_alerts(db: Session) -> dict:
    """
    Main scan engine: reads ONLY the SystemClock.
    Evaluates:
    - Application stage SLAs (approaching & overdue ladder L2 -> L3 -> L4)
    - EVC due & overdue ladder
    - Undertakings (T-30, T-15, T-7, T-1, & overdue ladder L2 -> L3 -> L4)
    - Document expiry (T-30, T-15, T-7, T-1, & expired ladder L2 -> L3 -> L4)
    Strictly climbs ONE level at a time and is 100% idempotent.
    """
    sync_escalation_rules_to_db(db)
    sys_time = get_system_time(db)
    sys_date = sys_time.date()

    alerts_created = 0

    # 1. SCAN UNDERTAKINGS
    undertakings = db.query(Undertaking).filter(
        Undertaking.status.in_(["PENDING", "SUBMITTED", "OVERDUE"])
    ).all()

    for u in undertakings:
        due_dt = u.due_date
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        
        diff_days = (due_dt.date() - sys_date).days
        app_no = u.application.application_no if u.application else f"App#{u.application_id}"

        if diff_days > 0:
            # Advance reminders (Level 1 to Institution)
            offsets = [(-30, "T-30", "UNDERTAKING_T_30"), (-15, "T-15", "UNDERTAKING_T_15"), (-7, "T-7", "UNDERTAKING_T_7"), (-1, "T-1", "UNDERTAKING_T_1")]
            for neg_offset, key, rule_code in offsets:
                if diff_days <= abs(neg_offset):
                    created = create_notification_if_not_exists(
                        db=db,
                        recipient_role="Institution",
                        recipient_user_id=None,
                        title=f"Undertaking Reminder ({key}): {u.condition_title}",
                        message=f"Mandatory condition for application {app_no} has {diff_days} day(s) remaining. Deadline: {due_dt.strftime('%Y-%m-%d')}.",
                        entity_type="UNDERTAKING",
                        entity_id=u.id,
                        trigger_key=key,
                        escalation_level=1,
                        rule_code=rule_code,
                        channel="ALL" if key == "T-1" else "IN_APP"
                    )
                    if created:
                        alerts_created += 1
        else:
            # Overdue Ladder (L2 -> L3 -> L4)
            days_overdue = abs(diff_days)
            u.status = "OVERDUE"

            # Level 2: Overdue breach -> Regional Officer
            if not has_notification_at_level(db, "UNDERTAKING", u.id, 2):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Regional Officer",
                    recipient_user_id=None,
                    title=f"URGENT Escalation (L2): Undertaking Overdue - {u.condition_title}",
                    message=f"Application {app_no} has breached statutory undertaking deadline by {days_overdue} day(s).",
                    entity_type="UNDERTAKING",
                    entity_id=u.id,
                    trigger_key="OVERDUE_L2",
                    escalation_level=2,
                    rule_code="UNDERTAKING_OVERDUE_L2",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

            # Level 3: 7+ days overdue and Level 2 already issued -> Bureau Officer
            elif days_overdue >= 7 and not has_notification_at_level(db, "UNDERTAKING", u.id, 3):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Bureau Officer",
                    recipient_user_id=None,
                    title=f"HIGH Escalation (L3): Undertaking Overdue 7+ Days - {u.condition_title}",
                    message=f"Application {app_no} undertaking is {days_overdue} days overdue. Regional office escalation pending resolution.",
                    entity_type="UNDERTAKING",
                    entity_id=u.id,
                    trigger_key="OVERDUE_L3",
                    escalation_level=3,
                    rule_code="UNDERTAKING_OVERDUE_L3",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

            # Level 4: 15+ days overdue and Level 3 already issued -> Admin / Higher Authority
            elif days_overdue >= 15 and not has_notification_at_level(db, "UNDERTAKING", u.id, 4):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Admin",
                    recipient_user_id=None,
                    title=f"CRITICAL Apex Escalation (L4): Undertaking Overdue 15+ Days - {u.condition_title}",
                    message=f"Application {app_no} chronic undertaking default ({days_overdue} days). Referred to Higher Authority for statutory show-cause.",
                    entity_type="UNDERTAKING",
                    entity_id=u.id,
                    trigger_key="OVERDUE_L4",
                    escalation_level=4,
                    rule_code="UNDERTAKING_OVERDUE_L4",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

    # 2. SCAN DOCUMENTS (LEASE & VALIDITY)
    documents = db.query(Document).filter(
        Document.status.in_(["VALID", "EXPIRING_SOON", "EXPIRED"])
    ).all()

    for d in documents:
        diff_days = (d.expiry_date - sys_date).days
        inst_name = d.institution.name if d.institution else f"Institution#{d.institution_id}"

        if diff_days > 0:
            if diff_days <= 30:
                d.status = "EXPIRING_SOON"
            offsets = [(-30, "T-30", "DOCUMENT_EXPIRY_T_30"), (-15, "T-15", "DOCUMENT_EXPIRY_T_15"), (-7, "T-7", "DOCUMENT_EXPIRY_T_7"), (-1, "T-1", "DOCUMENT_EXPIRY_T_1")]
            for neg_offset, key, rule_code in offsets:
                if diff_days <= abs(neg_offset):
                    created = create_notification_if_not_exists(
                        db=db,
                        recipient_role="Institution",
                        recipient_user_id=None,
                        title=f"Statutory Document Expiry Alert ({key}): {d.title}",
                        message=f"{d.document_type} for {inst_name} expires in {diff_days} day(s) on {d.expiry_date}. Submit renewal immediately.",
                        entity_type="DOCUMENT",
                        entity_id=d.id,
                        trigger_key=key,
                        escalation_level=1,
                        rule_code=rule_code,
                        channel="ALL" if key == "T-1" else "IN_APP"
                    )
                    if created:
                        alerts_created += 1
        else:
            days_overdue = abs(diff_days)
            d.status = "EXPIRED"

            # Level 2: Expired -> Regional Officer
            if not has_notification_at_level(db, "DOCUMENT", d.id, 2):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Regional Officer",
                    recipient_user_id=None,
                    title=f"URGENT Escalation (L2): Statutory Certificate Expired - {d.title}",
                    message=f"{d.document_type} for {inst_name} expired {days_overdue} day(s) ago without renewal verification.",
                    entity_type="DOCUMENT",
                    entity_id=d.id,
                    trigger_key="EXPIRED_L2",
                    escalation_level=2,
                    rule_code="DOCUMENT_EXPIRED_L2",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

            # Level 3: 7+ days expired -> Bureau Officer
            elif days_overdue >= 7 and not has_notification_at_level(db, "DOCUMENT", d.id, 3):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Bureau Officer",
                    recipient_user_id=None,
                    title=f"HIGH Escalation (L3): Document Expired 7+ Days - {d.title}",
                    message=f"{d.document_type} for {inst_name} has remained expired for {days_overdue} days.",
                    entity_type="DOCUMENT",
                    entity_id=d.id,
                    trigger_key="EXPIRED_L3",
                    escalation_level=3,
                    rule_code="DOCUMENT_EXPIRED_L3",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

            # Level 4: 15+ days expired -> Higher Authority
            elif days_overdue >= 15 and not has_notification_at_level(db, "DOCUMENT", d.id, 4):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Admin",
                    recipient_user_id=None,
                    title=f"CRITICAL Apex Escalation (L4): Statutory Non-Compliance 15+ Days - {d.title}",
                    message=f"Mandatory certificate for {inst_name} expired {days_overdue} days ago. Institute liable for intake reduction / withdrawal.",
                    entity_type="DOCUMENT",
                    entity_id=d.id,
                    trigger_key="EXPIRED_L4",
                    escalation_level=4,
                    rule_code="DOCUMENT_EXPIRED_L4",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

    # 3. SCAN APPLICATION STAGE SLAS
    apps = db.query(Application).filter(
        Application.status == "IN_PROGRESS",
        Application.stage_due_date.isnot(None)
    ).all()

    for app in apps:
        due_dt = app.stage_due_date
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        diff_days = (due_dt.date() - sys_date).days

        if 0 < diff_days <= 2:
            created = create_notification_if_not_exists(
                db=db,
                recipient_role="Regional Officer",
                recipient_user_id=None,
                title=f"Stage SLA Approaching: Application {app.application_no}",
                message=f"Application {app.application_no} at stage '{app.current_stage}' has {diff_days} day(s) before SLA deadline.",
                entity_type="APPLICATION",
                entity_id=app.id,
                trigger_key="STAGE_SLA_APPROACHING",
                escalation_level=1,
                rule_code="STAGE_SLA_APPROACHING",
                channel="IN_APP"
            )
            if created:
                alerts_created += 1
        elif diff_days <= 0:
            days_overdue = abs(diff_days)
            # Level 2 Overdue -> Regional Officer
            if not has_notification_at_level(db, "APPLICATION", app.id, 2):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Regional Officer",
                    recipient_user_id=None,
                    title=f"SLA Breach Escalation (L2): Application {app.application_no}",
                    message=f"Application {app.application_no} has exceeded SLA timeline at stage '{app.current_stage}' by {days_overdue} day(s).",
                    entity_type="APPLICATION",
                    entity_id=app.id,
                    trigger_key="STAGE_SLA_OVERDUE_L2",
                    escalation_level=2,
                    rule_code="STAGE_SLA_OVERDUE_L2",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1
            # Level 3: 7+ days overdue -> Bureau Officer
            elif days_overdue >= 7 and not has_notification_at_level(db, "APPLICATION", app.id, 3):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Bureau Officer",
                    recipient_user_id=None,
                    title=f"HIGH Escalation (L3): Application SLA Overdue 7+ Days",
                    message=f"Application {app.application_no} delayed by {days_overdue} days at stage '{app.current_stage}'. Requires Bureau intervention.",
                    entity_type="APPLICATION",
                    entity_id=app.id,
                    trigger_key="STAGE_SLA_OVERDUE_L3",
                    escalation_level=3,
                    rule_code="STAGE_SLA_OVERDUE_L3",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1
            # Level 4: 15+ days overdue -> Admin / Member Secretary
            elif days_overdue >= 15 and not has_notification_at_level(db, "APPLICATION", app.id, 4):
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Admin",
                    recipient_user_id=None,
                    title=f"CRITICAL Apex Escalation (L4): Application SLA Delayed 15+ Days",
                    message=f"Bottleneck alert: Application {app.application_no} is {days_overdue} days overdue at stage '{app.current_stage}'.",
                    entity_type="APPLICATION",
                    entity_id=app.id,
                    trigger_key="STAGE_SLA_OVERDUE_L4",
                    escalation_level=4,
                    rule_code="STAGE_SLA_OVERDUE_L4",
                    channel="ALL"
                )
                if created:
                    alerts_created += 1

    # 4. SCAN EVC INSPECTIONS
    evcs = db.query(EVC).filter(
        EVC.status.in_(["SCHEDULED", "QUEUED"])
    ).all()

    for evc in evcs:
        app_no = evc.application.application_no if evc.application else f"App#{evc.application_id}"
        if evc.status == "SCHEDULED" and evc.scheduled_date:
            sched_dt = evc.scheduled_date
            if sched_dt.tzinfo is None:
                sched_dt = sched_dt.replace(tzinfo=timezone.utc)
            diff_days = (sched_dt.date() - sys_date).days

            if 0 < diff_days <= 2:
                created = create_notification_if_not_exists(
                    db=db,
                    recipient_role="Committee Member",
                    recipient_user_id=None,
                    title=f"EVC Inspection Due in {diff_days} Day(s): {app_no}",
                    message=f"Scheduled EVC visit for application {app_no} is approaching on {sched_dt.strftime('%Y-%m-%d')}.",
                    entity_type="EVC",
                    entity_id=evc.id,
                    trigger_key="EVC_DUE_WARNING",
                    escalation_level=1,
                    rule_code="EVC_DUE_WARNING",
                    channel="IN_APP"
                )
                if created:
                    alerts_created += 1
            elif diff_days <= 0:
                days_overdue = abs(diff_days)
                if not has_notification_at_level(db, "EVC", evc.id, 2):
                    created = create_notification_if_not_exists(
                        db=db,
                        recipient_role="Regional Officer",
                        recipient_user_id=None,
                        title=f"EVC Report Overdue (L2): {app_no}",
                        message=f"EVC inspection date for {app_no} has passed ({days_overdue} days ago) without report completion.",
                        entity_type="EVC",
                        entity_id=evc.id,
                        trigger_key="EVC_OVERDUE_L2",
                        escalation_level=2,
                        rule_code="EVC_OVERDUE_L2",
                        channel="ALL"
                    )
                    if created:
                        alerts_created += 1
                elif days_overdue >= 5 and not has_notification_at_level(db, "EVC", evc.id, 3):
                    created = create_notification_if_not_exists(
                        db=db,
                        recipient_role="Bureau Officer",
                        recipient_user_id=None,
                        title=f"EVC Inspection Delayed 5+ Days (L3): {app_no}",
                        message=f"Inspection report for {app_no} has not been received after 5+ days.",
                        entity_type="EVC",
                        entity_id=evc.id,
                        trigger_key="EVC_OVERDUE_L3",
                        escalation_level=3,
                        rule_code="EVC_OVERDUE_L3",
                        channel="ALL"
                    )
                    if created:
                        alerts_created += 1

    db.commit()
    return {
        "status": "success",
        "scanned_at": sys_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "alerts_created": alerts_created
    }
