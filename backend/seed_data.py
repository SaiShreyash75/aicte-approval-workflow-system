import sys
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import text
from app.database import engine, Base, SessionLocal, init_db
from app.models.models import (
    Region, Institution, User, Application, StageTransition,
    EVC, Undertaking, Evidence, Document, EscalationRule,
    Notification, AuditLog, SystemClock
)
from app.auth.security import hash_password
from app.services.clock import reset_system_time, get_system_time
from app.services.escalation import scan_and_generate_alerts, sync_escalation_rules_to_db
from app.services.workflow import generate_case_summary

def seed_full():
    print("\n==================================================================")
    print("AICTE AUTOMATION SYSTEM - FULL REALISTIC SEED DATA GENERATOR")
    print("==================================================================")

    # 1. Drop existing tables in demo DB and recreate with append-only triggers
    print("[1/7] Initializing fresh database schema...")
    Base.metadata.drop_all(bind=engine)
    init_db()

    db = SessionLocal()
    try:
        # 2. System Clock
        now = datetime.now(timezone.utc)
        clock = SystemClock(id=1, simulated_date=now, is_simulated=False, updated_at=now)
        db.add(clock)
        db.flush()

        # 3. 4 Regions
        print("[2/7] Seeding 4 Regional Jurisdictions...")
        regions_data = [
            ("RO-NORTH", "Northern Regional Office (Kanpur)"),
            ("RO-WEST", "Western Regional Office (Mumbai)"),
            ("RO-SOUTH", "Southern Regional Office (Chennai)"),
            ("RO-EAST", "Eastern Regional Office (Kolkata)"),
        ]
        regions = {}
        for code, name in regions_data:
            r = Region(code=code, name=name)
            db.add(r)
            db.flush()
            regions[code] = r

        # 4. 15 Realistic Institutions
        print("[3/7] Seeding 15 Technical Institutions...")
        institutions_data = [
            # Northern
            ("1-1001", "Delhi Institute of Advanced Engineering & Technology", "RO-NORTH", "Sector 12, Dwarka, New Delhi", "principal.diaet@aicte.edu", False),
            ("1-1002", "Kanpur Polytechnic & Technical Campus", "RO-NORTH", "GT Road, Kalyanpur, Kanpur", "principal.kptc@aicte.edu", True),
            ("1-1003", "Lucknow Institute of Management Studies", "RO-NORTH", "Vipin Khand, Gomti Nagar, Lucknow", "director.lims@aicte.edu", False),
            ("1-1004", "Chandigarh College of Pharmacy & Research", "RO-NORTH", "Sector 26, Chandigarh", "principal.ccpr@aicte.edu", False),
            # Western
            ("1-2001", "VJTI Affiliated Applied Engineering College", "RO-WEST", "Matunga East, Mumbai, Maharashtra", "principal.vjti@aicte.edu", False),
            ("1-2002", "Pune College of Pharmacy & Innovation", "RO-WEST", "Erandwane, Paud Road, Pune", "principal.pcpi@aicte.edu", False),
            ("1-2003", "Gujarat Institute of Technology & AI", "RO-WEST", "SG Highway, Gota, Ahmedabad", "director.gita@aicte.edu", True),
            ("1-2004", "Vidarbha Regional Polytechnic Institute", "RO-WEST", "Seminary Hills, Nagpur", "principal.vrpi@aicte.edu", False),
            # Southern
            ("1-3001", "Chennai Institute of Advanced Technology", "RO-SOUTH", "Old Mahabalipuram Rd, Chennai", "principal.ciat@aicte.edu", False),
            ("1-3002", "Bangalore School of Business & Management", "RO-SOUTH", "Koramangala 4th Block, Bengaluru", "director.bsbm@aicte.edu", False),
            ("1-3003", "Hyderabad College of Engineering & Robotics", "RO-SOUTH", "Gachibowli, Hyderabad, Telangana", "principal.hcer@aicte.edu", True),
            ("1-3004", "Kerala Academy of Pharmaceutical Sciences", "RO-SOUTH", "Kalamassery, Kochi, Kerala", "principal.kaps@aicte.edu", False),
            # Eastern
            ("1-4001", "Bengal Institute of Technology & Science", "RO-EAST", "Sector V, Salt Lake, Kolkata", "principal.bits@aicte.edu", False),
            ("1-4002", "Patna Institute of Management & Technology", "RO-EAST", "Bailey Road, Patna, Bihar", "director.pimt@aicte.edu", True),
            ("1-4003", "Bhubaneswar College of Pharmacy & Healthcare", "RO-EAST", "Chandrasekharpur, Bhubaneswar", "principal.bcph@aicte.edu", False),
        ]
        institutions = []
        inst_by_code = {}
        for code, name, reg_code, addr, email, is_new in institutions_data:
            inst = Institution(
                code=code,
                name=name,
                region_id=regions[reg_code].id,
                address=addr,
                contact_email=email,
                is_new_institution=is_new,
                created_at=now - timedelta(days= random.randint(60, 300))
            )
            db.add(inst)
            db.flush()
            institutions.append(inst)
            inst_by_code[code] = inst

        # 5. Users across all 5 roles
        print("[4/7] Seeding Role-Based User Accounts (Password: Aicte@123)...")
        default_pwd_hash = hash_password("Aicte@123")
        users_to_create = [
            # Admin
            User(email="admin@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Dr. S. K. Murthy (Member Secretary / Admin)", role="Admin", created_at=now),
            # Regional Officers
            User(email="ro.north@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Dr. Rajesh Sharma (RO Northern Region)", role="Regional Officer", region_id=regions["RO-NORTH"].id, created_at=now),
            User(email="ro.west@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Dr. Anjali Deshmukh (RO Western Region)", role="Regional Officer", region_id=regions["RO-WEST"].id, created_at=now),
            User(email="ro.south@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Dr. K. Swaminathan (RO Southern Region)", role="Regional Officer", region_id=regions["RO-SOUTH"].id, created_at=now),
            User(email="ro.east@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Dr. Bipul Chatterjee (RO Eastern Region)", role="Regional Officer", region_id=regions["RO-EAST"].id, created_at=now),
            # Bureau Officers
            User(email="bo.approval@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Smt. Sunita Verma (Advisor, Approval Bureau)", role="Bureau Officer", created_at=now),
            User(email="bo.policy@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Shri Alok Tandon (Director, Approval Bureau)", role="Bureau Officer", created_at=now),
            # Committee Members
            User(email="evc.expert1@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Prof. K. Ramanathan (EVC Member, IIT Delhi)", role="Committee Member", created_at=now),
            User(email="evc.expert2@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Prof. Meenakshi Sundaram (EVC Member, Anna University)", role="Committee Member", created_at=now),
            User(email="sac.chair@aicte.gov.in", hashed_password=default_pwd_hash, full_name="Justice (Retd.) V. K. Grover (SAC Chairman)", role="Committee Member", created_at=now),
        ]
        # Institution logins for all 15 institutions
        for inst in institutions:
            users_to_create.append(
                User(
                    email=inst.contact_email,
                    hashed_password=default_pwd_hash,
                    full_name=f"Head of Institute - {inst.name[:30]}",
                    role="Institution",
                    institution_id=inst.id,
                    region_id=inst.region_id,
                    created_at=now
                )
            )

        db.add_all(users_to_create)
        db.flush()

        admin_user = users_to_create[0]
        ro_users = {
            regions["RO-NORTH"].id: users_to_create[1],
            regions["RO-WEST"].id: users_to_create[2],
            regions["RO-SOUTH"].id: users_to_create[3],
            regions["RO-EAST"].id: users_to_create[4],
        }
        bo_user = users_to_create[5]
        cm_user1 = users_to_create[7]
        # Committee Member users (indices 7, 8, 9 in users_to_create)
        cm_users = [users_to_create[7], users_to_create[8], users_to_create[9]]
        # Committee Member users (indices 7, 8, 9 in users_to_create)
        cm_users = [users_to_create[7], users_to_create[8], users_to_create[9]]

        # 6. Escalation rules sync
        sync_escalation_rules_to_db(db)

        # 7. 40 Applications spread across ALL 4 routes and ALL stages
        print("[5/7] Seeding 40 Applications with SLA offsets & history...")
        # Routes: Only Scrutiny (10), Scrutiny+EVC (14), EVC+SAC/SHC (8), Only EVC (8)
        # Stages distribution:
        # 6 Preliminary Scrutiny
        # 6 Scrutiny Committee Review
        # 4 Re-Scrutiny (REVERTED)
        # 5 EVC Queue
        # 7 EVC Inspection
        # 4 Regional Committee Review
        # 3 SAC/SHC Review
        # 3 Final Approval (IN_PROGRESS)
        # 2 Final Approval (APPROVED)
        app_matrix = [
            # (app_no, inst_idx, route, stage, status, sla_offset_days, priority_override)
            # 1-6 Preliminary Scrutiny
            ("AICTE/2026/101", 0, "Only Scrutiny", "Preliminary Scrutiny", "IN_PROGRESS", -5, "NORMAL"),  # OVERDUE (5 days past)
            ("AICTE/2026/102", 1, "Scrutiny+EVC", "Preliminary Scrutiny", "IN_PROGRESS", 1, "HIGH"),    # APPROACHING (1 day left)
            ("AICTE/2026/103", 4, "Scrutiny+EVC", "Preliminary Scrutiny", "IN_PROGRESS", 4, "NORMAL"),
            ("AICTE/2026/104", 6, "Scrutiny+EVC", "Preliminary Scrutiny", "IN_PROGRESS", 6, "HIGH"),
            ("AICTE/2026/105", 8, "Only Scrutiny", "Preliminary Scrutiny", "IN_PROGRESS", -2, "NORMAL"),  # OVERDUE (2 days past)
            ("AICTE/2026/106", 12, "Scrutiny+EVC", "Preliminary Scrutiny", "IN_PROGRESS", 2, "NORMAL"),  # APPROACHING (2 days left)

            # 7-12 Scrutiny Committee Review
            ("AICTE/2026/107", 2, "Only Scrutiny", "Scrutiny Committee Review", "IN_PROGRESS", -8, "NORMAL"), # OVERDUE (8 days past)
            ("AICTE/2026/108", 3, "Only Scrutiny", "Scrutiny Committee Review", "IN_PROGRESS", 1, "NORMAL"),  # APPROACHING (1 day left)
            ("AICTE/2026/109", 5, "Only Scrutiny", "Scrutiny Committee Review", "IN_PROGRESS", 5, "NORMAL"),
            ("AICTE/2026/110", 7, "Only Scrutiny", "Scrutiny Committee Review", "IN_PROGRESS", 7, "NORMAL"),
            ("AICTE/2026/111", 9, "Only Scrutiny", "Scrutiny Committee Review", "IN_PROGRESS", -4, "NORMAL"), # OVERDUE (4 days past)
            ("AICTE/2026/112", 13, "Only Scrutiny", "Scrutiny Committee Review", "IN_PROGRESS", 4, "HIGH"),

            # 13-16 Re-Scrutiny (REVERTED)
            ("AICTE/2026/113", 0, "Only Scrutiny", "Re-Scrutiny", "REVERTED", -3, "NORMAL"),  # OVERDUE (3 days past)
            ("AICTE/2026/114", 4, "Scrutiny+EVC", "Re-Scrutiny", "REVERTED", 2, "NORMAL"),   # APPROACHING (2 days left)
            ("AICTE/2026/115", 8, "EVC+SAC/SHC", "Re-Scrutiny", "REVERTED", 4, "NORMAL"),
            ("AICTE/2026/116", 10, "Only EVC", "Re-Scrutiny", "REVERTED", 5, "HIGH"),

            # 17-21 EVC Queue (5 apps)
            ("AICTE/2026/117", 1, "Scrutiny+EVC", "EVC Queue", "IN_PROGRESS", 3, "HIGH"),
            ("AICTE/2026/118", 6, "Scrutiny+EVC", "EVC Queue", "IN_PROGRESS", 4, "HIGH"),
            ("AICTE/2026/119", 10, "EVC+SAC/SHC", "EVC Queue", "IN_PROGRESS", -6, "HIGH"), # OVERDUE (6 days past)
            ("AICTE/2026/120", 11, "Only EVC", "EVC Queue", "IN_PROGRESS", 2, "NORMAL"),
            ("AICTE/2026/121", 13, "Only EVC", "EVC Queue", "IN_PROGRESS", 5, "HIGH"),

            # 22-28 EVC Inspection (7 apps)
            ("AICTE/2026/122", 1, "Scrutiny+EVC", "EVC Inspection", "IN_PROGRESS", 6, "HIGH"),
            ("AICTE/2026/123", 3, "Scrutiny+EVC", "EVC Inspection", "IN_PROGRESS", -4, "NORMAL"), # OVERDUE
            ("AICTE/2026/124", 5, "Scrutiny+EVC", "EVC Inspection", "IN_PROGRESS", 8, "NORMAL"),
            ("AICTE/2026/125", 7, "Only EVC", "EVC Inspection", "IN_PROGRESS", 5, "NORMAL"),
            ("AICTE/2026/126", 9, "EVC+SAC/SHC", "EVC Inspection", "IN_PROGRESS", -10, "NORMAL"), # OVERDUE
            ("AICTE/2026/127", 12, "EVC+SAC/SHC", "EVC Inspection", "IN_PROGRESS", 7, "NORMAL"),
            ("AICTE/2026/128", 14, "Only EVC", "EVC Inspection", "IN_PROGRESS", 9, "NORMAL"),

            # 29-32 Regional Committee Review (4 apps)
            ("AICTE/2026/129", 0, "Scrutiny+EVC", "Regional Committee Review", "IN_PROGRESS", 5, "NORMAL"),
            ("AICTE/2026/130", 4, "Scrutiny+EVC", "Regional Committee Review", "IN_PROGRESS", 6, "NORMAL"),
            ("AICTE/2026/131", 8, "Scrutiny+EVC", "Regional Committee Review", "IN_PROGRESS", -3, "NORMAL"), # OVERDUE
            ("AICTE/2026/132", 12, "Scrutiny+EVC", "Regional Committee Review", "IN_PROGRESS", 4, "NORMAL"),

            # 33-35 SAC/SHC Review (3 apps)
            ("AICTE/2026/133", 2, "EVC+SAC/SHC", "SAC/SHC Review", "IN_PROGRESS", 6, "NORMAL"),
            ("AICTE/2026/134", 6, "EVC+SAC/SHC", "SAC/SHC Review", "IN_PROGRESS", -7, "HIGH"), # OVERDUE
            ("AICTE/2026/135", 10, "EVC+SAC/SHC", "SAC/SHC Review", "IN_PROGRESS", 5, "HIGH"),

            # 36-38 Final Approval IN_PROGRESS (3 apps)
            ("AICTE/2026/136", 3, "Only Scrutiny", "Final Approval", "IN_PROGRESS", 4, "NORMAL"),
            ("AICTE/2026/137", 7, "Only EVC", "Final Approval", "IN_PROGRESS", 3, "NORMAL"),
            ("AICTE/2026/138", 11, "Scrutiny+EVC", "Final Approval", "IN_PROGRESS", -2, "NORMAL"), # OVERDUE

            # 39-40 Final Approval APPROVED (2 apps)
            ("AICTE/2026/139", 5, "Only Scrutiny", "Final Approval", "APPROVED", None, "NORMAL"),
            ("AICTE/2026/140", 9, "Scrutiny+EVC", "Final Approval", "APPROVED", None, "NORMAL"),
        ]

        apps_dict = {}
        for app_no, inst_idx, route, stage, stat, offset, prio in app_matrix:
            inst = institutions[inst_idx]
            sub_dt = now - timedelta(days=random.randint(15, 60))
            ent_dt = now - timedelta(days=random.randint(3, 14))
            due_dt = (now + timedelta(days=offset)) if offset is not None else None

            # Priority inherits HIGH if institution is new
            effective_priority = "HIGH" if inst.is_new_institution or prio == "HIGH" else "NORMAL"

            prog_types = ["Engineering & Technology", "Management (MBA)", "Pharmacy (B.Pharm)", "Polytechnic Diploma", "Computer Applications (MCA)"]
            prog = prog_types[inst_idx % len(prog_types)]

            application = Application(
                application_no=app_no,
                institution_id=inst.id,
                program_type=prog,
                application_type="Extension of Approval" if not inst.is_new_institution else "Setting up New Technical Institution",
                route_name=route,
                current_stage=stage,
                status=stat,
                priority=effective_priority,
                submitted_at=sub_dt,
                stage_entered_at=ent_dt,
                stage_due_date=due_dt,
                created_at=sub_dt,
                updated_at=ent_dt
            )
            db.add(application)
            db.flush()
            apps_dict[app_no] = application

            # Seed Transition history & initial Case summary
            ro_for_inst = ro_users[inst.region_id]
            t_init = StageTransition(
                application_id=application.id,
                from_stage="Application Submitted",
                to_stage=stage,
                action="ADVANCE",
                performed_by_user_id=ro_for_inst.id,
                remarks="Application scrutinized for statutory documentation completeness and processed into workflow stage.",
                created_at=ent_dt
            )
            db.add(t_init)

            # Record initial audit entry
            db.add(AuditLog(
                user_id=ro_for_inst.id,
                role=ro_for_inst.role,
                action="WORKFLOW_TRANSITION",
                entity_type="APPLICATION",
                entity_id=application.id,
                old_state="Application Submitted",
                new_state=f"{stage} ({stat})",
                remarks=f"Workflow advanced to {stage}. Priority: {effective_priority}",
                created_at=ent_dt
            ))

            # Auto-generate statutory case summary
            application.case_summary = generate_case_summary(
                db, application, "ADVANCE", ro_for_inst, "Statutory scrutiny initialized."
            )

        db.flush()

        # 8. Seed EVCs: 5 queued, 4 scheduled, 3 overdue, 3 completed (Total 15)
        print("[6/7] Seeding 15 EVC Inspection Dossiers...")
        evc_specs = [
            # 5 Queued
            ("AICTE/2026/117", "QUEUED", None, None, None, None),
            ("AICTE/2026/118", "QUEUED", None, None, None, None),
            ("AICTE/2026/119", "QUEUED", None, None, None, None),
            ("AICTE/2026/120", "QUEUED", None, None, None, None),
            ("AICTE/2026/121", "QUEUED", None, None, None, None),
            # 4 Scheduled
            ("AICTE/2026/122", "SCHEDULED", now + timedelta(days=4), "Prof. K. Ramanathan (IIT Delhi), Prof. A. Sengupta (Jadavpur)", None, None),
            ("AICTE/2026/124", "SCHEDULED", now + timedelta(days=7), "Dr. S. Ranganathan (NIT Trichy), Dr. P. Mehta (BITS Pilani)", None, None),
            ("AICTE/2026/125", "SCHEDULED", now + timedelta(days=5), "Dr. K. Swaminathan (Anna Univ), Prof. M. Joshi (COEP)", None, None),
            ("AICTE/2026/127", "SCHEDULED", now + timedelta(days=9), "Prof. Bipul Chatterjee (Kolkata), Dr. R. K. Goel (Kanpur)", None, None),
            # 3 Overdue EVCs (scheduled date passed without completion)
            ("AICTE/2026/123", "SCHEDULED", now - timedelta(days=4), "Prof. K. Ramanathan, Dr. Anjali Deshmukh", None, None),
            ("AICTE/2026/126", "SCHEDULED", now - timedelta(days=8), "Dr. P. V. Ramana (NIT Warangal), Dr. U. C. Jha", None, None),
            ("AICTE/2026/128", "SCHEDULED", now - timedelta(days=12), "Prof. Meenakshi Sundaram, Dr. B. N. Roy", None, None),
            # 3 Completed EVCs
            ("AICTE/2026/129", "COMPLETED", now - timedelta(days=6), "Prof. K. Ramanathan, Dr. R. Sharma", "RECOMMENDED", "Physical inspection verified classrooms, computer labs, library holdings, and faculty cadre. Recommended for full sanction."),
            ("AICTE/2026/130", "COMPLETED", now - timedelta(days=10), "Dr. S. K. Gupta, Dr. M. P. Singh", "DEFICIENCY_FOUND", "Shortage of 2 senior faculty in AI & Data Science labs. Institution submitted undertaking for rectification within 60 days."),
            ("AICTE/2026/140", "COMPLETED", now - timedelta(days=18), "Prof. Meenakshi Sundaram, Dr. A. Sengupta", "RECOMMENDED", "All AICTE Approval Process Handbook (APH) infrastructure and land norms fully met."),
        ]

        for evc_idx, (app_no, status_evc, sched_dt, comm, reco, summ) in enumerate(evc_specs):
            app_obj = apps_dict[app_no]
            comp_dt = (now - timedelta(days=2)) if status_evc == "COMPLETED" else None
            assigned_cm = cm_users[evc_idx % len(cm_users)]
            evc_rec = EVC(
                application_id=app_obj.id,
                assigned_user_id=assigned_cm.id,
                scheduled_date=sched_dt,
                committee_members=comm,
                status=status_evc,
                report_summary=summ,
                recommendations=reco,
                completed_at=comp_dt,
                created_at=now - timedelta(days=20)
            )
            db.add(evc_rec)
            db.flush()

            # Audit log for EVC
            db.add(AuditLog(
                user_id=admin_user.id,
                role="SYSTEM_SCHEDULER",
                action=f"EVC_{status_evc}",
                entity_type="EVC",
                entity_id=evc_rec.id,
                new_state=status_evc,
                remarks=f"EVC dossier seeded with status {status_evc} for {app_no}",
                created_at=now - timedelta(days=20)
            ))

        db.flush()

        # 9. Seed Undertakings:
        # Pending due at T-30, T-15, T-7, T-1, 3 already overdue, 3 submitted, 2 verified
        print("[7/7] Seeding Statutory Undertakings & Land Lease Documents...")
        undertakings_specs = [
            # T-30 (due in 28 days)
            ("AICTE/2026/101", "Digital Library DELNET Subscription Renewal", now + timedelta(days=28), "PENDING", None, None),
            # T-15 (due in 14 days)
            ("AICTE/2026/102", "Appointment of Anti-Ragging Committee & Squad", now + timedelta(days=14), "PENDING", None, None),
            # T-7 (due in 6 days)
            ("AICTE/2026/103", "Cadre Ratio Rectification in Mechanical Dept", now + timedelta(days=6), "PENDING", None, None),
            # T-1 (due in 1 day)
            ("AICTE/2026/104", "Installation of Fire Fighting Hydrants in Workshop", now + timedelta(days=1), "PENDING", None, None),
            # 3 Overdue
            ("AICTE/2026/107", "Barrier-Free Environment & Lifts for PwD", now - timedelta(days=5), "OVERDUE", None, None),
            ("AICTE/2026/111", "National Board of Accreditation (NBA) SAR Submission", now - timedelta(days=9), "OVERDUE", None, None),
            ("AICTE/2026/119", "Sewage Treatment Plant (STP) Environmental Clearance", now - timedelta(days=18), "OVERDUE", None, None),
            # 3 Submitted awaiting verification
            ("AICTE/2026/105", "Audited Financial Statements for FY 2025-26", now + timedelta(days=10), "SUBMITTED", None, None),
            ("AICTE/2026/108", "AICTE-Mandated Insurance for Students & Faculty", now + timedelta(days=8), "SUBMITTED", None, None),
            ("AICTE/2026/114", "Establishment of Internal Complaint Committee (ICC)", now + timedelta(days=12), "SUBMITTED", None, None),
            # 2 Verified
            ("AICTE/2026/106", "Recruitment of Qualified Laboratory Technicians", now - timedelta(days=2), "VERIFIED", "Verified appointment letters and joining reports. Norms fulfilled.", ro_users[institutions[12].region_id].id),
            ("AICTE/2026/110", "Solar Power Generation Unit Installation (100 KW)", now - timedelta(days=4), "VERIFIED", "Electricity Board net-metering synchronization certificate verified.", ro_users[institutions[7].region_id].id),
        ]

        for app_no, cond, due_dt, stat_u, off_rem, ver_by in undertakings_specs:
            app_obj = apps_dict[app_no]
            u_obj = Undertaking(
                application_id=app_obj.id,
                condition_title=cond,
                description=f"Statutory condition compliance required as per APH norms for {app_no}.",
                due_date=due_dt,
                status=stat_u,
                officer_remarks=off_rem,
                verified_by_user_id=ver_by,
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(days=2) if stat_u in ("SUBMITTED", "VERIFIED") else now - timedelta(days=30)
            )
            db.add(u_obj)
            db.flush()

            # If submitted or verified, attach dummy evidence file
            if stat_u in ("SUBMITTED", "VERIFIED"):
                ev_file = Evidence(
                    undertaking_id=u_obj.id,
                    file_name=f"compliance_evidence_{u_obj.id}.pdf",
                    file_path=f"uploads/undertakings/compliance_{u_obj.id}.pdf",
                    file_size=1024 * 340,
                    mime_type="application/pdf",
                    uploaded_by_user_id=admin_user.id,
                    uploaded_at=now - timedelta(days=5)
                )
                db.add(ev_file)

            # Audit entry
            db.add(AuditLog(
                user_id=admin_user.id,
                role="Admin",
                action=f"UNDERTAKING_{stat_u}",
                entity_type="UNDERTAKING",
                entity_id=u_obj.id,
                new_state=stat_u,
                remarks=f"Undertaking: {cond} [{stat_u}]",
                created_at=now - timedelta(days=30)
            ))

        db.flush()

        # 10. Seed Documents (Lease & Statutory Validity):
        # 4 Expiring within 30 days, 3 already expired, 2 renewal-submitted, rest valid (10+)
        today = now.date()
        doc_specs = [
            # 4 Expiring within 30 days
            (0, "Land Lease", "Registered 30-Year Campus Land Lease Deed", today - timedelta(days=10950), today + timedelta(days=12), "EXPIRING_SOON"),
            (2, "Fire Safety NOC", "State Fire Department Building Safety Certificate", today - timedelta(days=350), today + timedelta(days=15), "EXPIRING_SOON"),
            (4, "Building Occupancy", "Municipal Corporation Permanent Occupancy Certificate", today - timedelta(days=1800), today + timedelta(days=22), "EXPIRING_SOON"),
            (6, "Pollution Control NOC", "State Pollution Control Board Consent to Operate", today - timedelta(days=700), today + timedelta(days=28), "EXPIRING_SOON"),

            # 3 Already Expired
            (1, "Structural Stability", "PWD Certified Structural Stability Certificate", today - timedelta(days=1825), today - timedelta(days=5), "EXPIRED"),
            (3, "Land Lease", "Sub-Lease Extension Agreement", today - timedelta(days=7300), today - timedelta(days=14), "EXPIRED"),
            (5, "Environmental NOC", "State Environmental Impact Assessment Clearance", today - timedelta(days=1095), today - timedelta(days=25), "EXPIRED"),

            # 2 Renewal Submitted
            (7, "Fire Safety NOC", "Fire Protection & Hydrant Compliance Renewal", today - timedelta(days=365), today - timedelta(days=2), "RENEWAL_SUBMITTED"),
            (9, "Land Lease", "Perpetual 99-Year Lease Deed Renewal Document", today - timedelta(days=15000), today + timedelta(days=5), "RENEWAL_SUBMITTED"),

            # Valid documents (10+)
            (8, "Land Lease", "99-Year Government Granted Land Allotment Order", today - timedelta(days=5000), today + timedelta(days=7300), "VALID"),
            (10, "Building Safety", "National Building Code Safety Audit Report", today - timedelta(days=100), today + timedelta(days=630), "VALID"),
            (11, "Fire Safety NOC", "Fire Brigade Annual Inspection Certificate", today - timedelta(days=50), today + timedelta(days=315), "VALID"),
            (12, "Occupancy Certificate", "Town & Country Planning Approved Occupancy", today - timedelta(days=300), today + timedelta(days=1500), "VALID"),
            (13, "Land Ownership", "Registered Sale Deed & Mutation Record", today - timedelta(days=4000), today + timedelta(days=8000), "VALID"),
            (14, "Water Quality & Sanitisation", "Public Health Engineering Department Clearance", today - timedelta(days=60), today + timedelta(days=305), "VALID"),
            (0, "Lift & Escalator Safety", "State Electrical Inspectorate Safety License", today - timedelta(days=80), today + timedelta(days=285), "VALID"),
            (1, "Electrical Safety Certificate", "Central Electricity Authority Compliance", today - timedelta(days=90), today + timedelta(days=275), "VALID"),
            (2, "Land Lease", "Revenue Authority 50-Year Registered Lease Agreement", today - timedelta(days=3650), today + timedelta(days=5475), "VALID"),
            (3, "Building Occupancy", "Development Authority Part Occupancy Certificate", today - timedelta(days=120), today + timedelta(days=980), "VALID"),
            (4, "Fire Safety NOC", "Provisional Fire NOC for Phase-II Academic Block", today - timedelta(days=40), today + timedelta(days=325), "VALID"),
            (5, "Land Ownership", "Title Clearance & Non-Encumbrance Certificate", today - timedelta(days=1500), today + timedelta(days=6000), "VALID"),
        ]

        for inst_idx, doc_type, title, iss_d, exp_d, stat_d in doc_specs:
            inst_obj = institutions[inst_idx]
            doc_rec = Document(
                institution_id=inst_obj.id,
                application_id=None,
                document_type=doc_type,
                title=title,
                issue_date=iss_d,
                expiry_date=exp_d,
                file_name=f"doc_{inst_obj.code}_{doc_type.replace(' ', '_').lower()}.pdf",
                file_path=f"uploads/documents/{inst_obj.code}_{doc_type.replace(' ', '_').lower()}.pdf",
                status=stat_d,
                remarks=f"Document seeded with status {stat_d}",
                created_at=now - timedelta(days=40)
            )
            db.add(doc_rec)
            db.flush()

            db.add(AuditLog(
                user_id=admin_user.id,
                role="Admin",
                action=f"DOCUMENT_{stat_d}",
                entity_type="DOCUMENT",
                entity_id=doc_rec.id,
                new_state=stat_d,
                remarks=f"Registered {doc_type}: {title} (Expiry: {exp_d})",
                created_at=now - timedelta(days=40)
            ))

        db.commit()

        # 11. Initial Scan to populate alerts based on seeded data
        # Climbs the ladder level by level until initial steady state for current date
        print("\n>> Running initial compliance scans to establish ladder state...")
        scan_result1 = scan_and_generate_alerts(db)
        scan_result2 = scan_and_generate_alerts(db)
        scan_result3 = scan_and_generate_alerts(db)
        total_created = scan_result1.get('alerts_created', 0) + scan_result2.get('alerts_created', 0) + scan_result3.get('alerts_created', 0)
        print(f"   Initial ladder established: {total_created} alerts generated across levels.")

        # 12. Reset clock back to real current time
        reset_system_time(db)
        print("   SystemClock reset to current real date.")

        # 13. Print Summary Tables
        print_summary_tables(db)

    except Exception as e:
        db.rollback()
        print(f"Error during full seed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


def print_summary_tables(db: Session):
    apps = db.query(Application).all()
    regions = db.query(Region).all()
    sys_time = get_system_time(db)
    sys_date = sys_time.date()

    # Route breakdown
    by_route = {}
    by_stage = {}
    by_reg = {}
    overdue_count = 0
    approaching_count = 0

    for a in apps:
        by_route[a.route_name] = by_route.get(a.route_name, 0) + 1
        by_stage[a.current_stage] = by_stage.get(a.current_stage, 0) + 1
        reg_code = a.institution.region.code if (a.institution and a.institution.region) else "Unknown"
        by_reg[reg_code] = by_reg.get(reg_code, 0) + 1

        if a.stage_due_date and a.status in ("IN_PROGRESS", "REVERTED"):
            diff = (a.stage_due_date.replace(tzinfo=timezone.utc) if a.stage_due_date.tzinfo is None else a.stage_due_date) - sys_time
            if diff.total_seconds() < 0:
                overdue_count += 1
            elif 0 <= diff.days <= 2:
                approaching_count += 1

    evcs = db.query(EVC).all()
    evc_counts = {}
    for e in evcs:
        evc_counts[e.status] = evc_counts.get(e.status, 0) + 1

    undertakings = db.query(Undertaking).all()
    u_counts = {}
    for u in undertakings:
        u_counts[u.status] = u_counts.get(u.status, 0) + 1

    docs = db.query(Document).all()
    doc_counts = {}
    for d in docs:
        doc_counts[d.status] = doc_counts.get(d.status, 0) + 1

    notifs_count = db.query(Notification).count()
    audits_count = db.query(AuditLog).count()

    print("\n" + "=" * 68)
    print("DEMO DATABASE SEEDING SUMMARY")
    print("=" * 68)
    print(f"Total Applications Seeded : {len(apps)}")
    print(f"Total Institutions Seeded  : {db.query(Institution).count()} (4 Flagged New Institutions)")
    print(f"Total Regions              : {len(regions)}")
    print(f"Applications Overdue SLA   : {overdue_count} (Highlight Red)")
    print(f"Applications Near SLA      : {approaching_count} (Highlight Amber)")
    print(f"Total EVC Records          : {len(evcs)} (Queued: {evc_counts.get('QUEUED',0)}, Sched: {evc_counts.get('SCHEDULED',0)}, Comp: {evc_counts.get('COMPLETED',0)})")
    print(f"Total Undertakings         : {len(undertakings)} (Pending: {u_counts.get('PENDING',0)}, Overdue: {u_counts.get('OVERDUE',0)}, Sub: {u_counts.get('SUBMITTED',0)}, Ver: {u_counts.get('VERIFIED',0)})")
    print(f"Total Documents Tracked    : {len(docs)} (Expiring: {doc_counts.get('EXPIRING_SOON',0)}, Expired: {doc_counts.get('EXPIRED',0)}, Renewal: {doc_counts.get('RENEWAL_SUBMITTED',0)}, Valid: {doc_counts.get('VALID',0)})")
    print(f"Initial Alerts Generated   : {notifs_count}")
    print(f"Audit Trail Entries        : {audits_count}")

    print("\n--- Route Distribution ---")
    for r, cnt in by_route.items():
        print(f"  * {r:<25} : {cnt} applications")

    print("\n--- Stage Distribution ---")
    for s, cnt in by_stage.items():
        print(f"  * {s:<30} : {cnt} applications")

    print("\n--- Region Distribution ---")
    for reg, cnt in by_reg.items():
        print(f"  * {reg:<25} : {cnt} applications")

    print("\n" + "=" * 68)
    print("DEMO CREDENTIALS FOR ALL 5 ROLES (Password: Aicte@123)")
    print("=" * 68)
    print(f"  1. Admin            : admin@aicte.gov.in")
    print(f"  2. Regional Officer : ro.north@aicte.gov.in (Northern Region)")
    print(f"     Regional Officer : ro.west@aicte.gov.in  (Western Region)")
    print(f"     Regional Officer : ro.south@aicte.gov.in (Southern Region)")
    print(f"     Regional Officer : ro.east@aicte.gov.in  (Eastern Region)")
    print(f"  3. Bureau Officer   : bo.approval@aicte.gov.in")
    print(f"  4. Committee Member : evc.expert1@aicte.gov.in / sac.chair@aicte.gov.in")
    print(f"  5. Institution      : principal.diaet@aicte.edu (DIAET Delhi)")
    print(f"     Institution      : principal.vjti@aicte.edu  (VJTI Mumbai)")
    print(f"     Institution      : director.gita@aicte.edu   (GITA Gujarat - New Inst)")
    print("=" * 68 + "\n")

if __name__ == "__main__":
    seed_full()
