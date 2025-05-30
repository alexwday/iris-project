# Internal ICFR Subagent (`iris/src/agents/database_subagents/internal_icfr/`)

Implementation of the internal database subagent for querying internal RBC ICFR (Internal Control over Financial Reporting) documents.

## Overview

The Internal ICFR subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the ICFR database containing internal control procedures, SOX compliance requirements, and financial reporting controls.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_icfr"
* **Content Focus**: ICFR procedures and SOX compliance controls

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal ICFR subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
