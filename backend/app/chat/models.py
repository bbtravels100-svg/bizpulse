from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=6000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: List[ChatTurn] = Field(default_factory=list, max_length=20)


class InvestigationBrief(BaseModel):
    """Subset of the existing orchestrator's WriterOutput, presented in chat."""
    orchestration_id: str
    anomaly_id: str
    executive_summary: str
    problem_statement: str
    confirmed_evidence: List[str]
    likely_causes: List[str]
    target_team_and_priority: str
    recommended_action_plan: List[str]
    verification_and_success_criteria: List[str]


class AnalyticsAnswer(BaseModel):
    """Structured Gemini answer grounded in Python analytics data."""
    answer: str
    confirmed_facts: List[str] = Field(default_factory=list)
    possible_explanations: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    intent: Literal["investigation", "analytics", "general"]
    reply: str
    confirmed_facts: List[str] = Field(default_factory=list)
    possible_explanations: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    investigation: Optional[InvestigationBrief] = None
    # Set when an existing anomaly could be turned into action proposals.
    # Nothing is created until the user explicitly requests it.
    anomaly_id: Optional[str] = None
    can_propose_actions: bool = False
    data_sources_used: List[str] = Field(default_factory=list)
    model_used: str
    generated_at: str
