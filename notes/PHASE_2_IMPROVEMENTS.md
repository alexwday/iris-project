# Phase 2 Improvements

Housekeeping and enhancement tasks following the completion of the cascading retrieval architecture (Stages 1-10).

**Created:** 2025-12-13
**Research Completed:** 2025-12-13

---

## Research Summary

Deep research was conducted on all 24 tasks. Key findings:

### Critical Issues Identified

1. **Task 16 Missing agent_direct_response** - The plan missed `agent_direct_response/response_from_conversation.py` which must also be flattened
2. **Task 8 Conflict with Task 24** - `ssl_setup.py → rbc_security.py` in Task 8 conflicts with Task 24 which wants to replace the implementation entirely
3. **env_config.py Not Mentioned** - This critical file has no rename plan but is heavily referenced
4. **Task 4 Scope Underestimated** - psycopg2 is used in 8 different files, not just db_config.py

### External Project Research (Tasks 10 & 23)

**Aegis Project (Task 10):**
- Uses `sql_prompt.py` with SQLPromptManager class
- Prompts table schema: `id, model, layer, name, description, comments, system_prompt, user_prompt, tool_definition (JSON), uses_global (TEXT[]), version, created_at, updated_at`
- Uses `prompt_loader.py` for loading prompts with global prompt composition
- Has `uses_global` array field for composing global prompts (fiscal, project, database, restrictions)

**Local-LLM-Proxy Project (Task 23):**
- Simple pattern: `import rbc_security; rbc_security.enable_certs()`
- Uses try/except for optional availability
- DEV_MODE environment variable to skip setup locally
- Pattern is much simpler than current ssl_setup.py

---

## Task Summary (Updated)

| # | Task | Description | Complexity | Files | Status |
|---|------|-------------|------------|-------|--------|
| 0 | Consolidate databases | Migrate tables from `maven-finance` to `finance-dev` | Medium | 6 tables | **Complete** |
| 1 | Rename llm_connectors folder | Rename to `connections` | Low | 10 | **Complete** |
| 2 | Rename rbc_openai.py | Rename to `llm.py` | Low | 10 | **Complete** |
| 3 | Move and rename db_config | Rename to `postgres.py`, move to connections | **Medium** | 12 | **Complete** |
| 4 | SQLAlchemy migration | Update postgres.py to use SQLAlchemy, consolidate all DB access | **Very High** | 8 | **4a Complete** |
| 5 | Rename oauth_setup | Rename to `oauth.py` | Low | 6 | **Complete** |
| 6 | Move oauth.py | Move to connections folder | Low | 6 | **Complete** |
| 7 | Rename initial_setup folder | Rename to `utils` | **Medium** | 26 | **Complete** |
| 8 | Rename utils files | Rename multiple files in utils folder | **Medium** | 8 | **Complete** |
| 9 | Rename chat_model folder | Rename folder to `model`, file to `main.py` | Low | 8 | **Complete** |
| 10 | Research aegis prompt loading | Study aegis project's postgres prompt loading pattern | ✅ Done | - | **Complete** |
| 11 | Inventory all prompts | List every prompt in IRIS, add to postgres prompts table | Medium | 8 YAML | **Complete** |
| 12 | Migrate to postgres prompts | Update code to use postgres prompts, remove YAML usage | **High** | 8 | **Complete** |
| 13 | Archive prompt YAMLs | Move deprecated YAML files to notes/prompts folder | Low | 8 | **Complete** |
| 14 | Flatten subagent structure | Rename and move subagent.py files up, delete subfolders | Medium | 5 | **Complete** |
| 15 | Rename database_subagents | Rename to `tools` | Low | 6 | **Complete** |
| 16 | Flatten agent structure | Move agent py files up to agents folder, delete subfolders | **Medium** | 12 | **Complete** |
| 17 | Rename agents folder | Rename to `agent` | Low | 14 | Pending |
| 18 | Migrate global prompts | Move restrictions/project prompts to postgres | Medium | 7 | Pending |
| 19 | Refactor fiscal_statement | Move to utils, rename to `fiscal_context`, ensure universal usage | Medium | 6 | Pending |
| 20 | Remove database_statement | Verify postgres migration complete, then remove | Low | 6 | Pending |
| 21 | Move database_metadata_repo | Move to database_subagents, rename to `database_metadata` | Low | 4 | Pending |
| 22 | Delete global_prompts folder | Remove empty folder after migrations | Low | 1 | Pending |
| 23 | Research rbc_security lib | Study local-llm-proxy usage, plan SSL replacement | ✅ Done | - | **Complete** |
| 24 | Implement rbc_security | Replace ssl_setup with rbc_security, delete deprecated files | Medium | 5 | Pending |

---

## Task Details (Refined with Research)

### Task 0: Consolidate databases (maven-finance → finance-dev)

**Description:**
Migrate all IRIS tables from `maven-finance` database to `finance-dev` database. This consolidates IRIS and aegis into a single database, enabling IRIS to use the existing `prompts` table.

**Why:**
- `finance-dev` already has the `prompts` table with 34 aegis prompts
- Sharing one `prompts` table across projects (using `model` column to differentiate)
- Cleaner architecture with one database instead of two

**Tables to Migrate (6 tables):**
```
iris_database_registry    (16 rows)  - Database configurations
iris_document_metadata    (7 rows)   - Document metadata
iris_document_chunks      (49 rows)  - Document chunks with embeddings
iris_semantic_search      (30 rows)  - Semantic search data
apg_catalog               (5 rows)   - APG catalog entries
apg_content               (19 rows)  - APG content
```

**NOT migrated:**
- `process_monitor_logs` - Already exists in `finance-dev` with identical schema; just switch to using it
- `v_document_with_chunks` - This is a view; recreate after base tables are migrated

**Migration Steps:**
1. Export table schemas and data from `maven-finance`
2. Import into `finance-dev`
3. Recreate the `v_document_with_chunks` view
4. Update IRIS config: change `DB_NAME` from `maven-finance` to `finance-dev`
5. Update test files to use `finance-dev`
6. Verify all queries work
7. (Later) Drop `maven-finance` database

**Files to Update:**
```
services/src/initial_setup/env_config.py:58          # DB_NAME default
testing/local_data/start_local_server.py             # DB env vars
testing/local_data/test_full_local.py                # DB env vars
testing/local_data/populate_local_db.py              # DB connection
testing/populate_database_registry.py                # DB connection
testing/populate_unified_tables.py                   # DB connection
.env.example                                         # Documentation
```

**Risk:** Medium - Database migration, but local dev only
**Complexity:** Medium

---

### Task 1: Rename llm_connectors folder

**Description:**
Rename `services/src/llm_connectors` to `services/src/connections`

**Files Affected (10 files):**
```
services/src/llm_connectors/                         # Rename folder
services/src/llm_connectors/__init__.py              # Update path in header comment
services/src/llm_connectors/rbc_openai.py            # Update path in header comment
services/src/chat_model/model.py:34                  # from ..llm_connectors.rbc_openai import
services/src/agents/agent_router/router.py:26        # from ...llm_connectors.rbc_openai import
services/src/agents/agent_clarifier/clarifier.py:29 # from ...llm_connectors.rbc_openai import
services/src/agents/agent_summarizer/summarizer.py:25 # from ...llm_connectors.rbc_openai import
services/src/agents/agent_planner/planner.py:25      # from ...llm_connectors.rbc_openai import
services/src/agents/agent_direct_response/response_from_conversation.py:23 # from ...llm_connectors.rbc_openai import
services/src/agents/database_subagents/metadata_subagent/subagent.py:32 # from ....llm_connectors.rbc_openai import
services/src/agents/database_subagents/file_research_subagent/subagent.py:32 # from ....llm_connectors.rbc_openai import
README.md:67                                          # Documentation reference
```

**Risk:** Low - Simple folder rename with well-defined import paths
**Complexity:** Low (confirmed)

---

### Task 2: Rename rbc_openai.py

**Description:**
Rename `rbc_openai.py` to `llm.py` within the connections folder

**Files Affected (10 files):**
```
# Same files as Task 1, just updating the filename in imports
services/src/connections/rbc_openai.py → llm.py
services/src/chat_model/model.py:34
services/src/agents/agent_router/router.py:26
services/src/agents/agent_clarifier/clarifier.py:29
services/src/agents/agent_summarizer/summarizer.py:25
services/src/agents/agent_planner/planner.py:25
services/src/agents/agent_direct_response/response_from_conversation.py:23
services/src/agents/database_subagents/metadata_subagent/subagent.py:32
services/src/agents/database_subagents/file_research_subagent/subagent.py:32
```

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 3: Move and rename db_config

**Description:**
Rename `db_config.py` to `postgres.py` and move from initial_setup to connections folder

**Files Affected (12 files - more than originally estimated):**
```
services/src/initial_setup/db_config.py → services/src/connections/postgres.py
services/src/initial_setup/__init__.py:7             # from ..initial_setup.db_config import
services/src/chat_model/model.py:45                  # from ..initial_setup.db_config import
services/src/chat_model/model.py:956                 # from ..initial_setup.db_config import
services/src/global_prompts/database_metadata_repo.py:18 # from ..initial_setup.db_config import
services/src/agents/database_subagents/metadata_subagent/subagent.py:31 # from ....initial_setup.db_config import
services/src/agents/database_subagents/file_research_subagent/subagent.py:31 # from ....initial_setup.db_config import
testing/local_data/start_local_server.py:58          # import services.src.initial_setup.db_config
testing/local_data/test_full_local.py:62             # import services.src.initial_setup.db_config
testing/test_cascading_retrieval.py:56               # import services.src.initial_setup.db_config
testing/test_metadata_subagent.py:59                 # import services.src.initial_setup.db_config
testing/test_full_pipeline.py:39                     # import services.src.initial_setup.db_config
```

**Risk:** Medium - Testing files use full path imports, need careful update
**Complexity:** **Medium** (upgraded from Low)

---

### Task 4: SQLAlchemy migration

**Description:**
Update postgres.py to use SQLAlchemy ORM. Ensure ALL code uses this single connection module.

**Files Using psycopg2 Directly (8 files):**
```
services/src/initial_setup/db_config.py              # import psycopg2 - MAIN FILE
services/src/initial_setup/process_monitor_setup.py:24 # from psycopg2.extras import Json
services/src/chat_model/model.py:46                  # import psycopg2.extras
services/src/global_prompts/database_metadata_repo.py:15-16 # import psycopg2
services/src/agents/database_subagents/metadata_subagent/subagent.py:26-28 # import psycopg2
services/src/agents/database_subagents/file_research_subagent/subagent.py:26-28 # import psycopg2
testing/populate_database_registry.py:47-48          # import psycopg2
testing/populate_unified_tables.py:47-49             # import psycopg2
```

**Aegis Reference Pattern:**
The aegis project uses SQLAlchemy async with `postgresql+asyncpg://` driver:
- Connection pooling (pool_size=20, max_overflow=40)
- Async context managers for connections
- Session factory pattern

**Risk:** **Very High** - Core database access, affects all queries
**Complexity:** **Very High** (upgraded from High)

**Recommendation:** Consider splitting into sub-tasks:
1. Create SQLAlchemy engine/session in postgres.py
2. Migrate db_config functions (connect_to_db, construct_dsn)
3. Migrate database_metadata_repo queries
4. Migrate subagent queries
5. Migrate process_monitor_setup
6. Update testing files

---

### Task 5: Rename oauth_setup

**Description:**
Rename `oauth_setup.py` to `oauth.py`

**Files Affected (6 files):**
```
services/src/initial_setup/oauth_setup.py → oauth.py
services/src/chat_model/model.py:954                 # from ..initial_setup.oauth_setup import
services/src/initial_setup/process_monitor_setup.py:98 # stage_name == "oauth_setup"
testing/local_data/start_local_server.py:57          # import services.src.initial_setup.oauth_setup
testing/local_data/test_full_local.py:61             # import services.src.initial_setup.oauth_setup
testing/test_cascading_retrieval.py:55               # import services.src.initial_setup.oauth_setup
testing/test_metadata_subagent.py:58                 # import services.src.initial_setup.oauth_setup
testing/test_full_pipeline.py:82                     # import services.src.initial_setup.oauth_setup
```

**Note:** The process_monitor uses "oauth_setup" as a stage name - this is a string, not an import, so it can stay or be updated for consistency.

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 6: Move oauth.py

**Description:**
Move `oauth.py` from initial_setup (utils) to connections folder

**Files Affected:** Same as Task 5, import paths change from `..initial_setup.oauth` to `..connections.oauth`

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 7: Rename initial_setup folder

**Description:**
Rename `services/src/initial_setup` to `services/src/utils`

**Files Affected (26 import locations - HIGH IMPACT):**
```
# Main source files
services/src/llm_connectors/rbc_openai.py:26
services/src/api.py:31-32
services/src/chat_model/model.py:42,45,750,900,952-956
services/src/agents/agent_router/router.py:25
services/src/agents/agent_clarifier/clarifier.py:28
services/src/agents/agent_summarizer/summarizer.py:24
services/src/agents/agent_planner/planner.py:24
services/src/agents/agent_direct_response/response_from_conversation.py:22
services/src/agents/database_subagents/metadata_subagent/subagent.py:30-31
services/src/agents/database_subagents/file_research_subagent/subagent.py:30-31
services/src/global_prompts/database_metadata_repo.py:18
config/config.py:20

# Testing files
testing/local_data/start_local_server.py:57-58,127
testing/local_data/test_full_local.py:61-62,134
testing/test_cascading_retrieval.py:55-56
testing/test_metadata_subagent.py:58-59
testing/test_full_pipeline.py:32,39,82
testing/test_local_openai.py:24

# Initial_setup internal references (files within folder)
services/src/initial_setup/__init__.py:7-8
services/src/initial_setup/db_config.py:11
services/src/initial_setup/conversation_setup.py:20
services/src/initial_setup/logging_config.py:21
services/src/initial_setup/ssl_setup.py:35
services/src/initial_setup/oauth_setup.py:24
services/src/initial_setup/process_monitor_setup.py:25
services/src/initial_setup/env_config.py:13
```

**Risk:** Medium - Touches many files across codebase
**Complexity:** **Medium** (upgraded from Low)

---

### Task 8: Rename utils files

**Description:**
Rename multiple files within the utils folder:
- `conversation_setup.py` → `input_sanitizer.py`
- `logging_config.py` → `logging_format.py`
- `process_monitor_setup.py` → `process_monitoring.py`
- ~~`ssl_setup.py` → `rbc_security.py`~~ **CONFLICT - See Task 24**

**Files Affected per rename:**
```
# conversation_setup.py (1 reference)
services/src/chat_model/model.py:952

# logging_config.py (5 references)
services/src/api.py:31
services/src/chat_model/model.py:953
services/src/initial_setup/__init__.py:8
testing/test_local_openai.py:24
testing/test_full_pipeline.py:32
testing/local_data/test_full_local.py:134

# process_monitor_setup.py (2 references)
services/src/chat_model/model.py:750,900
```

**CONFLICT ALERT:** Task 8 wants to rename `ssl_setup.py → rbc_security.py`, but Task 24 wants to REPLACE ssl_setup.py with a completely new implementation using the rbc_security library. These conflict.

**Resolution:** Remove ssl_setup.py rename from Task 8. Task 24 will handle it.

**Risk:** Medium - Multiple renames
**Complexity:** **Medium** (upgraded from Low)

---

### Task 9: Rename chat_model folder

**Description:**
Rename `services/src/chat_model` folder to `services/src/model`, and rename `model.py` to `main.py`

**Files Affected (8 files):**
```
services/src/chat_model/ → services/src/model/
services/src/chat_model/model.py → services/src/model/main.py
services/src/api.py:90,108                           # from .chat_model.model import
testing/test_full_pipeline.py:98,130                 # from services.src.chat_model.model import
testing/local_data/test_full_local.py:145,190,238,286 # from services.src.chat_model.model import
testing/test_cascading_retrieval.py:217              # from services.src.chat_model.model import
```

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 10: Research aegis prompt loading ✅ COMPLETE

**Research Findings:**

**Prompt Table Schema (from aegis):**
```sql
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    model TEXT NOT NULL,          -- e.g., 'aegis', 'iris'
    layer TEXT,                   -- e.g., 'agent', 'subagent', 'global'
    name TEXT NOT NULL,           -- e.g., 'router', 'clarifier'
    description TEXT,
    comments TEXT,
    system_prompt TEXT,
    user_prompt TEXT,
    tool_definition JSON,         -- Single tool
    uses_global TEXT[],           -- Array of global prompts to compose
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key Patterns:**
1. `SQLPromptManager` class manages all prompt queries
2. `get_latest_prompt(model, layer, name)` fetches prompts
3. `uses_global` array specifies which global prompts to compose (fiscal, project, database, restrictions)
4. `prompt_loader.py` handles composition with global prompts
5. Order matters: fiscal > project > database > restrictions

**Implementation Plan for IRIS:**
1. Create `services/src/utils/prompt_loader.py`
2. Implement `IrisPromptManager` class using same table, filter by `model='iris'`
3. Create composition logic for global prompts
4. Migration script to populate prompts table with IRIS prompts

---

### Task 11: Inventory all prompts

**Description:**
Go through the entire IRIS project and list every prompt

**YAML Prompt Files Found (8 files):**
```
services/src/agents/agent_router/router_prompt.yaml
services/src/agents/agent_clarifier/clarifier_prompt.yaml
services/src/agents/agent_planner/planner_prompt.yaml
services/src/agents/agent_summarizer/summarizer_prompt.yaml
services/src/agents/agent_summarizer/summarizer_prompt_updated.yaml (duplicate?)
services/src/agents/agent_direct_response/response_prompt.yaml
services/src/agents/database_subagents/metadata_subagent/metadata_decision_prompt.yaml
services/src/agents/database_subagents/file_research_subagent/file_research_prompt.yaml
```

**Global Prompts (Python files - may move to postgres):**
```
services/src/global_prompts/project_statement.py     # get_project_statement()
services/src/global_prompts/restrictions_statement.py # get_restrictions_statement()
services/src/global_prompts/fiscal_statement.py       # get_fiscal_statement() - DYNAMIC
services/src/global_prompts/database_statement.py     # get_database_statement() - reads from registry
```

**Note:** fiscal_statement.py is dynamically generated based on current date. It cannot be stored in postgres as-is and should remain as Python code.

**Risk:** Medium
**Complexity:** Medium (confirmed)

---

### Task 12: Migrate to postgres prompts

**Description:**
Update all code to use the postgres prompts table directly.

**Files That Load YAML Prompts (7 files):**
```
services/src/agents/agent_router/router.py:121-124        # yaml_path, yaml.safe_load
services/src/agents/agent_clarifier/clarifier.py:124-127  # yaml_path, yaml.safe_load
services/src/agents/agent_planner/planner.py:169-172      # yaml_path, yaml.safe_load
services/src/agents/agent_summarizer/summarizer.py:61-64  # yaml_path, yaml.safe_load
services/src/agents/agent_direct_response/response_from_conversation.py:118-121
services/src/agents/database_subagents/metadata_subagent/subagent.py:278-281
services/src/agents/database_subagents/file_research_subagent/subagent.py:201-204
```

**Changes Required Per File:**
1. Remove `import yaml` and `import os`
2. Remove YAML loading function
3. Import prompt_loader
4. Replace YAML load with `prompt_loader.get_prompt(layer, name)`

**Risk:** High - Affects all agent prompt loading
**Complexity:** High (confirmed)

---

### Task 13: Archive prompt YAMLs

**Description:**
Move all deprecated prompt YAML files to notes/prompts folder

**Files to Move (8 files):**
```
→ notes/prompts/agent_router_prompt.yaml
→ notes/prompts/agent_clarifier_prompt.yaml
→ notes/prompts/agent_planner_prompt.yaml
→ notes/prompts/agent_summarizer_prompt.yaml
→ notes/prompts/agent_summarizer_prompt_updated.yaml
→ notes/prompts/agent_direct_response_prompt.yaml
→ notes/prompts/metadata_decision_prompt.yaml
→ notes/prompts/file_research_prompt.yaml
```

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 14: Flatten subagent structure

**Description:**
Move subagent.py files up and rename them

**Files Affected (5 items):**
```
# Renames
services/src/agents/database_subagents/metadata_subagent/subagent.py
  → services/src/agents/database_subagents/metadata_agent.py

services/src/agents/database_subagents/file_research_subagent/subagent.py
  → services/src/agents/database_subagents/file_research_agent.py

# Folders to delete
services/src/agents/database_subagents/metadata_subagent/
services/src/agents/database_subagents/file_research_subagent/

# Import updates
services/src/chat_model/model.py:39 (database_router imports, not direct subagent)
testing/test_metadata_subagent.py:105 (from ...metadata_subagent import)
```

**Note:** YAML files must be moved with Task 12-13 BEFORE this task, or paths break

**Risk:** Medium - Folder structure change
**Complexity:** Medium (confirmed)

---

### Task 15: Rename database_subagents

**Description:**
Rename to `database_tools`

**Files Affected (6 locations):**
```
services/src/agents/database_subagents/ → database_tools/
services/src/chat_model/model.py:39                  # from ..agents.database_subagents.database_router
testing/test_metadata_subagent.py:105                # from services.src.agents.database_subagents
README.md:65                                          # Documentation
```

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 16: Flatten agent structure ⚠️ UPDATED

**Description:**
Move each agent py file up to the main agents folder. **CRITICAL:** Must include agent_direct_response which was missing from original plan.

**Files Affected (12 items - 5 agents + folders + imports):**
```
# File moves (5 agents, not 4!)
services/src/agents/agent_planner/planner.py → services/src/agents/planner.py
services/src/agents/agent_clarifier/clarifier.py → services/src/agents/clarifier.py
services/src/agents/agent_router/router.py → services/src/agents/router.py
services/src/agents/agent_summarizer/summarizer.py → services/src/agents/summarizer.py
services/src/agents/agent_direct_response/response_from_conversation.py → services/src/agents/direct_response.py

# Folders to delete (5, not 4!)
services/src/agents/agent_planner/
services/src/agents/agent_clarifier/
services/src/agents/agent_router/
services/src/agents/agent_summarizer/
services/src/agents/agent_direct_response/

# Import updates
services/src/chat_model/model.py:945-951             # All 5 agent imports
testing/test_local_openai.py:32,62,101,132           # Agent imports in tests
```

**Note:** YAML files must be moved with Task 12-13 BEFORE this task

**Risk:** Medium
**Complexity:** **Medium** (upgraded - more files than originally listed)

---

### Task 17: Rename agents folder

**Description:**
Rename `services/src/agents` to `services/src/agent`

**Files Affected (14 locations):**
```
services/src/agents/ → services/src/agent/
services/src/chat_model/model.py:39,945-951
services/src/api.py (if any agent references)
testing/test_local_openai.py:32,62,101,132
testing/test_metadata_subagent.py:105
```

**Risk:** Low - Simple folder rename after flattening
**Complexity:** Low (confirmed)

---

### Task 18: Migrate global prompts

**Description:**
Move restrictions and project prompts to postgres

**Files Affected (7 agent files that call these):**
```
# Functions to migrate to postgres
get_project_statement()
get_restrictions_statement()

# Files that call them
services/src/agents/agent_direct_response/response_from_conversation.py:24-27
services/src/agents/agent_router/router.py:27-30
services/src/agents/agent_clarifier/clarifier.py:30-33
services/src/agents/agent_planner/planner.py:26-29
services/src/agents/agent_summarizer/summarizer.py:26-28
```

**Note:** These prompts are semi-static. Store in postgres as `model='iris', layer='global', name='project'/'restrictions'`

**Risk:** Medium
**Complexity:** Medium (confirmed)

---

### Task 19: Refactor fiscal_statement

**Description:**
Move to utils folder, rename to `fiscal_context.py`

**Files Affected (6 locations):**
```
services/src/global_prompts/fiscal_statement.py → services/src/utils/fiscal_context.py

# Import updates
services/src/agents/agent_direct_response/response_from_conversation.py:25
services/src/agents/agent_router/router.py:28
services/src/agents/agent_clarifier/clarifier.py:31
services/src/agents/agent_planner/planner.py:27
services/src/agents/agent_summarizer/summarizer.py:27
```

**Note:** This file MUST remain as Python code because it dynamically calculates fiscal year/quarter based on current date. Cannot move to postgres.

**Risk:** Low
**Complexity:** Low (corrected from Medium)

---

### Task 20: Remove database_statement

**Description:**
Verify postgres migration complete, then remove

**Files Affected (6 locations):**
```
# File to delete
services/src/global_prompts/database_statement.py

# References to update
services/src/chat_model/model.py:31,1012             # get_available_databases
services/src/api.py:278                              # get_available_databases
services/src/agents/agent_direct_response/response_from_conversation.py:26
services/src/agents/agent_router/router.py:29
services/src/agents/agent_planner/planner.py:28
services/src/agents/agent_clarifier/clarifier.py:32
testing/test_local_openai.py:133
testing/populate_database_registry.py:49             # AVAILABLE_DATABASES import
config/config.py:111                                 # AVAILABLE_DATABASES import
```

**Prerequisite:** Confirm iris_database_registry table contains all databases and get_available_databases() works from registry only

**Risk:** Medium - Ensure registry is complete
**Complexity:** Low (confirmed)

---

### Task 21: Move database_metadata_repo

**Description:**
Move to database_subagents (database_tools), rename to `database_metadata.py`

**Files Affected (4 locations):**
```
services/src/global_prompts/database_metadata_repo.py
  → services/src/agents/database_tools/database_metadata.py

# Import updates
services/src/api.py:316                              # from .global_prompts.database_metadata_repo
services/src/agents/database_subagents/metadata_subagent/subagent.py:33
services/src/agents/database_subagents/file_research_subagent/subagent.py:33
```

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 22: Delete global_prompts folder

**Description:**
After all migrations complete, delete the now-empty global_prompts folder

**Prerequisites:**
- Task 18 (global prompts to postgres) ✓
- Task 19 (fiscal_statement moved) ✓
- Task 20 (database_statement removed) ✓
- Task 21 (database_metadata_repo moved) ✓

**Files to Delete:**
```
services/src/global_prompts/__init__.py
services/src/global_prompts/                         # Entire folder
```

**Risk:** Low
**Complexity:** Low (confirmed)

---

### Task 23: Research rbc_security lib ✅ COMPLETE

**Research Findings from local-llm-proxy:**

**Usage Pattern (extremely simple):**
```python
def setup_rbc_security():
    """Enable RBC Security SSL certificates."""
    try:
        import rbc_security
        logger.info("Enabling RBC Security certificates...")
        rbc_security.enable_certs()
        logger.info("RBC Security certificates enabled")
    except ImportError:
        logger.warning("⚠️  rbc_security not available - install with: pip install rbc_security")
        logger.warning("⚠️  Continuing without SSL certificates (may fail in RBC environment)")
```

**Environment Variable Pattern:**
```python
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

if DEV_MODE:
    logger.info("🔧 DEV_MODE: Skipping rbc_security setup")
    return
```

**Key Differences from Current ssl_setup.py:**
- Current code manually loads certificate file and sets env vars
- rbc_security library handles everything internally
- No need for certificate file path management
- Much simpler - just call `enable_certs()`

---

### Task 24: Implement rbc_security

**Description:**
Replace ssl_setup.py with new rbc_security implementation

**Implementation Plan:**
```python
# services/src/utils/ssl_context.py (new file, simpler name)

import os
import logging

logger = logging.getLogger(__name__)

def setup_ssl():
    """
    Setup SSL certificates for RBC environment.

    Uses rbc_security library if available.
    Can be disabled with IRIS_DEV_MODE=true environment variable.
    """
    dev_mode = os.getenv("IRIS_DEV_MODE", "false").lower() == "true"

    if dev_mode:
        logger.info("DEV_MODE: Skipping SSL setup")
        return None

    try:
        import rbc_security
        logger.info("Enabling RBC Security certificates...")
        rbc_security.enable_certs()
        logger.info("RBC Security certificates enabled")
        return "rbc_security"
    except ImportError:
        logger.warning("rbc_security not available - install with: pip install rbc_security")
        logger.warning("Continuing without SSL certificates (may fail in RBC environment)")
        return None
```

**Files Affected:**
```
# New file
services/src/utils/ssl_context.py                    # New implementation

# Delete
services/src/initial_setup/ssl_setup.py             # Old implementation
services/src/initial_setup/rbc-ca-bundle.cer        # No longer needed

# Update
services/src/chat_model/model.py:955                 # from ..initial_setup.ssl_setup import
services/src/initial_setup/process_monitor_setup.py:95 # "ssl_setup" stage name
services/src/initial_setup/env_config.py:68-72       # SSL config vars (may no longer be needed)
```

**Risk:** Medium - SSL is critical for production
**Complexity:** Medium (confirmed)

---

## Revised Dependencies

```
Task 1 → Task 2, 3          # connections folder exists before file moves
Task 3 → Task 4             # postgres.py exists before SQLAlchemy migration
Task 5 → Task 6             # oauth renamed before moved
Task 7 → Task 8             # utils folder exists before file renames
Task 10 ✓ → Task 11 → Task 12 → Task 13   # prompt migration sequence
Task 12 → Task 14           # YAML files moved before flattening subagents
Task 12 → Task 16           # YAML files moved before flattening agents
Task 14 → Task 15           # subagents flattened before folder rename
Task 15 → Task 21           # database_tools exists before metadata_repo move
Task 16 → Task 17           # agents flattened before folder rename
Task 18, 19, 20, 21 → Task 22  # all global_prompts files moved before folder delete
Task 23 ✓ → Task 24         # research complete before implementation
```

---

## Revised Execution Order (Updated with Clarified Decisions)

**Phase 0: Database Consolidation (Prerequisite)**
```
0. Task 0: Migrate tables from maven-finance → finance-dev, update IRIS config
```

**Phase A: Connections Setup (Low Risk)**
```
1. Task 1: Rename llm_connectors → connections
2. Task 2: Rename rbc_openai.py → llm.py
3. Task 3: Move db_config.py → connections/postgres.py
4. Task 5: Rename oauth_setup.py → oauth.py
5. Task 6: Move oauth.py → connections/
```

**Phase B: Utils Setup (Medium Risk)**
```
6. Task 7: Rename initial_setup → utils
7. Task 8: Rename utils files (WITHOUT ssl_setup)
8. Task 9: Rename chat_model → model, model.py → main.py
```

**Phase B2: SQLAlchemy Foundation (Medium Risk) - NEW POSITION**
```
9. Task 4a: Create SQLAlchemy engine/session in connections/postgres.py
   - Add SQLAlchemy alongside existing psycopg2 (don't break anything yet)
   - Create Session factory for new code to use
```

**Phase C: Prompt Migration (High Risk)**
```
10. Task 11: Inventory all prompts, add to finance-dev prompts table
11. Task 12: Migrate code to use postgres prompts (prompt_loader uses SQLAlchemy)
12. Task 13: Archive YAML files to notes/prompts/
```

**Phase D: Structure Flattening (Medium Risk)**
```
13. Task 14: Flatten subagent structure, rename classes (MetadataSubagent → MetadataAgent)
14. Task 15: Rename database_subagents → database_tools
15. Task 16: Flatten agent structure (including agent_direct_response!)
16. Task 17: Rename agents → agent
```

**Phase E: Global Prompts Cleanup (Medium Risk)**
```
17. Task 18: Verify agents use postgres prompts via prompt_loader, delete project_statement.py & restrictions_statement.py
18. Task 19: Move fiscal_statement → utils/fiscal_context.py
19. Task 20: Remove database_statement.py, update all AVAILABLE_DATABASES references to use DatabaseMetadataRepository
20. Task 21: Move database_metadata_repo → database_tools/database_metadata.py
21. Task 22: Delete global_prompts folder
```

**Phase F: Complete SQLAlchemy Migration (High Risk)**
```
22. Task 4b: Create ORM models for all tables
23. Task 4c: Migrate database_metadata.py to SQLAlchemy
24. Task 4d: Migrate metadata_agent.py and file_research_agent.py to SQLAlchemy
25. Task 4e: Migrate process_monitoring.py to SQLAlchemy
26. Task 4f: Migrate main.py queries to SQLAlchemy
27. Task 4g: Remove psycopg2 imports and old connect_to_db() function
```

**Phase G: Security Refactor (Medium Risk)**
```
28. Task 24: Implement rbc_security with IRIS_USE_RBC_SECURITY env var, delete ssl_setup.py
```

---

## Risk Assessment Summary

| Phase | Risk Level | Key Concerns |
|-------|------------|--------------|
| A | Low | Simple renames, many files but low complexity |
| B | Medium | initial_setup has 26 import locations |
| C | **High** | Prompt loading is core functionality |
| D | Medium | Structure changes, but after prompts fixed |
| E | Medium | Dependencies between tasks |
| F | **Very High** | psycopg2 in 8 files, async migration complex |
| G | Medium | SSL is production-critical |

---

## Recommendations Before Implementation

1. **Create backup branch** before starting Phase A

2. **Split Task 4 (SQLAlchemy)** into 5-6 sub-tasks to reduce risk

3. **Test locally after each phase** - don't batch multiple phases

4. **Task 8 conflict resolved** - ssl_setup rename removed, handled by Task 24

5. **Task 16 updated** - agent_direct_response now included

6. **Consider env_config.py** - This critical file has no rename plan. It may be fine as-is, but worth noting.

7. **Documentation updates needed** - README.md references old paths (llm_connectors, database_subagents)

8. **Testing files use absolute imports** - Many testing/*.py files use `import services.src.initial_setup.X` patterns which need careful updating

---

## Clarified Decisions (2025-12-13)

Based on review discussion, the following decisions were made:

### 1. Model Configuration Storage
**Decision:** Store model config (capability, max_tokens, temperature) directly in each agent/subagent Python script at the top, NOT in the prompts table.

```python
# At top of each agent file
MODEL_CONFIG = {
    "capability": "large",
    "max_tokens": 4096,
    "temperature": 0.0
}
```

### 2. Summarizer Prompt Version
**Decision:** Merge the best of both files. The reference formatting evolved - use the newer [REF:x] only format but review both for any other improvements.

### 3. 'database' Global Prompt Handling
**Decision:** prompt_loader handles 'database' as a special case by calling a separate function (like `get_database_statement()`) that reads from `iris_database_registry`. This function is available to prompt_loader for insertion into composed prompts.

### 4. SQLAlchemy Timing
**Decision:** Move Task 4a (SQLAlchemy foundation) BEFORE Phase C, so prompt_loader.py uses SQLAlchemy from the start. Avoids rewriting prompt_loader later.

**Revised order:** Phase 0 → Phase A → Phase B → **Task 4a** → Phase C → Phase D → Phase E → Task 4b-4g → Phase G

### 5. AVAILABLE_DATABASES Cleanup
**Decision:** Update all code to use the postgres `iris_database_registry` table via `DatabaseMetadataRepository`. No compatibility exports - clean migration.

### 6. Class Renaming During Flattening
**Decision:** Yes, rename classes:
- `MetadataSubagent` → `MetadataAgent`
- `FileResearchSubagent` → `FileResearchAgent`

### 7. rbc_security Fallback Behavior
**Decision:** Warn and continue (don't fail fast). Add an environment variable to enable/disable:
- `IRIS_USE_RBC_SECURITY=true` (default for RBC environment)
- `IRIS_USE_RBC_SECURITY=false` (for local development)

When disabled, skip SSL setup entirely. When enabled but library unavailable, warn and continue.

### 8. Testing Files SQLAlchemy Migration
**Decision:** Skip. Testing populate scripts are standalone utilities and don't need SQLAlchemy migration.

### 9. Task 18 Clarification
**Decision:** Task 18 verifies that agents use postgres prompts (including global prompts) through prompt_loader, then deletes the now-unused `project_statement.py` and `restrictions_statement.py` files.

### 10. Table Ownership
**Decision:** Not an issue - same user owns tables in both local and work environments.

---

## Remaining Open Questions

1. Should `env_config.py` be renamed to something like `config.py` or `settings.py`? (Leaning toward: keep as-is)

2. For Task 4, use sync SQLAlchemy (simpler, current codebase is sync). Async migration can happen later if needed.
