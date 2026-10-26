from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.auth.dependencies import get_current_user, require_roles
from app.services.reports import (
    generate_pendency_data,
    generate_overdue_cases_data,
    generate_evc_status_data,
    generate_region_performance_data,
    dicts_to_csv_bytes,
    build_pdf_report
)

router = APIRouter(prefix="/api/reports", tags=["Reporting & Analytics"])

# 1. PENDENCY REPORT
@router.get("/pendency")
def get_pendency_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return generate_pendency_data(db)

@router.get("/pendency/csv")
def download_pendency_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = generate_pendency_data(db)
    fields = ["application_no", "institution", "region", "stage", "route", "days_in_stage", "ageing_bucket", "is_overdue", "status"]
    csv_bytes = dicts_to_csv_bytes(data["rows"], fields)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_pendency_report.csv"}
    )

@router.get("/pendency/pdf")
def download_pendency_pdf(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = generate_pendency_data(db)
    headers = ["App No", "Institution", "Region", "Stage", "Days in Stage", "Ageing", "Overdue"]
    rows = [
        [r["application_no"], r["institution"][:25], r["region"][:15], r["stage"][:20], str(r["days_in_stage"]), r["ageing_bucket"], r["is_overdue"]]
        for r in data["rows"]
    ]
    pdf_bytes = build_pdf_report(
        title="Application Pendency & Bottleneck Monitoring Report",
        subtitle=data["generated_at"],
        table_headers=headers,
        table_rows=rows
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=aicte_pendency_report.pdf"}
    )

# 2. OVERDUE CASES REPORT
@router.get("/overdue")
def get_overdue_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return generate_overdue_cases_data(db)

@router.get("/overdue/csv")
def download_overdue_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = generate_overdue_cases_data(db)
    fields = ["entity_type", "identifier", "institution", "region", "current_stage", "due_date", "days_overdue", "priority"]
    csv_bytes = dicts_to_csv_bytes(data["rows"], fields)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_overdue_cases.csv"}
    )

@router.get("/overdue/pdf")
def download_overdue_pdf(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = generate_overdue_cases_data(db)
    headers = ["Type", "Identifier", "Institution", "Stage/Detail", "Due Date", "Days OVD", "Priority"]
    rows = [
        [r["entity_type"], r["identifier"][:25], r["institution"][:25], r["current_stage"][:20], r["due_date"], str(r["days_overdue"]), r["priority"]]
        for r in data["rows"]
    ]
    pdf_bytes = build_pdf_report(
        title="Statutory Non-Compliance & Overdue Cases Dossier",
        subtitle=data["generated_at"],
        table_headers=headers,
        table_rows=rows
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=aicte_overdue_cases.pdf"}
    )

# 3. EVC STATUS REPORT
@router.get("/evc")
def get_evc_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return generate_evc_status_data(db)

@router.get("/evc/csv")
def download_evc_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = generate_evc_status_data(db)
    fields = ["application_no", "institution", "status", "scheduled_date", "committee", "recommendations", "is_overdue"]
    csv_bytes = dicts_to_csv_bytes(data["rows"], fields)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_evc_status_report.csv"}
    )

# 4. REGION PERFORMANCE REPORT
@router.get("/region-performance")
def get_region_performance_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return generate_region_performance_data(db)

@router.get("/region-performance/csv")
def download_region_performance_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data = generate_region_performance_data(db)
    fields = ["region_code", "region_name", "total_applications", "approved", "rejected", "pending", "overdue", "clearance_rate"]
    csv_bytes = dicts_to_csv_bytes(data["rows"], fields)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aicte_region_performance.csv"}
    )
