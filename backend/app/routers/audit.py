from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import AuditLog, User
from app.auth.dependencies import get_current_user, require_roles
from app.schemas.schemas import AuditLogResponse

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Trail (Append-Only)"])

@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Bureau Officer", "Regional Officer"))
):
    """
    Read-only audit log retrieval.
    Strictly NO PUT/PATCH/DELETE endpoints exist for this resource.
    """
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.id.desc()).limit(limit).all()
    return logs
