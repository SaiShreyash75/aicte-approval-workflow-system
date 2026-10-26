from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.models import SystemClock

def get_system_clock_record(db: Session) -> SystemClock:
    clock = db.query(SystemClock).filter(SystemClock.id == 1).first()
    if not clock:
        clock = SystemClock(
            id=1,
            simulated_date=datetime.now(timezone.utc),
            is_simulated=False,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(clock)
        db.commit()
        db.refresh(clock)
    return clock

def get_system_time(db: Session) -> datetime:
    """
    Returns the active system time.
    All business logic, SLA deadline calculation, and escalation scans must use this.
    """
    clock = get_system_clock_record(db)
    dt = clock.simulated_date
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def set_system_time(db: Session, target_dt: datetime) -> SystemClock:
    clock = get_system_clock_record(db)
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=timezone.utc)
    clock.simulated_date = target_dt
    clock.is_simulated = True
    clock.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clock)
    return clock

def advance_system_days(db: Session, days: int) -> SystemClock:
    current = get_system_time(db)
    new_dt = current + timedelta(days=days)
    return set_system_time(db, new_dt)

def reset_system_time(db: Session) -> SystemClock:
    clock = get_system_clock_record(db)
    clock.simulated_date = datetime.now(timezone.utc)
    clock.is_simulated = False
    clock.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clock)
    return clock
