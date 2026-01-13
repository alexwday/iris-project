"""
Process monitoring utilities.

Provides helpers to track stage timing, token usage, and LLM call details for
debugging and analysis.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .env_config import config

logger = logging.getLogger(__name__)


class ProcessStageMetrics:
    """
    Represents a single stage in the application process.

    Stores timing, token usage, and optional details for a specific
    stage of execution.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize a new process stage.

        Args:
            name: The name of the stage.
        """
        self.name = name
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: Optional[float] = None
        self.status: str = "not_started"
        self.llm_calls_data: List[Dict[str, Any]] = []
        self.details: Dict[str, Any] = {}

    def start(self) -> None:
        """Start timing the stage."""
        self.start_time = datetime.now(timezone.utc)
        self.status = "in_progress"

    def end(self, status: str = "completed") -> None:
        """
        End timing the stage.

        Args:
            status: Final status of the stage.
        """
        self.end_time = datetime.now(timezone.utc)
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = status

    def add_llm_call_details(self, call_details: Dict[str, Any]) -> None:
        """
        Add details of a single LLM call to this stage.

        Args:
            call_details: Dictionary containing 'model', 'prompt_tokens',
                'completion_tokens', 'cost', 'response_time_ms'.
        """
        self.llm_calls_data.append(call_details)

    def add_details(self, **kwargs: Any) -> None:
        """
        Add stage-specific details.

        Args:
            **kwargs: Key-value pairs to add to details.
        """
        self.details.update(kwargs)

    def get_total_tokens(self) -> int:
        """
        Calculate total tokens from all LLM calls in this stage.

        Returns:
            Total token count across prompts and completions.
        """
        return sum(
            call.get("prompt_tokens", 0) + call.get("completion_tokens", 0)
            for call in self.llm_calls_data
        )

    def get_total_cost(self) -> float:
        """
        Calculate total cost from all LLM calls in this stage.

        Returns:
            Combined cost of all LLM calls.
        """
        return sum(call.get("cost", 0.0) for call in self.llm_calls_data)


class ProcessMonitoringManager:
    """
    Monitors and reports on the stages of application execution.

    Provides methods to track timing, token usage, and stage-specific
    details for the application process.
    """

    def __init__(self, enabled: bool = False) -> None:
        """
        Initialize the process monitor.

        Args:
            enabled: Whether monitoring is enabled.
        """
        self.enabled = enabled
        self.stages: Dict[str, ProcessStageMetrics] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.run_uuid: Optional[uuid.UUID] = None

    def set_run_uuid(self, run_uuid: uuid.UUID) -> None:
        """
        Set the unique identifier for the current process run.

        Args:
            run_uuid: UUID for this process run.
        """
        if not self.enabled:
            return
        self.run_uuid = run_uuid

    def start_monitoring(self) -> None:
        """
        Start the overall monitoring process.

        Generates a run UUID when one has not been set.
        """
        if not self.enabled:
            return
        self.start_time = datetime.now(timezone.utc)
        if self.run_uuid is None:
            self.run_uuid = uuid.uuid4()
        self.stages = {}
        self.end_time = None

    def end_monitoring(self) -> None:
        """End the overall monitoring process."""
        if not self.enabled:
            return
        self.end_time = datetime.now(timezone.utc)

    def log_to_database(self, session: Any) -> None:
        """
        Log all collected stage data for the current run to the database.

        Args:
            session: SQLAlchemy session object within an active transaction.

        Raises:
            SQLAlchemyError: If the insert statement fails.
            ValueError: If stage data cannot be serialized.
            TypeError: If stage data has unexpected types.
            RuntimeError: If database execution cannot complete.
            OSError: If the database driver encounters an OS error.
        """
        if not self.enabled:
            return
        if not self.run_uuid:
            logger.error("Run UUID not set, cannot log process monitor data.")
            return
        if not self.stages:
            logger.warning("No stages recorded, skipping database logging.")
            return

        logger.info("Logging process monitor data for run_uuid: %s", self.run_uuid)

        insert_query = text(
            """
            INSERT INTO process_monitor_logs (
                run_uuid, model_name, stage_name, stage_start_time, stage_end_time,
                duration_ms, llm_calls, total_tokens, total_cost, status,
                decision_details, error_message
            ) VALUES (
                :run_uuid, :model_name, :stage_name, :stage_start_time, :stage_end_time,
                :duration_ms, :llm_calls, :total_tokens, :total_cost, :status,
                :decision_details, :error_message
            )
        """
        )

        records = self._prepare_records_for_db()
        if not records:
            logger.warning("No valid stage records prepared for DB logging.")
            return

        try:
            session.execute(insert_query, records)
        except (
            SQLAlchemyError,
            ValueError,
            TypeError,
            RuntimeError,
            OSError,
        ) as db_err:
            logger.error("Database error during process monitor logging: %s", db_err)
            raise

    def _prepare_records_for_db(self) -> List[Dict[str, Any]]:
        """
        Prepare stage records for database insertion.

        Returns:
            List of stage dictionaries ready for SQL execution.
        """
        records = []
        for stage in self.stages.values():
            try:
                duration_ms = (
                    int(stage.duration * 1000) if stage.duration is not None else None
                )
                llm_calls_json = (
                    json.dumps(stage.llm_calls_data) if stage.llm_calls_data else None
                )
                total_tokens = stage.get_total_tokens()
                total_cost = stage.get_total_cost()
                decision_details_str = stage.details.get("decision_details")
                error_message_str = (
                    stage.details.get("error") if stage.status == "error" else None
                )

                record = {
                    "run_uuid": str(self.run_uuid),
                    "model_name": config.PROCESS_MONITOR_MODEL_NAME,
                    "stage_name": stage.name,
                    "stage_start_time": stage.start_time,
                    "stage_end_time": stage.end_time,
                    "duration_ms": duration_ms,
                    "llm_calls": llm_calls_json,
                    "total_tokens": total_tokens if total_tokens > 0 else None,
                    "total_cost": total_cost if total_cost > 0 else None,
                    "status": stage.status,
                    "decision_details": decision_details_str,
                    "error_message": error_message_str,
                }
                records.append(record)
            except (KeyError, TypeError, AttributeError) as exc:
                logger.error(
                    "Error preparing stage '%s' data for DB: %s", stage.name, exc
                )
        return records

    def start_stage(self, stage_name: str) -> None:
        """
        Start timing a new stage.

        Args:
            stage_name: Name of the stage to start.
        """
        if not self.enabled:
            return

        if stage_name not in self.stages:
            self.stages[stage_name] = ProcessStageMetrics(stage_name)

        self.stages[stage_name].start()

    def end_stage(self, stage_name: str, status: str = "completed") -> None:
        """
        End timing for a stage.

        Args:
            stage_name: Name of the stage to end.
            status: Final status of the stage.
        """
        if not self.enabled or stage_name not in self.stages:
            return

        self.stages[stage_name].end(status)

    def add_llm_call_details_to_stage(
        self, stage_name: str, call_details: Dict[str, Any]
    ) -> None:
        """
        Add details of a single LLM call to the specified stage.

        Args:
            stage_name: The name of the stage to add details to.
            call_details: Dictionary with LLM call info.
        """
        if not self.enabled or stage_name not in self.stages:
            return
        self.stages[stage_name].add_llm_call_details(call_details)

    def add_stage_details(self, stage_name: str, **kwargs: Any) -> None:
        """
        Add details to a stage.

        Args:
            stage_name: Name of the stage to update.
            **kwargs: Key-value pairs to add to details.
        """
        if not self.enabled or stage_name not in self.stages:
            return
        self.stages[stage_name].add_details(**kwargs)


_monitor_state: Dict[str, ProcessMonitoringManager] = {
    "instance": ProcessMonitoringManager(enabled=False)
}


def set_process_monitoring_enabled(enabled: bool = True) -> None:
    """
    Enable or disable process monitoring.

    Args:
        enabled: Whether monitoring should be turned on.
    """
    if _monitor_state["instance"].enabled != enabled:
        _monitor_state["instance"] = ProcessMonitoringManager(enabled=enabled)


def get_process_monitor_instance() -> ProcessMonitoringManager:
    """
    Get the global process monitor instance.

    Returns:
        The shared ProcessMonitoringManager singleton.
    """
    return _monitor_state["instance"]
