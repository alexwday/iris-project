# Internal ESG Subagent (`iris/src/agents/database_subagents/internal_esg/`)

Implementation of the internal database subagent for querying internal RBC ESG (Environmental, Social, and Governance) documents.

## Overview

The Internal ESG subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the ESG database containing environmental, social, and governance policies, procedures, and reporting requirements.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_esg"
* **Content Focus**: RBC ESG documents and sustainability reporting procedures

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal ESG subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
