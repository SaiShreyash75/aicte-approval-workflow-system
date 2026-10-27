from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class SystemClock(Base):
    __tablename__ = "system_clock"

    id = Column(Integer, primary_key=True, index=True)
    simulated_date = Column(DateTime, nullable=False, default=utc_now)
    is_simulated = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    institutions = relationship("Institution", back_populates="region")
    users = relationship("User", back_populates="region")

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    address = Column(String(255), nullable=True)
    contact_email = Column(String(100), nullable=False)
    is_new_institution = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    region = relationship("Region", back_populates="institutions")
    users = relationship("User", back_populates="institution")
    applications = relationship("Application", back_populates="institution")
    documents = relationship("Document", back_populates="institution")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False)  # Institution, Regional Officer, Bureau Officer, Committee Member, Admin
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    region = relationship("Region", back_populates="users")
    institution = relationship("Institution", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    application_no = Column(String(50), unique=True, index=True, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    program_type = Column(String(100), default="Engineering & Technology")
    application_type = Column(String(100), default="Extension of Approval")
    route_name = Column(String(100), nullable=False)  # Only Scrutiny, Scrutiny+EVC, EVC+SAC/SHC, Only EVC, Custom
    current_stage = Column(String(100), nullable=False)
    status = Column(String(50), default="IN_PROGRESS")  # IN_PROGRESS, APPROVED, REJECTED, REVERTED
    priority = Column(String(20), default="NORMAL")  # NORMAL, HIGH (new institutions get HIGH)
    submitted_at = Column(DateTime, default=utc_now)
    stage_entered_at = Column(DateTime, default=utc_now)
    stage_due_date = Column(DateTime, nullable=True)
    case_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution", back_populates="applications")
    stage_transitions = relationship("StageTransition", back_populates="application", cascade="all, delete-orphan")
    evc = relationship("EVC", back_populates="application", uselist=False, cascade="all, delete-orphan")
    undertakings = relationship("Undertaking", back_populates="application", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="application")

class StageTransition(Base):
    __tablename__ = "stage_transitions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    from_stage = Column(String(100), nullable=False)
    to_stage = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # APPROVE, REVERT, REJECT, ADVANCE
    performed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remarks = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    application = relationship("Application", back_populates="stage_transitions")
    performed_by = relationship("User")

class EVC(Base):
    __tablename__ = "evcs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_date = Column(DateTime, nullable=True)
    committee_members = Column(Text, nullable=True)  # JSON or comma-separated list
    status = Column(String(50), default="QUEUED")  # QUEUED, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    report_summary = Column(Text, nullable=True)
    recommendations = Column(String(50), nullable=True)  # RECOMMENDED, NOT_RECOMMENDED, DEFICIENCY_FOUND
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    application = relationship("Application", back_populates="evc")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])

class Undertaking(Base):
    __tablename__ = "undertakings"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    condition_title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="PENDING")  # PENDING, SUBMITTED, VERIFIED, REJECTED, OVERDUE
    officer_remarks = Column(Text, nullable=True)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    application = relationship("Application", back_populates="undertakings")
    evidence_files = relationship("Evidence", back_populates="undertaking", cascade="all, delete-orphan")
    verified_by = relationship("User")

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    undertaking_id = Column(Integer, ForeignKey("undertakings.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=utc_now)

    undertaking = relationship("Undertaking", back_populates="evidence_files")
    uploaded_by = relationship("User")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    document_type = Column(String(100), nullable=False)  # Land Lease, Building Safety, Fire NOC, Occupancy Certificate
    title = Column(String(200), nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    status = Column(String(50), default="VALID")  # VALID, EXPIRING_SOON, EXPIRED, RENEWAL_SUBMITTED, VERIFIED
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    institution = relationship("Institution", back_populates="documents")
    application = relationship("Application", back_populates="documents")
    verified_by = relationship("User")

class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(100), unique=True, nullable=False)
    trigger_type = Column(String(50), nullable=False)  # UNDERTAKING_DEADLINE, LEASE_EXPIRY, STAGE_SLA, EVC_DELAY
    days_offset = Column(Integer, nullable=False)  # e.g., -30, -15, -7, -1, 0, 7
    recipient_role = Column(String(50), nullable=False)  # Institution, Regional Officer, Bureau Officer, Higher Authority
    escalation_level = Column(Integer, default=1)  # 1: Info/Warning, 2: Regional Esc, 3: Bureau Esc, 4: Apex Esc
    channel = Column(String(50), default="IN_APP")  # IN_APP, EMAIL, ALL
    is_active = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_role = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    entity_type = Column(String(50), nullable=False)  # APPLICATION, UNDERTAKING, DOCUMENT, EVC
    entity_id = Column(Integer, nullable=False)
    rule_id = Column(Integer, ForeignKey("escalation_rules.id"), nullable=True)
    trigger_key = Column(String(100), nullable=False)  # e.g. "T-30", "T-15", "T-7", "T-1", "OVERDUE", "STAGE_BREACH"
    escalation_level = Column(Integer, default=1)
    is_read = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    channel = Column(String(50), default="IN_APP")
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "rule_id", "trigger_key", name="uq_notification_idempotency"),
        Index("idx_notification_recipient", "recipient_role", "recipient_user_id", "is_read"),
    )

    recipient = relationship("User")
    rule = relationship("EscalationRule")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    old_state = Column(Text, nullable=True)
    new_state = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="audit_logs")
