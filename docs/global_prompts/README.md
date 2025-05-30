# Global Prompts (`iris/src/global_prompts/`)

This directory contains global prompt utilities and statements used across the IRIS system to provide consistent context, instructions, and knowledge source descriptions to the various agents.

## Overview

The global prompts system provides centralized generation of standardized context components for the IRIS system. These modules ensure consistent, compliant, and contextually appropriate behavior across all agents while maintaining centralized control over core system knowledge. Each module generates XML-formatted statements that establish foundational context for agent interactions, including database information, fiscal calendar awareness, project purpose, and compliance requirements.

## Key Components

* **`database_statement.py`**: Provides centralized descriptions of available databases and their usage guidelines
* **`fiscal_statement.py`**: Generates fiscal context statements based on RBC's fiscal calendar (November 1 - October 31)
* **`project_statement.py`**: Provides project context about IRIS system purpose and scope
* **`restrictions_statement.py`**: Defines compliance restrictions, quality guidelines, and confidence signaling requirements
* **`__init__.py`**: Marks the directory as a Python package

## Core Functions/Classes

### Database Statement Module (`database_statement.py`)

#### Purpose
Serves as the single source of truth for database information across the system, providing centralized descriptions of available databases and their usage guidelines.

#### Key Functions
* `get_database_statement()`: Generates XML-formatted database context statement

### Fiscal Statement Module (`fiscal_statement.py`)

#### Purpose
Provides current fiscal context for date-sensitive queries based on RBC's fiscal calendar (November 1 - October 31).

#### Key Functions
* `get_fiscal_statement()`: Generates XML-formatted fiscal context with current period information
* `get_fiscal_period()`: Calculates current fiscal year and quarter
* `get_quarter_dates()`: Calculates start/end dates for fiscal quarters

### Project Statement Module (`project_statement.py`)

#### Purpose
Establishes system context and purpose for all agent interactions, defining IRIS system capabilities and scope.

#### Key Functions
* `get_project_statement()`: Generates XML-formatted project context with timestamp

### Restrictions Statement Module (`restrictions_statement.py`)

#### Purpose
Ensures compliance and quality standards across all agent outputs through comprehensive guidelines and restrictions.

#### Key Functions
* `get_restrictions_statement()`: Generates combined compliance, quality, and confidence guidelines
* `get_compliance_restrictions()`: Provides legal and regulatory compliance rules
* `get_quality_guidelines()`: Establishes output quality standards
* `get_confidence_signaling()`: Defines confidence level signaling requirements

## Configuration

No external configuration required for the global prompts system. Each module uses:

* **Hardcoded Content**: Predefined templates and context structures for consistency
* **System-Based Values**: Dynamic values like timestamps and fiscal calculations based on system date
* **XML Formatting**: Standardized XML-style delimiters for structured prompt components

## Usage Examples

### Basic Integration Pattern
```python
from iris.src.global_prompts import (
    database_statement,
    fiscal_statement,
    project_statement,
    restrictions_statement
)

# Build comprehensive agent prompt
system_prompt = f"""
{project_statement.get_project_statement()}

{fiscal_statement.get_fiscal_statement()}

{database_statement.get_database_statement()}

{restrictions_statement.get_restrictions_statement()}

Your specific role is...
"""
```

## Integration Points

This module is used throughout the IRIS system:

* **All Agent Types**: Router, Clarifier, Planner, Database Subagents, Summarizer, and Direct Response agents
* **System Prompt Construction**: Core components included in agent system prompts
* **Context Injection**: Dynamic context added based on specific agent needs
* **Consistency Enforcement**: Ensures all agents operate with same foundational knowledge

## Dependencies

* **datetime**: For fiscal calendar calculations and timestamps
* **logging**: For operational logging and error tracking
* **typing**: For type hints (in some modules)

## Error Handling

Comprehensive error handling approach across all modules:

* **Consistent Error Patterns**: All modules use standardized try-catch blocks with logging
* **Fallback Statements**: Each module provides appropriate fallback content if generation fails
* **Graceful Degradation**: System continues to function with minimal context if errors occur
* **Comprehensive Logging**: All errors are logged with appropriate context for debugging

## Security Considerations

* **No External Input**: Modules only use system data and hardcoded content, no user input processing
* **No Sensitive Data**: Only processes publicly available context information
* **Static Content**: Uses predefined templates and system-based calculations
* **Safe Fallbacks**: Fallback statements provide minimal information disclosure

## Performance Notes

* **Lightweight Operations**: Simple string formatting and basic calculations with minimal overhead
* **No Caching Required**: Statement generation is fast enough to perform on-demand for each request
* **Memory Efficient**: Uses basic string operations and built-in system functions
* **No Network Dependencies**: All operations performed locally using system resources

---

This global prompts system ensures consistent, compliant, and contextually appropriate behavior across all IRIS agents while maintaining centralized control over core system knowledge.
