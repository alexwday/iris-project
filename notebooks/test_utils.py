"""
Utility functions for IRIS test notebooks
"""

import logging
from IPython.display import display, HTML
import json
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Import IRIS modules
from iris.src.initial_setup.oauth.oauth import setup_oauth
from iris.src.initial_setup.oauth.local_auth_settings import OPENAI_API_KEY
from iris.src.chat_model.model_settings import IS_RBC_ENV

def get_test_token():
    """
    Get authentication token for testing, handling both RBC and local environments.
    
    Returns:
        str: Authentication token for API access (OAuth token in RBC, API key in local)
    """
    try:
        # Try to get token through the normal setup_oauth function
        return setup_oauth()
    except Exception as e:
        # If there's an error and we're in local environment, return the API key directly
        if not IS_RBC_ENV:
            logging.info("Fallback to direct API key for local testing")
            return OPENAI_API_KEY
        else:
            # In RBC environment, we can't proceed without successful OAuth
            raise e

def create_conversation(messages):
    """Create a conversation dictionary from a list of messages."""
    return {"messages": messages}

def display_conversation(conversation):
    """Display a conversation in a readable format."""
    html = "<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px;'>"
    html += "<h3>Conversation</h3>"
    for msg in conversation["messages"]:
        role = msg["role"]
        content = msg["content"]
        
        # Apply different styling based on role
        if role == "system":
            color = "#4a4a4a"
            bg_color = "#e0e0e0"
        elif role == "user":
            color = "#001f3f"
            bg_color = "#d9e5ff"
        else:  # assistant
            color = "#006400"
            bg_color = "#e6ffe6"
            
        html += f"<div style='margin-bottom: 10px; padding: 8px; border-radius: 3px; background-color: {bg_color};'>"
        html += f"<strong style='color: {color};'>{role.upper()}</strong>: {content}"
        html += "</div>"
    html += "</div>"
    
    display(HTML(html))

def display_agent_result(title, result, include_thought=False):
    """Display an agent's result in a readable format."""
    html = f"<div style='background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 5px solid #007acc;'>"
    html += f"<h3>{title}</h3>"
    
    # Convert result to pretty JSON for display
    if isinstance(result, dict):
        for key, value in result.items():
            # Skip thought field if not requested
            if key == "thought" and not include_thought:
                continue
                
            if isinstance(value, (dict, list)):
                html += f"<p><strong>{key}:</strong></p>"
                html += f"<pre style='background-color: #f0f0f0; padding: 10px; border-radius: 3px;'>"
                html += json.dumps(value, indent=2)
                html += "</pre>"
            else:
                html += f"<p><strong>{key}:</strong> {value}</p>"
    else:
        html += f"<p>{result}</p>"
    
    html += "</div>"
    display(HTML(html))

class TokenCounter:
    """Class to track token usage from logging."""
    def __init__(self):
        self.tokens = {
            "prompt": 0,
            "completion": 0
        }
        self.setup_logging()
    
    def setup_logging(self):
        """Set up logging handler to capture token usage."""
        # Create custom handler
        class TokenLogHandler(logging.Handler):
            def __init__(self, counter):
                super().__init__()
                self.counter = counter
                
            def emit(self, record):
                if record.name == "iris.src.llm_connectors.rbc_openai" and "Token usage" in record.msg:
                    msg = record.msg
                    # Extract token counts using string parsing
                    if "Completion:" in msg and "Prompt:" in msg:
                        try:
                            # Parse completion tokens
                            completion_part = msg.split("Completion:")[1].split("(")[0].strip()
                            completion_tokens = int(completion_part)
                            
                            # Parse prompt tokens
                            prompt_part = msg.split("Prompt:")[1].split("(")[0].strip()
                            prompt_tokens = int(prompt_part)
                            
                            # Add to counter
                            self.counter.tokens["prompt"] += prompt_tokens
                            self.counter.tokens["completion"] += completion_tokens
                        except:
                            pass
        
        # Add handler to logger
        logger = logging.getLogger("iris.src.llm_connectors.rbc_openai")
        handler = TokenLogHandler(self)
        logger.addHandler(handler)
    
    def reset(self):
        """Reset token counters."""
        self.tokens = {"prompt": 0, "completion": 0}
    
    def get_total(self):
        """Get total token usage."""
        return self.tokens["prompt"] + self.tokens["completion"]