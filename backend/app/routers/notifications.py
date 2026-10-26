from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.models.models import Notification, User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["In-App Notifications & Alerts"])

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    recipient_role: str
    recipient_user_id: Optional[int] = None
    entity_type: str
    entity_id: int
    trigger_key: str
    escalation_level: int
    channel: str
    is_read: bool
    is_closed: bool
    closed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UnreadCountResponse(BaseModel):
    unread_count: int

@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Notification)

    # Scoping by role
    if current_user.role == "Admin":
        pass  # Admins can see all notifications across system
    elif current_user.role == "Bureau Officer":
        query = query.filter(Notification.recipient_role.in_(["Bureau Officer", "Admin"]))
    elif current_user.role == "Regional Officer":
        query = query.filter(Notification.recipient_role == "Regional Officer")
    elif current_user.role == "Committee Member":
        query = query.filter(Notification.recipient_role == "Committee Member")
    elif current_user.role == "Institution":
        query = query.filter(Notification.recipient_role == "Institution")

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifs = query.order_by(Notification.id.desc()).limit(limit).all()
    return notifs

@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.is_read == False)

    if current_user.role == "Admin":
        pass
    elif current_user.role == "Bureau Officer":
        query = query.filter(Notification.recipient_role.in_(["Bureau Officer", "Admin"]))
    elif current_user.role == "Regional Officer":
        query = query.filter(Notification.recipient_role == "Regional Officer")
    elif current_user.role == "Committee Member":
        query = query.filter(Notification.recipient_role == "Committee Member")
    elif current_user.role == "Institution":
        query = query.filter(Notification.recipient_role == "Institution")

    count = query.count()
    return UnreadCountResponse(unread_count=count)

@router.post("/{notification_id}/mark-read", response_model=NotificationResponse)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.is_read == False)
    if current_user.role != "Admin":
        query = query.filter(Notification.recipient_role == current_user.role)

    unread_items = query.all()
    for item in unread_items:
        item.is_read = True
    db.commit()
    return {"status": "success", "marked_read_count": len(unread_items)}
