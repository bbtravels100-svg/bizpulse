import time
import subprocess
import httpx
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoints_live():
    print("=" * 70)
    print("BIZPULSE - LIVE HTTP ENDPOINTS TEST (/api/gemini/test & /api/investigate)")
    print("=" * 70)
    print("Starting FastAPI backend on 127.0.0.1:8000...")

    proc = subprocess.Popen(
        ["D:\\Bizpulse\\backend\\.venv\\Scripts\\uvicorn.exe", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd="D:\\Bizpulse\\backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    for i in range(15):
        time.sleep(0.5)
        try:
            r = client.get("/api/health")
            if r.status_code == 200:
                print(f"Backend ready in {(i+1)*0.5:.1f}s.")
                break
        except Exception:
            pass
    else:
        print("Backend failed to start in time.")
        proc.kill()
        sys.exit(1)

    try:
        # 1. Test /api/gemini/test
        print("\n1. Testing POST /api/gemini/test...")
        t0 = time.time()
        resp_test = client.post("/api/gemini/test", json={"prompt": "You are connected to BizPulse. Reply with: Gemini connection successful."})
        elapsed_test = round((time.time() - t0) * 1000, 1)
        print(f"Status: {resp_test.status_code} in {elapsed_test}ms")
        data_test = resp_test.json()
        print(f"Response: {data_test}")
        assert resp_test.status_code == 200
        assert data_test["connection_status"] == "connected"

        # 2. Test POST /api/investigate
        print("\n2. Testing POST /api/investigate...")
        t0 = time.time()
        resp_inv = client.post("/api/investigate", json={"anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"})
        elapsed_inv = round((time.time() - t0) * 1000, 1)
        print(f"Status: {resp_inv.status_code} in {elapsed_inv}ms")
        data_inv = resp_inv.json()
        assert resp_inv.status_code == 200
        assert data_inv["status"] == "completed"
        assert "facts" in data_inv
        assert "analysis" in data_inv
        print(f"Investigation ID: {data_inv['investigation_id']}")
        print(f"What happened: {data_inv['analysis']['what_happened']}")
        print(f"Department: {data_inv['analysis']['responsible_department']}")
        print(f"Hypotheses count: {len(data_inv['analysis']['hypotheses'])}")
        print("\nALL LIVE HTTP TESTS PASSED!")

    finally:
        print("\nStopping backend server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        print("Backend server stopped.")

if __name__ == '__main__':
    test_endpoints_live()
