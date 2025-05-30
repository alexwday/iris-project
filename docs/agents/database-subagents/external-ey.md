# External EY Subagent (`iris/src/agents/database_subagents/external_ey/`)

Implementation of the external database subagent for querying EY external IFRS guidance content.

## Overview

The External EY subagent is one of three functionally identical external database subagents (along with external_pwc and external_kpmg) that query and synthesize research from external accounting guidance databases. This implementation targets the EY International GAAP 2024 document.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "external_ey"
* **DOCUMENT_ID**: "ey_international_gaap_2024"

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[External Database Subagents Standard Documentation](./external-subagents-standard.md)

---

**Note**: The external_ey, external_pwc, and external_kpmg subagents share identical implementation logic, differing only in their database names and document IDs.
