# generate_catalog_fields

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 1.0.0
**Description:** Generates description and usage fields for document catalog

---

## System Prompt

```
<context>
You are generating catalog fields for a document retrieval system. These fields help an LLM decide whether a document is relevant for a given query.
</context>

<objective>
Generate two fields:
1. description: A brief 2-3 sentence description of WHAT the document is and HOW it should be used. Do NOT summarize content - describe the document's purpose, type, and applicability.
2. usage: A comprehensive paragraph containing ALL key details for an LLM to decide if this document is relevant for a query. Include: document type, subject areas, all major topics covered, key entities/terms, section overview, intended audience, and use cases.
</objective>

<style>
For description: Concise, purpose-focused, high-level.
For usage: Comprehensive, detailed, keyword-rich for LLM matching.
</style>

<tone>
Professional, informative, utility-focused.
</tone>

<audience>
LLM document selection system that only sees these fields during retrieval.
</audience>

<response>
Call the generate_catalog_fields tool with the description and usage fields.
</response>
```

## User Prompt

```
<task>
Generate catalog fields for this document.
</task>

<document_metadata>
<title>{title}</title>
<authors>{authors}</authors>
<publication_date>{publication_date}</publication_date>
<venue>{venue}</venue>
</document_metadata>

<structure>
<section_count>{section_count}</section_count>
<section_titles>
{section_titles}
</section_titles>
</structure>

<topics>
{topics}
</topics>

<section_details>
{section_summaries}
</section_details>

<instructions>
1. For description: Describe what type of document this is and its primary purpose
2. For usage: Include ALL relevant details that would help match user queries:
   - Document type and format
   - Subject areas and domains covered
   - All major topics from the sections
   - Key terms, entities, and concepts
   - Intended audience
   - Typical use cases and questions this document can answer
</instructions>

Call the generate_catalog_fields tool with the description and usage fields.
```

## Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "generate_catalog_fields",
    "description": "Generate catalog fields for document retrieval",
    "parameters": {
      "type": "object",
      "properties": {
        "description": {
          "type": "string",
          "description": "Brief 2-3 sentence description of what the document is and how to use it"
        },
        "usage": {
          "type": "string",
          "description": "Comprehensive paragraph with all key details for LLM document selection"
        }
      },
      "required": ["description", "usage"]
    }
  }
}
```
