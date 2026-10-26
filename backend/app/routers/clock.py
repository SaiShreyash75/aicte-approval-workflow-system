from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.auth.dependencies import get_current_user, require_roles
from app.services.clock import get_system_time, advance_system_days, set_system_time, reset_system_time, get_system_clock_record
from app.services.audit import record_audit
from app.schemas.schemas import SystemClockResponse, AdvanceClockRequest, SetClockRequest

router = APIRouter(prefix="/api/admin/time", tags=["Simulate Time & Clock"])

@router.get("", response_model=SystemClockResponse)
def get_clock(db: Session = Depends(get_db)):
    clock = get_system_clock_record(db)
    current_time = get_system_time(db)
    return SystemClockResponse(
        simulated_date=current_time,
        is_simulated=clock.is_simulated,
        formatted_date=current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    )

@router.post("/advance", response_model=SystemClockResponse)
def advance_clock(
    req: AdvanceClockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Bureau Officer"))
):
    old_time = get_system_time(db)
    clock = advance_system_days(db, req.days)
    new_time = get_system_time(db)

    record_audit(
        db=db,
        action="ADVANCE_SIMULATED_TIME",
        entity_type="SYSTEM_CLOCK",
        entity_id=clock.id,
        role=current_user.role,
        user_id=current_user.id,
        old_state=old_time.isoformat(),
        new_state=new_time.isoformat(),
        remarks=f"Advanced virtual clock by {req.days} days"
    )

    # Immediately trigger scan after advancing time
    from app.services.escalation import scan_and_generate_alerts
    scan_and_generate_alerts(db)

    return SystemClockResponse(
        simulated_date=new_time,
        is_simulated=clock.is_simulated,
        formatted_date=new_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    )

@router.post("/set", response_model=SystemClockResponse)
def set_clock(
    req: SetClockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Bureau Officer"))
):
    old_time = get_system_time(db)
    clock = set_system_time(db, req.target_date)
    new_time = get_system_time(db)

    record_audit(
        db=db,
        action="SET_SIMULATED_TIME",
        entity_type="SYSTEM_CLOCK",
        entity_id=clock.id,
        role=current_user.role,
        user_id=current_user.id,
        old_state=old_time.isoformat(),
        new_state=new_time.isoformat(),
        remarks=f"Set virtual clock to {req.target_date.isoformat()}"
    )

    # Immediately trigger scan after setting time
    from app.services.escalation import scan_and_generate_alerts
    scan_and_generate_alerts(db)

    return SystemClockResponse(
        simulated_date=new_time,
        is_simulated=clock.is_simulated,
        formatted_date=new_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    )

@router.post("/reset", response_model=SystemClockResponse)
def reset_clock(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Bureau Officer"))
):
    old_time = get_system_time(db)
    clock = reset_system_time(db)
    new_time = get_system_time(db)

    record_audit(
        db=db,
        action="RESET_SIMULATED_TIME",
        entity_type="SYSTEM_CLOCK",
        entity_id=clock.id,
        role=current_user.role,
        user_id=current_user.id,
        old_state=old_time.isoformat(),
        new_state=new_time.isoformat(),
        remarks="Reset virtual clock to real system time"
    )

    return SystemClockResponse(
        simulated_date=new_time,
        is_simulated=clock.is_simulated,
        formatted_date=new_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    )

@router.post("/scan")
def trigger_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Bureau Officer", "Regional Officer"))
):
    from app.services.escalation import scan_and_generate_alerts
    result = scan_and_generate_alerts(db)
    return result
