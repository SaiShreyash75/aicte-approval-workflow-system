import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app.models.models import Region, Institution, User, Application, SystemClock, EscalationRule, AuditLog
from app.auth.security import hash_password
from datetime import datetime, timezone, timedelta

TEST_DB_FILE = Path(__file__).resolve().parent.parent / "test_isolated_aicte.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Remove old test DB if existed
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()

    Base.metadata.create_all(bind=test_engine)

    # Install SQLite append-only triggers on test DB
    with test_engine.connect() as conn:
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'AuditLog is append-only: updates are prohibited');
            END;
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'AuditLog is append-only: deletions are prohibited');
            END;
        """))
        conn.commit()

    # Seed isolated test data
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    clock = SystemClock(id=1, simulated_date=now, is_simulated=False, updated_at=now)
    db.add(clock)

    reg = Region(code="RO-TEST", name="Test Regional Office")
    db.add(reg)
    db.flush()

    inst = Institution(
        code="1-TEST01",
        name="Test Institute of Technology",
        region_id=reg.id,
        address="Campus Road",
        contact_email="test@inst.edu",
        is_new_institution=False,
        created_at=now
    )
    db.add(inst)
    db.flush()

    pwd_hash = hash_password("Aicte@123")
    users = [
        User(email="admin@aicte.gov.in", hashed_password=pwd_hash, full_name="Admin User", role="Admin", created_at=now),
        User(email="ro.north@aicte.gov.in", hashed_password=pwd_hash, full_name="RO User", role="Regional Officer", region_id=reg.id, created_at=now),
        User(email="bo.approval@aicte.gov.in", hashed_password=pwd_hash, full_name="BO User", role="Bureau Officer", created_at=now),
        User(email="evc.expert@aicte.gov.in", hashed_password=pwd_hash, full_name="EVC Expert", role="Committee Member", created_at=now),
        User(email="principal@diaet.edu.in", hashed_password=pwd_hash, full_name="Principal User", role="Institution", institution_id=inst.id, region_id=reg.id, created_at=now),
    ]
    db.add_all(users)
    db.flush()

    app_init = Application(
        application_no="AICTE/TEST/INIT01",
        institution_id=inst.id,
        program_type="Engineering",
        application_type="Extension",
        route_name="Scrutiny+EVC",
        current_stage="Preliminary Scrutiny",
        status="IN_PROGRESS",
        priority="NORMAL",
        submitted_at=now,
        stage_entered_at=now,
        stage_due_date=now + timedelta(days=7),
        created_at=now
    )
    db.add(app_init)

    audit = AuditLog(
        user_id=users[0].id,
        role="Admin",
        action="TEST_INIT",
        entity_type="SYSTEM",
        entity_id=None,
        remarks="Test DB initialized",
        created_at=now
    )
    db.add(audit)

    db.commit()
    db.close()

    # Override FastAPI dependency
    app.dependency_overrides[get_db] = override_get_db

    yield

    # Clean up test DB after all tests run
    app.dependency_overrides.clear()
    test_engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def auth_tokens(client):
    roles = {
        "Admin": "admin@aicte.gov.in",
        "Regional Officer": "ro.north@aicte.gov.in",
        "Bureau Officer": "bo.approval@aicte.gov.in",
        "Committee Member": "evc.expert@aicte.gov.in",
        "Institution": "principal@diaet.edu.in",
    }
    tokens = {}
    for role, email in roles.items():
        resp = client.post("/api/auth/login", json={"email": email, "password": "Aicte@123"})
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        tokens[role] = resp.json()["access_token"]
    return tokens

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
