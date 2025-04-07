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
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Configure module logger
logger = logging.getLogger(__name__)


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
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.status = "not_started"
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cost = 0.0
        self.details = {}
    
    def start(self) -> None:
        """Start timing the stage."""
        self.start_time = datetime.now()
        self.status = "in_progress"
    
    def end(self, status: str = "completed") -> None:
        """
        End timing the stage.
        
        Args:
            status (str): Final status of the stage
        """
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = status
    
    def update_tokens(self, prompt_tokens: int = 0, completion_tokens: int = 0, 
                     total_tokens: int = 0, cost: float = 0.0) -> None:
        """
        Update token usage for the stage.
        
        Args:
            prompt_tokens (int): Number of prompt tokens used
            completion_tokens (int): Number of completion tokens used
            total_tokens (int): Total number of tokens used
            cost (float): Cost of token usage
        """
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.cost = cost
    
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
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "details": self.details
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
        self.current_stage = None
        self.start_time = None
        self.end_time = None
    
    def start_monitoring(self) -> None:
        """Start the overall monitoring process."""
        if not self.enabled:
            return
        
        self.start_time = datetime.now()
        logger.debug("Process monitoring started")
    
    def end_monitoring(self) -> None:
        """End the overall monitoring process."""
        if not self.enabled:
            return
        
        self.end_time = datetime.now()
        logger.debug("Process monitoring ended")
    
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
    
    def update_stage_tokens(self, stage_name: str, prompt_tokens: int = 0, 
                          completion_tokens: int = 0, total_tokens: int = 0, 
                          cost: float = 0.0) -> None:
        """
        Update token usage for a stage.
        
        Args:
            stage_name (str): Name of the stage to update
            prompt_tokens (int): Number of prompt tokens used
            completion_tokens (int): Number of completion tokens used
            total_tokens (int): Total number of tokens used
            cost (float): Cost of token usage
        """
        if not self.enabled or stage_name not in self.stages:
            return
        
        # Update token usage
        self.stages[stage_name].update_tokens(
            prompt_tokens, completion_tokens, total_tokens, cost
        )
    
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
                "cost": 0.0
            }
        
        prompt_tokens = sum(stage.prompt_tokens for stage in self.stages.values())
        completion_tokens = sum(stage.completion_tokens for stage in self.stages.values())
        total_tokens = sum(stage.total_tokens for stage in self.stages.values())
        cost = sum(stage.cost for stage in self.stages.values())
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost
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
            summary += f"**Start Time:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
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
        
        for stage_name, stage in sorted(self.stages.items(), key=lambda x: (x[1].start_time or datetime.max)):
            status_icon = "✅" if stage.status == "completed" else "❌" if stage.status == "error" else "⏳"
            summary += f"\n{status_icon} **{stage.name}**\n"
            
            if stage.start_time:
                summary += f"  - Start: {stage.start_time.strftime('%H:%M:%S')}\n"
            if stage.end_time:
                summary += f"  - End: {stage.end_time.strftime('%H:%M:%S')}\n"
            if stage.duration is not None:
                summary += f"  - Duration: {stage.duration:.2f} seconds\n"
            
            if stage.total_tokens > 0:
                summary += f"  - Tokens: {stage.total_tokens} (Cost: ${stage.cost:.6f})\n"
            
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
            "stages": {name: stage.to_dict() for name, stage in self.stages.items()}
        }
        
        return json.dumps(data, indent=2)


# Create a global instance that can be imported and used by other modules
process_monitor = ProcessMonitor(enabled=False)


def enable_monitoring(enabled: bool = True) -> None:
    """
    Enable or disable process monitoring.
    
    Args:
        enabled (bool): Whether to enable monitoring
    """
    global process_monitor
    
    # Create a new instance with the desired enabled state
    process_monitor = ProcessMonitor(enabled=enabled)
    
    if enabled:
        process_monitor.start_monitoring()
        logger.debug("Process monitoring enabled")
    else:
        logger.debug("Process monitoring disabled")


def get_process_monitor() -> ProcessMonitor:
    """
    Get the global process monitor instance.
    
    Returns:
        ProcessMonitor: The global process monitor instance
    """
    return process_monitor