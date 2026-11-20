import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Set pythonpath to backend root
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

ANOMALIES = [
    {
        "id": "ANOMALY_REV_001",
        "name": "Problem 1: Week 1 vs Week 2 Revenue Decline (-18.00%)",
    },
    {
        "id": "ANOMALY_PROFIT_PROD_005",
        "name": "Problem 2: Low Product Profitability (PROD_005 at 4.00% gross margin)",
    },
    {
        "id": "ANOMALY_FUNNEL_MOBILE_001",
        "name": "Problem 3: Mobile Payment Completion Deterioration (74.98% -> 21.95%)",
    },
]

def main():
    print("=" * 80)
    print("BIZPULSE PHASE 2C: MULTI-PROBLEM BUSINESS INVESTIGATION LIVE VERIFICATION")
    print("=" * 80)

    results = {}

    for item in ANOMALIES:
        anomaly_id = item["id"]
        anomaly_name = item["name"]
        print(f"\n[RUNNING INVESTIGATION] {anomaly_name}")
        print(f"Anomaly ID: {anomaly_id}")
        t0 = time.time()

        resp = client.post("/api/investigate", json={"anomaly_id": anomaly_id})
        duration = time.time() - t0

        if resp.status_code != 200:
            print(f"❌ FAILED ({resp.status_code}): {resp.text}")
            continue

        data = resp.json()
        results[anomaly_id] = data

        print(f"✅ COMPLETED in {duration:.2f}s | Investigation ID: {data['investigation_id']} | Model: {data['model_used']}")
        print("\n--- CONFIRMED FACTS (Computed Deterministically by Python Engine) ---")
        for k, v in data["facts"]["metric_facts"].items():
            if isinstance(v, list):
                print(f"  • {k}: [{len(v)} items]")
            elif isinstance(v, dict):
                print(f"  • {k}: {json.dumps(v, indent=4)}")
            else:
                print(f"  • {k}: {v}")

        print(f"\n  Correlated Timeline Events: {len(data['facts']['timeline_events'])} events")
        for ev in data["facts"]["timeline_events"][:3]:
            print(f"    - [{ev['timestamp']}] ({ev['event_type']}): {ev['description']}")

        print("\n--- AI-GENERATED BUSINESS ANALYSIS (Google Gemini) ---")
        print(f"  What Happened: {data['analysis']['what_happened']}")
        print(f"  Why Important: {data['analysis']['why_important']}")
        print(f"  Responsible Department: {data['analysis']['responsible_department']}")
        print("\n  Causal Hypotheses:")
        for idx, h in enumerate(data['analysis']['hypotheses'], 1):
            print(f"    {idx}. [{h['confidence_level'].upper()} CONFIDENCE] {h['cause']}")
            for ev in h['supporting_evidence']:
                print(f"       - {ev}")

        print("\n  Recommended Actions:")
        for act in data['analysis']['recommended_actions']:
            print(f"    👉 {act}")

        print("\n  Verification Steps:")
        for ver in data['analysis']['verification_steps']:
            print(f"    🔍 {ver}")

        print("-" * 80)

    # Save full results to a JSON file for documentation
    output_path = backend_dir / "scripts" / "live_investigation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved complete investigation outputs to: {output_path}")

if __name__ == "__main__":
    main()
