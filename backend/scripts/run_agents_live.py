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

ANOMALY_TEST_CASES = [
    {
        "id": "ANOMALY_FUNNEL_MOBILE_001",
        "label": "Mobile Payment Completion Deterioration",
    },
    {
        "id": "ANOMALY_REV_001",
        "label": "Week 1 vs Week 2 Revenue Decline",
    },
    {
        "id": "ANOMALY_PROFIT_PROD_005",
        "label": "Low Gross Margin for Heavy Duty Monitor Stand",
    },
]

def run_live_test(anomaly_id: str, label: str):
    print("\n" + "=" * 90)
    print(f"BIZPULSE MULTI-AGENT ORCHESTRATION: {label.upper()}")
    print(f"Anomaly ID: {anomaly_id}")
    print("=" * 90)

    t0 = time.time()
    resp = client.post("/api/agents/run", json={"anomaly_id": anomaly_id})
    elapsed = time.time() - t0

    if resp.status_code != 200:
        print(f"❌ FAILED with status {resp.status_code}: {resp.text}")
        return None

    data = resp.json()

    print(f"\n✅ PIPELINE COMPLETED in {elapsed:.2f}s | Orchestration ID: {data['orchestration_id']} | Status: {data['status']}")
    print(f"Model: {data['model_used']} | Generated At: {data['created_at']}")

    # 1. Facts
    print("\n" + "-" * 40 + " DETERMINISTIC FACTS (PYTHON ENGINE) " + "-" * 40)
    print(f"Title: {data['facts']['anomaly_title']}")
    for k, v in list(data['facts']['metric_facts'].items())[:5]:
        if isinstance(v, (dict, list)):
            print(f"  • {k}: {type(v).__name__} ({len(v)} items)")
        else:
            print(f"  • {k}: {v}")

    # 2. Stage 1: Analyst
    analyst = data["stages"]["analyst"]
    print("\n" + "-" * 40 + f" AGENT 1: ANALYST ({analyst['duration_ms']:.0f}ms) " + "-" * 40)
    print(f"Status: {analyst['status'].upper()}")
    if analyst["output"]:
        out = analyst["output"]
        print(f"Severity: {out['severity_assessment'].upper()}")
        print(f"Analytical Summary: {out['analytical_summary']}")
        print("Validated Key Metrics:")
        for m in out["key_metrics_validated"]:
            print(f"  ✓ {m}")
        print("Patterns Identified:")
        for p in out["patterns_identified"]:
            print(f"  🔍 {p}")

    # 3. Stage 2: Connector
    connector = data["stages"]["connector"]
    print("\n" + "-" * 40 + f" AGENT 2: CONNECTOR ({connector['duration_ms']:.0f}ms) " + "-" * 40)
    print(f"Status: {connector['status'].upper()}")
    if connector["output"]:
        out = connector["output"]
        print("Cross-Department Connections:")
        for conn in out["cross_department_connections"]:
            depts = " <-> ".join(conn["departments_involved"])
            print(f"  🔗 [{conn['connection_type'].upper()}] ({depts})")
            print(f"     Finding: {conn['finding']}")
            for ev in conn["supporting_evidence"]:
                print(f"     Evidence: {ev}")
        print(f"Collaboration Rationale: {out['collaboration_rationale']}")

    # 4. Stage 3: Router
    router = data["stages"]["router"]
    print("\n" + "-" * 40 + f" AGENT 3: ROUTER ({router['duration_ms']:.0f}ms) " + "-" * 40)
    print(f"Status: {router['status'].upper()}")
    if router["output"]:
        out = router["output"]
        print(f"Primary Department: {out['primary_department']}")
        print(f"Collaborating Departments: {', '.join(out['collaborating_departments'])}")
        print(f"Recommended Role/Team: {out['recommended_role_or_team']}")
        print(f"Priority: {out['priority'].upper()}")
        print(f"Suggested Next Action: {out['suggested_next_action']}")
        print(f"Routing Justification: {out['routing_justification']}")

    # 5. Stage 4: Writer
    writer = data["stages"]["writer"]
    print("\n" + "-" * 40 + f" AGENT 4: WRITER ({writer['duration_ms']:.0f}ms) " + "-" * 40)
    print(f"Status: {writer['status'].upper()}")
    if writer["output"]:
        out = writer["output"]
        print(f"Executive Summary:\n  {out['executive_summary']}")
        print(f"\nProblem Statement:\n  {out['problem_statement']}")
        print(f"\nTarget Team & Priority:\n  {out['target_team_and_priority']}")
        print("\nConfirmed Evidence:")
        for ev in out["confirmed_evidence"]:
            print(f"  • {ev}")
        print("\nLikely Causes:")
        for c in out["likely_causes"]:
            print(f"  • {c}")
        print("\nRecommended Action Plan:")
        for idx, act in enumerate(out["recommended_action_plan"], 1):
            print(f"  {idx}. {act}")
        print("\nVerification & Success Criteria:")
        for crit in out["verification_and_success_criteria"]:
            print(f"  ✓ {crit}")

    return data


def main():
    print("=" * 90)
    print("STARTING LIVE MULTI-AGENT ORCHESTRATION VERIFICATION (GEMINI LIVE API)")
    print("=" * 90)

    # Run for Mobile Payment Anomaly as the primary showcase
    results = {}
    for case in ANOMALY_TEST_CASES:
        res = run_live_test(case["id"], case["label"])
        if res:
            results[case["id"]] = res

    # Save to JSON
    out_file = backend_dir / "scripts" / "live_multi_agent_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved live multi-agent outputs to: {out_file}")


if __name__ == "__main__":
    main()
