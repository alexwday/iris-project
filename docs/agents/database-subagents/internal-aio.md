# Internal AIO Subagent (`iris/src/agents/database_subagents/internal_aio/`)

Implementation of the internal database subagent for querying RBC AIO (Auditor Independence Office) policy documents, procedures, and FAQs.

## Overview

The Internal AIO subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the AIO (Auditor Independence Office) database containing policy documents, procedures, and FAQs related to auditor independence requirements.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_aio"
* **Content Focus**: AIO policy documents, procedures, and FAQs

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal AIO subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
