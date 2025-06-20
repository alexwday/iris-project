# Internal Cheatsheets Subagent (`iris/src/agents/database_subagents/internal_cheatsheets/`)

Implementation of the internal database subagent for querying internal RBC Finance Cheatsheets documents.

## Overview

The Internal Cheatsheets subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the RBC Finance Cheatsheets database containing quick reference guides and procedural summaries.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_cheatsheets"
* **Content Focus**: RBC Finance Cheatsheets and quick reference guides

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal Cheatsheets subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
