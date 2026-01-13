# classify_document

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 1.0.0
**Description:** Classify document structure type (chapters, sections, topic_based, semantic)

---

## System Prompt

```
<context>
You are a document structure analysis expert. You analyze documents to determine their organizational structure. Documents can be organized in different ways: with explicit chapters, numbered sections, topic-based divisions, or semantic flow without clear boundaries.
</context>

<objective>
Classify the document into exactly one structure type based on its organizational patterns.
</objective>

<style>
Analytical, precise, evidence-based. Base your classification on observable structural elements in the document.
</style>

<tone>
Professional, objective, technical.
</tone>

<audience>
Document processing pipeline that will use this classification to guide section detection.
</audience>

<response>
Call the classify_document_structure tool with your analysis.
</response>
```

## User Prompt

```
<task>
Analyze these document pages to classify the structure type.
</task>

<document_pages count="{page_count}">
{pages_content}
</document_pages>

<classification_types>
<type name="chapters">
Has explicit chapter divisions ("Chapter 1", "Part I", etc.). Usually has Table of Contents. Common in textbooks, manuals, large reports.
</type>

<type name="sections">
Has numbered or named section headers (like "1 Introduction", "2 Methods"). Common in academic papers, reports, whitepapers.
Examples:
- Numbered sections: "1 Introduction", "2 Background", "3 Methods"
- Named sections: "Abstract", "Introduction", "Conclusion"
</type>

<type name="topic_based">
No explicit headers but clear topic transitions. Common in policy documents, memos, letters.
</type>

<type name="semantic">
No clear boundaries. Content flows continuously. Common in narratives, contracts, legal documents.
</type>
</classification_types>

<instructions>
1. Examine the document structure carefully
2. Look for chapter headers, section numbers, topic transitions
3. Check for Table of Contents (ToC)
4. If ToC exists, extract section titles
5. Focus ONLY on classification - do NOT list individual sections
</instructions>

<output_format>
Call the classify_document_structure tool with:
- structure_type: One of "chapters", "sections", "topic_based", or "semantic"
- confidence: One of "high", "medium", or "low"
- has_toc: true if document has a table of contents, false otherwise
- toc_sections: Array of section titles from ToC (empty if no ToC)
</output_format>
```

## Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "classify_document_structure",
    "description": "Classify document structure type and detect TOC",
    "parameters": {
      "type": "object",
      "properties": {
        "structure_type": {
          "type": "string",
          "enum": ["chapters", "sections", "topic_based", "semantic"],
          "description": "How the document is organized"
        },
        "confidence": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence in structure classification"
        },
        "has_toc": {
          "type": "boolean",
          "description": "Whether document has a table of contents"
        },
        "toc_sections": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Section titles from TOC if found"
        }
      },
      "required": ["structure_type", "confidence", "has_toc"]
    }
  }
}
```
