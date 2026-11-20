import time
import subprocess
import httpx
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_live_api():
    print("Starting FastAPI backend on 127.0.0.1:8000...")
    proc = subprocess.Popen(
        ["D:\\Bizpulse\\backend\\.venv\\Scripts\\uvicorn.exe", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd="D:\\Bizpulse\\backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    client = httpx.Client(base_url=BASE_URL, timeout=5.0)

    # Wait for server to come up
    for i in range(15):
        time.sleep(0.5)
        try:
            r = client.get("/api/health")
            if r.status_code == 200:
                print(f"Backend ready after {(i+1)*0.5:.1f}s!")
                break
        except Exception:
            pass
    else:
        print("Backend failed to start in time.")
        proc.kill()
        sys.exit(1)

    endpoints = [
        ("GET", "/api/health", {}),
        ("GET", "/api/overview", {}),
        ("GET", "/api/sales", {}),
        ("GET", "/api/products/profitability", {"low_margin_threshold": "15.0"}),
        ("GET", "/api/funnel", {}),
        ("GET", "/api/anomalies", {}),
        ("GET", "/api/events", {}),
        ("GET", "/", {}),
    ]

    results = []
    try:
        print("\nTesting all endpoints live...")
        for method, path, params in endpoints:
            t0 = time.time()
            resp = client.get(path, params=params)
            elapsed_ms = round((time.time() - t0) * 1000, 1)

            status = resp.status_code
            data = resp.json()

            summary = ""
            if path == "/api/health":
                summary = f"status={data.get('status')}, service={data.get('service')}"
            elif path == "/api/overview":
                summary = f"revenue=${data.get('total_revenue'):,.2f}, WoW={data.get('week_over_week', {}).get('percentage_change')}%, anomalies={data.get('anomalies_detected_count')}"
            elif path == "/api/sales":
                summary = f"revenue=${data.get('total_revenue'):,.2f}, products_count={len(data.get('products', []))}, daily_count={len(data.get('daily_trend', []))}"
            elif path == "/api/products/profitability":
                low = [p['product_name'] for p in data.get('products', []) if p.get('is_low_margin')]
                summary = f"total_products={data.get('total_products')}, low_margin_flagged={low}"
            elif path == "/api/funnel":
                mobile_drop = data.get('device_comparison', {}).get('mobile', {}).get('payment_completion_relative_change_pct')
                det = data.get('device_comparison', {}).get('mobile', {}).get('deterioration_detected')
                summary = f"mobile_payment_change={mobile_drop}%, mobile_deterioration={det}"
            elif path == "/api/anomalies":
                titles = [f"[{a['category']}] {a['title']}" for a in data.get('anomalies', [])]
                summary = f"count={data.get('count')}, list={titles}"
            elif path == "/api/events":
                summary = f"events_count={data.get('count')}"
            elif path == "/":
                summary = f"message='{data.get('message')}', endpoints_count={len(data.get('endpoints', {}))}"

            results.append({
                "endpoint": path,
                "status_code": status,
                "latency_ms": elapsed_ms,
                "summary": summary
            })
            print(f"[{status}] {path:<26} ({elapsed_ms:>5.1f}ms) -> {summary}")

    finally:
        print("\nStopping backend server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        print("Backend server stopped.")

if __name__ == "__main__":
    test_live_api()
