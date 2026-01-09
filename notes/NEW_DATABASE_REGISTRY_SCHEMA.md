# iris_database_registry - Schema Design

## Overview

This table replaces the hardcoded `AVAILABLE_DATABASES` dictionary in `services/src/global_prompts/database_statement.py`, moving database configuration from code to PostgreSQL for easier administration and per-database research parameter management.

## Table Name: `iris_database_registry`

**Purpose:** Central registry for all research databases, their descriptions, access controls, and search configuration parameters.

---

## Core Schema

### Primary Fields

| Column Name | Type | Nullable | Description | Notes |
|------------|------|----------|-------------|-------|
| `db_source` | `VARCHAR(100)` PRIMARY KEY | NOT NULL | Unique database identifier | e.g., `internal_capm`, `external_ey` |
| `db_name` | `VARCHAR(255)` | NOT NULL | Human-readable database name | e.g., "Corporate Accounting Policy Manuals" |
| `db_summary` | `TEXT` | NOT NULL | Brief database description | **For context/awareness** - Used by agents that just need to know what databases exist |
| `db_description` | `TEXT` | NOT NULL | Detailed usage guidance | **For selection/planning** - Includes content details, strategy, query tips, priority/tier info, when to use |

**Description Usage Pattern:**
- **Summary** (`db_summary`): Just the content description from current `description` field
  - Example: *"RBC's comprehensive accounting policies, detailing recognition, measurement, disclosure, and compliance requirements under IFRS and U.S. GAAP frameworks."*
  - Used by: Router (awareness), Summarizer (context), Direct Response (general knowledge)

- **Description** (`db_description`): Combines current `description` + `content_type` + `use_when` + priority/tier into comprehensive guidance
  - Example: *"**Content:** RBC's comprehensive accounting policies under IFRS and U.S. GAAP. Policies and procedures covering recognition, measurement, disclosure, and compliance. **Tier:** Accounting Primary Source. **When to Use:** Always consult first for RBC accounting policy questions. Check for US GAAP flags when relevant. **Query Strategy:** Use RBC-specific terminology and policy area names."*
  - Used by: Planner (database selection), Database Router (detailed routing decisions)

### Search Mode Configuration

| Column Name | Type | Nullable | Description | Notes |
|------------|------|----------|-------------|-------|
| `search_modes` | `TEXT[]` | NOT NULL DEFAULT ARRAY['catalog', 'semantic'] | Available search modes | Options: `catalog`, `semantic`, `metadata_summary` |

### Search Configurations (JSONB)

| Column Name | Type | Nullable | Description | Notes |
|------------|------|----------|-------------|-------|
| `catalog_config` | `JSONB` | NULL | Catalog search parameters | Flexible structure, add fields as needed |
| `semantic_config` | `JSONB` | NULL | Semantic search parameters | Flexible structure, add fields as needed |
| `metadata_config` | `JSONB` | NULL | Metadata summary parameters | Flexible structure, add fields as needed |

**Example `catalog_config`:**
```json
{
  "max_files": 5,
  "max_file_size_mb": 10.0,
  "max_depth_pages": 50,
  "allow_full_file": true
}
```

**Example `semantic_config`:**
```json
{
  "top_k": 10,
  "max_chunks": 20,
  "min_similarity": 0.70,
  "expand_sections": true
}
```

**Example `metadata_config`:**
```json
{
  "top_k": 10,
  "max_files": 8,
  "max_tokens": 2000
}
```

### Access Control & Metadata

| Column Name | Type | Nullable | Description | Notes |
|------------|------|----------|-------------|-------|
| `sample_questions` | `JSONB` | NULL | Array of example questions | Used for testing and UI examples |
| `enabled` | `BOOLEAN` | NOT NULL DEFAULT true | Whether database is active | Allow disabling without deletion |
| `ad_groups` | `TEXT[]` | NULL | Active Directory groups for access | Multiple groups can access same database |
| `created_at` | `TIMESTAMP` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Record creation time | |
| `updated_at` | `TIMESTAMP` | NOT NULL DEFAULT CURRENT_TIMESTAMP | Last modification time | Auto-updated on changes |

**Example `sample_questions` value:**
```json
[
  "What is the IFRS and U.S. GAAP difference on firm commitment related to hedging?",
  "Is a call option in a financial instrument an embedded derivative?",
  "What threshold is considered to be probable under IFRS?"
]
```

---

## Complete Column Summary

| # | Column | Type | Purpose |
|---|--------|------|---------|
| 1 | `db_source` | `VARCHAR(100)` PK | Unique identifier |
| 2 | `db_name` | `VARCHAR(255)` | Human-readable name |
| 3 | `db_summary` | `TEXT` | Brief description (for awareness) |
| 4 | `db_description` | `TEXT` | Detailed guidance (for planning) |
| 5 | `search_modes` | `TEXT[]` | Enabled search modes |
| 6 | `research_config` | `JSONB` | **Primary** - Cascading retrieval parameters |
| 7 | `catalog_config` | `JSONB` | (Legacy) Catalog search parameters |
| 8 | `semantic_config` | `JSONB` | (Legacy) Semantic search parameters |
| 9 | `metadata_config` | `JSONB` | (Legacy) Metadata search parameters |
| 10 | `sample_questions` | `JSONB` | Example queries |
| 11 | `enabled` | `BOOLEAN` | Active/inactive flag |
| 12 | `ad_groups` | `TEXT[]` | AD groups for access control |
| 13 | `created_at` | `TIMESTAMP` | Creation timestamp |
| 14 | `updated_at` | `TIMESTAMP` | Update timestamp |

**Total: 14 columns** - Clean, flexible JSONB configs allow adding fields without schema changes.

---

## Indexes

```sql
CREATE INDEX idx_iris_db_registry_enabled ON iris_database_registry(enabled);
CREATE INDEX idx_iris_db_registry_ad_groups ON iris_database_registry USING GIN(ad_groups);
CREATE INDEX idx_iris_db_registry_search_modes ON iris_database_registry USING GIN(search_modes);
```

---

## Initial Data Migration

### Source Data
- **AVAILABLE_DATABASES** dict (16 databases) → core fields
- **questions_mapping** dict → `sample_questions`
- **ad_group_to_db_mapping** from Config → `ad_groups`

### Migration Mapping

| Source Field | Target Column | Transformation |
|-------------|---------------|----------------|
| dict key | `db_source` | Direct |
| `"name"` | `db_name` | Direct |
| `"description"` | `db_summary` | Direct (just the description text) |
| `"description"` + `"content_type"` + `"use_when"` | `db_description` | **Combine into formatted text** (see template below) |
| From questions_mapping | `sample_questions` | Convert list to JSONB array |
| N/A | `enabled` | Default: `true` |
| From Config mapping | `ad_groups` | Lookup from `ad_group_to_db_mapping`, convert to array |
| N/A | `search_modes` | Default: `['catalog', 'semantic']` (add `metadata_summary` later) |
| N/A | `catalog_config` | NULL initially, populate with sensible defaults per database |
| N/A | `semantic_config` | NULL initially, populate with sensible defaults per database |
| N/A | `metadata_config` | NULL initially, populate with sensible defaults per database |

### Description Template

Combine existing fields into a single comprehensive description:

```
**Content:** {description}. {content_type} covering [key topics].

**Tier/Priority:** [Extracted from use_when: "Tier 1 (Domain Specific)", "Accounting Primary Source", etc.]

**When to Use:** [Extracted from use_when strategy section]

**Query Strategy:** [Extracted from use_when query tips section]

**Query Type:** {query_type}
```

**Example for internal_capm:**
```
**Content:** RBC's comprehensive accounting policies, detailing recognition, measurement, disclosure, and compliance requirements under IFRS and U.S. GAAP frameworks. Policies and procedures covering all aspects of financial reporting.

**Tier/Priority:** Accounting Primary Source - Always consult first for accounting questions.

**When to Use:** Official RBC policy statements. The primary source for RBC accounting policy. Check US GAAP flags when relevant.

**Query Strategy:** Use RBC-specific terms, policy areas; check US GAAP flags.

**Query Type:** semantic search
```

---

## Research Config (Cascading Retrieval Architecture)

The `research_config` JSONB column controls the Cascading Retrieval Architecture behavior per database.

### Research Config Fields

| Field | Type | Description |
|-------|------|-------------|
| `batch_size` | int | Number of documents per batch in metadata processing |
| `max_selected_files` | int | Maximum files to select for deep research (Path A limit) |
| `top_chunks_in_catalog_selection` | int | Top chunks per file in file_selection mode (Path A) |
| `top_chunks_in_metadata_research` | int | Top chunks per file in metadata_research mode (Path B/C) |
| `page_threshold_for_full_content` | int | Page count threshold for full content inclusion |
| `enable_db_wide_deep_research` | bool | Whether DB-wide queries can trigger deep research (Path B vs C) |

### High-Volume Databases (CAPM, Wiki, Memos)
```json
{
  "batch_size": 10,
  "max_selected_files": 15,
  "top_chunks_in_catalog_selection": 1,
  "top_chunks_in_metadata_research": 3,
  "page_threshold_for_full_content": 150,
  "enable_db_wide_deep_research": true
}
```

### Domain-Specific Databases (PAR, AIO, ESG, etc.)
```json
{
  "batch_size": 10,
  "max_selected_files": 10,
  "top_chunks_in_catalog_selection": 1,
  "top_chunks_in_metadata_research": 3,
  "page_threshold_for_full_content": 150,
  "enable_db_wide_deep_research": true
}
```

### External Authoritative (IASB, EY)
```json
{
  "batch_size": 10,
  "max_selected_files": 8,
  "top_chunks_in_catalog_selection": 2,
  "top_chunks_in_metadata_research": 3,
  "page_threshold_for_full_content": 100,
  "enable_db_wide_deep_research": true
}
```

---

## Legacy Search Configs (Deprecated)

The following config sections are from the original schema design but have been superseded by `research_config` for the Cascading Retrieval Architecture.

### High-Volume Semantic Databases (CAPM, Wiki, Memos)
```json
{
  "catalog_config": {
    "max_files": 3,
    "max_file_size_mb": 5.0,
    "max_depth_pages": 30,
    "allow_full_file": false
  },
  "semantic_config": {
    "top_k": 15,
    "max_chunks": 25,
    "min_similarity": 0.72,
    "expand_sections": true
  },
  "metadata_config": {
    "top_k": 20,
    "max_files": 15,
    "max_tokens": 3000
  }
}
```

### Domain-Specific Databases (PAR, AIO, ESG, etc.)
```json
{
  "catalog_config": {
    "max_files": 5,
    "max_file_size_mb": 10.0,
    "max_depth_pages": 50,
    "allow_full_file": true
  },
  "semantic_config": {
    "top_k": 10,
    "max_chunks": 20,
    "min_similarity": 0.70,
    "expand_sections": true
  },
  "metadata_config": {
    "top_k": 10,
    "max_files": 8,
    "max_tokens": 2000
  }
}
```

### External Authoritative (IASB)
```json
{
  "catalog_config": {
    "max_files": 2,
    "max_file_size_mb": 3.0,
    "max_depth_pages": 20,
    "allow_full_file": false
  },
  "semantic_config": {
    "top_k": 20,
    "max_chunks": 30,
    "min_similarity": 0.75,
    "expand_sections": false
  },
  "metadata_config": {
    "top_k": 15,
    "max_files": 10,
    "max_tokens": 2500
  }
}
```

---

## Access Patterns

### Agent Query Patterns

**For awareness/context (Router, Summarizer):**
```sql
-- Lightweight query - just need to know what databases exist
SELECT db_source, db_name, db_summary
FROM iris_database_registry
WHERE enabled = true;
```

**For planning/selection (Planner, Database Router):**
```sql
-- Full context query - need detailed guidance for database selection
SELECT db_source, db_name, db_summary, db_description, search_modes,
       catalog_config, semantic_config, metadata_config
FROM iris_database_registry
WHERE enabled = true;
```

**User-Specific Database List (with AD group filtering):**
```sql
-- Get databases accessible to a user's AD groups
SELECT db_source, db_name, db_summary, sample_questions
FROM iris_database_registry
WHERE enabled = true
  AND (ad_groups && $1::text[] OR ad_groups IS NULL);
  -- $1 is an array of user's AD groups, && is array overlap operator
```

**Get Search Config for Specific Database:**
```sql
-- Get all search configuration for a specific database
SELECT db_source, search_modes,
       catalog_config, semantic_config, metadata_config
FROM iris_database_registry
WHERE db_source = $1 AND enabled = true;
```

---

## Repository Pattern (from RESEARCH_DB_ENHANCEMENTS.md)

Create `services/src/global_prompts/database_metadata_repo.py`:

**Features:**
- Read from `iris_database_registry` via `connect_to_db`
- In-memory caching with TTL (e.g., 5 minutes)
- Fallback to `AVAILABLE_DATABASES` dict if DB query fails (preserves local dev)
- Cache invalidation method for admin updates

**API:**
```python
def get_database_registry(use_cache=True) -> dict:
    """Returns all enabled databases with full config"""

def get_database_config(db_source: str) -> dict:
    """Returns config for a specific database"""

def get_search_config(db_source: str, mode: str) -> dict:
    """Returns search config for a specific database and mode (catalog/semantic/metadata)"""

def invalidate_cache():
    """Force cache refresh on next query"""
```

---

## Backward Compatibility

### Phase 1: Dual-Read (Safe Rollout)
1. Create table and populate data
2. Repository reads from DB with fallback to dict
3. `get_available_databases()` becomes thin wrapper around repo
4. `get_database_statement()` builds XML from DB rows

### Phase 2: DB-Primary
1. Remove fallback to dict
2. All reads from database
3. Keep dict for local dev environments only

### Phase 3: Full Migration
1. Remove AVAILABLE_DATABASES dict from code
2. Local dev uses minimal seeded database

---

## Benefits

1. **Dynamic Configuration**: Update database configs without code changes
2. **Per-Database Limits**: Fine-grained control over search parameters
3. **Access Control**: AD group integration for user permissions
4. **Auditing**: Track when configs change via `updated_at`
5. **Scalability**: Add new databases via INSERT instead of code deploy
6. **Testing**: Enable/disable databases per environment
7. **Multi-Mode Search**: Configure which search modes available per database
8. **Performance Tuning**: Adjust limits based on observed usage patterns

---

## Next Steps

1. Create SQL migration script (`migrations/001_create_iris_database_registry.sql`)
2. Create data seeding script (`migrations/002_seed_database_registry.sql`)
3. Implement repository layer (`database_metadata_repo.py`)
4. Update `get_available_databases()` to use repository
5. Update `get_database_statement()` to build from DB
6. Test with local PostgreSQL
7. Define default `research_config` values per database
8. Create admin utility for updating configs

---

## Related Documentation
- `DATABASE_SCHEMAS.md` - Existing table schemas
- `RESEARCH_DB_ENHANCEMENTS.md` - Full enhancement plan
- `services/src/global_prompts/database_statement.py` - Current implementation
