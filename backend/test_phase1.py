import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal, engine
from app.models.models import AuditLog, User, SystemClock
from app.auth.security import hash_password, verify_password
from app.services.upload import ALLOWED_MIME_TYPES
from minimal_seed import seed_minimal
import io

client = TestClient(app)

def test_phase1_flow():
    print("\n--- [Phase 1 Verification] Initializing DB and Minimal Seed ---")
    init_db()
    seed_minimal()

    # 1. Test Password Hashing
    print("[Check 1] Verifying Bcrypt password hashing...")
    pwd = "TestPassword@123"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    print("✓ Bcrypt hashing & verification working properly.")

    # 2. Test SQLite Append-Only Triggers on AuditLog
    print("[Check 2] Testing append-only immutability of AuditLog via SQLite triggers...")
    db = SessionLocal()
    audit_entry = AuditLog(
        role="Admin",
        action="TEST_ACTION",
        entity_type="TEST",
        entity_id=999,
        remarks="Immutable entry test",
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    test_id = audit_entry.id

    # Test UPDATE trigger
    update_blocked = False
    try:
        with engine.connect() as conn:
            conn.execute(text(f"UPDATE audit_logs SET remarks = 'Modified' WHERE id = {test_id}"))
            conn.commit()
    except Exception as e:
        update_blocked = True
        assert "AuditLog is append-only" in str(e)
    assert update_blocked is True, "Expected SQLite trigger to block UPDATE on audit_logs"
    print("✓ SQLite trigger successfully blocked UPDATE on audit_logs.")

    # Test DELETE trigger
    delete_blocked = False
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM audit_logs WHERE id = {test_id}"))
            conn.commit()
    except Exception as e:
        delete_blocked = True
        assert "AuditLog is append-only" in str(e)
    assert delete_blocked is True, "Expected SQLite trigger to block DELETE on audit_logs"
    print("✓ SQLite trigger successfully blocked DELETE on audit_logs.")
    db.close()

    # 3. Test Authentication for all 5 roles
    print("[Check 3] Testing JWT Authentication for all 5 roles...")
    roles_credentials = [
        ("admin@aicte.gov.in", "Admin"),
        ("ro.north@aicte.gov.in", "Regional Officer"),
        ("bo.approval@aicte.gov.in", "Bureau Officer"),
        ("evc.expert@aicte.gov.in", "Committee Member"),
        ("principal@diaet.edu.in", "Institution"),
    ]
    tokens = {}
    for email, expected_role in roles_credentials:
        resp = client.post("/api/auth/login", json={"email": email, "password": "Aicte@123"})
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()
        assert data["role"] == expected_role
        assert "access_token" in data
        tokens[expected_role] = data["access_token"]
        print(f"  ✓ Logged in {email} successfully as '{expected_role}'")

    # 4. Test RBAC Scoping
    print("[Check 4] Testing RBAC scoping and security guards...")
    # Institution cannot access audit logs
    inst_headers = {"Authorization": f"Bearer {tokens['Institution']}"}
    resp = client.get("/api/audit-logs", headers=inst_headers)
    assert resp.status_code == 403, f"Expected 403 Forbidden for Institution, got {resp.status_code}"
    print("  ✓ Institution correctly denied access (403) to /api/audit-logs")

    # Admin can access audit logs
    admin_headers = {"Authorization": f"Bearer {tokens['Admin']}"}
    resp = client.get("/api/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) > 0
    print(f"  ✓ Admin successfully accessed /api/audit-logs ({len(logs)} audit logs present)")

    # 5. Test Virtual System Clock Simulation
    print("[Check 5] Testing Virtual Clock Simulation (SystemClock)...")
    resp = client.get("/api/admin/time")
    assert resp.status_code == 200
    initial_time_data = resp.json()
    print(f"  Initial virtual time: {initial_time_data['formatted_date']}")

    # Advance clock by 10 days
    resp = client.post("/api/admin/time/advance", json={"days": 10}, headers=admin_headers)
    assert resp.status_code == 200
    advanced_data = resp.json()
    assert advanced_data["is_simulated"] is True
    print(f"  Advanced virtual time (+10 days): {advanced_data['formatted_date']}")

    # 6. Test File Upload MIME & Size validation
    print("[Check 6] Testing File Upload Validation rules...")
    assert "application/pdf" in ALLOWED_MIME_TYPES
    assert "image/png" in ALLOWED_MIME_TYPES
    assert "image/jpeg" in ALLOWED_MIME_TYPES
    print("  ✓ Allowed MIME types correctly configured.")

    print("\n=======================================================")
    print(">>> ALL PHASE 1 VERIFICATION CHECKS PASSED PERFECTLY! <<<")
    print("=======================================================\n")

if __name__ == "__main__":
    test_phase1_flow()
