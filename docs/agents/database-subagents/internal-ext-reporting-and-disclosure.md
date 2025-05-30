# Internal External Reporting and Disclosure Subagent (`iris/src/agents/database_subagents/internal_ext_reporting_and_disclosure/`)

Implementation of the internal database subagent for querying internal RBC External Reporting and Disclosure documents.

## Overview

The Internal External Reporting and Disclosure subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the External Reporting and Disclosure database containing financial reporting requirements, disclosure policies, and regulatory filing procedures.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_ext_reporting_and_disclosure"
* **Content Focus**: External reporting requirements and disclosure procedures

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal External Reporting and Disclosure subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
