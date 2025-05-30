# Internal Compliance Subagent (`iris/src/agents/database_subagents/internal_compliance/`)

Implementation of the internal database subagent for querying internal RBC Compliance documents.

## Overview

The Internal Compliance subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the Compliance database containing regulatory requirements, policies, and compliance procedures.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_compliance"
* **Content Focus**: RBC Compliance documents and regulatory procedures

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal Compliance subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
