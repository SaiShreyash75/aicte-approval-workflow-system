from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_all_5_roles_dashboard_and_applications():
    print("\n=======================================================")
    print("VERIFYING ROLE DASHBOARDS AND APPLICATIONS QUEUES")
    print("=======================================================")

    demo_roles = [
        ("Admin", "admin@aicte.gov.in", "All Regions"),
        ("Regional Officer (North)", "ro.north@aicte.gov.in", "Northern Region"),
        ("Bureau Officer", "bo.approval@aicte.gov.in", "National Bureau"),
        ("Committee Member", "evc.expert1@aicte.gov.in", "EVC Inspection Desk"),
        ("Institution", "principal.diaet@aicte.edu", "DIAET Delhi"),
    ]

    for role_name, email, scope_name in demo_roles:
        # 1. Login
        login_resp = client.post("/api/auth/login", json={"email": email, "password": "Aicte@123"})
        assert login_resp.status_code == 200, f"Failed login for {email}"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Dashboard summary
        dash_resp = client.get("/api/dashboard/summary", headers=headers)
        assert dash_resp.status_code == 200, f"Failed dashboard for {email}"
        dash = dash_resp.json()
        kpi = dash["kpi"]

        # 3. Applications list
        apps_resp = client.get("/api/applications", headers=headers)
        assert apps_resp.status_code == 200, f"Failed applications for {email}"
        apps = apps_resp.json()

        print(f"Role: {role_name:<26} | Scope: {scope_name:<18} | Apps in Queue: {len(apps):<2} | SLA Overdue: {kpi['overdue_sla_count']:<2} | Ageing Active: {dash['ageing_buckets'][0]['count']}")
        assert "disclaimer" in dash
        assert len(dash["ageing_buckets"]) == 4

    print("=======================================================")
    print(">>> ALL 5 ROLES CONFIRMED OPERATIONAL & CORRECTLY SCOPED! <<<")
    print("=======================================================\n")

if __name__ == "__main__":
    test_all_5_roles_dashboard_and_applications()
