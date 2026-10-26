from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from typing import Optional, List, Any

# Auth schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: str
    region_id: Optional[int] = None
    institution_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    region_id: Optional[int] = None
    institution_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Clock schemas
class SystemClockResponse(BaseModel):
    simulated_date: datetime
    is_simulated: bool
    formatted_date: str

class AdvanceClockRequest(BaseModel):
    days: int

class SetClockRequest(BaseModel):
    target_date: datetime

# Audit log schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    role: str
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    remarks: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Region & Institution schemas
class RegionResponse(BaseModel):
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True

class InstitutionResponse(BaseModel):
    id: int
    code: str
    name: str
    region_id: int
    address: Optional[str] = None
    contact_email: str
    is_new_institution: bool

    class Config:
        from_attributes = True

# Workflow & Transition schemas
class WorkflowActionRequest(BaseModel):
    action: str  # APPROVE, REVERT, REJECT
    remarks: str

class StageTransitionResponse(BaseModel):
    id: int
    application_id: int
    from_stage: str
    to_stage: str
    action: str
    performed_by_user_id: int
    performed_by_name: Optional[str] = None
    performed_by_role: Optional[str] = None
    remarks: str
    created_at: datetime

    class Config:
        from_attributes = True

# EVC schemas
class EVCScheduleRequest(BaseModel):
    scheduled_date: datetime
    committee_members: str

class EVCCompleteRequest(BaseModel):
    recommendations: str  # RECOMMENDED, NOT_RECOMMENDED, DEFICIENCY_FOUND
    report_summary: str

class EVCResponse(BaseModel):
    id: int
    application_id: int
    application_no: Optional[str] = None
    institution_name: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    committee_members: Optional[str] = None
    status: str
    report_summary: Optional[str] = None
    recommendations: Optional[str] = None
    completed_at: Optional[datetime] = None
    is_overdue: bool = False
    days_overdue: int = 0
    priority: str = "NORMAL"

    class Config:
        from_attributes = True

# Evidence schemas
class EvidenceResponse(BaseModel):
    id: int
    undertaking_id: int
    file_name: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

# Undertaking schemas
class UndertakingVerifyRequest(BaseModel):
    action: str  # VERIFY or REJECT
    remarks: str

class UndertakingResponse(BaseModel):
    id: int
    application_id: int
    condition_title: str
    description: str
    due_date: datetime
    status: str
    officer_remarks: Optional[str] = None
    evidence_files: List[EvidenceResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

# Document schemas
class DocumentCreateRequest(BaseModel):
    institution_id: int
    application_id: Optional[int] = None
    document_type: str
    title: str
    issue_date: date
    expiry_date: date

class DocumentVerifyRequest(BaseModel):
    action: str  # VERIFY or REJECT
    remarks: str
    new_expiry_date: Optional[date] = None

class DocumentResponse(BaseModel):
    id: int
    institution_id: int
    application_id: Optional[int] = None
    document_type: str
    title: str
    issue_date: date
    expiry_date: date
    file_name: Optional[str] = None
    status: str
    days_to_expiry: int = 0
    remarks: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Application schemas
class ApplicationMinimalResponse(BaseModel):
    id: int
    application_no: str
    institution_id: int
    institution_name: Optional[str] = None
    route_name: str
    current_stage: str
    status: str
    priority: str
    submitted_at: datetime
    stage_due_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class ApplicationDetailResponse(BaseModel):
    id: int
    application_no: str
    institution_id: int
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    region_name: Optional[str] = None
    program_type: str
    application_type: str
    route_name: str
    current_stage: str
    status: str
    priority: str
    submitted_at: datetime
    stage_entered_at: datetime
    stage_due_date: Optional[datetime] = None
    case_summary: Optional[str] = None
    allowed_roles: List[str] = []
    can_revert_to: Optional[str] = None
    next_stage: Optional[str] = None
    stage_transitions: List[StageTransitionResponse] = []
    evc: Optional[EVCResponse] = None
    undertakings: List[UndertakingResponse] = []
    documents: List[DocumentResponse] = []

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
