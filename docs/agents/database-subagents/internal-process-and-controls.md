# Internal Process and Controls Subagent (`iris/src/agents/database_subagents/internal_process_and_controls/`)

Implementation of the internal database subagent for querying internal RBC Process and Controls documents.

## Overview

The Internal Process and Controls subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the Process and Controls database containing business process documentation, control procedures, and operational guidelines.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_process_and_controls"
* **Content Focus**: Process documentation and control procedures

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal Process and Controls subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
