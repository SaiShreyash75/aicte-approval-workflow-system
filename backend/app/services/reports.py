import io
import csv
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.models import Application, Region, Institution, EVC, Undertaking, Document
from app.services.clock import get_system_time

def get_ageing_bucket(days: int) -> str:
    if days <= 7:
        return "0-7 days"
    elif days <= 15:
        return "8-15 days"
    elif days <= 30:
        return "16-30 days"
    return "30+ days"

def generate_pendency_data(db: Session) -> dict:
    sys_time = get_system_time(db)
    apps = db.query(Application).filter(Application.status.in_(["IN_PROGRESS", "REVERTED"])).all()

    by_stage = {}
    by_region = {}
    ageing = {"0-7 days": 0, "8-15 days": 0, "16-30 days": 0, "30+ days": 0}
    detailed_rows = []

    for app in apps:
        stage = app.current_stage
        by_stage[stage] = by_stage.get(stage, 0) + 1

        reg_name = app.institution.region.name if (app.institution and app.institution.region) else "Unknown"
        by_region[reg_name] = by_region.get(reg_name, 0) + 1

        days_pending = (sys_time - (app.stage_entered_at.replace(tzinfo=timezone.utc) if app.stage_entered_at.tzinfo is None else app.stage_entered_at)).days
        bucket = get_ageing_bucket(max(0, days_pending))
        ageing[bucket] += 1

        is_overdue = False
        if app.stage_due_date:
            due = app.stage_due_date.replace(tzinfo=timezone.utc) if app.stage_due_date.tzinfo is None else app.stage_due_date
            is_overdue = due < sys_time

        detailed_rows.append({
            "application_no": app.application_no,
            "institution": app.institution.name if app.institution else "N/A",
            "region": reg_name,
            "stage": stage,
            "route": app.route_name,
            "days_in_stage": days_pending,
            "ageing_bucket": bucket,
            "is_overdue": "YES" if is_overdue else "NO",
            "status": app.status
        })

    return {
        "report_title": "AICTE Application Pendency & Ageing Report",
        "generated_at": sys_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_pending": len(apps),
        "by_stage": by_stage,
        "by_region": by_region,
        "ageing_buckets": ageing,
        "rows": detailed_rows
    }

def generate_overdue_cases_data(db: Session) -> dict:
    sys_time = get_system_time(db)
    sys_date = sys_time.date()
    rows = []

    # 1. Overdue Applications
    apps = db.query(Application).filter(Application.status.in_(["IN_PROGRESS", "REVERTED"])).all()
    for app in apps:
        if app.stage_due_date:
            due = app.stage_due_date.replace(tzinfo=timezone.utc) if app.stage_due_date.tzinfo is None else app.stage_due_date
            if due < sys_time:
                days = (sys_time - due).days
                rows.append({
                    "entity_type": "APPLICATION",
                    "identifier": app.application_no,
                    "institution": app.institution.name if app.institution else "N/A",
                    "region": app.institution.region.name if (app.institution and app.institution.region) else "N/A",
                    "current_stage": app.current_stage,
                    "due_date": due.strftime("%Y-%m-%d"),
                    "days_overdue": days,
                    "priority": app.priority
                })

    # 2. Overdue Undertakings
    undertakings = db.query(Undertaking).filter(Undertaking.status.in_(["PENDING", "SUBMITTED", "OVERDUE"])).all()
    for u in undertakings:
        due = u.due_date.replace(tzinfo=timezone.utc) if u.due_date.tzinfo is None else u.due_date
        if due < sys_time:
            days = (sys_time - due).days
            rows.append({
                "entity_type": "UNDERTAKING",
                "identifier": f"{u.condition_title} (App: {u.application.application_no if u.application else u.application_id})",
                "institution": u.application.institution.name if (u.application and u.application.institution) else "N/A",
                "region": u.application.institution.region.name if (u.application and u.application.institution and u.application.institution.region) else "N/A",
                "current_stage": f"Undertaking: {u.status}",
                "due_date": due.strftime("%Y-%m-%d"),
                "days_overdue": days,
                "priority": u.application.priority if u.application else "NORMAL"
            })

    # 3. Expired Documents
    docs = db.query(Document).all()
    for d in docs:
        if d.expiry_date < sys_date and d.status != "VERIFIED":
            days = (sys_date - d.expiry_date).days
            rows.append({
                "entity_type": "DOCUMENT",
                "identifier": f"{d.document_type}: {d.title}",
                "institution": d.institution.name if d.institution else "N/A",
                "region": d.institution.region.name if (d.institution and d.institution.region) else "N/A",
                "current_stage": f"Doc: {d.status}",
                "due_date": d.expiry_date.strftime("%Y-%m-%d"),
                "days_overdue": days,
                "priority": "HIGH"
            })

    # 4. Overdue EVCs
    evcs = db.query(EVC).all()
    for evc in evcs:
        app_no = evc.application.application_no if evc.application else f"App#{evc.application_id}"
        inst_name = evc.application.institution.name if (evc.application and evc.application.institution) else "N/A"
        reg_name = evc.application.institution.region.name if (evc.application and evc.application.institution and evc.application.institution.region) else "N/A"
        if evc.status == "SCHEDULED" and evc.scheduled_date:
            sched = evc.scheduled_date.replace(tzinfo=timezone.utc) if evc.scheduled_date.tzinfo is None else evc.scheduled_date
            if sched < sys_time:
                days = (sys_time - sched).days
                rows.append({
                    "entity_type": "EVC",
                    "identifier": f"EVC Inspection ({app_no})",
                    "institution": inst_name,
                    "region": reg_name,
                    "current_stage": "EVC Scheduled (Overdue)",
                    "due_date": sched.strftime("%Y-%m-%d"),
                    "days_overdue": days,
                    "priority": evc.application.priority if evc.application else "HIGH"
                })
        elif evc.status == "QUEUED" and evc.application and evc.application.stage_due_date:
            due = evc.application.stage_due_date.replace(tzinfo=timezone.utc) if evc.application.stage_due_date.tzinfo is None else evc.application.stage_due_date
            if due < sys_time:
                days = (sys_time - due).days
                rows.append({
                    "entity_type": "EVC",
                    "identifier": f"EVC Queued ({app_no})",
                    "institution": inst_name,
                    "region": reg_name,
                    "current_stage": "EVC Queued (Delay)",
                    "due_date": due.strftime("%Y-%m-%d"),
                    "days_overdue": days,
                    "priority": evc.application.priority if evc.application else "HIGH"
                })

    return {
        "report_title": "AICTE Statutory Non-Compliance & Overdue Cases Dossier",
        "generated_at": sys_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_overdue": len(rows),
        "rows": sorted(rows, key=lambda x: x["days_overdue"], reverse=True)
    }

def generate_evc_status_data(db: Session) -> dict:
    sys_time = get_system_time(db)
    evcs = db.query(EVC).all()
    counts = {"QUEUED": 0, "SCHEDULED": 0, "IN_PROGRESS": 0, "COMPLETED": 0, "OVERDUE": 0}
    rows = []

    for evc in evcs:
        app_no = evc.application.application_no if evc.application else f"App#{evc.application_id}"
        inst_name = evc.application.institution.name if (evc.application and evc.application.institution) else "N/A"
        is_ovd = False
        if evc.status == "SCHEDULED" and evc.scheduled_date:
            sched = evc.scheduled_date.replace(tzinfo=timezone.utc) if evc.scheduled_date.tzinfo is None else evc.scheduled_date
            if sched < sys_time:
                is_ovd = True
                counts["OVERDUE"] += 1
        counts[evc.status] = counts.get(evc.status, 0) + 1

        rows.append({
            "application_no": app_no,
            "institution": inst_name,
            "status": evc.status,
            "scheduled_date": evc.scheduled_date.strftime("%Y-%m-%d") if evc.scheduled_date else "Not Scheduled",
            "committee": evc.committee_members or "Not Allocated",
            "recommendations": evc.recommendations or "Pending",
            "is_overdue": "YES" if is_ovd else "NO"
        })

    return {
        "report_title": "AICTE Expert Visit Committee (EVC) Status Report",
        "generated_at": sys_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "counts": counts,
        "rows": rows
    }

def generate_region_performance_data(db: Session) -> dict:
    sys_time = get_system_time(db)
    regions = db.query(Region).all()
    rows = []

    for r in regions:
        apps = db.query(Application).join(Institution).filter(Institution.region_id == r.id).all()
        total = len(apps)
        approved = sum(1 for a in apps if a.status == "APPROVED")
        rejected = sum(1 for a in apps if a.status == "REJECTED")
        pending = sum(1 for a in apps if a.status in ("IN_PROGRESS", "REVERTED"))
        overdue = 0
        for a in apps:
            if a.status in ("IN_PROGRESS", "REVERTED") and a.stage_due_date:
                due = a.stage_due_date.replace(tzinfo=timezone.utc) if a.stage_due_date.tzinfo is None else a.stage_due_date
                if due < sys_time:
                    overdue += 1

        clearance_rate = f"{(approved / total * 100):.1f}%" if total > 0 else "0%"

        rows.append({
            "region_code": r.code,
            "region_name": r.name,
            "total_applications": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "overdue": overdue,
            "clearance_rate": clearance_rate
        })

    return {
        "report_title": "AICTE Region-Wise Performance & Disposal Benchmark",
        "generated_at": sys_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "rows": rows
    }

def dicts_to_csv_bytes(rows: list[dict], fieldnames: list[str]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")

def build_pdf_report(title: str, subtitle: str, table_headers: list[str], table_rows: list[list[str]]) -> bytes:
    """
    Generates a PDF using ReportLab with disclaimer banner, metadata, and structured data tables.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1e3a8a")
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569")
    )
    disclaimer_style = ParagraphStyle(
        'DisclaimerBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#92400e"),
        backColor=colors.HexColor("#fef3c7"),
        borderPadding=6
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )

    story = [
        Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)", title_style),
        Paragraph(title, ParagraphStyle('Heading2', parent=title_style, fontSize=12, textColor=colors.HexColor("#0f172a"))),
        Paragraph(f"Generated on: {subtitle}", subtitle_style),
        Spacer(1, 10),
        Paragraph(
            "<b>STATUTORY DISCLAIMER:</b> Automated alerts and pendency metrics support, but do not replace, statutory scrutiny and decisions of the competent authority.",
            disclaimer_style
        ),
        Spacer(1, 12),
    ]

    # Convert table text to Paragraphs for clean wrapping
    wrapped_data = [[Paragraph(f"<b>{h}</b>", table_cell_style) for h in table_headers]]
    for row in table_rows:
        wrapped_data.append([Paragraph(str(c), table_cell_style) for c in row])

    # Table styling
    t = Table(wrapped_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))

    story.append(t)
    doc.build(story)
    return buffer.getvalue()
