import pytest
import io
import uuid
from datetime import datetime, timezone, timedelta, date
from app.models.models import (
    Application, Institution, User, Undertaking, Document, EVC, StageTransition, AuditLog
)

def test_01_clock_reset(client, auth_tokens):
    """Requirement 1: Reset SystemClock via API and verify it starts from real date."""
    admin_token = auth_tokens["Admin"]
    resp = client.post("/api/admin/time/reset", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_simulated"] is False


def test_02_upload_rejection_security(client, auth_tokens, db_session):
    """Requirement 6: Real upload rejection tests for fake .exe disguised as .pdf, and oversized files."""
    inst_token = auth_tokens["Institution"]

    app_record = db_session.query(Application).first()
    u = Undertaking(
        application_id=app_record.id,
        condition_title="Fire Safety & NOC",
        description="Submit valid Fire Safety certificate for building block B",
        due_date=datetime.now(timezone.utc) + timedelta(days=20),
        status="PENDING",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    # 1. Fake .exe file disguised as .pdf (starts with MZ header)
    fake_exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00Malicious_Payload_Binary"
    files = {"file": ("malicious_payload.pdf", io.BytesIO(fake_exe_content), "application/pdf")}
    resp = client.post(
        f"/api/compliance/undertakings/{u.id}/evidence",
        files=files,
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert resp.status_code == 400
    assert "Executable or prohibited binary signature detected" in resp.json()["detail"] or "does not match" in resp.json()["detail"]

    # 2. Oversized file (> 10MB)
    oversized_content = b"%PDF-1.4 " + (b"X" * (11 * 1024 * 1024))
    files_oversized = {"file": ("large_doc.pdf", io.BytesIO(oversized_content), "application/pdf")}
    resp_large = client.post(
        f"/api/compliance/undertakings/{u.id}/evidence",
        files=files_oversized,
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert resp_large.status_code == 400
    assert "exceeds maximum allowed limit" in resp_large.json()["detail"]

    # 3. Valid PDF upload must succeed
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nValid Fire NOC certificate"
    files_valid = {"file": ("valid_fire_noc.pdf", io.BytesIO(valid_pdf_content), "application/pdf")}
    resp_valid = client.post(
        f"/api/compliance/undertakings/{u.id}/evidence",
        files=files_valid,
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["status"] == "SUBMITTED"
    assert len(data["evidence_files"]) >= 1


def test_03_role_authorization_and_denial(client, auth_tokens, db_session):
    """Requirement 3: Role not allowed for stage must be rejected with 403."""
    inst_token = auth_tokens["Institution"]
    cm_token = auth_tokens["Committee Member"]

    # App at 'Preliminary Scrutiny' (Only Regional Officer or Admin allowed)
    app_record = db_session.query(Application).filter(Application.current_stage == "Preliminary Scrutiny").first()
    assert app_record is not None

    # Test 1: Institution role tries to approve
    resp = client.post(
        f"/api/applications/{app_record.id}/transition",
        json={"action": "APPROVE", "remarks": "Unauthorized self-approval"},
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"]

    # Test 2: Committee Member tries to approve Preliminary Scrutiny
    resp = client.post(
        f"/api/applications/{app_record.id}/transition",
        json={"action": "APPROVE", "remarks": "Committee member attempting early scrutiny"},
        headers={"Authorization": f"Bearer {cm_token}"}
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"]


def test_04_mandatory_remarks_enforcement(client, auth_tokens, db_session):
    """Requirement 3: Every transition requires mandatory non-empty remarks."""
    ro_token = auth_tokens["Regional Officer"]
    app_record = db_session.query(Application).filter(Application.current_stage == "Preliminary Scrutiny").first()

    # Empty remarks
    resp = client.post(
        f"/api/applications/{app_record.id}/transition",
        json={"action": "APPROVE", "remarks": "   "},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert resp.status_code == 400
    assert "Mandatory remarks" in resp.json()["detail"]


def test_05_route_only_scrutiny_end_to_end(client, auth_tokens, db_session):
    """Requirement 7: Test 'Only Scrutiny' route end to end with case summary generation."""
    ro_token = auth_tokens["Regional Officer"]
    bo_token = auth_tokens["Bureau Officer"]

    now = datetime.now(timezone.utc)
    unique_no = f"AICTE/TEST/ONLY_SCRUTINY_{uuid.uuid4().hex[:6]}"
    app_scrutiny = Application(
        application_no=unique_no,
        institution_id=1,
        program_type="Management",
        application_type="Extension of Approval",
        route_name="Only Scrutiny",
        current_stage="Preliminary Scrutiny",
        status="IN_PROGRESS",
        priority="NORMAL",
        submitted_at=now,
        stage_entered_at=now,
        stage_due_date=now + timedelta(days=7),
        created_at=now
    )
    db_session.add(app_scrutiny)
    db_session.commit()
    db_session.refresh(app_scrutiny)

    # 1. Preliminary Scrutiny (RO approves -> Scrutiny Committee Review)
    resp1 = client.post(
        f"/api/applications/{app_scrutiny.id}/transition",
        json={"action": "APPROVE", "remarks": "All preliminary documents verified and valid."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["current_stage"] == "Scrutiny Committee Review"
    assert data1["case_summary"] is not None
    assert "AICTE STATUTORY SCRUTINY CASE SUMMARY" in data1["case_summary"]

    # 2. Scrutiny Committee Review (BO approves -> Final Approval)
    resp2 = client.post(
        f"/api/applications/{app_scrutiny.id}/transition",
        json={"action": "APPROVE", "remarks": "Committee appraised and recommended."},
        headers={"Authorization": f"Bearer {bo_token}"}
    )
    assert resp2.status_code == 200
    assert resp2.json()["current_stage"] == "Final Approval"

    # 3. Final Approval (BO approves -> APPROVED status)
    resp3 = client.post(
        f"/api/applications/{app_scrutiny.id}/transition",
        json={"action": "APPROVE", "remarks": "Competent authority granted approval order."},
        headers={"Authorization": f"Bearer {bo_token}"}
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["status"] == "APPROVED"
    assert data3["stage_due_date"] is None


def test_06_revert_flow_to_re_scrutiny(client, auth_tokens, db_session):
    """Requirement 7 & 2: Revert to Re-Scrutiny with mandatory reason, then re-advance."""
    ro_token = auth_tokens["Regional Officer"]

    now = datetime.now(timezone.utc)
    unique_no = f"AICTE/TEST/REVERT_FLOW_{uuid.uuid4().hex[:6]}"
    app_revert = Application(
        application_no=unique_no,
        institution_id=1,
        program_type="Engineering",
        application_type="New Course Addition",
        route_name="Only Scrutiny",
        current_stage="Scrutiny Committee Review",
        status="IN_PROGRESS",
        priority="NORMAL",
        submitted_at=now,
        stage_entered_at=now,
        stage_due_date=now + timedelta(days=7),
        created_at=now
    )
    db_session.add(app_revert)
    db_session.commit()
    db_session.refresh(app_revert)

    # Revert with mandatory reason
    revert_reason = "Affiliation letter from state technical university is missing stamp"
    resp = client.post(
        f"/api/applications/{app_revert.id}/transition",
        json={"action": "REVERT", "remarks": revert_reason},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_stage"] == "Re-Scrutiny"
    assert data["status"] == "REVERTED"
    assert revert_reason in data["case_summary"]

    # Advance from Re-Scrutiny back to Scrutiny Committee Review
    resp_re_advance = client.post(
        f"/api/applications/{app_revert.id}/transition",
        json={"action": "APPROVE", "remarks": "Updated affiliation certificate re-verified."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert resp_re_advance.status_code == 200
    assert resp_re_advance.json()["current_stage"] == "Scrutiny Committee Review"
    assert resp_re_advance.json()["status"] == "IN_PROGRESS"


def test_07_route_scrutiny_plus_evc_and_auto_queue(client, auth_tokens, db_session):
    """Requirements 4 & 7: Test Scrutiny+EVC route, auto-queue EVC, schedule, complete and advance."""
    ro_token = auth_tokens["Regional Officer"]
    cm_token = auth_tokens["Committee Member"]
    bo_token = auth_tokens["Bureau Officer"]

    now = datetime.now(timezone.utc)
    unique_no = f"AICTE/TEST/SCRUTINY_EVC_{uuid.uuid4().hex[:6]}"
    app_evc_flow = Application(
        application_no=unique_no,
        institution_id=1,
        program_type="Engineering & Technology",
        application_type="Setting up New Technical Campus",
        route_name="Scrutiny+EVC",
        current_stage="Preliminary Scrutiny",
        status="IN_PROGRESS",
        priority="HIGH",
        submitted_at=now,
        stage_entered_at=now,
        stage_due_date=now + timedelta(days=7),
        created_at=now
    )
    db_session.add(app_evc_flow)
    db_session.commit()
    db_session.refresh(app_evc_flow)

    # 1. Preliminary Scrutiny approved -> advances to EVC Queue
    resp1 = client.post(
        f"/api/applications/{app_evc_flow.id}/transition",
        json={"action": "APPROVE", "remarks": "Preliminary scrutiny cleared. Forwarding to EVC."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert resp1.status_code == 200
    assert resp1.json()["current_stage"] == "EVC Queue"

    # Verify EVC auto-queued
    evc_record = db_session.query(EVC).filter(EVC.application_id == app_evc_flow.id).first()
    assert evc_record is not None
    assert evc_record.status == "QUEUED"

    # 2. Schedule EVC
    inspect_date = now + timedelta(days=4)
    sched_resp = client.post(
        f"/api/evc/{app_evc_flow.id}/schedule",
        json={
            "scheduled_date": inspect_date.isoformat(),
            "committee_members": "Dr. V. K. Bansal (IIT Delhi), Dr. M. P. Singh (NIT Kurukshetra)"
        },
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert sched_resp.status_code == 200
    assert sched_resp.json()["status"] == "SCHEDULED"

    # RO advances workflow to 'EVC Inspection'
    client.post(
        f"/api/applications/{app_evc_flow.id}/transition",
        json={"action": "APPROVE", "remarks": "EVC schedule confirmed with institute."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )

    # 3. Committee Member completes inspection report
    complete_resp = client.post(
        f"/api/evc/{app_evc_flow.id}/complete",
        json={
            "recommendations": "RECOMMENDED",
            "report_summary": "Infrastructure, laboratories, and computer centers meet AICTE norms completely."
        },
        headers={"Authorization": f"Bearer {cm_token}"}
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "COMPLETED"

    # 4. RO advances to Regional Committee Review
    resp_rcr = client.post(
        f"/api/applications/{app_evc_flow.id}/transition",
        json={"action": "APPROVE", "remarks": "EVC recommendations accepted by RO."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert resp_rcr.status_code == 200
    assert resp_rcr.json()["current_stage"] == "Regional Committee Review"

    # 5. BO advances to Final Approval
    resp_fa = client.post(
        f"/api/applications/{app_evc_flow.id}/transition",
        json={"action": "APPROVE", "remarks": "Forwarded to competent authority."},
        headers={"Authorization": f"Bearer {bo_token}"}
    )
    assert resp_fa.status_code == 200
    assert resp_fa.json()["current_stage"] == "Final Approval"

    # 6. Final Approval granted
    resp_fin = client.post(
        f"/api/applications/{app_evc_flow.id}/transition",
        json={"action": "APPROVE", "remarks": "Letter of Approval (LoA) issued."},
        headers={"Authorization": f"Bearer {bo_token}"}
    )
    assert resp_fin.status_code == 200
    assert resp_fin.json()["status"] == "APPROVED"


def test_08_route_only_evc_and_evc_sac_shc(client, auth_tokens, db_session):
    """Requirement 1 & 7: Verify 'Only EVC' and 'EVC+SAC/SHC' routes."""
    ro_token = auth_tokens["Regional Officer"]
    bo_token = auth_tokens["Bureau Officer"]
    cm_token = auth_tokens["Committee Member"]

    # Only EVC Route
    now = datetime.now(timezone.utc)
    unique_no = f"AICTE/TEST/ONLY_EVC_{uuid.uuid4().hex[:6]}"
    app_only_evc = Application(
        application_no=unique_no,
        institution_id=1,
        program_type="Engineering",
        application_type="Surprise Inspection",
        route_name="Only EVC",
        current_stage="EVC Queue",
        status="IN_PROGRESS",
        priority="HIGH",
        submitted_at=now,
        stage_entered_at=now,
        stage_due_date=now + timedelta(days=5),
        created_at=now
    )
    db_session.add(app_only_evc)
    db_session.commit()
    db_session.refresh(app_only_evc)

    # Advance EVC Queue -> EVC Inspection
    client.post(
        f"/api/applications/{app_only_evc.id}/transition",
        json={"action": "APPROVE", "remarks": "Direct EVC scheduled"},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    # Complete EVC
    client.post(
        f"/api/evc/{app_only_evc.id}/complete",
        json={"recommendations": "RECOMMENDED", "report_summary": "Direct inspection passed."},
        headers={"Authorization": f"Bearer {cm_token}"}
    )
    # Advance EVC Inspection -> Final Approval
    client.post(
        f"/api/applications/{app_only_evc.id}/transition",
        json={"action": "APPROVE", "remarks": "Forwarded to final disposition"},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    # Final Approval
    resp = client.post(
        f"/api/applications/{app_only_evc.id}/transition",
        json={"action": "APPROVE", "remarks": "Approved based on direct EVC."},
        headers={"Authorization": f"Bearer {bo_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


def test_09_evc_overdue_detection_with_simulated_clock(client, auth_tokens, db_session):
    """Requirement 4: EVC due/overdue detection using virtual SystemClock."""
    admin_token = auth_tokens["Admin"]
    ro_token = auth_tokens["Regional Officer"]

    client.post("/api/admin/time/reset", headers={"Authorization": f"Bearer {admin_token}"})

    now = datetime.now(timezone.utc)
    unique_no = f"AICTE/TEST/EVC_DELAY_{uuid.uuid4().hex[:6]}"
    app_delay = Application(
        application_no=unique_no,
        institution_id=1,
        program_type="Engineering",
        application_type="Extension",
        route_name="Only EVC",
        current_stage="EVC Queue",
        status="IN_PROGRESS",
        priority="NORMAL",
        submitted_at=now,
        stage_entered_at=now,
        stage_due_date=now + timedelta(days=5),
        created_at=now
    )
    db_session.add(app_delay)
    db_session.commit()
    db_session.refresh(app_delay)

    # Schedule inspection 3 days from now
    inspect_time = now + timedelta(days=3)
    client.post(
        f"/api/evc/{app_delay.id}/schedule",
        json={"scheduled_date": inspect_time.isoformat(), "committee_members": "Prof. Rao"},
        headers={"Authorization": f"Bearer {ro_token}"}
    )

    # Advance virtual clock by 6 days (past the scheduled inspection date)
    client.post(
        "/api/admin/time/advance",
        json={"days": 6},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Query EVCs
    resp = client.get("/api/evc", headers={"Authorization": f"Bearer {ro_token}"})
    assert resp.status_code == 200
    evcs = [e for e in resp.json() if e["application_id"] == app_delay.id]
    assert len(evcs) == 1
    assert evcs[0]["is_overdue"] is True
    assert evcs[0]["days_overdue"] >= 2


def test_10_compliance_undertakings_and_document_validity(client, auth_tokens, db_session):
    """Requirement 5: Undertaking verification & Document (lease) validity and renewal tracking."""
    ro_token = auth_tokens["Regional Officer"]
    inst_token = auth_tokens["Institution"]

    # 1. Undertaking Verification
    u = Undertaking(
        application_id=1,
        condition_title="Faculty Cadre Ratio Test",
        description="Recruit 3 Assistant Professors to meet 1:15 ratio",
        due_date=datetime.now(timezone.utc) + timedelta(days=15),
        status="SUBMITTED",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    # Officer verifies undertaking
    v_resp = client.post(
        f"/api/compliance/undertakings/{u.id}/verify",
        json={"action": "VERIFY", "remarks": "Appointment letters and joining reports verified."},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert v_resp.status_code == 200
    assert v_resp.json()["status"] == "VERIFIED"

    # 2. Document (Land Lease) validity & renewal
    doc = Document(
        institution_id=1,
        application_id=1,
        document_type="Land Lease",
        title="Campus Land 99-Year Registered Lease Agreement",
        issue_date=date(2000, 1, 1),
        expiry_date=date(2026, 11, 10),
        status="VALID",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Query documents
    d_resp = client.get("/api/compliance/documents?institution_id=1", headers={"Authorization": f"Bearer {ro_token}"})
    assert d_resp.status_code == 200
    matching = [d for d in d_resp.json() if d["id"] == doc.id]
    assert len(matching) == 1
    assert matching[0]["status"] in ("EXPIRING_SOON", "VALID")

    # Institution uploads renewal file
    valid_pdf = b"%PDF-1.4\nRenewed 30-year lease agreement signed by Revenue Dept"
    files = {"file": ("renewed_lease.pdf", io.BytesIO(valid_pdf), "application/pdf")}
    renew_resp = client.post(
        f"/api/compliance/documents/{doc.id}/renew",
        data={"new_expiry_date": "2056-11-10"},
        files=files,
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert renew_resp.status_code == 200
    assert renew_resp.json()["status"] == "RENEWAL_SUBMITTED"

    # RO verifies renewal
    verify_resp = client.post(
        f"/api/compliance/documents/{doc.id}/verify",
        json={"action": "VERIFY", "remarks": "Registered lease renewal verified from Land Registry portal", "new_expiry_date": "2056-11-10"},
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "VERIFIED"
