# External PwC Subagent (`iris/src/agents/database_subagents/external_pwc/`)

Implementation of the external database subagent for querying PwC external IFRS guidance content.

## Overview

The External PwC subagent is one of three functionally identical external database subagents (along with external_ey and external_kpmg) that query and synthesize research from external accounting guidance databases. This implementation targets the PwC Canada IFRS Manual.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "external_pwc"
* **DOCUMENT_ID**: "pwc_ca_ifrs_manual"

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[External Database Subagents Standard Documentation](./external-subagents-standard.md)

---

**Note**: The external_ey, external_pwc, and external_kpmg subagents share identical implementation logic, differing only in their database names and document IDs.
