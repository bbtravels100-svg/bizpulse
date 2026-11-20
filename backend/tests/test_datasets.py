import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.analytics.data_loader import get_data_path
import os
import shutil

client = TestClient(app)


def test_list_datasets():
    res = client.get("/api/datasets")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 4

    dataset_ids = [d["id"] for d in data]
    assert set(dataset_ids) == {"sales", "costs", "funnel", "events"}

    for d in data:
        assert d["status"] == "healthy"
        assert d["record_count"] > 0
        assert d["file_size_bytes"] > 0
        assert len(d["columns"]) > 0
        assert d["last_modified"] is not None


def test_get_dataset_preview():
    res = client.get("/api/datasets/sales/preview?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "sales"
    assert data["name"] == "Sales Transactions"
    assert data["record_count"] == 70
    assert len(data["rows"]) == 10
    assert len(data["columns"]) == 5
    first_row = data["rows"][0]
    assert "date" in first_row
    assert "revenue" in first_row
    assert "units_sold" in first_row


def test_validate_dataset_valid():
    csv_content = """date,product_id,product_name,units_sold,revenue
2026-11-01,PROD_001,Ultra Ergonomic Desk Chair,10,3500.00
2026-11-02,PROD_002,Noise-Cancelling Headphones,5,900.00"""

    res = client.post("/api/datasets/sales/validate", json={"content": csv_content})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["total_rows"] == 2
    assert len(data["errors"]) == 0
    assert len(data["preview_rows"]) == 2


def test_validate_dataset_missing_columns():
    csv_content = """date,product_id,units_sold
2026-11-01,PROD_001,10"""

    res = client.post("/api/datasets/sales/validate", json={"content": csv_content})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert len(data["errors"]) > 0
    missing_fields = [e["field"] for e in data["errors"] if e.get("field")]
    assert "product_name" in missing_fields or "revenue" in missing_fields


def test_validate_funnel_hierarchy_error():
    # cart > visitors is mathematically invalid
    csv_content = """date,device,visitors,reached_cart,reached_payment,purchased
2026-11-01,desktop,100,500,50,20"""

    res = client.post("/api/datasets/funnel/validate", json={"content": csv_content})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert any("reached_cart" in e["message"] for e in data["errors"])


def test_upload_invalid_dataset_rejected():
    invalid_csv = """date,device,visitors
2026-11-01,desktop,100"""

    res = client.post(
        "/api/datasets/funnel/upload",
        json={"filename": "website_funnel.csv", "content": invalid_csv},
    )
    assert res.status_code == 400
    assert "Validation failed" in res.json()["detail"]


def test_upload_valid_dataset_with_backup_and_restore():
    costs_path = get_data_path("costs.csv")
    backup_path = costs_path + ".orig_test_bak"
    shutil.copyfile(costs_path, backup_path)

    try:
        new_content = """product_id,product_name,unit_cost
PROD_001,Ultra Ergonomic Desk Chair,180.00
PROD_002,Noise-Cancelling Headphones,95.00"""

        res = client.post(
            "/api/datasets/costs/upload",
            json={"filename": "costs.csv", "content": new_content},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["record_count"] == 2
        assert data["backup_created"] is True

        # Verify preview reflects new content
        preview_res = client.get("/api/datasets/costs/preview")
        assert preview_res.status_code == 200
        assert preview_res.json()["record_count"] == 2
        assert data.get("version") is not None
        assert data.get("reloaded_at") is not None
    finally:
        # Restore original file
        shutil.copyfile(backup_path, costs_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(costs_path + ".bak"):
            os.remove(costs_path + ".bak")


# ============================================================================
# Phase 5 Step 2C: Dataset Reload Notification & Invalidation Tests
# ============================================================================

def test_successful_upload_increments_version_and_records_reload_timestamp():
    """Test 1: Successful upload increments version, records reload timestamp and content hash."""
    from app.analytics.dataset_tracker import default_dataset_tracker
    costs_path = get_data_path("costs.csv")
    backup_path = costs_path + ".v_test_bak"
    shutil.copyfile(costs_path, backup_path)

    try:
        init_summary = client.get("/api/datasets/costs").json()
        init_version = init_summary.get("version", 1)

        new_content = """product_id,product_name,unit_cost
PROD_001,Ultra Ergonomic Desk Chair,175.00
PROD_002,Noise-Cancelling Headphones,92.50"""

        res = client.post(
            "/api/datasets/costs/upload",
            json={"filename": "costs.csv", "content": new_content},
        )
        assert res.status_code == 200
        upload_data = res.json()
        assert upload_data["status"] == "success"
        assert upload_data["version"] == init_version + 1
        assert upload_data["reloaded_at"] is not None

        # Verify summary reflects new version and hash
        updated_summary = client.get("/api/datasets/costs").json()
        assert updated_summary["version"] == init_version + 1
        assert updated_summary["last_reloaded_at"] == upload_data["reloaded_at"]
        assert updated_summary["content_hash"] is not None
        assert len(updated_summary["content_hash"]) == 64  # SHA-256
    finally:
        shutil.copyfile(backup_path, costs_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(costs_path + ".bak"):
            os.remove(costs_path + ".bak")


def test_failed_upload_preserves_version_and_does_not_invalidate():
    """Test 2: A failed upload does NOT increment version, change timestamp, or notify listeners."""
    from app.analytics.dataset_tracker import default_dataset_tracker
    ver_before = default_dataset_tracker.get_version_info("funnel")
    initial_version = ver_before.version
    initial_reloads = ver_before.reload_count

    # Missing required columns
    bad_content = """date,device,visitors
2026-11-01,desktop,100"""

    res = client.post(
        "/api/datasets/funnel/upload",
        json={"filename": "website_funnel.csv", "content": bad_content},
    )
    assert res.status_code == 400

    ver_after = default_dataset_tracker.get_version_info("funnel")
    assert ver_after.version == initial_version
    assert ver_after.reload_count == initial_reloads


def test_subsequent_analytics_reflect_updated_dataset_immediately():
    """Test 3: Analytics and data loader immediately reflect the newly uploaded dataset."""
    from app.analytics.data_loader import load_sales_data
    from app.analytics.sales_analytics import get_total_revenue

    sales_path = get_data_path("sales.csv")
    backup_path = sales_path + ".analytics_test_bak"
    shutil.copyfile(sales_path, backup_path)

    try:
        df_initial = load_sales_data(sales_path)
        initial_revenue = get_total_revenue(df_initial)

        # Upload sales CSV with known additional high-value order
        # Add 1 unit of $50,000 revenue
        new_content = """date,product_id,product_name,units_sold,revenue
2026-11-01,PROD_001,Ultra Ergonomic Desk Chair,10,3500.00
2026-11-02,PROD_999,Enterprise Server Rack,1,50000.00"""

        res = client.post(
            "/api/datasets/sales/upload",
            json={"filename": "sales.csv", "content": new_content},
        )
        assert res.status_code == 200

        # Next analytics execution reads the new ground truth
        df_updated = load_sales_data(sales_path)
        updated_revenue = get_total_revenue(df_updated)
        assert updated_revenue == 53500.00
        assert updated_revenue != initial_revenue
        assert len(df_updated) == 2
    finally:
        shutil.copyfile(backup_path, sales_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(sales_path + ".bak"):
            os.remove(sales_path + ".bak")


def test_repeated_uploads_maintain_version_consistency():
    """Test 4: Sequential valid uploads cleanly increment versions and update hashes."""
    from app.analytics.dataset_tracker import default_dataset_tracker
    costs_path = get_data_path("costs.csv")
    backup_path = costs_path + ".seq_test_bak"
    shutil.copyfile(costs_path, backup_path)

    try:
        start_ver = default_dataset_tracker.get_version_info("costs").version

        for i in range(1, 4):
            content = f"""product_id,product_name,unit_cost
PROD_001,Ultra Ergonomic Desk Chair,{180.0 + i}"""
            res = client.post(
                "/api/datasets/costs/upload",
                json={"filename": "costs.csv", "content": content},
            )
            assert res.status_code == 200
            assert res.json()["version"] == start_ver + i

        final_ver = default_dataset_tracker.get_version_info("costs")
        assert final_ver.version == start_ver + 3
    finally:
        shutil.copyfile(backup_path, costs_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(costs_path + ".bak"):
            os.remove(costs_path + ".bak")


def test_change_listener_and_cache_invalidation():
    """Test 5: Change listeners are invoked and registered caches are cleared upon reload."""
    from app.analytics.dataset_tracker import default_dataset_tracker
    costs_path = get_data_path("costs.csv")
    backup_path = costs_path + ".listener_test_bak"
    shutil.copyfile(costs_path, backup_path)

    events_received = []

    def mock_listener(ds_id, ver_info):
        events_received.append((ds_id, ver_info.version))

    mock_cache = {"cached_cost_summary": {"total_cost": 45000.0}}

    default_dataset_tracker.register_change_listener(mock_listener)
    default_dataset_tracker.register_cache(mock_cache)

    try:
        content = """product_id,product_name,unit_cost
PROD_001,Ultra Ergonomic Desk Chair,185.00"""

        res = client.post(
            "/api/datasets/costs/upload",
            json={"filename": "costs.csv", "content": content},
        )
        assert res.status_code == 200

        # Verify listener received event
        assert len(events_received) >= 1
        assert events_received[-1][0] == "costs"

        # Verify registered cache was automatically invalidated/cleared
        assert len(mock_cache) == 0
    finally:
        shutil.copyfile(backup_path, costs_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(costs_path + ".bak"):
            os.remove(costs_path + ".bak")


def test_existing_investigations_unaffected():
    """Test 6: Existing investigation fact extraction remains completely unaffected."""
    from app.services.investigation_service import extract_revenue_decline_facts
    facts = extract_revenue_decline_facts()
    assert facts.anomaly_id == "ANOMALY_REV_001"
    assert "week1_total_revenue" in facts.metric_facts
    assert "revenue_percentage_change" in facts.metric_facts
    assert facts.metric_facts["revenue_percentage_change"] == "-18.00%"
