# Fiscal Statement (`iris/src/global_prompts/fiscal_statement.py`)

This module generates fiscal context statements based on the current date and RBC's fiscal calendar. The fiscal year runs from November 1st to October 31st, and this module provides automatic calculation of current fiscal periods with formatted context for use in agent prompts.

## Overview

High-level fiscal calendar utility that provides temporal context for the IRIS system. It automatically calculates current fiscal periods based on RBC's fiscal year structure (November 1st through October 31st) and generates standardized fiscal context statements for use in agent prompts. The module ensures all agents have consistent temporal awareness for time-sensitive accounting policy queries.

## Key Components

* **`fiscal_statement.py`**: Main module containing fiscal calendar calculations and statement generation

## Core Functions/Classes

### `get_fiscal_period()`

#### Purpose
Calculates the current fiscal year and quarter based on today's date using RBC's fiscal calendar structure.

#### Parameters
* No parameters required

#### Returns
* **Tuple[int, int]**: Tuple containing (fiscal_year, fiscal_quarter)

#### Workflow
1. **Get Current Date**: Retrieve current datetime and extract month/year
2. **Calculate Fiscal Year**: If current month ≥ November (11), use next calendar year; otherwise use current calendar year  
3. **Calculate Fiscal Quarter**: Adjust months to align with fiscal year start (November = month 1) and group into quarters

#### Error Handling
* **Exception**: Generic exception handling with logging - should not fail under normal circumstances

### `get_quarter_dates(fiscal_year, fiscal_quarter)`

#### Purpose
Calculates precise start and end dates for any fiscal quarter in the specified fiscal year.

#### Parameters
* **`fiscal_year`** (int): The fiscal year (e.g., 2024)
* **`fiscal_quarter`** (int): The fiscal quarter (1-4)

#### Returns
* **Dict[str, datetime]**: Dictionary with `start_date` and `end_date` as datetime objects

#### Workflow
1. **Validate Quarter**: Ensure fiscal_quarter is between 1-4
2. **Calculate Start Date**: Determine first day of quarter's first month, accounting for calendar year transitions
3. **Calculate End Date**: Determine last day of quarter's last month using next month calculation minus one day

#### Error Handling
* **ValueError**: Raised when fiscal_quarter is not between 1-4

### `get_quarter_range_str(fiscal_quarter)`

#### Purpose
Returns human-readable date range string for a fiscal quarter using predefined mappings.

#### Parameters
* **`fiscal_quarter`** (int): The fiscal quarter (1-4)

#### Returns
* **str**: Formatted date range string (e.g., "November 1st to January 31st")

#### Workflow
1. **Lookup Range**: Use dictionary mapping to find corresponding date range string
2. **Return Range**: Return formatted string or "Invalid quarter" for invalid input

#### Error Handling
* **Invalid Quarter**: Returns "Invalid quarter" string for quarters outside 1-4 range

### `get_fiscal_statement()`

#### Purpose
Generates a comprehensive fiscal context statement with XML structure for use in agent prompts.

#### Parameters
* No parameters required

#### Returns
* **str**: XML-formatted fiscal context statement

#### Workflow
1. **Get Current Date**: Format current date as YYYY-MM-DD
2. **Calculate Fiscal Period**: Use get_fiscal_period() to determine current fiscal year and quarter
3. **Get Quarter Range**: Use get_quarter_range_str() to get human-readable range
4. **Generate XML**: Construct XML statement with all fiscal context elements

#### Error Handling
* **Exception**: Generic exception handling with logging, returns fallback XML statement

## Configuration

No external configuration required. The module uses hardcoded fiscal calendar definitions:

* **Fiscal Year Start**: November 1st (month 11)
* **Fiscal Year End**: October 31st (month 10)
* **Quarter Definitions**: Fixed 3-month periods aligned with fiscal year structure

## Usage Examples

### Current Fiscal Context
```python
from iris.src.global_prompts.fiscal_statement import get_fiscal_statement

fiscal_context = get_fiscal_statement()
print(fiscal_context)
# Outputs current fiscal context in XML format
```

### Specific Fiscal Period Analysis
```python
from iris.src.global_prompts.fiscal_statement import get_fiscal_period, get_quarter_dates

# Get current period
fiscal_year, quarter = get_fiscal_period()
print(f"Current period: FY{fiscal_year} Q{quarter}")

# Get specific quarter dates
q2_dates = get_quarter_dates(fiscal_year, 2)
print(f"Q2 starts: {q2_dates['start_date'].strftime('%B %d, %Y')}")
print(f"Q2 ends: {q2_dates['end_date'].strftime('%B %d, %Y')}")
```

### Integration in Agent Prompts
```python
# In agent system prompt construction
from iris.src.global_prompts.fiscal_statement import get_fiscal_statement

system_prompt = f"""
{get_fiscal_statement()}

You are an accounting policy assistant...
"""
```

## Integration Points

This module is used throughout the IRIS system:

### Agent Prompts
* **Clarifier Agent**: Provides fiscal context for query refinement
* **Planner Agent**: Informs database selection with time-sensitive context
* **Database Subagents**: Enables fiscal-aware query formulation
* **Summarizer Agent**: Provides fiscal context for synthesis

### Use Cases
* **Quarterly Reporting**: Understanding current reporting period
* **Fiscal Year Planning**: Policy updates and planning cycles  
* **Period-Specific Queries**: Questions about current or specific fiscal periods
* **Temporal Context**: Any query where fiscal timing is relevant

## Dependencies

* **datetime**: For date calculations and formatting
* **timedelta**: For date arithmetic in quarter calculations
* **typing**: For type hints (Tuple, Dict)
* **logging**: For error handling and debugging

## Error Handling

Comprehensive error handling approach:

* **ValueError in get_quarter_dates**: Raised when fiscal_quarter is not between 1-4, provides clear error message
* **Generic Exception in get_fiscal_statement**: Catches all exceptions during statement generation and returns fallback XML statement
* **Logging**: All errors are logged with appropriate context for debugging
* **Fallback Behavior**: System continues to function with minimal fiscal context if errors occur

## Security Considerations

* **No External Input**: Module only uses system datetime, no user input processing required
* **No Sensitive Data**: Only processes publicly available fiscal calendar information
* **Static Data**: Uses hardcoded fiscal calendar definitions, no external data sources

## Performance Notes

* **Lightweight Operations**: All calculations are simple date arithmetic with minimal processing overhead
* **No Caching Required**: Calculations are fast enough to perform on-demand for each request
* **Memory Efficient**: Uses built-in datetime objects and simple data structures
* **No Network Dependencies**: All calculations performed locally using system time

---

This module ensures all IRIS agents have consistent and accurate fiscal context for time-sensitive accounting policy queries and responses.