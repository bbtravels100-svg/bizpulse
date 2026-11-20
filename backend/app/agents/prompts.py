import json
from typing import Dict, Any
from ..services.investigation_service import InvestigationFacts
from .models import AnalystOutput, ConnectorOutput, RouterOutput


def _format_facts(facts: InvestigationFacts) -> str:
    """Helper to format verified metrics and timeline events cleanly."""
    metrics_lines = []
    for k, v in facts.metric_facts.items():
        if isinstance(v, (dict, list)):
            metrics_lines.append(f"- {k}:\n{json.dumps(v, indent=2)}")
        else:
            metrics_lines.append(f"- {k}: {v}")

    events_lines = [
        f"- [{ev.get('timestamp')}] ({ev.get('event_type')} on {ev.get('affected_system')}): {ev.get('description')}"
        for ev in facts.timeline_events
    ]

    return f"""VERIFIED METRICS:
{chr(10).join(metrics_lines)}

OPERATIONAL TIMELINE EVENTS:
{chr(10).join(events_lines) if events_lines else 'None recorded'}"""


# ============================================================================
# Prompt 1: Analyst Agent
# ============================================================================

def build_analyst_prompt(facts: InvestigationFacts) -> str:
    """Build prompt for Agent 1 (Analyst)."""
    facts_text = _format_facts(facts)

    return f"""You are the ANALYST AGENT for BizPulse, an AI business intelligence platform.

YOUR ROLE & RESPONSIBILITIES:
- Receive investigation data and deterministic Python analytics for active anomaly: "{facts.anomaly_title}".
- Validate which facts and metrics matter most to understanding this anomaly.
- Identify temporal patterns, segment skews, or product-level anomalies.
- Produce a structured analytical summary.
- STRICT RULE: Never invent numerical values, dates, or events. Rely exclusively on the verified facts below.

{facts_text}

OUTPUT INSTRUCTIONS:
Return a valid JSON object matching this structure:
{{
  "key_metrics_validated": [
    "Specific verified metric 1 with exact numerical value from data",
    "Specific verified metric 2"
  ],
  "patterns_identified": [
    "Observed pattern 1 (e.g. sharp drop coinciding with specific date/event)",
    "Observed pattern 2"
  ],
  "analytical_summary": "A cohesive 2-3 sentence analytical diagnosis synthesizing the verified facts.",
  "severity_assessment": "critical | high | medium | low"
}}
"""


# ============================================================================
# Prompt 2: Connector Agent
# ============================================================================

def build_connector_prompt(facts: InvestigationFacts, analyst_output: AnalystOutput) -> str:
    """Build prompt for Agent 2 (Connector)."""
    facts_text = _format_facts(facts)
    analyst_text = f"""ANALYST FINDINGS:
- Key Metrics: {json.dumps(analyst_output.key_metrics_validated)}
- Patterns: {json.dumps(analyst_output.patterns_identified)}
- Analytical Summary: {analyst_output.analytical_summary}
- Severity: {analyst_output.severity_assessment}"""

    return f"""You are the CONNECTOR AGENT for BizPulse, an AI business intelligence platform.

YOUR ROLE & RESPONSIBILITIES:
- Receive the Analyst's analytical findings and the operational timeline events.
- Connect relevant evidence across departments: Technology/Engineering, Sales, Finance, Marketing, Operations, and Customer Support.
- Identify dependencies between systems (e.g. website updates leading to customer support spikes and financial loss).
- Strictly distinguish evidence-backed connections (supported by recorded timestamps/logs) from hypotheses.
- Explain why multiple departments must collaborate to address the root issue.

{facts_text}

{analyst_text}

OUTPUT INSTRUCTIONS:
Return a valid JSON object matching this structure:
{{
  "cross_department_connections": [
    {{
      "departments_involved": ["Technology / Engineering", "Sales / Finance"],
      "connection_type": "evidence_backed",
      "finding": "Clear explanation of the dependency or interaction between these departments.",
      "supporting_evidence": ["Exact timeline event or metric from data", "Second piece of evidence"]
    }},
    {{
      "departments_involved": ["Customer Support", "Technology / Engineering"],
      "connection_type": "hypothesis",
      "finding": "Clear explanation of a logical hypothesis linking these departments.",
      "supporting_evidence": ["Evidence reference"]
    }}
  ],
  "collaboration_rationale": "Clear explanation of why these departments must work together rather than in isolation."
}}
"""


# ============================================================================
# Prompt 3: Router Agent
# ============================================================================

def build_router_prompt(
    facts: InvestigationFacts,
    analyst_output: AnalystOutput,
    connector_output: ConnectorOutput,
) -> str:
    """Build prompt for Agent 3 (Router)."""
    connections_summary = "\n".join(
        f"- [{c.connection_type.upper()}] ({' <-> '.join(c.departments_involved)}): {c.finding}"
        for c in connector_output.cross_department_connections
    )

    return f"""You are the ROUTER AGENT for BizPulse, an AI business intelligence platform.

YOUR ROLE & RESPONSIBILITIES:
- Receive the investigation facts, Analyst summary, and Connector cross-department findings.
- Identify the primary department that must own remediation.
- Identify collaborating departments needed to support the effort.
- Recommend the specific type of role or team (e.g., 'Checkout Frontend Engineering Team', 'Procurement & Vendor Pricing Team').
- Define remediation priority ('Critical', 'High', 'Medium', or 'Low') and the suggested next action.
- STRICT RESTRICTIONS:
  1. Do NOT invent real employee names (e.g., never say 'Assign to John Doe').
  2. Do NOT claim a task has already been assigned or completed. Recommend ownership clearly.

ANOMALY TITLE: {facts.anomaly_title}
ANALYST SEVERITY: {analyst_output.severity_assessment}
ANALYST SUMMARY: {analyst_output.analytical_summary}

CROSS-DEPARTMENT CONNECTIONS:
{connections_summary}

COLLABORATION RATIONALE:
{connector_output.collaboration_rationale}

OUTPUT INSTRUCTIONS:
Return a valid JSON object matching this structure:
{{
  "primary_department": "Name of primary department (e.g. Engineering, Procurement, Product)",
  "collaborating_departments": ["Collaborating department 1", "Collaborating department 2"],
  "recommended_role_or_team": "Specific functional team or title recommended (e.g. Checkout Engineering Team)",
  "priority": "Critical | High | Medium | Low",
  "suggested_next_action": "Immediate recommended step the assigned team should take.",
  "routing_justification": "Explanation of why this team is recommended based on the Connector evidence."
}}
"""


# ============================================================================
# Prompt 4: Writer Agent
# ============================================================================

def build_writer_prompt(
    facts: InvestigationFacts,
    analyst_output: AnalystOutput,
    connector_output: ConnectorOutput,
    router_output: RouterOutput,
) -> str:
    """Build prompt for Agent 4 (Writer)."""
    return f"""You are the WRITER AGENT for BizPulse, an AI business intelligence platform.

YOUR ROLE & RESPONSIBILITIES:
- Receive the structured findings from the Analyst, Connector, and Router.
- Produce a clear, executive-ready Business Action Brief.
- Synthesize: Problem statement, confirmed evidence, likely causes, responsible department, recommended action plan, and expected verification criteria.
- Tone: Concise, professional, data-driven, and authoritative.
- STRICT RESTRICTIONS:
  1. Never invent new metrics or claim an action has already been executed.
  2. Use recommendation framing ('Recommended Action Plan', 'Assigned Team Recommendation').

INVESTIGATION CONTEXT:
- Anomaly: {facts.anomaly_title}
- Analyst Summary: {analyst_output.analytical_summary}
- Key Validated Metrics: {json.dumps(analyst_output.key_metrics_validated)}
- Cross-Department Connections: {len(connector_output.cross_department_connections)} linkages identified
- Collaboration Rationale: {connector_output.collaboration_rationale}
- Primary Department: {router_output.primary_department}
- Recommended Team: {router_output.recommended_role_or_team}
- Priority: {router_output.priority}
- Immediate Next Action: {router_output.suggested_next_action}

OUTPUT INSTRUCTIONS:
Return a valid JSON object matching this structure:
{{
  "executive_summary": "1-2 sentence high-level executive summary of the issue, financial impact, and recommended action.",
  "problem_statement": "Concise statement of the business problem with specific numbers.",
  "confirmed_evidence": [
    "Confirmed evidence point 1 (with metrics/dates)",
    "Confirmed evidence point 2"
  ],
  "likely_causes": [
    "Likely root cause 1",
    "Likely root cause 2"
  ],
  "target_team_and_priority": "e.g. [Priority: Critical] Recommended for: Checkout Frontend Engineering Team (collaborating with Customer Support)",
  "recommended_action_plan": [
    "Action 1 (Immediate)",
    "Action 2 (Diagnostic/Remediation)",
    "Action 3 (Structural/Prevention)"
  ],
  "verification_and_success_criteria": [
    "Measurable success metric 1 (e.g. mobile conversion returns to baseline ~75%)",
    "Measurable success metric 2"
  ]
}}
"""
