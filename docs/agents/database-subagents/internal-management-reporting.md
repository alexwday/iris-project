# Internal Management Reporting Subagent (`iris/src/agents/database_subagents/internal_management_reporting/`)

Implementation of the internal database subagent for querying internal RBC Management Reporting documents.

## Overview

The Internal Management Reporting subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the Management Reporting database containing internal reporting procedures, management information systems, and dashboard requirements.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_management_reporting"
* **Content Focus**: Management reporting procedures and internal reporting systems

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal Management Reporting subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
