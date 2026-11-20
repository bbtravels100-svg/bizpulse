import os
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.database import init_auth_db
from app.auth.security import create_access_token
from app.auth.models import UserResponse
from app.actions.models import (
    ActionCreateRequest,
    ActionApproveRequest,
    ActionStatus,
    TaskStatusUpdateRequest,
)
from app.actions.service import default_action_service


@pytest.fixture(autouse=True)
def init_db_fixture():
    init_auth_db()


@pytest.fixture
def client():
    return TestClient(app)


# ─── Helper Functions to Generate Role-Based Headers ────────────────────

def get_auth_headers(
    user_id: str,
    email: str,
    role: str,
    department: str = "Operations",
    is_active: bool = True,
) -> dict:
    """Generate valid JWT Authorization header for specified role."""
    token = create_access_token({
        "sub": user_id,
        "email": email,
        "name": f"Test {role}",
        "role": role,
        "department": department,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ceo_headers():
    return get_auth_headers("usr-demo-000", "ceo.sarah@bizpulse.internal", "CEO / Admin", "Executive Leadership")


@pytest.fixture
def ops_headers():
    return get_auth_headers("usr-demo-001", "alex.morgan@bizpulse.internal", "Operations Manager", "Operations")


@pytest.fixture
def finance_headers():
    return get_auth_headers("usr-demo-002", "jordan.lee@bizpulse.internal", "Finance Analyst", "Finance")


@pytest.fixture
def marketing_headers():
    return get_auth_headers("usr-demo-003", "taylor.swift@bizpulse.internal", "Marketing Lead", "Marketing")


@pytest.fixture
def employee_headers():
    return get_auth_headers("usr-demo-004", "sam.coder@bizpulse.internal", "Employee", "Engineering")


@pytest.fixture
def ops_employee_headers():
    return get_auth_headers("usr-demo-005", "casey.ops@bizpulse.internal", "Employee", "Operations")


# ─── 1. Unauthenticated Requests Return 401 ────────────────────────────

def test_unauthenticated_request_to_overview_returns_401(client):
    """Unauthenticated calls to business overview return 401."""
    res = client.get("/api/overview")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_unauthenticated_request_to_actions_returns_401(client):
    """Unauthenticated calls to action listing return 401."""
    res = client.get("/api/actions")
    assert res.status_code == 401


def test_unauthenticated_request_to_datasets_returns_401(client):
    """Unauthenticated calls to dataset catalog return 401."""
    res = client.get("/api/datasets")
    assert res.status_code == 401


def test_unauthenticated_request_to_chat_returns_401(client):
    """Unauthenticated calls to AI chat return 401."""
    res = client.post("/api/chat", json={"message": "Hello"})
    assert res.status_code == 401


# ─── 2. Authenticated Authorized Access Succeeds ───────────────────────

def test_authenticated_ceo_access_succeeds(client, ceo_headers):
    """CEO / Admin can access all overview, sales, and analytics."""
    res = client.get("/api/overview", headers=ceo_headers)
    assert res.status_code == 200
    assert "total_revenue" in res.json()


def test_authenticated_ops_access_succeeds(client, ops_headers):
    """Operations Manager can access sales and operational tasks."""
    res = client.get("/api/sales", headers=ops_headers)
    assert res.status_code == 200
    assert "total_revenue" in res.json()


# ─── 3. Inactive User Is Denied ────────────────────────────────────────

def test_inactive_user_is_denied(client):
    """Deactivated accounts cannot access protected routes even with valid signature."""
    # Seed or use an inactive token with non-existent / deactivated user
    token = create_access_token({"sub": "usr-inactive-999", "email": "inactive@bizpulse.internal"})
    res = client.get("/api/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


# ─── 4. Role Restrictions (403 Forbidden) ──────────────────────────────

def test_employee_cannot_approve_or_reject_proposals(client, employee_headers):
    """Employees cannot approve or reject action proposals (403 Forbidden)."""
    uid = uuid.uuid4().hex[:6]
    action = default_action_service.create_action(ActionCreateRequest(
        problem_description=f"Test proposal {uid}",
        recommended_action=f"Do test action {uid}",
        responsible_department="Engineering",
        suggested_owner_role="Engineer",
        suggested_deadline="2026-12-01",
        expected_outcome="Fixed",
        verification_criteria="Tests pass",
        investigation_id=f"INV-{uid}",
        anomaly_id=f"ANOM-{uid}",
    ))

    # Employee tries to approve
    approve_res = client.post(f"/api/actions/{action.id}/approve", headers=employee_headers)
    assert approve_res.status_code == 403
    assert "action:approve" in approve_res.json()["detail"]

    # Employee tries to reject
    reject_res = client.post(
        f"/api/actions/{action.id}/reject",
        json={"reason": "Not needed"},
        headers=employee_headers,
    )
    assert reject_res.status_code == 403
    assert "action:reject" in reject_res.json()["detail"]


def test_ops_manager_cannot_approve_or_reject_proposals(client, ops_headers):
    """Operations Manager cannot approve proposals (CEO-only operation)."""
    uid = uuid.uuid4().hex[:6]
    action = default_action_service.create_action(ActionCreateRequest(
        problem_description=f"Test proposal {uid}",
        recommended_action=f"Do test action {uid}",
        responsible_department="Operations",
        suggested_owner_role="Ops Lead",
        suggested_deadline="2026-12-01",
        expected_outcome="Fixed",
        verification_criteria="Tests pass",
        investigation_id=f"INV-{uid}",
        anomaly_id=f"ANOM-{uid}",
    ))

    approve_res = client.post(f"/api/actions/{action.id}/approve", headers=ops_headers)
    assert approve_res.status_code == 403
    assert "action:approve" in approve_res.json()["detail"]


def test_ceo_can_approve_and_reject_proposals(client, ceo_headers):
    """CEO / Admin has permission to approve proposals."""
    uid = uuid.uuid4().hex[:6]
    action = default_action_service.create_action(ActionCreateRequest(
        problem_description=f"Test proposal {uid}",
        recommended_action=f"Do test action {uid}",
        responsible_department="Operations",
        suggested_owner_role="Ops Lead",
        suggested_deadline="2026-12-01",
        expected_outcome="Fixed",
        verification_criteria="Tests pass",
        investigation_id=f"INV-{uid}",
        anomaly_id=f"ANOM-{uid}",
    ))

    approve_res = client.post(f"/api/actions/{action.id}/approve", headers=ceo_headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == ActionStatus.APPROVED.value


def test_employee_cannot_upload_datasets(client, employee_headers):
    """Employees cannot upload or replace CSV datasets (403 Forbidden)."""
    res = client.post(
        "/api/datasets/sales/upload",
        json={"filename": "sales.csv", "content": "date,product_id,product_name,units_sold,revenue\n"},
        headers=employee_headers,
    )
    assert res.status_code == 403
    assert "dataset:upload" in res.json()["detail"]


def test_ops_manager_cannot_upload_datasets(client, ops_headers):
    """Operations Manager cannot upload datasets (CEO / Admin only)."""
    res = client.post(
        "/api/datasets/sales/upload",
        json={"filename": "sales.csv", "content": "date,product_id,product_name,units_sold,revenue\n"},
        headers=ops_headers,
    )
    assert res.status_code == 403
    assert "dataset:upload" in res.json()["detail"]


def test_employee_cannot_run_investigations(client, employee_headers):
    """Employees cannot trigger automated AI investigations (403 Forbidden)."""
    res = client.post(
        "/api/investigate",
        json={"anomaly_id": "ANOMALY_REV_001"},
        headers=employee_headers,
    )
    assert res.status_code == 403
    assert "ai:investigate" in res.json()["detail"]


def test_marketing_lead_cannot_view_profitability(client, marketing_headers):
    """Marketing Lead cannot view unit costs and product profitability margins (403 Forbidden)."""
    res = client.get("/api/products/profitability", headers=marketing_headers)
    assert res.status_code == 403
    assert "profitability:read" in res.json()["detail"]


def test_finance_analyst_can_view_profitability(client, finance_headers):
    """Finance Analyst has permission to view profitability margins."""
    res = client.get("/api/products/profitability", headers=finance_headers)
    assert res.status_code == 200
    assert "products" in res.json()


# ─── 5. Resource-Level Authorization on Tasks ──────────────────────────

def test_employee_cannot_modify_unrelated_department_task(client, employee_headers):
    """
    Resource-Level Check: Employee from 'Engineering' cannot update status or add notes
    to a task assigned to 'Operations' department (403 Forbidden).
    """
    uid = uuid.uuid4().hex[:6]
    action = default_action_service.create_action(ActionCreateRequest(
        problem_description=f"Operations task {uid}",
        recommended_action=f"Execute warehouse logistics {uid}",
        responsible_department="Operations",
        suggested_owner_role="Warehouse Manager",
        suggested_deadline="2026-12-05",
        expected_outcome="Optimized",
        verification_criteria="Done",
        investigation_id=f"INV-OPS-{uid}",
        anomaly_id=f"ANOM-OPS-{uid}",
    ))
    default_action_service.approve_action(action.id, ActionApproveRequest())

    # Engineering employee tries to change Operations task status
    res = client.patch(
        f"/api/tasks/{action.id}/status",
        json={"new_status": ActionStatus.IN_PROGRESS.value},
        headers=employee_headers,
    )
    assert res.status_code == 403
    assert "outside your department" in res.json()["detail"]

    # Engineering employee tries to add note to Operations task
    note_res = client.post(
        f"/api/tasks/{action.id}/notes",
        json={"note": "Attempted note from wrong department"},
        headers=employee_headers,
    )
    assert note_res.status_code == 403
    assert "outside your department" in note_res.json()["detail"]


def test_employee_can_modify_assigned_department_task(client, ops_employee_headers):
    """
    Resource-Level Check: Employee belonging to 'Operations' department CAN update
    an 'Operations' task status (200 OK).
    """
    uid = uuid.uuid4().hex[:6]
    action = default_action_service.create_action(ActionCreateRequest(
        problem_description=f"Operations task {uid}",
        recommended_action=f"Optimize loading dock {uid}",
        responsible_department="Operations",
        suggested_owner_role="Operations Staff",
        suggested_deadline="2026-12-05",
        expected_outcome="Optimized",
        verification_criteria="Done",
        investigation_id=f"INV-OPS-{uid}",
        anomaly_id=f"ANOM-OPS-{uid}",
    ))
    default_action_service.approve_action(action.id, ActionApproveRequest())

    # Operations employee updates Operations task
    res = client.patch(
        f"/api/tasks/{action.id}/status",
        json={"new_status": ActionStatus.IN_PROGRESS.value},
        headers=ops_employee_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == ActionStatus.IN_PROGRESS.value


def test_employee_cannot_reassign_tasks(client, ops_employee_headers):
    """Employees cannot reassign tasks regardless of department (403 Forbidden)."""
    uid = uuid.uuid4().hex[:6]
    action = default_action_service.create_action(ActionCreateRequest(
        problem_description=f"Operations task {uid}",
        recommended_action=f"Optimize loading dock {uid}",
        responsible_department="Operations",
        suggested_owner_role="Operations Staff",
        suggested_deadline="2026-12-05",
        expected_outcome="Optimized",
        verification_criteria="Done",
        investigation_id=f"INV-OPS-{uid}",
        anomaly_id=f"ANOM-OPS-{uid}",
    ))
    default_action_service.approve_action(action.id, ActionApproveRequest())

    res = client.patch(
        f"/api/tasks/{action.id}/assignment",
        json={"responsible_department": "Finance"},
        headers=ops_employee_headers,
    )
    assert res.status_code == 403
    assert "task:assign" in res.json()["detail"]
