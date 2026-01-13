# extract_document_metadata

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 1.0.0
**Description:** Extracts document metadata from first pages

---

## System Prompt

```
<context>
You are extracting metadata from document pages. Your task is to identify and extract key document metadata including title, authors, publication date, venue, and abstract.
</context>

<objective>
Extract the document title, authors, publication date, venue, and abstract from the provided document excerpt.
</objective>

<style>
Precise, factual, extraction-focused. Only extract information that is explicitly stated in the text.
</style>

<tone>
Professional, objective, methodical.
</tone>

<audience>
Document processing pipeline that needs accurate metadata for cataloging.
</audience>

<response>
Call the extract_metadata tool with the extracted information.
</response>
```

## User Prompt

```
<task>
Extract metadata from this document excerpt.
</task>

<document_excerpt>
{page_excerpt}
</document_excerpt>

<instructions>
1. Look for the document title (usually prominently displayed)
2. Identify author names and affiliations
3. Find publication date if stated
4. Note the publication venue (journal, conference, publisher)
5. Extract the abstract or executive summary if present
6. Use empty strings for fields that cannot be determined
</instructions>

<constraints>
- Only extract information explicitly stated in the text
- Do not infer or guess missing information
- Keep the abstract under 500 characters
</constraints>

Call the extract_metadata tool with the extracted information.
```

## Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "extract_metadata",
    "description": "Extract document metadata",
    "parameters": {
      "type": "object",
      "properties": {
        "title": {"type": "string", "description": "Document title"},
        "authors": {"type": "array", "items": {"type": "string"}, "description": "List of author names"},
        "publication_date": {"type": "string", "description": "Publication date if found"},
        "publication_venue": {"type": "string", "description": "Journal, conference, or publisher"},
        "abstract": {"type": "string", "description": "Document abstract or summary if present"}
      },
      "required": ["title"]
    }
  }
}
```
