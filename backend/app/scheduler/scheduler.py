import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.escalation import scan_and_generate_alerts

logger = logging.getLogger("aicte.scheduler")
scheduler = BackgroundScheduler()

def daily_escalation_job():
    """
    Periodic background job running the escalation & compliance scan.
    Reads ONLY the simulated SystemClock.
    """
    logger.info("APScheduler: Running daily compliance and escalation scan...")
    db = SessionLocal()
    try:
        result = scan_and_generate_alerts(db)
        logger.info(f"APScheduler: Scan completed. Alerts created: {result.get('alerts_created', 0)}")
    except Exception as e:
        logger.error(f"APScheduler scan error: {e}", exc_info=True)
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Run daily at 00:00 (and every 30 minutes in background)
        scheduler.add_job(daily_escalation_job, "cron", hour=0, minute=0, id="daily_escalation_scan", replace_existing=True)
        scheduler.add_job(daily_escalation_job, "interval", minutes=30, id="interval_escalation_scan", replace_existing=True)
        scheduler.start()
        logger.info("APScheduler started successfully.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
