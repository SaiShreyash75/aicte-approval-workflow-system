# AICTE Centralized Approval Workflow Automation & Statutory Compliance System

## 1. Purpose

The **AICTE Centralized Approval Workflow Automation & Statutory Compliance System** is an enterprise-grade regulatory processing and monitoring platform built in alignment with the **AICTE Approval Process Handbook (APH)**.

It provides end-to-end digitization, strict role-based workflow enforcement, time-bound SLA tracking, multi-tier automated escalation ladders, and immutable auditability for technical education institutions, regional offices, expert committees, and council bureaus across India.

### Key Capabilities
- **Multi-Route Workflow Engine**: Manages complex application pathways (*Scrutiny-Only*, *Scrutiny + EVC*, *Scrutiny + EVC + SAC*) with role-scoped gatekeeper permissions.
- **Statutory Pendency & Ageing Intelligence**: Tracks applications across regulatory ageing buckets (`0–7 days`, `8–15 days`, `16–30 days`, `30+ days`) and highlights bottleneck stages.
- **Time-Bound Undertakings & Document Validity**: Monitors institutional conditional compliance (e.g., Fire Safety, Cadre Ratio, Land Lease Deeds) and statutory certificate expiration dates.
- **Automated Escalation Ladder**: Generates hierarchical alerts (`L1 Notice` → `L2 Regional Officer` → `L3 Bureau Officer` → `L4 Apex / Member Secretary`) with email notifications.
- **Virtual Time-Travel Engine**: Deterministic simulated clock for end-to-end regression testing, SLA breach verification, and statutory timeline validation.
- **Immutable Append-Only Audit Trail**: Guaranteed integrity with database-level SQLite triggers prohibiting updates and deletions.
- **Statutory Reporting & PDF Export**: Instant generation of official CSV and ReportLab PDF dossiers containing mandatory regulatory disclaimer banners.

---

## 2. System Architecture

```
+----------------------------------------------------------------------------------------------------+
|                                    REACT 18 SINGLE PAGE APP (Vite)                                  |
|   Dashboard  |  Applications  |  EVC Desk  |  Compliance  |  Notifications  |  Reports  |  Audit Trail  |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                            HTTPS / JSON
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                    FASTAPI BACKEND REST API                                        |
|                          OAuth2 Password Bearer / JWT Auth / Role RBAC                              |
|   [/api/auth]   [/api/applications]   [/api/evc]   [/api/compliance]   [/api/notifications]        |
|   [/api/dashboard]        [/api/reports]        [/api/admin/time]        [/api/audit-logs]         |
+----------------------------------------------------------------------------------------------------+
                                                  |
             +------------------------------------+------------------------------------+
             |                                    |                                    |
             v                                    v                                    v
+--------------------------+   +------------------------------------+   +----------------------------+
|      WORKFLOW ENGINE     |   |   COMPLIANCE & UNDERTAKINGS TRACKER|   |  NOTIFICATION & ESCALATION |
|  - Stage Transition FSM  |   |   - Conditional Undertaking Status |   |  - Rule Evaluation Engine  |
|  - Role Access Checks    |   |   - Expiry Countdown Calculations  |   |  - Multi-Tier Escalation   |
|  - Next / Revert Stages  |   |   - Secure File Upload & Validation|   |    (L1 -> L2 -> L3 -> L4)  |
|  - Due Date Calculations |   |   - Magic Byte Security Scanning   |   |  - In-App & Simulated Mail |
+--------------------------+   +------------------------------------+   +----------------------------+
             |                                    |                                    |
             +------------------------------------+------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                     BACKGROUND & CLOCK SERVICES                                     |
|    - APScheduler Background Jobs (Recurring 6-hour regulatory scans)                                |
|    - SystemClock Virtual Time-Travel Engine (advance_system_days / set_system_time / reset)        |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                   DATA STORAGE & ATTESTATION LAYER                                 |
|    - SQLite Relational Database (`aicte.db`)                                                       |
|    - Local Secure Upload Storage (`uploads/`) with hash-based unique filenames                     |
|    - Immutable `audit_logs` Table (Protected by SQLite ABORT triggers on UPDATE / DELETE)          |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. 3-Command Setup

To run the complete system locally:

```bash
# 1. Start the FastAPI backend server
cd backend && ./venv/bin/uvicorn app.main:app --port 8000

# 2. Seed realistic demo data (40 applications across 4 regions, undertakings, documents & users)
cd backend && ./venv/bin/python seed_data.py

# 3. Start the React frontend development server
cd frontend && npm run dev
```

The frontend will be available at `http://localhost:5173` and the backend Swagger documentation at `http://localhost:8000/docs`.

---

## 4. Demo Logins by Role

> **Standard Password for All Demo Accounts**: `Aicte@123`

| Role | Email Address | Scope & Jurisdiction | Primary Desk Functionality |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@aicte.gov.in` | National / Apex | Full system scrutiny, virtual clock controls, all notifications, user oversight |
| **Regional Officer (North)** | `ro.north@aicte.gov.in` | Northern Region (RO-NO) | Preliminary Scrutiny, EVC scheduling, undertaking & document verification |
| **Regional Officer (West)** | `ro.west@aicte.gov.in` | Western Region (RO-WE) | Western regional applications, compliance approvals, regional KPIs |
| **Regional Officer (South)** | `ro.south@aicte.gov.in` | Southern Region (RO-SO) | Southern regional applications, compliance approvals, regional KPIs |
| **Regional Officer (East)** | `ro.east@aicte.gov.in` | Eastern Region (RO-EA) | Eastern regional applications, compliance approvals, regional KPIs |
| **Bureau Officer** | `bo.approval@aicte.gov.in` | National Bureau | Executive Committee & SAC approvals, L3 escalation management, council reviews |
| **Bureau Officer (Policy)** | `bo.policy@aicte.gov.in` | National Bureau | Regulatory policy oversight, macro disposal benchmarks, statutory exports |
| **EVC Expert / Committee** | `evc.expert1@aicte.gov.in` | Assigned Visits | Expert Visit Committee desk, report recommendations, deficiency findings |
| **EVC Expert 2** | `evc.expert2@aicte.gov.in` | Assigned Visits | Assigned inspection dossiers, EVC report submission |
| **SAC Chair** | `sac.chair@aicte.gov.in` | Standing Appeals | Standing Appeals Committee hearing recommendations |
| **Institution Principal** | `principal.diaet@aicte.edu` | Delhi Institute (1-1001) | Application progress, upload undertaking evidence, document renewal requests |
| **Institution Principal** | `principal.kptc@aicte.edu` | Kanpur Polytechnic | Application tracking, compliance status, in-app institutional notices |

---

## 5. 5-Minute Demo Walkthrough

### Step 1: Regional & Council Scrutiny Overview (1 min)
1. Log in as **Regional Officer** (`ro.north@aicte.gov.in` / `Aicte@123`).
2. Navigate to **Dashboard** to view active KPIs: total applications, stage distribution, and ageing buckets (`0–7 days`, `8–15 days`, `16–30 days`, `30+ days`).
3. Click **Applications** in the sidebar to review applications strictly scoped to the Northern jurisdiction.
4. Open an application (e.g. `AICTE/2026/101`) to inspect stage transitions, assigned committee members, and pending undertakings.

### Step 2: Time Travel & Multi-Tier Escalations (1 min)
1. Log in as **Admin** (`admin@aicte.gov.in` / `Aicte@123`).
2. Click the **Simulate Clock** button in the top navigation bar.
3. Advance the virtual clock by **+15 days**.
4. Observe the instantaneous execution of the escalation engine:
   - Applications exceeding stage deadlines are escalated to Level 2 (Regional Officer) and Level 3 (Bureau Officer).
   - Critical delays (>15 days overdue) trigger Level 4 Apex escalations.
   - Simulated email transmissions are recorded in `simulated_emails.log`.

### Step 3: Notification Triage & Alert Management (1 min)
1. Switch to **Regional Officer** (`ro.north@aicte.gov.in`) or stay as **Admin**.
2. Click **Notifications & Alerts** in the sidebar.
3. Filter alerts by:
   - **Escalation Level**: Filter by `L2 REGIONAL` or `L3 BUREAU`.
   - **Entity Type**: Filter by `APPLICATION`, `UNDERTAKING`, or `EVC`.
   - **Resolution State**: Filter by `Active Only` or `Closed / Resolved`.
4. Click **Mark Read** on individual items or use **Mark All Read**.

### Step 4: Evidence Upload with Security Checks (1 min)
1. Log in as **Institution Principal** (`principal.diaet@aicte.edu` / `Aicte@123`).
2. Navigate to **Compliance & Documents** and open the **Time-Bound Undertakings** tab.
3. Locate a pending undertaking (e.g., *Appointment of Anti-Ragging Committee*).
4. Attempt to upload an executable binary or renamed `.exe` file; notice the magic-byte validator immediately blocks it with a `400 Bad Request`.
5. Upload a genuine compliance PDF document. Notice the undertaking status transitions to `SUBMITTED`.

### Step 5: Verification, Alert Resolution & Audit Trail (1 min)
1. Log back in as **Regional Officer** (`ro.north@aicte.gov.in`).
2. In **Compliance & Documents**, review the submitted proof of compliance.
3. Click **Verify / Scrutinize**, enter remarks, and approve.
4. Notice that associated escalation alerts for this undertaking are automatically marked as **Resolved / Closed**.
5. Navigate to **Immutable Audit Trail** in the sidebar to observe the cryptographically complete ledger of events:
   - `ADVANCE_SIMULATED_TIME`
   - `UNDERTAKING_EVIDENCE_UPLOADED`
   - `UNDERTAKING_VERIFIED`
   - `ALERT_CLOSED`
6. Click **Reports & Exports** to download the official **Pendency Dossier** and **Overdue Cases Dossier** in CSV and formatted PDF formats.

---

## 6. Regulatory Verification & Test Checklist

| Evaluation Area | System Implementation | Verification Command / Evidence |
| :--- | :--- | :--- |
| **Workflow Accuracy** | Validates legal transition sequence (`Scrutiny` → `EVC` → `SAC` → `Council Bureau`). Unauthorized role transitions strictly prohibited with `403 Forbidden`. | `cd backend && ./venv/bin/python -m pytest tests/test_phase2_workflow.py` |
| **Alert Timeliness** | Proactive reminders trigger at -2 days, SLA breach escalations trigger at Day 0, L3 triggers at Day 7, L4 Apex triggers at Day 15. | Verified in `app/services/escalation.py` rule matrix and `simulated_emails.log` |
| **Deadline Reliability** | SystemClock virtual time-travel engine ensures reproducible, deterministic dates across all services and tests. | Verified via `GET /api/admin/time` and automated test suite |
| **Pending-Case Visibility** | Real-time pendency categorized by ageing buckets (`0–7`, `8–15`, `16–30`, `30+`) and region-wise disposal benchmarking. | Live on Dashboard and `/api/reports/pendency` |
| **Reduction in Manual Follow-up** | Automatic generation of in-app and email alerts upon SLA breach; automatic resolution/closure of alerts once evidence is verified. | Verified via `test_alerts_closed_on_resolution` in test suite |
| **Audit-Trail Completeness** | Append-only SQLite triggers (`prevent_audit_log_update`, `prevent_audit_log_delete`) prevent tampering or modification. | Verified in `tests/test_phase1.py::test_audit_log_immutability` |

---

## 7. Statutory Disclaimer

> **STATUTORY DISCLAIMER**:
> Automated alerts, pendency metrics, and algorithmic escalation notifications support, but do not replace, statutory scrutiny, on-site committee evaluations, and official decisions of the competent authority under the All India Council for Technical Education Act, 1987.
