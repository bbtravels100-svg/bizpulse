from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.models import WriterOutput
from app.main import app
from app.services.gemini_service import GeminiAuthError

client = TestClient(app)


def _fake_orchestration(status="completed"):
    brief = WriterOutput(
        executive_summary="Mobile payment completion fell sharply.",
        problem_statement="Mobile payment completion dropped.",
        confirmed_evidence=["Mobile payment completion fell in Week 2."],
        likely_causes=["Possible: frontend release affected the mobile payment sheet."],
        target_team_and_priority="Engineering - Critical",
        recommended_action_plan=["Review the release."],
        verification_and_success_criteria=["Completion recovers."],
    )
    stage = SimpleNamespace(status="completed", agent_name="X")
    return SimpleNamespace(
        status=status,
        final_action_brief=brief if status == "completed" else None,
        orchestration_id="ORCH-TEST",
        anomaly_id="ANOMALY_FUNNEL_MOBILE_001",
        model_used="test-model",
        stages=SimpleNamespace(analyst=stage, connector=stage, router=stage, writer=stage),
    )


def test_investigation_uses_existing_orchestrator():
    with patch("app.chat.service.generate_json", return_value={"intent": "investigation", "anomaly_id": "ANOMALY_FUNNEL_MOBILE_001"}), \
         patch("app.chat.service.run_agent_pipeline", return_value=_fake_orchestration()) as pipe:
        r = client.post("/api/chat", json={"message": "What is happening with mobile conversions?"})
    assert r.status_code == 200
    body = r.json()
    pipe.assert_called_once_with(anomaly_id="ANOMALY_FUNNEL_MOBILE_001")
    assert body["intent"] == "investigation"
    assert body["can_propose_actions"] is True
    assert body["anomaly_id"] == "ANOMALY_FUNNEL_MOBILE_001"
    assert body["confirmed_facts"] and body["possible_explanations"]
    assert body["investigation"]["orchestration_id"] == "ORCH-TEST"


def test_analytics_answer_grounded_in_python_data():
    answer = {
        "answer": "Total revenue is as reported.",
        "confirmed_facts": ["Revenue fell week over week."],
        "possible_explanations": [],
        "follow_up_questions": ["Which product declined most?"],
    }
    calls = []

    def fake_json(prompt, model_name=None):
        calls.append(prompt)
        return {"intent": "analytics", "anomaly_id": None} if len(calls) == 1 else answer

    with patch("app.chat.service.generate_json", side_effect=fake_json), \
         patch("app.chat.service.run_agent_pipeline") as pipe:
        r = client.post("/api/chat", json={"message": "What is our total revenue?", "history": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "analytics"
    assert body["can_propose_actions"] is False
    assert body["investigation"] is None
    pipe.assert_not_called()
    # The grounding prompt carries real engine output (154700.0 total revenue in the dataset).
    assert "154700" in calls[1]


def test_classifier_failure_falls_back_to_keywords():
    seq = [ValueError("bad json"), {"answer": "ok", "confirmed_facts": [], "possible_explanations": [], "follow_up_questions": []}]

    def fake_json(prompt, model_name=None):
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch("app.chat.service.generate_json", side_effect=fake_json):
        r = client.post("/api/chat", json={"message": "Which product sells the most?"})
    assert r.status_code == 200
    assert r.json()["intent"] == "analytics"


def test_unknown_anomaly_id_from_classifier_is_not_investigated():
    seq = [{"intent": "investigation", "anomaly_id": "ANOMALY_FAKE"}, {"answer": "ok"}]
    with patch("app.chat.service.generate_json", side_effect=lambda *a, **k: seq.pop(0)), \
         patch("app.chat.service.run_agent_pipeline") as pipe:
        r = client.post("/api/chat", json={"message": "why?"})
    assert r.status_code == 200
    pipe.assert_not_called()


def test_failed_investigation_returns_error_not_fake_answer():
    bad = _fake_orchestration(status="failed")
    bad.stages.analyst = SimpleNamespace(status="failed", agent_name="Analyst")
    with patch("app.chat.service.generate_json", return_value={"intent": "investigation", "anomaly_id": "ANOMALY_REV_001"}), \
         patch("app.chat.service.run_agent_pipeline", return_value=bad):
        r = client.post("/api/chat", json={"message": "why did revenue decline"})
    assert r.status_code == 502
    assert "Analyst" in r.json()["detail"]


def test_malformed_ai_answer_returns_502():
    seq = [{"intent": "analytics", "anomaly_id": None}, {"unexpected": True}]
    with patch("app.chat.service.generate_json", side_effect=lambda *a, **k: seq.pop(0)):
        r = client.post("/api/chat", json={"message": "revenue?"})
    assert r.status_code == 502


def test_auth_error_maps_to_401_without_leaking_key():
    with patch("app.chat.service.generate_json", side_effect=GeminiAuthError("Authentication failed")):
        r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 401


def test_validation_rejects_empty_and_oversized_messages():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 2001}).status_code == 422


def test_transient_503_is_retried_then_succeeds():
    from app.services.gemini_service import GeminiServiceError

    calls = {"n": 0}

    def flaky(prompt, model_name=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise GeminiServiceError("Gemini API error (503): 503 UNAVAILABLE")
        return {"intent": "general", "anomaly_id": None} if calls["n"] == 2 else {"answer": "Hello!"}

    with patch("app.chat.service.generate_json", side_effect=flaky), patch("app.chat.service.time.sleep"):
        r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert r.json()["reply"] == "Hello!"
    assert calls["n"] == 3


def test_persistent_503_returns_502_after_retries():
    from app.services.gemini_service import GeminiServiceError

    with patch("app.chat.service.generate_json", side_effect=GeminiServiceError("503 UNAVAILABLE")) as g, \
         patch("app.chat.service.time.sleep"):
        r = client.post("/api/chat", json={"message": "hello"})
    # classifier falls back to keywords (3 attempts), then answer call fails (3 attempts)
    assert r.status_code == 502
    assert g.call_count == 6
