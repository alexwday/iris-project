# Database Statement (`iris/src/global_prompts/database_statement.py`)

The database statement module provides centralized descriptions and configurations for all available databases in the IRIS system. It serves as the single source of truth for database information, generating structured statements for agent prompts and ensuring consistent database selection strategies across the system.

## Overview

This module maintains comprehensive metadata for all databases accessible to IRIS agents, including internal RBC databases and external knowledge sources. It generates structured XML statements for agent prompts, provides strategic guidance for database selection, and ensures consistent query strategies across the entire system. The module supports hierarchical database organization with clear priorities and usage patterns.

## Key Components

* **`database_statement.py`**: Contains database configurations and statement generation logic
* **`AVAILABLE_DATABASES`**: Centralized configuration dictionary with complete database metadata

## Core Functions/Classes

### `get_database_statement()`

#### Purpose
Generates XML-formatted statement describing all available databases for inclusion in agent system prompts.

#### Parameters
None

#### Returns
* **str**: Formatted XML statement with complete database information organized by type

#### Workflow
1. **Database Grouping**: Separates internal and external databases for structured presentation
2. **XML Generation**: Creates hierarchical XML structure with database metadata
3. **Strategic Organization**: Orders databases by priority and strategic importance
4. **Usage Integration**: Includes detailed strategic guidance for each database
5. **Structure Validation**: Ensures consistent XML formatting for LLM parsing

#### Error Handling
* **Static Configuration**: Database structure is static and rarely fails
* **Consistent Formatting**: Maintains XML structure integrity

### `get_available_databases()`

#### Purpose
Returns the complete database configuration dictionary for programmatic access by other system modules.

#### Parameters
None

#### Returns
* **dict**: Complete database configuration with all metadata and strategic guidance

#### Workflow
1. **Direct Access**: Provides unmodified access to AVAILABLE_DATABASES dictionary
2. **Module Integration**: Enables other modules to access database metadata programmatically

### Database Configuration Schema

#### Purpose
Standardized structure for database metadata ensuring consistency across all database definitions.

#### Schema Structure
```python
"database_id": {
    "name": "Human-readable database name",
    "description": "Detailed description of database contents and scope",
    "query_type": "Type of search/query supported (semantic search, keyword, hybrid)",
    "content_type": "Type of content stored (policies, guidance, standards, etc.)",
    "use_when": "Strategic guidance including tier, priority, and query strategies"
}
```

#### Strategic Components
* **Tier Classification**: Primary, supplementary, or authoritative source designation
* **Query Strategy**: Specific guidance for effective database queries
* **Usage Context**: When and how to use each database effectively
* **RBC Integration**: Internal database integration with RBC-specific terminology

## Configuration

Database categories and their strategic roles:

### Internal Databases (RBC-specific)
* **Accounting Core**: `internal_capm`, `internal_cheatsheets`, `internal_wiki` (always consulted first)
* **Accounting Support**: `internal_memos` (deeper analysis when needed)
* **Domain-Specific**: PAR, AIO, ICFR, ESG, compliance, reporting policies (tier 1 within domains)

### External Databases (External sources)
* **Supplementary**: `external_ey`, `external_kpmg`, `external_pwc` (only when requested or internal insufficient)
* **Authoritative**: `external_iasb` (official IFRS standards when internal unclear)

## Usage Examples

### Agent Prompt Integration
```python
from iris.src.global_prompts.database_statement import get_database_statement

database_info = get_database_statement()
system_prompt = f"""
You are an expert assistant with access to the following databases:

{database_info}

Select appropriate databases based on the strategic guidance provided.
"""
```

### Database Metadata Access
```python
from iris.src.global_prompts.database_statement import get_available_databases

databases = get_available_databases()
database_names = {db_id: db_info['name'] for db_id, db_info in databases.items()}
```

### Strategic Query Planning
```python
# Example for finance policy queries
priority_order = [
    'internal_capm',  # Always first
    'internal_cheatsheets',  # Context
    'internal_wiki',  # Applications
    'internal_memos'  # Deep analysis if needed
]
```

## Integration Points

How this module integrates with other IRIS components:

* **Agent Planner**: Uses database descriptions and strategic guidance for database selection decisions
* **Agent Clarifier**: References database capabilities for scope understanding and planning
* **Database Router**: Validates database availability and routing decisions
* **Model Orchestration**: Accesses display names and metadata for user interface presentation
* **Agent Prompts**: Embedded in system prompts to guide agent database selection

## Dependencies

* **`logging`**: Module initialization logging and debugging information

## Error Handling

Comprehensive error handling approach:

* **Static Configuration**: Database configuration is static and rarely experiences runtime failures
* **Schema Consistency**: Manual review and validation maintains consistent database schema
* **XML Structure**: Robust XML generation with consistent formatting
* **Fallback Behavior**: System gracefully handles missing or invalid database configurations

## Security Considerations

* **Information Disclosure**: Database descriptions carefully crafted to avoid exposing sensitive system details
* **Access Control**: Database availability controlled through centralized configuration
* **Strategic Guidance**: Usage patterns designed to prioritize internal sources appropriately
* **External Source Control**: Clear guidelines for when external sources are appropriate

## Performance Notes

* **Static Configuration**: Database metadata loaded once at module initialization
* **XML Generation**: Efficient string concatenation for statement generation
* **Memory Efficiency**: Lightweight configuration structure with minimal memory footprint
* **Query Optimization**: Strategic guidance designed to minimize unnecessary database queries

---

[Related Documentation: Agent Planner (`planner.py`), Database Router (`database_router.py`)]