import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check_preserved(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "BizPulse API"

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data

def test_overview_endpoint(client):
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 154700.00
    assert data["week_over_week"]["percentage_change"] == -18.0
    assert data["anomalies_detected_count"] >= 3

def test_sales_endpoint(client):
    response = client.get("/api/sales")
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue"] == 154700.00
    assert len(data["products"]) == 5
    assert len(data["daily_trend"]) == 14

def test_product_profitability_endpoint(client):
    response = client.get("/api/products/profitability?low_margin_threshold=15.0")
    assert response.status_code == 200
    data = response.json()
    assert data["low_margin_products_count"] >= 1
    # Check that PROD_005 is in the list with 4.0% margin
    stand = next(p for p in data["products"] if p["product_id"] == "PROD_005")
    assert stand["gross_profit_margin_pct"] == 4.0
    assert stand["is_low_margin"] is True

def test_funnel_endpoint(client):
    response = client.get("/api/funnel")
    assert response.status_code == 200
    data = response.json()
    assert "overall_funnel" in data
    assert "device_comparison" in data
    assert data["device_comparison"]["mobile"]["deterioration_detected"] is True

def test_anomalies_endpoint(client):
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 3
    # Check that supporting evidence is present
    for anomaly in data["anomalies"]:
        assert "supporting_evidence" in anomaly
        assert "recommended_actions" in anomaly

def test_events_endpoint(client):
    response = client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 5
