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

# Define agent types for workflow context
AGENT_TYPES = [
    "router",
    "direct_response",
    "clarifier",
    "planner",
    "judge",
    "summarizer" # Added new agent type
]

# Standard sections for error handling
ERROR_HANDLING_SECTIONS = [
    "UNEXPECTED_INPUT",
    "AMBIGUOUS_REQUEST",
    "MISSING_INFORMATION",
    "SYSTEM_LIMITATIONS",
    "CONFIDENCE_SIGNALING"
]

# Standard sections for input/output specifications
IO_SPECIFICATION_SECTIONS = [
    "INPUT_FORMAT",
    "INPUT_VALIDATION",
    "OUTPUT_FORMAT",
    "OUTPUT_VALIDATION"
]

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

def get_io_specifications(agent_type: str) -> str:
    """
    Generate standardized input/output specifications for a specific agent type.
    
    Args:
        agent_type (str): The type of agent ("router", "direct_response", "clarifier", "planner", "judge")
        
    Returns:
        str: Formatted input/output specifications
    """
    if agent_type == "router":
        return """# INPUT/OUTPUT SPECIFICATIONS

## Input Format
- You receive a complete conversation history in the form of messages
- Each message contains a "role" (user or assistant) and "content" (text)
- The most recent message is the one you need to route

## Input Validation
- Verify that the latest message contains a clear query or request
- Check if the query relates to accounting, finance, or related topics
- Assess if previous conversation provides relevant context

## Output Format
- Your output must be a tool call to route_query
- The function_name parameter must be either "response_from_conversation" or "research_from_database"
- No additional text or explanation should be included

## Output Validation
- Ensure you've selected exactly one routing option
- Verify your decision aligns with the routing criteria
- Confirm you're using the tool call format correctly
"""
    
    elif agent_type == "direct_response":
        return """# INPUT/OUTPUT SPECIFICATIONS

## Input Format
- You receive a complete conversation history in the form of messages
- Each message contains a "role" (user or assistant) and "content" (text)
- The Router has determined this query can be answered from conversation context

## Input Validation
- Verify that you understand the user's query from the latest message
- Check if the conversation history contains sufficient information to answer
- Identify any relevant information from previous exchanges

## Output Format
- Your output should be a comprehensive, well-structured response
- Use appropriate formatting (headings, lists, tables) for clarity
- Include definitions of technical terms when they first appear
- Structure your response according to the query type guidelines

## Output Validation
- Ensure your response directly addresses the user's query
- Verify you've only used information from the conversation history
- Check that your response follows the appropriate structure for the query type
- Confirm you've acknowledged any limitations due to missing information
"""
    
    elif agent_type == "clarifier":
        return """# INPUT/OUTPUT SPECIFICATIONS

## Input Format
- You receive a complete conversation history in the form of messages
- Each message contains a "role" (user or assistant) and "content" (text)
- The Router has determined this query requires database research

## Input Validation
- Verify that you understand the user's research need
- Check if the conversation contains sufficient context for effective research
- Identify any missing essential information that would improve search quality

## Output Format
- Your output must be a tool call to make_clarifier_decision
- The action parameter must be either "request_essential_context" or "create_research_statement"
- The output parameter must contain either numbered questions or a research statement
- The is_continuation parameter must indicate if this is continuing previous research

## Output Validation
- For "request_essential_context": Ensure questions are clear, specific, and numbered
- For "create_research_statement": Ensure the statement is comprehensive and database-aware
- Verify your decision aligns with the context sufficiency criteria
- Confirm you've correctly identified if this is a continuation
"""
    
    elif agent_type == "planner":
        return """# INPUT/OUTPUT SPECIFICATIONS

## Input Format
- You receive a research statement created by the Clarifier
- You have access to information about all available databases
- You may receive information about whether this is a continuation of previous research

## Input Validation
- Verify that you understand the research need from the statement
- Identify the key accounting topics, standards, or policies involved
- Determine which databases would be most relevant for this research

## Output Format
- Your output must be a tool call to submit_query_plan
- The queries parameter must contain 1-5 database queries, each with:
  * database: The specific database to query
  * query: The search text optimized for that database
- The overall_strategy parameter must explain your research approach

## Output Validation
- Ensure each query is optimized for its specific database
- Verify you've prioritized the most relevant databases
- Confirm your queries follow a logical progression
- Check that your overall strategy explains your approach clearly
- For continuations, verify you're not duplicating previous queries
"""
    
    elif agent_type == "judge":
        return """# INPUT/OUTPUT SPECIFICATIONS

## Input Format
- You receive the original research statement
- You receive completed database queries and their results
- You receive any remaining planned queries that haven't been executed
- You have access to information about all available databases

## Input Validation
- Verify that you understand the original research need
- Assess the quality and relevance of the query results
- Evaluate whether the results address all key aspects of the research statement

## Output Format
- Your output must be a tool call to submit_research_decision
- The action parameter must be either "continue_research" or "stop_research"
- The reason parameter must explain your decision concisely based on criteria

## Output Validation
- Ensure your decision is based on the quantitative assessment framework
- Verify your reason references specific findings from the completed queries
- For "continue_research": Confirm you've explained the expected value of remaining queries
- For "stop_research": Confirm your reason clearly justifies why research should end based on the criteria
"""

    elif agent_type == "summarizer":
        return """# INPUT/OUTPUT SPECIFICATIONS

## Input Format
- You receive the original research statement
- You receive the list of completed database queries and their full results
- You have access to information about all available databases

## Input Validation
- Verify that you understand the original research need
- Confirm that the completed query results are present and accessible

## Output Format
- Your output must be ONLY the markdown-formatted summary text
- Do not include any preamble or extra conversational text
- Follow the structure and content requirements defined in your main task prompt

## Output Validation
- Ensure your summary accurately reflects the findings in the query results
- Verify the summary guides the user without excessive repetition of results
- Check that markdown formatting is correct and enhances readability
"""

    else:
        logger.warning(f"Unknown agent type: {agent_type}, returning empty IO specifications")
        return ""

def get_error_handling_instructions(agent_type: str) -> str:
    """
    Generate standardized error handling instructions for a specific agent type.
    
    Args:
        agent_type (str): The type of agent ("router", "direct_response", "clarifier", "planner", "judge")
        
    Returns:
        str: Formatted error handling instructions
    """
    common_instructions = """# ERROR HANDLING

## Unexpected Input
- If you receive input in an unexpected format, extract what information you can
- Focus on the core intent rather than getting caught up in formatting issues
- If the input is completely unintelligible, respond with your best interpretation

## Ambiguous Requests
- When faced with multiple possible interpretations, choose the most likely one
- Explicitly acknowledge the ambiguity in your response
- Proceed with the most reasonable interpretation given the context

## Missing Information
- When critical information is missing, make reasonable assumptions based on context
- Clearly state any assumptions you've made
- Indicate the limitations of your response due to missing information

## System Limitations
- If you encounter limitations in your capabilities, acknowledge them transparently
- Provide the best possible response within your constraints
- Never fabricate information to compensate for limitations

## Confidence Signaling
- HIGH CONFIDENCE: Proceed normally with your decision
- MEDIUM CONFIDENCE: Proceed but explicitly note areas of uncertainty
- LOW CONFIDENCE: Acknowledge significant uncertainty and provide caveats
"""

    if agent_type == "router":
        return common_instructions + """
## Router-Specific Error Handling
- If the query is ambiguous between research/direct response, prefer research
- If you can't determine the query type, default to research_from_database
- If the conversation history is inconsistent, focus on the most recent query
- If the query contains multiple questions, route based on the most complex one
"""
    
    elif agent_type == "direct_response":
        return common_instructions + """
## Direct Response-Specific Error Handling
- If the conversation lacks sufficient information, acknowledge the limitations
- If the query requires information not in the conversation, explain what's missing
- If the query is outside your domain, provide general information but note the limitations
- If asked about database information, remind that you're using conversation context only
"""
    
    elif agent_type == "clarifier":
        return common_instructions + """
## Clarifier-Specific Error Handling
- If the research need is unclear, request clarification on the specific accounting topic
- If multiple interpretations are possible, ask for confirmation of the intended meaning
- If the query is too broad, ask for specific aspects the user is interested in
- If continuation is ambiguous, assume it's a continuation if context was just provided
"""
    
    elif agent_type == "planner":
        return common_instructions + """
## Planner-Specific Error Handling
- If the research statement is vague, create queries for the most likely interpretations
- If unsure which databases to query, include a broader range of relevant databases
- If the topic spans multiple standards, create queries for each relevant standard
- If continuation information is missing, avoid duplicating previous queries
"""
    
    elif agent_type == "judge":
        return common_instructions + """
## Judge-Specific Error Handling
- If results are of low quality, acknowledge this in your evaluation reason
- If uncertain about stopping research, err on the side of continuing research, providing a clear reason based on potential value or gaps
"""

    elif agent_type == "summarizer":
        return common_instructions + """
## Summarizer-Specific Error Handling
- If query results are missing or incomplete, generate the best possible summary from available data and note the limitations
- If results are contradictory, clearly highlight the contradictions in the summary
- If results are sparse or low quality, reflect this honestly in the summary's tone and conclusions
- Focus on synthesizing the provided information; do not introduce external knowledge
"""

    else:
        logger.warning(f"Unknown agent type: {agent_type}, returning empty error handling instructions")
        return ""

def get_workflow_context(agent_type: str) -> str:
    """
    Generate a standardized workflow context section for a specific agent type.
    
    Args:
        agent_type (str): The type of agent ("router", "direct_response", "clarifier", "planner", "judge")
        
    Returns:
        str: Formatted workflow context section
    """
    if agent_type == "router":
        return """# WORKFLOW CONTEXT

## Complete Agent Workflow
User Query → Router (YOU) → [Direct Response OR Research Path (Clarifier → Planner → Database Queries → Judge → Summarizer)]

## Your Position
You are the ROUTER AGENT, positioned at the FIRST STAGE of the workflow.
You are the entry point for all user queries and determine the entire processing path.

## Upstream Context
Before you:
- The user has submitted a query about accounting policies or standards
- You receive the complete conversation history including all previous exchanges
- No other agents have processed this query yet

## Your Responsibility
Your core task is to DETERMINE WHETHER THE QUERY REQUIRES DATABASE RESEARCH.
Success means correctly routing queries based on whether they can be answered from conversation context alone or require authoritative database information.

## Downstream Impact
After you:
- If you choose "response_from_conversation": The Direct Response Agent will generate an immediate answer without database research.
- If you choose "research_from_database": The Clarifier Agent will assess if sufficient context exists to proceed with research.
- Your decision directly impacts response time, comprehensiveness, and authority of information provided to the user."""
    
    elif agent_type == "direct_response":
        return """# WORKFLOW CONTEXT

## Complete Agent Workflow
User Query → Router → [Direct Response (YOU) OR Research Path (Clarifier → Planner → Database Queries → Judge → Summarizer)]

## Your Position
You are the DIRECT RESPONSE AGENT, activated when the Router determines a query can be answered without database research.

## Upstream Context
Before you:
- The Router Agent has determined that the query can be answered from conversation context
- You receive the complete conversation history including all previous exchanges
- No database research has been performed for this query

## Your Responsibility
Your core task is to GENERATE A COMPREHENSIVE RESPONSE USING ONLY CONVERSATION CONTEXT.
Success means providing accurate, helpful information that addresses the user's query without requiring database lookups.

## Downstream Impact
After you:
- Your response will be delivered directly to the user
- No other agents will process this query
- The user will evaluate your response for accuracy, clarity, and helpfulness"""
    
    elif agent_type == "clarifier":
        return """# WORKFLOW CONTEXT

## Complete Agent Workflow
User Query → Router → [Direct Response OR Research Path (Clarifier (YOU) → Planner → Database Queries → Judge → Summarizer)]

## Your Position
You are the CLARIFIER AGENT, the first stage in the research path after the Router determines database research is needed.

## Upstream Context
Before you:
- The Router Agent has determined that database research is necessary
- You receive the complete conversation history including all previous exchanges
- No research has been performed yet, and you must determine if sufficient context exists

## Your Responsibility
Your core task is to ASSESS IF SUFFICIENT CONTEXT EXISTS TO PROCEED WITH RESEARCH.
Success means either obtaining essential missing context or creating a comprehensive research statement that enables effective database queries.

## Downstream Impact
After you:
- If you choose "request_essential_context": The user will be asked to provide additional information.
- If you choose "create_research_statement": The Planner Agent will use your research statement to design database queries.
- Your decision impacts research quality, efficiency, and the user's experience with the system."""
    
    elif agent_type == "planner":
        return """# WORKFLOW CONTEXT

## Complete Agent Workflow
User Query → Router → Research Path (Clarifier → Planner (YOU) → Database Queries → Judge → Summarizer)

## Your Position
You are the PLANNER AGENT, responsible for designing the database query strategy after the Clarifier confirms sufficient context exists.

## Upstream Context
Before you:
- The Router Agent has determined that database research is necessary
- The Clarifier Agent has created a research statement with sufficient context
- You receive this research statement along with information about available databases
- No database queries have been executed yet

## Your Responsibility
Your core task is to DESIGN AN OPTIMAL SET OF DATABASE QUERIES.
Success means creating a comprehensive query plan that efficiently targets the most relevant databases with well-formulated queries.

## Downstream Impact
After you:
- Your query plan will be executed against the specified databases.
- The Judge Agent will evaluate the results of your queries to determine if research should continue or stop.
- The quality and relevance of information found depends directly on your query design."""
    
    elif agent_type == "judge":
        return """# WORKFLOW CONTEXT

## Complete Agent Workflow
User Query → Router → Research Path (Clarifier → Planner → Database Queries → Judge (YOU) → Summarizer)

## Your Position
You are the JUDGE AGENT, responsible for evaluating research progress after each query (if needed) and deciding whether to continue or stop.

## Upstream Context
Before you:
- The Router Agent determined that database research was necessary
- The Clarifier Agent created a research statement with sufficient context
- The Planner Agent designed a set of database queries
- Database queries have been executed and results are available for evaluation
- You receive the research statement, completed queries with results, and any remaining planned queries

## Your Responsibility
Your core task is to EVALUATE RESEARCH PROGRESS AND DECIDE WHETHER TO CONTINUE OR STOP.
Success means correctly identifying when enough authoritative information has been found OR when remaining queries offer little value.

## Downstream Impact
After you:
- If you choose "continue_research": The next database query in the plan will be executed.
- If you choose "stop_research": The Summarizer Agent will be invoked to generate the final research summary for the user.
- Your decision determines the balance between research thoroughness and response efficiency."""

    elif agent_type == "summarizer":
        return """# WORKFLOW CONTEXT

## Complete Agent Workflow
User Query → Router → Research Path (Clarifier → Planner → Database Queries → Judge → Summarizer (YOU))

## Your Position
You are the SUMMARIZER AGENT, the final stage in the research path, responsible for synthesizing all gathered information into a user-friendly summary.

## Upstream Context
Before you:
- The research process has concluded, either by the Judge deciding to stop or by completing all planned queries.
- You receive the original research statement and all completed queries with their results.

## Your Responsibility
Your core task is to GENERATE A COMPREHENSIVE, CLEAR, AND CONCISE SUMMARY of the research findings.
Success means providing a summary that accurately reflects the research, guides the user to relevant details, and highlights key takeaways and potential inconsistencies.

## Downstream Impact
After you:
- Your generated summary will be streamed directly to the user as the final output of the research process.
- The user will evaluate the quality, clarity, and usefulness of your summary."""

    else:
        logger.warning(f"Unknown agent type: {agent_type}, returning empty workflow context")
        return ""

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
                          profile: Optional[str] = None, standardize: bool = True, agent_type: Optional[str] = None) -> str:
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
    full_prompt = f"{prefix}You are {agent_role}.\n\n"
    
    # Add workflow context if agent type is provided
    if agent_type and agent_type in AGENT_TYPES:
        workflow_context = get_workflow_context(agent_type)
        full_prompt += f"{workflow_context}\n\n"
        
        # Add input/output specifications
        io_specs = get_io_specifications(agent_type)
        full_prompt += f"{io_specs}\n\n"
        
        # Add error handling instructions
        error_handling = get_error_handling_instructions(agent_type)
        full_prompt += f"{error_handling}\n\n"
    
    # Add the agent task
    full_prompt += agent_task
    
    return full_prompt
