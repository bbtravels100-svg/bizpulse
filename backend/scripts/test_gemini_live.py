import time
import subprocess
import httpx
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_real_gemini_endpoint():
    print("=" * 60)
    print("BIZPULSE - LIVE GEMINI CONNECTIVITY VERIFICATION")
    print("=" * 60)
    print("Starting FastAPI backend on 127.0.0.1:8000...")
    
    proc = subprocess.Popen(
        ["D:\\Bizpulse\\backend\\.venv\\Scripts\\uvicorn.exe", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd="D:\\Bizpulse\\backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    client = httpx.Client(base_url=BASE_URL, timeout=180.0)

    # Wait for server ready
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
        print("\nSending live POST /api/gemini/test request to Gemini API...")
        test_payload = {
            "prompt": "You are connected to BizPulse. Reply with: Gemini connection successful."
        }
        
        t0 = time.time()
        response = client.post("/api/gemini/test", json=test_payload)
        client_latency_ms = round((time.time() - t0) * 1000, 2)

        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error details: {response.text}")
            sys.exit(1)

        data = response.json()
        print("\n--- Verified Live Response from Gemini ---")
        print(f"Connection Status:  {data.get('connection_status')}")
        print(f"Configured Model:   {data.get('model_name')}")
        print(f"Actual Response:    \"{data.get('response')}\"")
        print(f"Gemini API Latency: {data.get('response_time_ms')} ms")
        print(f"Total HTTP Latency: {client_latency_ms} ms")
        
        # Verify no secret is leaked
        dumped = json.dumps(data)
        assert "AQ.Ab8" not in dumped, "CRITICAL: API key found in response!"
        assert "api_key" not in data, "CRITICAL: api_key key found in payload!"
        print("\nSecurity check: PASSED (No credentials exposed).")

    finally:
        print("\nStopping backend server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        print("Backend server stopped.")

if __name__ == "__main__":
    test_real_gemini_endpoint()
