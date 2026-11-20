import time
import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError

from ..services.gemini_service import (
    generate_json,
    get_gemini_model_name,
    GeminiServiceError,
    _sanitize_error,
)
from ..services.investigation_service import InvestigationFacts
from .models import (
    AnalystOutput,
    ConnectorOutput,
    RouterOutput,
    WriterOutput,
    StageResult,
)
from .prompts import (
    build_analyst_prompt,
    build_connector_prompt,
    build_router_prompt,
    build_writer_prompt,
)

logger = logging.getLogger("bizpulse.agents")


class AnalystAgent:
    """
    Role 1: Analyst Agent
    Receives deterministic analytics facts, validates key metrics, identifies patterns,
    and produces an analytical summary without inventing numbers.
    """
    NAME = "Analyst"

    def run(self, facts: InvestigationFacts, model_name: Optional[str] = None) -> StageResult:
        t0 = time.perf_counter()
        model = model_name or get_gemini_model_name()
        logger.info(f"[{self.NAME}] Starting analysis for anomaly {facts.anomaly_id} using model {model}")

        try:
            prompt = build_analyst_prompt(facts)
            raw_json = generate_json(prompt=prompt, model_name=model)
            output = AnalystOutput(**raw_json)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(f"[{self.NAME}] Completed successfully in {duration_ms}ms")
            return StageResult(
                agent_name=self.NAME,
                status="completed",
                duration_ms=duration_ms,
                output=output,
            )
        except ValidationError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Analyst output validation failed: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except GeminiServiceError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Gemini API error during Analyst stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Unexpected error in Analyst stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )


class ConnectorAgent:
    """
    Role 2: Connector Agent
    Connects relevant evidence across departments, identifies dependencies, and
    distinguishes evidence-backed connections from hypotheses.
    """
    NAME = "Connector"

    def run(
        self,
        facts: InvestigationFacts,
        analyst_output: AnalystOutput,
        model_name: Optional[str] = None,
    ) -> StageResult:
        t0 = time.perf_counter()
        model = model_name or get_gemini_model_name()
        logger.info(f"[{self.NAME}] Starting cross-department correlation using model {model}")

        try:
            prompt = build_connector_prompt(facts, analyst_output)
            raw_json = generate_json(prompt=prompt, model_name=model)
            output = ConnectorOutput(**raw_json)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(f"[{self.NAME}] Completed successfully in {duration_ms}ms")
            return StageResult(
                agent_name=self.NAME,
                status="completed",
                duration_ms=duration_ms,
                output=output,
            )
        except ValidationError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Connector output validation failed: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except GeminiServiceError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Gemini API error during Connector stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Unexpected error in Connector stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )


class RouterAgent:
    """
    Role 3: Router Agent
    Identifies responsible department, recommends role/team and next actions.
    Never invents personal employee names or claims actions have been executed.
    """
    NAME = "Router"

    def run(
        self,
        facts: InvestigationFacts,
        analyst_output: AnalystOutput,
        connector_output: ConnectorOutput,
        model_name: Optional[str] = None,
    ) -> StageResult:
        t0 = time.perf_counter()
        model = model_name or get_gemini_model_name()
        logger.info(f"[{self.NAME}] Starting routing determination using model {model}")

        try:
            prompt = build_router_prompt(facts, analyst_output, connector_output)
            raw_json = generate_json(prompt=prompt, model_name=model)
            output = RouterOutput(**raw_json)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(f"[{self.NAME}] Completed successfully in {duration_ms}ms")
            return StageResult(
                agent_name=self.NAME,
                status="completed",
                duration_ms=duration_ms,
                output=output,
            )
        except ValidationError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Router output validation failed: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except GeminiServiceError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Gemini API error during Router stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Unexpected error in Router stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )


class WriterAgent:
    """
    Role 4: Writer Agent
    Synthesizes structured findings from all prior roles into an executive-ready
    business action brief with measurable verification steps.
    """
    NAME = "Writer"

    def run(
        self,
        facts: InvestigationFacts,
        analyst_output: AnalystOutput,
        connector_output: ConnectorOutput,
        router_output: RouterOutput,
        model_name: Optional[str] = None,
    ) -> StageResult:
        t0 = time.perf_counter()
        model = model_name or get_gemini_model_name()
        logger.info(f"[{self.NAME}] Starting business action brief synthesis using model {model}")

        try:
            prompt = build_writer_prompt(facts, analyst_output, connector_output, router_output)
            raw_json = generate_json(prompt=prompt, model_name=model)
            output = WriterOutput(**raw_json)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(f"[{self.NAME}] Completed successfully in {duration_ms}ms")
            return StageResult(
                agent_name=self.NAME,
                status="completed",
                duration_ms=duration_ms,
                output=output,
            )
        except ValidationError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Writer output validation failed: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except GeminiServiceError as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Gemini API error during Writer stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_msg = _sanitize_error(f"Unexpected error in Writer stage: {str(e)}")
            logger.error(f"[{self.NAME}] {err_msg}")
            return StageResult(
                agent_name=self.NAME,
                status="failed",
                duration_ms=duration_ms,
                error=err_msg,
            )
