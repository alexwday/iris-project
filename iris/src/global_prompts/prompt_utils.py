# global_prompts/prompt_utils.py
"""
Prompt Utilities

Provides utility functions for generating and combining prompt components
from different prompt statements for easy use in agent prompting.
"""

import logging
from typing import List, Optional, Dict, Tuple

# Import all statement modules
from .project_statement import get_project_statement
from .fiscal_calendar import get_fiscal_statement
from .database_statement import get_database_statement
from .restrictions_statement import get_restrictions_statement, get_compliance_restrictions, get_quality_guidelines

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Standard sections for agent prompts
STANDARD_SECTIONS = [
    "CONTEXT",
    "TASK",
    "ANALYSIS",
    "OUTPUT",
    "CONSTRAINTS"
]

# Standard component profiles for different agent types
AGENT_PROFILES = {
    "router": ["project", "fiscal", "databases"],  # Added databases for awareness
    "researcher": ["project", "fiscal", "databases", "query_guidance"],
    "evaluator": ["project", "fiscal", "databases", "quality"],  # Added databases for awareness
    "responder": ["project", "fiscal", "databases", "quality"]  # Added databases for awareness
}

def combine_prompt_statements(statements: List[str], separator: str = "\n\n") -> str:
    """
    Combine multiple prompt statements with a separator.
    
    Args:
        statements (List[str]): List of statement strings to combine
        separator (str, optional): Separator to use between statements. Defaults to "\n\n".
        
    Returns:
        str: Combined prompt statement
    """
    # Filter out any None or empty statements
    valid_statements = [s for s in statements if s]
    return separator.join(valid_statements)

def get_agent_prompt_prefix(
    include_project: bool = True,
    include_fiscal: bool = True,
    include_databases: bool = False,
    include_restrictions: bool = True,
    custom_statements: Optional[List[str]] = None
) -> str:
    """
    Generate a prefix for agent prompts that includes relevant context statements.
    
    Args:
        include_project (bool, optional): Include project statement. Defaults to True.
        include_fiscal (bool, optional): Include fiscal calendar statement. Defaults to True.
        include_databases (bool, optional): Include database descriptions. Defaults to False.
        include_restrictions (bool, optional): Include output restrictions. Defaults to True.
        custom_statements (Optional[List[str]], optional): Additional custom statements. Defaults to None.
        
    Returns:
        str: Combined prefix for agent prompts
    """
    statements = []
    
    # Add requested standard statements
    if include_project:
        statements.append(get_project_statement())
    
    if include_fiscal:
        statements.append(get_fiscal_statement())
    
    if include_databases:
        statements.append(get_database_statement())
    
    if include_restrictions:
        statements.append(get_restrictions_statement())
    
    # Add any custom statements
    if custom_statements:
        statements.extend(custom_statements)
    
    # Combine all statements with double line breaks
    combined = combine_prompt_statements(statements)
    
    # Format as a clear prefix
    if combined:
        return f"# CONTEXT\n\n{combined}\n\n# TASK\n"
    else:
        return ""

def get_research_prompt_components() -> Dict[str, str]:
    """
    Get all components needed for research-oriented prompts.
    
    Returns:
        Dict[str, str]: Dictionary with all prompt components
    """
    return {
        "project_context": get_project_statement(),
        "fiscal_context": get_fiscal_statement(),
        "database_info": get_database_statement(),
        "compliance_restrictions": get_compliance_restrictions(),
        "quality_guidelines": get_quality_guidelines()
    }

def format_section(title: str, content: str) -> str:
    """
    Format a prompt section with standardized header and content.
    
    Args:
        title (str): Section title (will be uppercased)
        content (str): Section content
        
    Returns:
        str: Formatted section
    """
    return f"# {title.upper()}\n\n{content.strip()}"

def split_task_sections(task: str) -> Tuple[str, Dict[str, str]]:
    """
    Split a task string into its main task description and structured sections.
    
    Args:
        task (str): The full task text with sections
        
    Returns:
        Tuple[str, Dict[str, str]]: Main task description and dictionary of sections
    """
    lines = task.strip().split('\n')
    current_section = None
    main_task: List[str] = []
    section_lines: Dict[str, List[str]] = {}
    
    for line in lines:
        # Check if this is a section header
        if line.strip().startswith('# '):
            current_section = line.strip()[2:].strip()
            section_lines[current_section] = []
        # If we're in a section, add to it
        elif current_section:
            section_lines[current_section].append(line)
        # Otherwise add to main task
        else:
            main_task.append(line)
    
    # Join sections back together
    sections: Dict[str, str] = {}
    for section_name, lines_list in section_lines.items():
        sections[section_name] = '\n'.join(lines_list).strip()
    
    # Join main task
    main_task_str = '\n'.join(main_task).strip()
    
    return main_task_str, sections

def standardize_task_format(task: str) -> str:
    """
    Standardize a task definition to use consistent section formatting.
    
    Args:
        task (str): Original task definition
        
    Returns:
        str: Standardized task with consistent section headers
    """
    main_desc, sections = split_task_sections(task)
    
    # Map commonly used section names to standard names
    section_mapping = {
        'ANALYSIS INSTRUCTIONS': 'ANALYSIS',
        'DECISION CRITERIA': 'ANALYSIS',
        'QUERY PLANNING STRATEGY': 'ANALYSIS',
        'EVALUATION CONTEXT': 'CONTEXT',
        'RESPONSE INSTRUCTIONS': 'ANALYSIS',
        'DECISION OPTIONS': 'ANALYSIS',
        'TRADE-OFF CONSIDERATIONS': 'ANALYSIS',
        'CONTINUATION DETECTION': 'ANALYSIS',
        'CONTINUATION HANDLING': 'ANALYSIS',
        'RESPONSE FORMAT': 'OUTPUT',
        'OUTPUT REQUIREMENTS': 'OUTPUT',
        'CONSTRAINTS': 'CONSTRAINTS',
    }
    
    # Group sections by standard name
    section_content_lists: Dict[str, List[str]] = {}
    for section_name, content in sections.items():
        std_name = section_mapping.get(section_name, section_name)
        if std_name not in section_content_lists:
            section_content_lists[std_name] = []
        section_content_lists[std_name].append(content)
    
    # Combine sections with the same standard name
    standardized_sections: Dict[str, str] = {}
    for std_name, contents in section_content_lists.items():
        standardized_sections[std_name] = '\n\n'.join(contents)
    
    # Construct the new task string with standard sections
    result = main_desc if main_desc else ""
    
    # Add standardized sections in a consistent order
    for section in STANDARD_SECTIONS:
        if section in standardized_sections:
            if result:
                result += "\n\n"
            result += format_section(section, standardized_sections[section])
    
    # Add any remaining non-standard sections
    for section, content in standardized_sections.items():
        if section not in STANDARD_SECTIONS:
            if result:
                result += "\n\n"
            result += format_section(section, content)
    
    return result

# Additional convenience functions
def get_full_system_prompt(agent_role: str, agent_task: str, include_components: Optional[List[str]] = None, 
                          profile: Optional[str] = None, standardize: bool = True) -> str:
    """
    Generate a complete system prompt with context and agent instructions.
    
    Args:
        agent_role (str): Description of the agent's role
        agent_task (str): Specific task instructions for the agent
        include_components (List[str], optional): List of components to include from 
            ["project", "fiscal", "databases", "query_guidance", "compliance", "quality"]
        profile (str, optional): Predefined profile to use ("router", "researcher", "evaluator", "responder")
        standardize (bool, optional): Whether to standardize task section formatting. Defaults to True.
            
    Returns:
        str: Complete system prompt
    """
    # If profile is provided, use its component list
    if profile and profile in AGENT_PROFILES:
        include_components = AGENT_PROFILES[profile]
    # Otherwise use default components
    elif include_components is None:
        include_components = ["project", "fiscal", "compliance", "quality"]
    
    # Convert component names to boolean flags
    flags = {
        "include_project": "project" in include_components,
        "include_fiscal": "fiscal" in include_components,
        "include_databases": "databases" in include_components,
        "include_restrictions": any(c in include_components for c in ["compliance", "quality"])
    }
    
    # Get basic prefix with standard components
    prefix = get_agent_prompt_prefix(
        include_project=flags.get("include_project", True),
        include_fiscal=flags.get("include_fiscal", True),
        include_databases=flags.get("include_databases", False),
        include_restrictions=flags.get("include_restrictions", True)
    )
    
    # Query guidance is now included in planner settings directly
    
    # Standardize task format if requested
    if standardize:
        agent_task = standardize_task_format(agent_task)
    
    # Construct the full prompt
    full_prompt = f"{prefix}You are {agent_role}.\n\n{agent_task}"
    
    return full_prompt