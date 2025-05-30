# Project Statement (`iris/src/global_prompts/project_statement.py`)

This module generates a project context statement that provides essential context about the IRIS system's purpose and scope. It establishes the AI's role and capabilities for all agent interactions, ensuring consistent understanding of the system's mission across all components.

## Overview

This module provides standardized project context for the IRIS system, generating XML-formatted statements that describe the system's purpose, capabilities, and scope. The module serves as a foundational component for establishing consistent context across all agent interactions, ensuring all parts of the system understand their role in serving RBC's Accounting Policy Group through intelligent research and response capabilities.

## Key Components

* **`project_statement.py`**: Main module containing project context generation functionality

## Core Functions/Classes

### `get_project_statement()`

#### Purpose
Generates a comprehensive project context statement with current timestamp in XML format for use in agent system prompts.

#### Parameters
* No parameters required

#### Returns
* **str**: XML-formatted project context statement with timestamp

#### Workflow
1. **Get Current Time**: Generate timestamp in "YYYY-MM-DD HH:MM:SS" format
2. **Build XML Statement**: Construct structured XML with project context elements
3. **Include Core Elements**: Add project purpose, knowledge sources, and system purpose sections
4. **Return Statement**: Provide complete formatted statement for prompt integration

#### Error Handling
* **Exception**: Generic exception handling with logging, returns minimal fallback statement

## Configuration

No external configuration required. The module uses hardcoded project context elements:

* **Project Purpose**: Fixed description of IRIS system mission and capabilities
* **Knowledge Sources**: Standard internal and external source descriptions  
* **System Purpose**: Static explanation of RAG-based analysis and response capabilities

## Usage Examples

### Basic Usage
```python
from iris.src.global_prompts.project_statement import get_project_statement

project_context = get_project_statement()
print(project_context)
# Outputs complete project context with current timestamp
```

### Integration in System Prompts
```python
# In agent system prompt construction
from iris.src.global_prompts.project_statement import get_project_statement

system_prompt = f"""
{get_project_statement()}

You are an AI assistant specialized in accounting policy research...
"""
```

### Prompt Composition
```python
# Combined with other global prompts
from iris.src.global_prompts.project_statement import get_project_statement
from iris.src.global_prompts.restrictions_statement import get_restrictions_statement

full_context = f"""
{get_project_statement()}

{get_restrictions_statement()}

Your specific role is...
"""
```

## Integration Points

This module is used throughout the IRIS system:

### Agent System Prompts
* **Router Agent**: Establishes system context for routing decisions
* **Clarifier Agent**: Provides context for query refinement
* **Planner Agent**: Informs database selection with system purpose
* **Database Subagents**: Frames research scope and objectives
* **Summarizer Agent**: Provides context for synthesis goals
* **Direct Response Agent**: Establishes conversational context

### User Interface Context
* **System Introduction**: Explains capabilities to users
* **Response Framing**: Provides context for system responses
* **Expectation Setting**: Clarifies system scope and limitations

## Key Messages Conveyed

### To AI Agents
1. **Primary Mission**: Serve RBC's Accounting Policy Group
2. **Core Technology**: RAG-based research and response system
3. **Dual Capability**: Conversation-based and research-based responses
4. **Quality Focus**: Accurate, policy-compliant guidance

### To Users (Indirectly)
1. **Natural Interaction**: Can engage in conversational format
2. **Intelligent Research**: System independently researches topics
3. **Comprehensive Sources**: Access to internal and external documentation
4. **Permission Awareness**: Respects access limitations

## Maintenance

### Content Updates
Update the project statement when:
* System capabilities change significantly
* New major features are added
* Scope or mission evolves
* Organization structure changes

### Version Considerations
* **Timestamp Automatic**: No manual timestamp management needed
* **Content Static**: Core project description remains stable
* **XML Structure**: Maintain consistent format for LLM parsing

## Dependencies

* **datetime**: For timestamp generation
* **logging**: For error handling and debugging

## Error Handling

Comprehensive error handling approach:

* **Generic Exception in get_project_statement**: Catches all exceptions during statement generation and returns minimal fallback statement
* **Logging**: All errors are logged with appropriate context for debugging
* **Fallback Behavior**: System continues with basic project context if full statement generation fails
* **Minimal Fallback**: Provides essential project description even when full formatting fails

## Security Considerations

* **No External Input**: Module only uses system datetime, no user input processing required
* **No Sensitive Data**: Only processes publicly available project description information
* **Static Content**: Uses hardcoded project context descriptions, no external data sources
* **Safe Fallback**: Fallback statement provides minimal information disclosure

## Performance Notes

* **Lightweight Operations**: Simple string formatting and timestamp generation with minimal overhead
* **No Caching Required**: Statement generation is fast enough to perform on-demand for each request
* **Memory Efficient**: Uses basic string operations and built-in datetime functions
* **No Network Dependencies**: All operations performed locally using system resources

---

This module ensures all IRIS agents have consistent understanding of the system's purpose, capabilities, and scope, enabling coherent and mission-aligned responses across all interactions.