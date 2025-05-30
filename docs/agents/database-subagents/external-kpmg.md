# External KPMG Subagent (`iris/src/agents/database_subagents/external_kpmg/`)

Implementation of the external database subagent for querying KPMG external IFRS guidance content.

## Overview

The External KPMG subagent is one of three functionally identical external database subagents (along with external_ey and external_pwc) that query and synthesize research from external accounting guidance databases. This implementation targets the KPMG Insights into IFRS 20th Edition.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "external_kpmg"
* **DOCUMENT_ID**: "kpmg_insights_into_ifrs_20th_edition"

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[External Database Subagents Standard Documentation](./external-subagents-standard.md)

---

**Note**: The external_ey, external_pwc, and external_kpmg subagents share identical implementation logic, differing only in their database names and document IDs.
