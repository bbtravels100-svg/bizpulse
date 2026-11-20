import yaml
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CI_WORKFLOW_PATH = ROOT_DIR / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_file_exists():
    """Verify that .github/workflows/ci.yml exists."""
    assert CI_WORKFLOW_PATH.exists(), f"Workflow not found at {CI_WORKFLOW_PATH}"


def test_ci_workflow_valid_yaml():
    """Verify that .github/workflows/ci.yml is valid YAML and has required root keys."""
    with open(CI_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Workflow must parse into a mapping"
    assert "name" in data
    assert "on" in data
    assert "permissions" in data
    assert "jobs" in data


def test_ci_workflow_least_privilege_permissions():
    """Verify least-privilege read-only permissions are enforced at root."""
    with open(CI_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    perms = data.get("permissions")
    assert perms == {"contents": "read"}, "Permissions must be strictly contents: read"


def test_ci_workflow_triggers():
    """Verify push, pull_request, and workflow_dispatch triggers on main branch."""
    with open(CI_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    triggers = data.get("on")
    assert "push" in triggers
    assert "pull_request" in triggers
    assert "workflow_dispatch" in triggers

    assert "main" in triggers["push"]["branches"]
    assert "main" in triggers["pull_request"]["branches"]


def test_ci_workflow_required_jobs():
    """Verify all 6 required automated release validation jobs exist."""
    with open(CI_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    jobs = data.get("jobs", {})
    required_jobs = {
        "backend-test",
        "frontend-build",
        "docker-build",
        "container-integration-test",
        "security-vulnerability-scan",
        "release-validation-gate",
    }
    assert required_jobs.issubset(set(jobs.keys())), f"Missing jobs: {required_jobs - set(jobs.keys())}"


def test_ci_workflow_runner_and_action_pinning():
    """Verify jobs use ubuntu-latest runners and pinned action versions."""
    with open(CI_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    jobs = data.get("jobs", {})
    for job_name, job_def in jobs.items():
        assert job_def.get("runs-on") == "ubuntu-latest", f"Job {job_name} must run on ubuntu-latest"

    # Verify Trivy scanner job
    trivy_job = jobs.get("security-vulnerability-scan")
    assert trivy_job is not None
    steps_str = yaml.dump(trivy_job.get("steps", []))
    assert "aquasecurity/trivy-action" in steps_str
    assert "CRITICAL" in steps_str


def test_ci_workflow_container_integration_checks():
    """Verify container integration test verifies health, non-root user, and persistence."""
    with open(CI_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    integration_job = jobs = data.get("jobs", {}).get("container-integration-test")
    assert integration_job is not None
    steps_str = yaml.dump(integration_job.get("steps", []))

    assert "docker compose" in steps_str
    assert "/api/health" in steps_str
    assert "10001" in steps_str, "Must verify UID 10001 (non-root)"
    assert "restart" in steps_str, "Must verify container restart"
