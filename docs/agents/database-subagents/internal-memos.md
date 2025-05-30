# Internal Memos Subagent (`iris/src/agents/database_subagents/internal_memos/`)

Implementation of the internal database subagent for querying internal RBC Memos documents.

## Overview

The Internal Memos subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the Memos database containing internal communications, policy memos, and procedural announcements.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_memos"
* **Content Focus**: Internal memos and policy communications

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal Memos subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
