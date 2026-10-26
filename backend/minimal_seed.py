import sys
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal, init_db
from app.models.models import (
    Region, Institution, User, Application, SystemClock, AuditLog, EscalationRule
)
from app.auth.security import hash_password

def seed_minimal():
    init_db()
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already contains data. Skipping minimal seed.")
            return

        print("Seeding minimal Phase 1 data...")
        now = datetime.now(timezone.utc)

        # 1. System Clock
        clock = SystemClock(id=1, simulated_date=now, is_simulated=False, updated_at=now)
        db.add(clock)

        # 2. 1 Region
        region_north = Region(code="RO-NORTH", name="Northern Regional Office (Kanpur)")
        db.add(region_north)
        db.flush()

        # 3. 1 Institution
        inst = Institution(
            code="1-10001",
            name="Delhi Institute of Advanced Engineering & Technology",
            region_id=region_north.id,
            address="Sector 12, Dwarka, New Delhi 110078",
            contact_email="principal@diaet.edu.in",
            is_new_institution=False,
            created_at=now
        )
        db.add(inst)
        db.flush()

        # 4. 5 Users (one for each role)
        password_hash = hash_password("Aicte@123")
        users = [
            User(
                email="admin@aicte.gov.in",
                hashed_password=password_hash,
                full_name="System Administrator",
                role="Admin",
                created_at=now
            ),
            User(
                email="ro.north@aicte.gov.in",
                hashed_password=password_hash,
                full_name="Dr. Rajesh Sharma (RO North)",
                role="Regional Officer",
                region_id=region_north.id,
                created_at=now
            ),
            User(
                email="bo.approval@aicte.gov.in",
                hashed_password=password_hash,
                full_name="Smt. Sunita Verma (Bureau Officer)",
                role="Bureau Officer",
                created_at=now
            ),
            User(
                email="evc.expert@aicte.gov.in",
                hashed_password=password_hash,
                full_name="Prof. K. Ramanathan (EVC Member)",
                role="Committee Member",
                created_at=now
            ),
            User(
                email="principal@diaet.edu.in",
                hashed_password=password_hash,
                full_name="Dr. A. K. Gupta (Principal, DIAET)",
                role="Institution",
                institution_id=inst.id,
                region_id=region_north.id,
                created_at=now
            ),
        ]
        db.add_all(users)
        db.flush()

        # 5. 3 Applications across different routes/stages
        apps = [
            Application(
                application_no="AICTE/2026/001",
                institution_id=inst.id,
                program_type="Engineering & Technology",
                application_type="Extension of Approval",
                route_name="Scrutiny+EVC",
                current_stage="Preliminary Scrutiny",
                status="IN_PROGRESS",
                priority="NORMAL",
                submitted_at=now - timedelta(days=3),
                stage_entered_at=now - timedelta(days=3),
                stage_due_date=now + timedelta(days=7),
                created_at=now - timedelta(days=3)
            ),
            Application(
                application_no="AICTE/2026/002",
                institution_id=inst.id,
                program_type="Management (MBA)",
                application_type="New Course Addition",
                route_name="Only Scrutiny",
                current_stage="Document Scrutiny",
                status="IN_PROGRESS",
                priority="NORMAL",
                submitted_at=now - timedelta(days=5),
                stage_entered_at=now - timedelta(days=5),
                stage_due_date=now + timedelta(days=5),
                created_at=now - timedelta(days=5)
            ),
            Application(
                application_no="AICTE/2026/003",
                institution_id=inst.id,
                program_type="Engineering & Technology",
                application_type="Increase in Intake",
                route_name="Only EVC",
                current_stage="EVC Inspection",
                status="IN_PROGRESS",
                priority="HIGH",
                submitted_at=now - timedelta(days=2),
                stage_entered_at=now - timedelta(days=2),
                stage_due_date=now + timedelta(days=8),
                created_at=now - timedelta(days=2)
            ),
        ]
        db.add_all(apps)
        db.flush()

        # 6. Basic Escalation Rules for Phase 1/2 seed
        rules = [
            EscalationRule(
                rule_code="STAGE_SLA_BREACH",
                trigger_type="STAGE_SLA",
                days_offset=0,
                recipient_role="Regional Officer",
                escalation_level=1,
                channel="IN_APP",
                description="Triggered when stage reaches SLA deadline"
            ),
            EscalationRule(
                rule_code="UNDERTAKING_T_30",
                trigger_type="UNDERTAKING_DEADLINE",
                days_offset=-30,
                recipient_role="Institution",
                escalation_level=1,
                channel="IN_APP",
                description="Reminder 30 days before undertaking due date"
            ),
            EscalationRule(
                rule_code="LEASE_EXPIRY_T_30",
                trigger_type="LEASE_EXPIRY",
                days_offset=-30,
                recipient_role="Institution",
                escalation_level=1,
                channel="IN_APP",
                description="Advance alert 30 days before lease expiry"
            ),
        ]
        db.add_all(rules)

        # 7. Initial Audit Log
        audit = AuditLog(
            user_id=users[0].id,
            role="Admin",
            action="PHASE_1_INITIAL_SEED",
            entity_type="SYSTEM",
            entity_id=None,
            remarks="Initialized Phase 1 minimal seed: 1 region, 1 institution, 5 users, 3 applications, 3 rules.",
            created_at=now
        )
        db.add(audit)

        db.commit()
        print("Phase 1 minimal seed successfully completed!")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_minimal()
