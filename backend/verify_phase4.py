import sys
from datetime import timezone
from app.database import SessionLocal
from app.models.models import Application, Notification, Undertaking, Document, EVC
from app.services.reports import generate_pendency_data, generate_overdue_cases_data
from app.services.escalation import scan_and_generate_alerts
from app.services.clock import reset_system_time, advance_system_days, get_system_time

def verify_phase4():
    print("\n========================================================")
    print("PHASE 4 VERIFICATION: REPORTS, TOTALS & ESCALATIONS")
    print("========================================================")

    db = SessionLocal()
    try:
        # Reset clock first to real time
        reset_system_time(db)
        base_time = get_system_time(db)

        # 1. Total applications check
        total_apps = db.query(Application).count()
        print(f"[Check 1] Total Seeded Applications: {total_apps}")
        assert total_apps == 40, f"Expected 40 applications, got {total_apps}"
        print("  ✓ Total applications count equals 40.")

        # 2. Pendency report check
        pendency = generate_pendency_data(db)
        approved_count = db.query(Application).filter(Application.status == "APPROVED").count()
        print(f"[Check 2] Pendency Report:")
        print(f"  * Total Active / Pending Applications : {pendency['total_pending']}")
        print(f"  * Final Approved Applications         : {approved_count}")
        print(f"  * Total (Pending + Approved)          : {pendency['total_pending'] + approved_count}")
        assert (pendency['total_pending'] + approved_count) == 40
        print("  ✓ Pendency report totals account for all 40 applications perfectly.")

        # 3. Overdue report check with full component breakdown
        overdue_data = generate_overdue_cases_data(db)
        total_overdue = overdue_data["total_overdue"]

        # Component counts
        sys_date = base_time.date()
        apps_ovd = 0
        for a in db.query(Application).filter(Application.status.in_(["IN_PROGRESS", "REVERTED"])).all():
            if a.stage_due_date:
                due = a.stage_due_date.replace(tzinfo=timezone.utc) if a.stage_due_date.tzinfo is None else a.stage_due_date
                if due < base_time:
                    apps_ovd += 1

        undertakings_ovd = 0
        for u in db.query(Undertaking).filter(Undertaking.status.in_(["PENDING", "SUBMITTED", "OVERDUE"])).all():
            due = u.due_date.replace(tzinfo=timezone.utc) if u.due_date.tzinfo is None else u.due_date
            if due < base_time:
                undertakings_ovd += 1

        docs_expired = 0
        for d in db.query(Document).all():
            if d.expiry_date < sys_date and d.status != "VERIFIED":
                docs_expired += 1

        evcs_ovd = 0
        for e in db.query(EVC).all():
            if e.status == "SCHEDULED" and e.scheduled_date:
                sched = e.scheduled_date.replace(tzinfo=timezone.utc) if e.scheduled_date.tzinfo is None else e.scheduled_date
                if sched < base_time:
                    evcs_ovd += 1
            elif e.status == "QUEUED" and e.application and e.application.stage_due_date:
                due = e.application.stage_due_date.replace(tzinfo=timezone.utc) if e.application.stage_due_date.tzinfo is None else e.application.stage_due_date
                if due < base_time:
                    evcs_ovd += 1

        sum_components = apps_ovd + undertakings_ovd + docs_expired + evcs_ovd

        print(f"[Check 3] Overdue Dossier Report Breakdown:")
        print(f"  * Overdue Applications  : {apps_ovd}")
        print(f"  * Overdue Undertakings  : {undertakings_ovd}")
        print(f"  * Expired Documents     : {docs_expired}")
        print(f"  * Overdue EVCs          : {evcs_ovd}")
        print(f"  * Sum of Components     : {sum_components}")
        print(f"  * Report Total Overdue  : {total_overdue}")

        assert total_overdue == sum_components, f"Mismatch: report has {total_overdue}, but sum of components is {sum_components}"
        print(f"  ✓ Verified: Overdue report count ({total_overdue}) strictly equals the sum of all 4 overdue categories.")

        # 4. Idempotency test on seeded DB
        initial_notifs = db.query(Notification).count()
        print(f"[Check 4] Idempotency Check:")
        print(f"  * Initial Alerts Count in DB: {initial_notifs}")
        rescan = scan_and_generate_alerts(db)
        count_after_rescan = db.query(Notification).count()
        print(f"  * Immediate re-scan created {rescan.get('alerts_created')} alerts.")
        assert count_after_rescan == initial_notifs, "Re-scan must create 0 duplicates"
        print("  ✓ Zero duplicates generated on re-scan.")

        # 5. Advance +7 days live test
        print(f"[Check 5] Advancing Simulated Clock by +7 Days...")
        advance_system_days(db, 7)
        advanced_time = get_system_time(db)
        print(f"  * Advanced Virtual Time: {advanced_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        advance_scan = scan_and_generate_alerts(db)
        new_alerts = advance_scan.get("alerts_created")
        total_after_advance = db.query(Notification).count()
        print(f"  * New Alerts/Escalations Triggered after +7 Days : {new_alerts}")
        print(f"  * Total Alerts in System                       : {total_after_advance}")
        assert new_alerts > 0, "Advancing 7 days must trigger subsequent reminders and ladder escalations"
        print("  ✓ Subsequent reminders and escalations fired cleanly.")

        # Re-scan at +7 days to verify idempotency at advanced time
        rescan_advance = scan_and_generate_alerts(db)
        count_after_advance_rescan = db.query(Notification).count()
        assert count_after_advance_rescan == total_after_advance
        print("  ✓ Advanced virtual clock state is also 100% idempotent (0 duplicates on re-scan).")

        # 6. Reset clock back to current real time
        reset_system_time(db)
        print("\n[Check 6] Resetting SystemClock back to real current date...")
        final_time = get_system_time(db)
        print(f"  * SystemClock reset to: {final_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("  ✓ Clock cleanly restored.")

        print("\n========================================================")
        print(">>> ALL PHASE 4 VERIFICATION CHECKS PASSED PERFECTLY! <<<")
        print("========================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    verify_phase4()
