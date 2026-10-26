import pytest
from datetime import datetime, timezone, timedelta, date
from app.models.models import Undertaking, Document, Application, Notification, AuditLog, EVC
from app.services.escalation import scan_and_generate_alerts, close_alerts_for_entity
from app.services.clock import reset_system_time, advance_system_days, get_system_time

def test_01_scan_twice_zero_duplicates(client, auth_tokens, db_session):
    """Requirement 8: Rerunning scan or advancing time must produce ZERO duplicate alerts."""
    admin_token = auth_tokens["Admin"]

    # Reset clock
    client.post("/api/admin/time/reset", headers={"Authorization": f"Bearer {admin_token}"})

    # First scan
    resp1 = client.post("/api/admin/time/scan", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp1.status_code == 200
    count_after_scan1 = db_session.query(Notification).count()

    # Second scan immediately with no state change
    resp2 = client.post("/api/admin/time/scan", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp2.status_code == 200
    assert resp2.json()["alerts_created"] == 0
    count_after_scan2 = db_session.query(Notification).count()

    assert count_after_scan1 == count_after_scan2, "Scan must be strictly idempotent: count of notifications must not increase."


def test_02_advance_time_reminders_and_ladder_progression(client, auth_tokens, db_session):
    """
    Requirements 1, 2, 8:
    Advance +7/+15/+30 days -> correct reminders fire at the right offsets.
    Escalation ladder climbs ONE level at a time:
    Level 1 (Institution) -> Level 2 (Regional Officer) -> Level 3 (Bureau Officer) -> Level 4 (Admin/Higher Authority).
    """
    admin_token = auth_tokens["Admin"]

    # Reset clock to real time
    client.post("/api/admin/time/reset", headers={"Authorization": f"Bearer {admin_token}"})
    base_time = get_system_time(db_session)

    # Create an undertaking with due date exactly base_time + 30 days
    u = Undertaking(
        application_id=1,
        condition_title="Accreditation Compliance NBA Phase-II",
        description="Submit NBA Tier-1 compliance documentation for CSE",
        due_date=base_time + timedelta(days=30),
        status="PENDING",
        created_at=base_time
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    # 1. Day 0 (30 days remaining): Scan should create T-30 reminder (Level 1, Institution)
    client.post("/api/admin/time/scan", headers={"Authorization": f"Bearer {admin_token}"})
    notifs_t30 = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.trigger_key == "T-30"
    ).all()
    assert len(notifs_t30) == 1
    assert notifs_t30[0].escalation_level == 1
    assert notifs_t30[0].recipient_role == "Institution"

    # 2. Advance clock by 15 days (15 days remaining): Scan should create T-15 reminder (Level 1, Institution)
    client.post("/api/admin/time/advance", json={"days": 15}, headers={"Authorization": f"Bearer {admin_token}"})
    notifs_t15 = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.trigger_key == "T-15"
    ).all()
    assert len(notifs_t15) == 1
    assert notifs_t15[0].escalation_level == 1

    # 3. Advance clock by 8 days (Total 23 days advanced, 7 days remaining): T-7 reminder
    client.post("/api/admin/time/advance", json={"days": 8}, headers={"Authorization": f"Bearer {admin_token}"})
    notifs_t7 = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.trigger_key == "T-7"
    ).all()
    assert len(notifs_t7) == 1

    # 4. Advance clock by 6 days (Total 29 days advanced, 1 day remaining): T-1 reminder
    client.post("/api/admin/time/advance", json={"days": 6}, headers={"Authorization": f"Bearer {admin_token}"})
    notifs_t1 = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.trigger_key == "T-1"
    ).all()
    assert len(notifs_t1) == 1

    # 5. Advance clock by 2 days (Total 31 days advanced, 1 day overdue!):
    # LADDER CHECK: Only Level 2 (Regional Officer) should be generated! Not Level 3 or 4 yet!
    client.post("/api/admin/time/advance", json={"days": 2}, headers={"Authorization": f"Bearer {admin_token}"})
    l2_notif = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.escalation_level == 2
    ).all()
    assert len(l2_notif) == 1
    assert l2_notif[0].recipient_role == "Regional Officer"

    # Verify Level 3 has NOT triggered yet (only 1 day overdue, threshold is 7 days)
    l3_early = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.escalation_level == 3
    ).all()
    assert len(l3_early) == 0, "Ladder must not jump ahead: Level 3 should not trigger before 7 days overdue."

    # 6. Advance clock by 6 days (Total 37 days advanced, 7 days overdue):
    # LADDER CHECK: Now Level 3 (Bureau Officer) triggers!
    client.post("/api/admin/time/advance", json={"days": 6}, headers={"Authorization": f"Bearer {admin_token}"})
    l3_notif = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.escalation_level == 3
    ).all()
    assert len(l3_notif) == 1
    assert l3_notif[0].recipient_role == "Bureau Officer"

    # Verify Level 4 has NOT triggered yet (threshold is 15 days)
    l4_early = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.escalation_level == 4
    ).all()
    assert len(l4_early) == 0

    # 7. Advance clock by 8 days (Total 45 days advanced, 15 days overdue):
    # LADDER CHECK: Now Level 4 (Admin/Higher Authority) triggers!
    client.post("/api/admin/time/advance", json={"days": 8}, headers={"Authorization": f"Bearer {admin_token}"})
    l4_notif = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u.id,
        Notification.escalation_level == 4
    ).all()
    assert len(l4_notif) == 1
    assert l4_notif[0].recipient_role == "Admin"


def test_03_resolving_issue_closes_related_alerts_and_audits(client, auth_tokens, db_session):
    """Requirement 6 & 8: When the underlying issue is verified, close related alerts and record AuditLog."""
    ro_token = auth_tokens["Regional Officer"]

    # Create an undertaking with open active alerts
    base_time = get_system_time(db_session)
    u_resolve = Undertaking(
        application_id=1,
        condition_title="Fire Safety Certificate Phase-III",
        description="Verify installation of fire hydrants",
        due_date=base_time - timedelta(days=2),  # Already overdue
        status="SUBMITTED",
        created_at=base_time - timedelta(days=10)
    )
    db_session.add(u_resolve)
    db_session.commit()
    db_session.refresh(u_resolve)

    # Generate an alert for this undertaking
    client.post("/api/admin/time/scan", headers={"Authorization": f"Bearer {auth_tokens['Admin']}"})

    open_alerts = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u_resolve.id,
        Notification.is_closed == False
    ).all()
    assert len(open_alerts) > 0, "Expected open alerts before verification"

    # Regional Officer verifies the undertaking
    v_resp = client.post(
        f"/api/compliance/undertakings/{u_resolve.id}/verify",
        json={"action": "VERIFY", "remarks": "On-site photos and Fire Dept certificate verified."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert v_resp.status_code == 200
    assert v_resp.json()["status"] == "VERIFIED"

    # Verify all alerts for this undertaking are now marked closed
    remaining_open = db_session.query(Notification).filter(
        Notification.entity_type == "UNDERTAKING",
        Notification.entity_id == u_resolve.id,
        Notification.is_closed == False
    ).all()
    assert len(remaining_open) == 0, "All alerts must be closed when issue is resolved."

    # Verify AuditLog recorded the closure
    audit_closure = db_session.query(AuditLog).filter(
        AuditLog.action == "ALERT_CLOSED",
        AuditLog.entity_type == "NOTIFICATION"
    ).first()
    assert audit_closure is not None


def test_04_in_app_notifications_api_and_role_scoping(client, auth_tokens, db_session):
    """Requirement 5: Test In-app notifications API list, unread-count, mark-read, and role scoping."""
    inst_token = auth_tokens["Institution"]
    ro_token = auth_tokens["Regional Officer"]

    # 1. Institution checks notifications
    resp_inst = client.get("/api/notifications", headers={"Authorization": f"Bearer {inst_token}"})
    assert resp_inst.status_code == 200
    inst_notifs = resp_inst.json()
    for n in inst_notifs:
        assert n["recipient_role"] == "Institution", "Institution should only see notifications addressed to its role"

    # 2. Regional Officer checks notifications
    resp_ro = client.get("/api/notifications", headers={"Authorization": f"Bearer {ro_token}"})
    assert resp_ro.status_code == 200
    ro_notifs = resp_ro.json()
    for n in ro_notifs:
        assert n["recipient_role"] == "Regional Officer"

    # 3. Unread count check
    resp_unread = client.get("/api/notifications/unread-count", headers={"Authorization": f"Bearer {ro_token}"})
    assert resp_unread.status_code == 200
    assert "unread_count" in resp_unread.json()

    # 4. Mark read
    if len(ro_notifs) > 0:
        target_id = ro_notifs[0]["id"]
        read_resp = client.post(f"/api/notifications/{target_id}/mark-read", headers={"Authorization": f"Bearer {ro_token}"})
        assert read_resp.status_code == 200
        assert read_resp.json()["is_read"] is True


def test_05_reports_api_csv_and_pdf(client, auth_tokens):
    """
    Requirement 7:
    Reports API: CSV for all, PDF (reportlab) for pendency and overdue cases.
    """
    admin_token = auth_tokens["Admin"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Pendency CSV & PDF
    csv_resp = client.get("/api/reports/pendency/csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["Content-Type"]
    assert b"application_no,institution" in csv_resp.content

    pdf_resp = client.get("/api/reports/pendency/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["Content-Type"]
    assert pdf_resp.content.startswith(b"%PDF"), "Pendency PDF export must be a valid PDF document"

    # 2. Overdue cases CSV & PDF
    ovd_csv = client.get("/api/reports/overdue/csv", headers=headers)
    assert ovd_csv.status_code == 200
    assert "text/csv" in ovd_csv.headers["Content-Type"]

    ovd_pdf = client.get("/api/reports/overdue/pdf", headers=headers)
    assert ovd_pdf.status_code == 200
    assert "application/pdf" in ovd_pdf.headers["Content-Type"]
    assert ovd_pdf.content.startswith(b"%PDF"), "Overdue PDF export must be a valid PDF document"

    # 3. EVC Status CSV
    evc_csv = client.get("/api/reports/evc/csv", headers=headers)
    assert evc_csv.status_code == 200
    assert "text/csv" in evc_csv.headers["Content-Type"]

    # 4. Region Performance CSV
    reg_csv = client.get("/api/reports/region-performance/csv", headers=headers)
    assert reg_csv.status_code == 200
    assert "text/csv" in reg_csv.headers["Content-Type"]


def test_06_dashboard_summary_role_scoping(client, auth_tokens):
    """Phase 5 Backend Req: Test role scoping of /api/dashboard/summary."""
    admin_token = auth_tokens["Admin"]
    ro_token = auth_tokens["Regional Officer"]
    inst_token = auth_tokens["Institution"]
    cm_token = auth_tokens["Committee Member"]

    # 1. Admin summary
    resp_admin = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()
    assert "kpi" in data_admin
    assert "ageing_buckets" in data_admin
    assert "bottleneck_stages" in data_admin
    assert "officer_workload" in data_admin
    assert "disclaimer" in data_admin
    assert "statutory scrutiny" in data_admin["disclaimer"]

    # 2. Regional Officer summary
    resp_ro = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {ro_token}"})
    assert resp_ro.status_code == 200
    data_ro = resp_ro.json()
    assert data_ro["user_role"] == "Regional Officer"

    # 3. Institution summary
    resp_inst = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {inst_token}"})
    assert resp_inst.status_code == 200
    data_inst = resp_inst.json()
    assert data_inst["user_role"] == "Institution"
    # Institution's application count must be less than or equal to total admin count
    assert data_inst["kpi"]["total_applications"] <= data_admin["kpi"]["total_applications"]

    # 4. Committee Member summary
    resp_cm = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {cm_token}"})
    assert resp_cm.status_code == 200
    data_cm = resp_cm.json()
    assert data_cm["user_role"] == "Committee Member"
    # Scoped: must NOT be all 40 applications
    assert data_cm["kpi"]["total_applications"] < data_admin["kpi"]["total_applications"]

    # Also test /api/applications scoping for Committee Member
    resp_cm_apps = client.get("/api/applications", headers={"Authorization": f"Bearer {cm_token}"})
    assert resp_cm_apps.status_code == 200
    cm_apps = resp_cm_apps.json()
    assert len(cm_apps) < 40
