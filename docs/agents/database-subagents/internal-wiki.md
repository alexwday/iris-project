# Internal Wiki Subagent (`iris/src/agents/database_subagents/internal_wiki/`)

Implementation of the internal database subagent for querying internal RBC Wiki documents.

## Overview

The Internal Wiki subagent is one of the standard internal database subagents that query and synthesize research from internal RBC content. This implementation targets the Wiki database containing knowledge base articles, FAQs, troubleshooting guides, and procedural documentation.

## Key Differences

This subagent uses the following specific configurations:
* **DATABASE_NAME**: "internal_wiki"
* **Content Focus**: Wiki articles and knowledge base documentation

## Documentation

For complete documentation of functionality, components, and usage, please refer to:
[Internal Database Subagents Standard Documentation](./internal-subagents-standard.md)

---

**Note**: The internal Wiki subagent shares identical implementation logic with other standard internal subagents, differing only in database name and content focus.
