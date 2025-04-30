# python/iris/src/initial_setup/process_monitor.py
"""
Process Monitoring Module

This module provides a structured way to monitor and report on the
various stages of execution in the application. It tracks timing,
token usage, and stage-specific details for debugging and analysis.

Classes:
    ProcessMonitor: Tracks and reports on application execution stages

Dependencies:
    - time
    - datetime
    - logging
    - typing
"""

import time
import logging
import uuid  # Import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import psycopg2 # Use project's standard DB connection method
from psycopg2.extras import Json # For inserting JSONB

# Configure module logger
logger = logging.getLogger(__name__)


# --- Helper to extract decision details ---
def _extract_decision_details(stage_name: str, details: Dict[str, Any]) -> Optional[str]:
    """Extracts key decision details based on stage name for logging."""
    # Simple extraction logic based on previously discussed plan
    try:
        if stage_name == "router":
            decision = details.get('decision', {})
            return f"Function: {decision.get('function_name')}"
        elif stage_name == "planner":
            dbs = details.get('selected_databases', [])
            return f"Selected DBs: {', '.join(dbs)}" if dbs else "No DBs selected"
        elif stage_name == "clarifier":
            action = details.get('action')
            # Assuming 'output' holds statement/questions from clarifier_decision
            output = details.get('decision', {}).get('output', '')
            return f"Action: {action}, Output: {output[:250]}..." # Truncate long outputs
        elif stage_name == "summary":
            # Extract details from summary agent
            scope = details.get('scope', 'N/A')
            num_results = details.get('num_results', 0)
            sources = details.get('sources', [])
            source_count = len(sources) if sources else 0
            return f"Scope: {scope}, Results: {num_results}, Sources: {source_count}"
        elif stage_name.startswith("db_query_"):
            # Look for both initial and final IDs
            initial_ids = details.get('initial_document_ids')
            final_ids = details.get('final_document_ids')
            # Fallback to old key for backward compatibility or if only one is logged
            legacy_ids = details.get('document_ids') or details.get('chunk_ids')

            details_parts = []
            if initial_ids:
                count = len(initial_ids)
                ids_str = ', '.join(map(str, initial_ids[:5])) # Show fewer IDs per list
                suffix = "..." if count > 5 else ""
                details_parts.append(f"Initial ({count}): [{ids_str}{suffix}]")
            if final_ids:
                count = len(final_ids)
                ids_str = ', '.join(map(str, final_ids[:5])) # Show fewer IDs per list
                suffix = "..." if count > 5 else ""
                details_parts.append(f"Final ({count}): [{ids_str}{suffix}]")
            elif legacy_ids and not initial_ids: # Show legacy only if new ones aren't present
                 count = len(legacy_ids)
                 ids_str = ', '.join(map(str, legacy_ids[:10])) # Keep 10 for legacy view
                 suffix = "..." if count > 10 else ""
                 details_parts.append(f"Selected ({count}): [{ids_str}{suffix}]")

            if details_parts:
                return " ".join(details_parts)
            # Fallbacks if no IDs are present
            elif details.get('status_summary'):
                 return f"Status: {details.get('status_summary')}"
            elif details.get('result_count') is not None:
                 return f"Result Count: {details.get('result_count')}" # Less likely now
        elif stage_name == "ssl_setup":
            cert_path = details.get('cert_path', 'default')
            return f"Certificate Path: {cert_path}"
        elif stage_name == "oauth_setup":
            # Extract token details (don't include actual tokens)
            token_type = details.get('token_type', 'N/A')
            token_length = details.get('token_length', 0)
            return f"Token Type: {token_type}, Length: {token_length}"
        elif stage_name == "conversation_processing":
            # Extract conversation details
            message_count = details.get('message_count', 0)
            return f"Messages: {message_count}"
        # Add more specific stage handlers if needed
    except Exception as e:
        logger.warning(f"Error extracting decision details for stage '{stage_name}': {e}")
    # Return None if no specific detail is extracted
    return None


class ProcessStage:
    """
    Represents a single stage in the application process.

    This class stores timing, token usage, and optional details
    for a specific stage of execution.
    """

    def __init__(self, name: str):
        """
        Initialize a new process stage.

        Args:
            name (str): The name of the stage
        """
        self.name = name
        self.start_time: Optional[datetime] = None # Type hint
        self.end_time: Optional[datetime] = None   # Type hint
        self.duration: Optional[float] = None      # Store duration in seconds
        self.status: str = "not_started"
        self.llm_calls_data: List[Dict[str, Any]] = [] # Store detailed LLM calls
        self.details: Dict[str, Any] = {}

    def start(self) -> None:
        """Start timing the stage."""
        # Ensure timezone-aware datetime
        self.start_time = datetime.now(timezone.utc)
        self.status = "in_progress"

    def end(self, status: str = "completed") -> None:
        """
        End timing the stage.

        Args:
            status (str): Final status of the stage
        """
        # Ensure timezone-aware datetime
        self.end_time = datetime.now(timezone.utc)
        if self.start_time:
            # Calculate duration in seconds
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = status

    # Remove old update_tokens method
    # def update_tokens(...) -> None: ...

    def add_llm_call_details(self, call_details: Dict[str, Any]) -> None:
        """
        Add details of a single LLM call to this stage.

        Args:
            call_details (Dict[str, Any]): Dictionary containing details like
                                           'model', 'input_tokens', 'output_tokens',
                                           'cost', 'response_time_ms'.
        """
        # Basic validation could be added here if needed
        self.llm_calls_data.append(call_details)

    def add_details(self, **kwargs) -> None:
        """
        Add stage-specific details.

        Args:
            **kwargs: Key-value pairs to add to details
        """
        self.details.update(kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the stage to a dictionary.

        Returns:
            dict: Stage data as a dictionary
        """
        return {
            "name": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status,
            # Remove old token fields
            # "prompt_tokens": self.prompt_tokens,
            # "completion_tokens": self.completion_tokens,
            # "total_tokens": self.total_tokens,
            # "cost": self.cost,
            "llm_calls_data": self.llm_calls_data, # Add new field
            "details": self.details,
        }


class ProcessMonitor:
    """
    Monitors and reports on the stages of application execution.

    This class provides methods to track timing, token usage,
    and stage-specific details for the application process.
    """

    def __init__(self, enabled: bool = False):
        """
        Initialize the process monitor.

        Args:
            enabled (bool): Whether monitoring is enabled
        """
        self.enabled = enabled
        self.stages: Dict[str, ProcessStage] = {}
        self.current_stage: Optional[str] = None # Type hint
        self.start_time: Optional[datetime] = None # Overall start time, type hint
        self.end_time: Optional[datetime] = None   # Overall end time, type hint
        self.run_uuid: Optional[uuid.UUID] = None  # Unique ID for the entire run
        
        # Add debug logging for initialization
        logging.getLogger(__name__).info(f"ProcessMonitor initialized with enabled={enabled}")

    def set_run_uuid(self, run_uuid: uuid.UUID) -> None:
        """Sets the unique identifier for the current process run."""
        if not self.enabled:
            return
        self.run_uuid = run_uuid
        logger.debug(f"Process monitor run UUID set: {run_uuid}")

    def start_monitoring(self) -> None:
        """Start the overall monitoring process."""
        if not self.enabled:
            return
        # Ensure timezone-aware datetime
        self.start_time = datetime.now(timezone.utc)
        # Reset stages for the new monitoring period
        self.stages = {}
        self.current_stage = None
        self.end_time = None
        # run_uuid should be set separately by the caller using set_run_uuid
        logger.debug("Process monitoring started")

    def end_monitoring(self) -> None:
        """End the overall monitoring process."""
        if not self.enabled:
            return
        # Ensure timezone-aware datetime
        self.end_time = datetime.now(timezone.utc)
        logger.debug("Process monitoring ended")
        # Note: Database logging is triggered separately by the caller

    def log_to_database(self, cursor) -> None:
        """
        Logs all collected stage data for the current run to the database.

        Args:
            cursor: A psycopg2 database cursor object obtained from the caller,
                    expected to be within an active transaction.
        """
        if not self.enabled:
            logger.debug("Process monitoring disabled, skipping database logging.")
            return
        if not self.run_uuid:
            logger.error("Run UUID not set, cannot log process monitor data to database.")
            return
        if not self.stages:
            logger.warning("No stages recorded for this run, skipping database logging.")
            return

        logger.info(f"Logging process monitor data for run_uuid: {self.run_uuid}")
        
        # DEBUG: Print statements to help diagnose the issue
        logger.info(f"Number of stages to log: {len(self.stages)}")
        for stage_name, stage in self.stages.items():
            logger.info(f"Stage '{stage_name}' - start: {stage.start_time}, end: {stage.end_time}, status: {stage.status}")

        insert_query = """
            INSERT INTO process_monitor_logs (
                run_uuid, model_name, stage_name, stage_start_time, stage_end_time,
                duration_ms, llm_calls, total_tokens, total_cost, status,
                decision_details, error_message
                -- user_id, environment, custom_metadata, notes are omitted for now
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            );
        """

        records_to_insert = []
        for stage in self.stages.values():
            try:
                # Prepare data for insertion
                duration_ms = int(stage.duration * 1000) if stage.duration is not None else None
                llm_calls_json = Json(stage.llm_calls_data) if stage.llm_calls_data else None

                # Calculate totals from llm_calls_data
                total_tokens = 0
                total_cost = 0.0
                if stage.llm_calls_data:
                    for call in stage.llm_calls_data:
                        # Use correct keys 'prompt_tokens' and 'completion_tokens'
                        total_tokens += call.get('prompt_tokens', 0) + call.get('completion_tokens', 0)
                        total_cost += call.get('cost', 0.0)

                decision_details_str = _extract_decision_details(stage.name, stage.details)
                error_message_str = stage.details.get('error') if stage.status == 'error' else None

                # Convert UUID to string for PostgreSQL compatibility
                record = (
                    str(self.run_uuid),  # Convert UUID to string
                    'iris', # model_name
                    stage.name,
                    stage.start_time, # Already timezone-aware UTC
                    stage.end_time,   # Already timezone-aware UTC
                    duration_ms,
                    llm_calls_json,
                    total_tokens if total_tokens > 0 else None, # Store NULL if 0
                    total_cost if total_cost > 0 else None,     # Store NULL if 0.0
                    stage.status,
                    decision_details_str,
                    error_message_str
                )
                records_to_insert.append(record)
            except Exception as e:
                logger.error(f"Error preparing stage '{stage.name}' data for DB logging: {e}", exc_info=True)
                # Continue to next stage if possible

        if not records_to_insert:
            logger.warning("No valid stage records prepared for DB logging.")
            return

        try:
            # Log each record individually for better debugging
            for record in records_to_insert:
                logger.info(f"Inserting record with stage_name={record[2]}")
                try:
                    cursor.execute(insert_query, record)
                    logger.info(f"Successfully inserted record for stage {record[2]}")
                except Exception as record_err:
                    logger.error(f"Error inserting record for stage {record[2]}: {record_err}")
                    # Try to log more detailed info about the record
                    for i, value in enumerate(record):
                        logger.info(f"  Param {i}: {type(value)} = {value}")
                    raise
            
            # Log success message
            logger.info(f"Successfully logged {len(records_to_insert)} stages for run_uuid: {self.run_uuid}")
        except Exception as db_err:
            # Log the error, but let the caller handle transaction rollback/commit
            logger.error(f"Database error during process monitor logging for run_uuid {self.run_uuid}: {db_err}", exc_info=True)
            # Re-raise the exception so the caller knows the logging failed and can rollback
            raise


    def start_stage(self, stage_name: str) -> None:
        """
        Start timing a new stage.

        Args:
            stage_name (str): Name of the stage to start
        """
        if not self.enabled:
            return

        # Create the stage if it doesn't exist
        if stage_name not in self.stages:
            self.stages[stage_name] = ProcessStage(stage_name)

        # Start the stage
        self.stages[stage_name].start()
        self.current_stage = stage_name

        logger.debug(f"Started process stage: {stage_name}")

    def end_stage(self, stage_name: str, status: str = "completed") -> None:
        """
        End timing for a stage.

        Args:
            stage_name (str): Name of the stage to end
            status (str): Final status of the stage
        """
        if not self.enabled or stage_name not in self.stages:
            return

        # End the stage
        self.stages[stage_name].end(status)

        if self.current_stage == stage_name:
            self.current_stage = None

        logger.debug(f"Ended process stage: {stage_name} with status: {status}")

    # Remove old update_stage_tokens method entirely
    # def update_stage_tokens(...) -> None: ...

    def add_llm_call_details_to_stage(self, stage_name: str, call_details: Dict[str, Any]) -> None:
        """
        Adds details of a single LLM call to the specified stage.

        Args:
            stage_name (str): The name of the stage to add details to.
            call_details (Dict[str, Any]): Dictionary with LLM call info.
        """
        if not self.enabled or stage_name not in self.stages:
            logger.warning(f"Attempted to add LLM details to non-existent or disabled stage: {stage_name}")
            return

        self.stages[stage_name].add_llm_call_details(call_details)


    def add_stage_details(self, stage_name: str, **kwargs) -> None:
        """
        Add details to a stage.

        Args:
            stage_name (str): Name of the stage to update
            **kwargs: Key-value pairs to add to details
        """
        if not self.enabled or stage_name not in self.stages:
            return

        # Add details
        self.stages[stage_name].add_details(**kwargs)

    def get_stage_data(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific stage.

        Args:
            stage_name (str): Name of the stage to get data for

        Returns:
            dict: Stage data as a dictionary
        """
        if not self.enabled or stage_name not in self.stages:
            return None

        return self.stages[stage_name].to_dict()

    def get_all_stages(self) -> List[Dict[str, Any]]:
        """
        Get data for all stages.

        Returns:
            list: List of stage data dictionaries
        """
        if not self.enabled:
            return []

        return [stage.to_dict() for stage in self.stages.values()]

    def get_total_duration(self) -> Optional[float]:
        """
        Get the total duration of all completed stages.

        Returns:
            float: Total duration in seconds
        """
        if not self.enabled or not self.start_time:
            return None

        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        else:
            return (datetime.now() - self.start_time).total_seconds()

    def get_total_tokens(self) -> Dict[str, Any]:
        """
        Get the total token usage across all stages.

        Returns:
            dict: Token usage totals
        """
        if not self.enabled:
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
            }

        prompt_tokens = sum(stage.prompt_tokens for stage in self.stages.values())
        completion_tokens = sum(
            stage.completion_tokens for stage in self.stages.values()
        )
        total_tokens = sum(stage.total_tokens for stage in self.stages.values())
        cost = sum(stage.cost for stage in self.stages.values())

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
        }

    def format_summary(self) -> str:
        """
        Format a summary of the monitoring data.

        Returns:
            str: Formatted summary as markdown
        """
        if not self.enabled:
            return ""

        # Get total token usage
        token_totals = self.get_total_tokens()

        # Calculate total duration
        total_duration = self.get_total_duration()

        # Format the summary
        summary = "\n\n---\n"
        summary += "## Process Monitoring Summary\n\n"

        # Add timing information
        if self.start_time:
            summary += (
                f"**Start Time:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        if self.end_time:
            summary += f"**End Time:** {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        if total_duration:
            summary += f"**Total Duration:** {total_duration:.2f} seconds\n"

        # Add token totals
        summary += "\n**Token Usage:**\n"
        summary += f"- Prompt Tokens: {token_totals['prompt_tokens']}\n"
        summary += f"- Completion Tokens: {token_totals['completion_tokens']}\n"
        summary += f"- Total Tokens: {token_totals['total_tokens']}\n"
        summary += f"- Cost: ${token_totals['cost']:.6f}\n"

        # Add stage information
        summary += "\n**Stages:**\n"

        for stage_name, stage in sorted(
            self.stages.items(), key=lambda x: (x[1].start_time or datetime.max)
        ):
            status_icon = (
                "✅"
                if stage.status == "completed"
                else "❌" if stage.status == "error" else "⏳"
            )
            summary += f"\n{status_icon} **{stage.name}**\n"

            if stage.start_time:
                summary += f"  - Start: {stage.start_time.strftime('%H:%M:%S')}\n"
            if stage.end_time:
                summary += f"  - End: {stage.end_time.strftime('%H:%M:%S')}\n"
            if stage.duration is not None:
                summary += f"  - Duration: {stage.duration:.2f} seconds\n"

            if stage.total_tokens > 0:
                summary += (
                    f"  - Tokens: {stage.total_tokens} (Cost: ${stage.cost:.6f})\n"
                )

            # Add important details if present
            if stage.details:
                for key, value in stage.details.items():
                    # Handle different types of values
                    if isinstance(value, list) and len(value) > 0:
                        summary += f"  - {key}: {len(value)} items\n"
                    elif isinstance(value, dict) and value:
                        summary += f"  - {key}: {len(value)} properties\n"
                    elif isinstance(value, str) and len(value) > 50:
                        summary += f"  - {key}: {value[:50]}...\n"
                    else:
                        summary += f"  - {key}: {value}\n"

        return summary

    def to_json(self) -> str:
        """
        Convert the monitoring data to a JSON string.

        Returns:
            str: JSON representation of monitoring data
        """
        if not self.enabled:
            return "{}"

        data = {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.get_total_duration(),
            "token_totals": self.get_total_tokens(),
            "stages": {name: stage.to_dict() for name, stage in self.stages.items()},
        }

        # Use default=str for non-serializable types like UUID if needed elsewhere
        return json.dumps(data, indent=2, default=str)


# Create a global instance that can be imported and used by other modules
process_monitor = ProcessMonitor(enabled=False)


def enable_monitoring(enabled: bool = True) -> None:
    """
    Enable or disable process monitoring.

    Args:
        enabled (bool): Whether to enable monitoring
    """
    global process_monitor
    
    # Log current state
    logger.info(f"Enable_monitoring called with enabled={enabled}. Current state: {process_monitor.enabled}")

    # Avoid recreating if the state is already correct
    # Also, ensure we don't disable if it wasn't enabled to begin with
    if process_monitor.enabled != enabled:
        # Only create new instance if state *changes*
        logger.info(f"Creating new ProcessMonitor instance with enabled={enabled}")
        try:
            process_monitor = ProcessMonitor(enabled=enabled)
            if enabled:
                # process_monitor.start_monitoring() # Start monitoring is called explicitly by model.py now
                logger.info("Process monitoring enabled by state change.")
            else:
                logger.info("Process monitoring disabled by state change.")
        except Exception as e:
            logger.error(f"Error creating ProcessMonitor: {e}", exc_info=True)
    elif enabled and not process_monitor.enabled:
        # Handle case where it should be enabled but somehow isn't (e.g., initial state)
        logger.info("Explicitly creating new ProcessMonitor in enabled state")
        try:
            process_monitor = ProcessMonitor(enabled=True)
            logger.info("Process monitoring explicitly enabled.")
        except Exception as e:
            logger.error(f"Error explicitly enabling ProcessMonitor: {e}", exc_info=True)
    elif enabled:
         # If already enabled, maybe reset stages? Or assume caller handles run lifecycle.
         # For now, just log that it's already enabled.
         logger.info("Process monitoring was already enabled.")
    else: # enabled is False and process_monitor.enabled is False
        logger.info("Process monitoring was already disabled.")
        
    # Log the final state to confirm
    logger.info(f"Final process_monitor state: enabled={process_monitor.enabled}")


def get_process_monitor() -> ProcessMonitor:
    """
    Get the global process monitor instance.

    Returns:
        ProcessMonitor: The global process monitor instance
    """
    return process_monitor
