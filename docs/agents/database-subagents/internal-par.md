# Internal PAR Subagent (`iris/src/agents/database_subagents/internal_par/`)

Implementation of the internal database subagent for querying internal RBC PAR (Policies, Audit, and Risk) documents.

## Overview

The Internal PAR subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the PAR database containing policies, audit procedures, and risk management documentation.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_par"
* **Content Focus**: PAR policies, audit procedures, and risk management

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal PAR subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
