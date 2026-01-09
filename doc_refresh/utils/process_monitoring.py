"""
Process Monitoring Module for Document Refresh Pipeline.

Provides a structured way to monitor and report on the various stages
of document processing. Tracks timing, token usage, and stage-specific
details for debugging and analysis.

Simplified version without SQLAlchemy dependency - uses raw psycopg2 or
console logging instead.

Classes:
    ProcessStage: Represents a single stage in the pipeline
    ProcessMonitor: Tracks and reports on pipeline execution stages

Functions:
    enable_monitoring: Enable or disable process monitoring
    get_process_monitor: Get the global process monitor instance
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProcessStage:
    """
    Represents a single stage in the document refresh pipeline.

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
        self.embedding_calls_data: List[Dict[str, Any]] = []
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

    def add_embedding_call_details(self, call_details: Dict[str, Any]) -> None:
        """
        Add details of a single embedding call to this stage.

        Args:
            call_details: Dictionary containing 'model', 'token_count', 'cost'.
        """
        self.embedding_calls_data.append(call_details)

    def add_details(self, **kwargs: Any) -> None:
        """
        Add stage-specific details.

        Args:
            **kwargs: Key-value pairs to add to details.
        """
        self.details.update(kwargs)

    def get_total_tokens(self) -> int:
        """Calculate total tokens from all LLM calls in this stage."""
        total = 0
        for call in self.llm_calls_data:
            total += call.get("prompt_tokens", 0) + call.get("completion_tokens", 0)
        for call in self.embedding_calls_data:
            total += call.get("token_count", 0)
        return total

    def get_total_cost(self) -> float:
        """Calculate total cost from all LLM and embedding calls in this stage."""
        llm_cost = sum(call.get("cost", 0.0) for call in self.llm_calls_data)
        embedding_cost = sum(call.get("cost", 0.0) for call in self.embedding_calls_data)
        return llm_cost + embedding_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert stage to dictionary for reporting."""
        return {
            "name": self.name,
            "status": self.status,
            "duration_seconds": self.duration,
            "llm_calls": len(self.llm_calls_data),
            "embedding_calls": len(self.embedding_calls_data),
            "total_tokens": self.get_total_tokens(),
            "total_cost": self.get_total_cost(),
            "details": self.details,
        }


class ProcessMonitor:
    """
    Monitors and reports on the stages of document refresh execution.

    Provides methods to track timing, token usage, and stage-specific
    details for the pipeline process.
    """

    def __init__(self, enabled: bool = False) -> None:
        """
        Initialize the process monitor.

        Args:
            enabled: Whether monitoring is enabled.
        """
        self.enabled = enabled
        self.stages: Dict[str, ProcessStage] = {}
        self.current_stage: Optional[str] = None
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
        """Start the overall monitoring process."""
        if not self.enabled:
            return
        self.start_time = datetime.now(timezone.utc)
        self.stages = {}
        self.current_stage = None
        self.end_time = None
        self.run_uuid = uuid.uuid4()

    def end_monitoring(self) -> None:
        """End the overall monitoring process."""
        if not self.enabled:
            return
        self.end_time = datetime.now(timezone.utc)

    def start_stage(self, stage_name: str) -> None:
        """
        Start timing a new stage.

        Args:
            stage_name: Name of the stage to start.
        """
        if not self.enabled:
            return

        if stage_name not in self.stages:
            self.stages[stage_name] = ProcessStage(stage_name)

        self.stages[stage_name].start()
        self.current_stage = stage_name
        logger.info("Stage started: %s", stage_name)

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
        if self.current_stage == stage_name:
            self.current_stage = None

        stage = self.stages[stage_name]
        logger.info(
            "Stage ended: %s (status=%s, duration=%.2fs, cost=$%.4f)",
            stage_name,
            status,
            stage.duration or 0,
            stage.get_total_cost(),
        )

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

    def add_embedding_call_details_to_stage(
        self, stage_name: str, call_details: Dict[str, Any]
    ) -> None:
        """
        Add details of a single embedding call to the specified stage.

        Args:
            stage_name: The name of the stage to add details to.
            call_details: Dictionary with embedding call info.
        """
        if not self.enabled or stage_name not in self.stages:
            return
        self.stages[stage_name].add_embedding_call_details(call_details)

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

    def get_total_duration(self) -> Optional[float]:
        """Get total duration of the entire run."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def get_total_cost(self) -> float:
        """Get total cost across all stages."""
        return sum(stage.get_total_cost() for stage in self.stages.values())

    def get_total_tokens(self) -> int:
        """Get total tokens across all stages."""
        return sum(stage.get_total_tokens() for stage in self.stages.values())

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all stages for reporting.

        Returns:
            Dictionary with run summary and stage details.
        """
        return {
            "run_uuid": str(self.run_uuid) if self.run_uuid else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": self.get_total_duration(),
            "total_cost": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "stages": {name: stage.to_dict() for name, stage in self.stages.items()},
        }

    def print_summary(self) -> None:
        """Print a formatted summary to the console."""
        if not self.enabled:
            return

        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("DOCUMENT REFRESH PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Run UUID: {summary['run_uuid']}")
        print(f"Duration: {summary['total_duration_seconds']:.2f} seconds")
        print(f"Total Cost: ${summary['total_cost']:.4f}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print("-" * 60)

        for stage_name, stage_data in summary["stages"].items():
            print(f"\n{stage_name}:")
            print(f"  Status: {stage_data['status']}")
            print(f"  Duration: {stage_data['duration_seconds']:.2f}s")
            print(f"  LLM Calls: {stage_data['llm_calls']}")
            print(f"  Embedding Calls: {stage_data['embedding_calls']}")
            print(f"  Cost: ${stage_data['total_cost']:.4f}")
            if stage_data["details"]:
                for key, value in stage_data["details"].items():
                    print(f"  {key}: {value}")

        print("=" * 60 + "\n")

    def to_json(self) -> str:
        """Export summary as JSON string."""
        return json.dumps(self.get_summary(), indent=2, default=str)


_monitor_state: Dict[str, ProcessMonitor] = {"instance": ProcessMonitor(enabled=False)}


def enable_monitoring(enabled: bool = True) -> None:
    """Enable or disable process monitoring."""
    if _monitor_state["instance"].enabled != enabled:
        _monitor_state["instance"] = ProcessMonitor(enabled=enabled)


def get_process_monitor() -> ProcessMonitor:
    """Get the global process monitor instance."""
    return _monitor_state["instance"]
