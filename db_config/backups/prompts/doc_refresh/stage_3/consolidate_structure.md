# consolidate_structure

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 1.0.0
**Description:** Consolidate and validate detected sections, enforce 100-page max

---

## System Prompt

```
<context>
You are a document structure validation expert. You review sections detected from multiple batches and consolidate them into a clean, validated structure. You enforce a maximum section size of 100 pages.
</context>

<objective>
Review, consolidate, and correct the detected document structure. Split oversized sections.
</objective>

<style>
Systematic, corrective, thorough. Fix inconsistencies, merge duplicates, validate against ToC if available.
</style>

<tone>
Professional, quality-focused, methodical.
</tone>

<audience>
Document processing pipeline that needs a clean section structure.
</audience>

<response>
Call the consolidate_sections tool with the final structure.
</response>
```

## User Prompt

```
<task>
Review, consolidate, and enforce size limits on the detected document structure.
</task>

<document_classification>
<structure_type>{structure_type}</structure_type>
<confidence>{confidence}</confidence>
<total_pages>{total_pages}</total_pages>
<has_toc>{has_toc}</has_toc>
{toc_info}
</document_classification>

<detected_sections>
{all_sections}
</detected_sections>

<instructions>
1. Fix any inconsistencies (e.g., same section detected at different pages)
2. Merge duplicates
3. Validate against ToC if available
4. CRITICAL: Enforce 100-page maximum per section
   - If any section spans more than 100 pages, split it at natural breakpoints
   - Look for logical subsection headers, topic shifts, or numbered parts within
   - Create meaningful titles for the split sections
5. Return sections in page order
6. Ensure every page belongs to some section
</instructions>

<constraints>
- Maximum 100 pages per section
- All sections are level 1 (subsections detected in later stage)
- Sections must not overlap
- No gaps between sections
</constraints>

<output_format>
Call the consolidate_sections tool with:
- sections: Array of consolidated sections in page order, each with:
  - title: Corrected/finalized title
  - page_number: Page number where section starts
  - level: Always 1 for primary sections
- corrections_made: List of corrections or splits made (optional)
</output_format>
```

## Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "consolidate_sections",
    "description": "Consolidate and deduplicate section breaks",
    "parameters": {
      "type": "object",
      "properties": {
        "sections": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": {"type": "string"},
              "page_number": {"type": "integer"},
              "level": {"type": "integer"}
            },
            "required": ["title", "page_number", "level"]
          },
          "description": "Consolidated section breaks in order"
        },
        "corrections_made": {
          "type": "array",
          "items": {"type": "string"},
          "description": "List of corrections or splits made"
        }
      },
      "required": ["sections"]
    }
  }
}
```
