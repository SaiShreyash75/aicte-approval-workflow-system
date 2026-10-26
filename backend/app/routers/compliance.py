from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from app.database import get_db
from app.models.models import Undertaking, Evidence, Document, Institution, Application, User
from app.auth.dependencies import get_current_user, require_roles
from app.services.upload import save_uploaded_file
from app.services.compliance import (
    evaluate_undertaking_status,
    verify_undertaking,
    evaluate_document_validity,
    verify_document_renewal
)
from app.services.clock import get_system_time
from app.services.audit import record_audit
from app.schemas.schemas import (
    UndertakingResponse,
    UndertakingVerifyRequest,
    DocumentResponse,
    DocumentVerifyRequest,
    EvidenceResponse
)

router = APIRouter(prefix="/api/compliance", tags=["Compliance, Undertakings & Documents"])

# ----------------- UNDERTAKINGS -----------------

@router.get("/undertakings", response_model=List[UndertakingResponse])
def get_undertakings(
    application_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Undertaking).join(Application, Undertaking.application_id == Application.id).join(Institution, Application.institution_id == Institution.id)

    if current_user.role == "Institution":
        if current_user.institution_id:
            query = query.filter(Institution.id == current_user.institution_id)
        else:
            return []
    elif current_user.role == "Regional Officer":
        if current_user.region_id:
            query = query.filter(Institution.region_id == current_user.region_id)

    if application_id:
        query = query.filter(Undertaking.application_id == application_id)

    undertakings = query.order_by(Undertaking.due_date.asc()).all()
    result = []
    for u in undertakings:
        curr_status = evaluate_undertaking_status(db, u)
        if status_filter and curr_status != status_filter:
            continue
        ev_list = [
            EvidenceResponse(
                id=ev.id,
                undertaking_id=ev.undertaking_id,
                file_name=ev.file_name,
                file_size=ev.file_size,
                mime_type=ev.mime_type,
                uploaded_at=ev.uploaded_at
            ) for ev in u.evidence_files
        ]
        result.append(UndertakingResponse(
            id=u.id,
            application_id=u.application_id,
            condition_title=u.condition_title,
            description=u.description,
            due_date=u.due_date,
            status=curr_status,
            officer_remarks=u.officer_remarks,
            evidence_files=ev_list,
            created_at=u.created_at
        ))
    return result

@router.post("/undertakings/{undertaking_id}/evidence", response_model=UndertakingResponse)
async def upload_undertaking_evidence(
    undertaking_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Institution", "Admin"))
):
    undertaking = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
    if not undertaking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Undertaking not found")

    # Check ownership
    if current_user.role == "Institution":
        app = undertaking.application
        if not app or app.institution_id != current_user.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    file_name, file_path, file_size, content_type = await save_uploaded_file(file, subfolder="undertakings")

    sys_time = get_system_time(db)
    evidence = Evidence(
        undertaking_id=undertaking.id,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        mime_type=content_type,
        uploaded_by_user_id=current_user.id,
        uploaded_at=sys_time
    )
    db.add(evidence)

    undertaking.status = "SUBMITTED"
    undertaking.updated_at = sys_time

    record_audit(
        db=db,
        action="UNDERTAKING_EVIDENCE_UPLOADED",
        entity_type="UNDERTAKING",
        entity_id=undertaking.id,
        role=current_user.role,
        user_id=current_user.id,
        old_state="PENDING",
        new_state="SUBMITTED",
        remarks=f"Evidence document uploaded: {file_name} ({file_size} bytes)"
    )

    db.commit()
    db.refresh(undertaking)

    ev_list = [
        EvidenceResponse(
            id=ev.id,
            undertaking_id=ev.undertaking_id,
            file_name=ev.file_name,
            file_size=ev.file_size,
            mime_type=ev.mime_type,
            uploaded_at=ev.uploaded_at
        ) for ev in undertaking.evidence_files
    ]
    return UndertakingResponse(
        id=undertaking.id,
        application_id=undertaking.application_id,
        condition_title=undertaking.condition_title,
        description=undertaking.description,
        due_date=undertaking.due_date,
        status=undertaking.status,
        officer_remarks=undertaking.officer_remarks,
        evidence_files=ev_list,
        created_at=undertaking.created_at
    )

@router.post("/undertakings/{undertaking_id}/verify", response_model=UndertakingResponse)
def verify_undertaking_action(
    undertaking_id: int,
    req: UndertakingVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Regional Officer", "Bureau Officer", "Admin"))
):
    undertaking = verify_undertaking(
        db=db,
        undertaking_id=undertaking_id,
        action=req.action.upper(),
        remarks=req.remarks,
        actor=current_user
    )
    ev_list = [
        EvidenceResponse(
            id=ev.id,
            undertaking_id=ev.undertaking_id,
            file_name=ev.file_name,
            file_size=ev.file_size,
            mime_type=ev.mime_type,
            uploaded_at=ev.uploaded_at
        ) for ev in undertaking.evidence_files
    ]
    return UndertakingResponse(
        id=undertaking.id,
        application_id=undertaking.application_id,
        condition_title=undertaking.condition_title,
        description=undertaking.description,
        due_date=undertaking.due_date,
        status=undertaking.status,
        officer_remarks=undertaking.officer_remarks,
        evidence_files=ev_list,
        created_at=undertaking.created_at
    )

# ----------------- DOCUMENTS (LEASE & VALIDITY) -----------------

@router.get("/documents", response_model=List[DocumentResponse])
def get_documents(
    institution_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document).join(Institution, Document.institution_id == Institution.id)

    if current_user.role == "Institution":
        if current_user.institution_id:
            query = query.filter(Document.institution_id == current_user.institution_id)
        else:
            return []
    elif current_user.role == "Regional Officer":
        if current_user.region_id:
            query = query.filter(Institution.region_id == current_user.region_id)

    if institution_id:
        query = query.filter(Document.institution_id == institution_id)
    if doc_type:
        query = query.filter(Document.document_type == doc_type)

    docs = query.order_by(Document.expiry_date.asc()).all()
    sys_date = get_system_time(db).date()
    result = []
    for d in docs:
        curr_status = evaluate_document_validity(db, d)
        days_left = (d.expiry_date - sys_date).days
        result.append(DocumentResponse(
            id=d.id,
            institution_id=d.institution_id,
            application_id=d.application_id,
            document_type=d.document_type,
            title=d.title,
            issue_date=d.issue_date,
            expiry_date=d.expiry_date,
            file_name=d.file_name,
            status=curr_status,
            days_to_expiry=days_left,
            remarks=d.remarks,
            created_at=d.created_at
        ))
    return result

@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    institution_id: int = Form(...),
    document_type: str = Form(...),
    title: str = Form(...),
    issue_date: str = Form(...),
    expiry_date: str = Form(...),
    application_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Institution", "Regional Officer", "Admin"))
):
    iss_dt = date.fromisoformat(issue_date)
    exp_dt = date.fromisoformat(expiry_date)
    file_name = None
    file_path = None

    if file:
        file_name, file_path, _, _ = await save_uploaded_file(file, subfolder="documents")

    sys_time = get_system_time(db)
    doc = Document(
        institution_id=institution_id,
        application_id=application_id,
        document_type=document_type,
        title=title,
        issue_date=iss_dt,
        expiry_date=exp_dt,
        file_name=file_name,
        file_path=file_path,
        status="VALID",
        created_at=sys_time
    )
    db.add(doc)
    db.flush()

    record_audit(
        db=db,
        action="DOCUMENT_REGISTERED",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        role=current_user.role,
        user_id=current_user.id,
        old_state="NONE",
        new_state=f"VALID (exp: {exp_dt})",
        remarks=f"Document {title} [{document_type}] registered"
    )

    db.commit()
    db.refresh(doc)

    sys_date = sys_time.date()
    days_left = (doc.expiry_date - sys_date).days
    return DocumentResponse(
        id=doc.id,
        institution_id=doc.institution_id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        title=doc.title,
        issue_date=doc.issue_date,
        expiry_date=doc.expiry_date,
        file_name=doc.file_name,
        status=evaluate_document_validity(db, doc),
        days_to_expiry=days_left,
        remarks=doc.remarks,
        created_at=doc.created_at
    )

@router.post("/documents/{document_id}/renew", response_model=DocumentResponse)
async def renew_document(
    document_id: int,
    new_expiry_date: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Institution", "Admin"))
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_name, file_path, _, _ = await save_uploaded_file(file, subfolder="documents")
    new_exp = date.fromisoformat(new_expiry_date)

    sys_time = get_system_time(db)
    old_status = doc.status
    doc.file_name = file_name
    doc.file_path = file_path
    doc.status = "RENEWAL_SUBMITTED"
    doc.remarks = f"Renewal submitted with proposed expiry date {new_exp}"
    doc.updated_at = sys_time

    record_audit(
        db=db,
        action="DOCUMENT_RENEWAL_SUBMITTED",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        role=current_user.role,
        user_id=current_user.id,
        old_state=old_status,
        new_state="RENEWAL_SUBMITTED",
        remarks=f"Uploaded renewal certificate: {file_name}"
    )

    db.commit()
    db.refresh(doc)

    sys_date = sys_time.date()
    days_left = (doc.expiry_date - sys_date).days
    return DocumentResponse(
        id=doc.id,
        institution_id=doc.institution_id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        title=doc.title,
        issue_date=doc.issue_date,
        expiry_date=doc.expiry_date,
        file_name=doc.file_name,
        status=doc.status,
        days_to_expiry=days_left,
        remarks=doc.remarks,
        created_at=doc.created_at
    )

@router.post("/documents/{document_id}/verify", response_model=DocumentResponse)
def verify_document_action(
    document_id: int,
    req: DocumentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Regional Officer", "Bureau Officer", "Admin"))
):
    doc = verify_document_renewal(
        db=db,
        document_id=document_id,
        action=req.action.upper(),
        remarks=req.remarks,
        new_expiry_date=req.new_expiry_date,
        actor=current_user
    )

    sys_date = get_system_time(db).date()
    days_left = (doc.expiry_date - sys_date).days
    return DocumentResponse(
        id=doc.id,
        institution_id=doc.institution_id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        title=doc.title,
        issue_date=doc.issue_date,
        expiry_date=doc.expiry_date,
        file_name=doc.file_name,
        status=doc.status,
        days_to_expiry=days_left,
        remarks=doc.remarks,
        created_at=doc.created_at
    )
