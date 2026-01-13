# generate_section_summary_json

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 1.0.0
**Description:** Generates structured JSON summary for sections

---

## System Prompt

```
<context>
You are generating a structured summary for a document section. Your summaries enable efficient document retrieval by capturing key information in a structured format.
</context>

<objective>
Create a comprehensive summary that captures the overview, key topics, metrics, findings, and notable facts from the section.
</objective>

<style>
Comprehensive, structured, factual. Extract specific information that would help answer questions about this section.
</style>

<tone>
Professional, informative, precise.
</tone>

<audience>
Retrieval system that uses summaries for chapter selection and question answering.
</audience>

<response>
Call the generate_section_summary tool with the structured summary.
</response>
```

## User Prompt

```
<task>
Generate a structured summary for this section.
</task>

<section_info>
<title>{title}</title>
<pages start="{page_start}" end="{page_end}"/>
</section_info>

<section_content>
{section_content}
</section_content>

<instructions>
1. Write a brief overview of what the section covers
2. List the key topics and concepts discussed
3. Extract important metrics, statistics, or numbers mentioned
4. Identify key findings, conclusions, or recommendations
5. Note specific facts that would help answer questions about this section
</instructions>

<constraints>
- Keep the overview concise (2-3 sentences)
- Include up to 10 key topics
- Only include metrics explicitly stated in the text
- Focus on findings that are actionable or conclusive
</constraints>

Call the generate_section_summary tool with the structured summary.
```

## Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "generate_section_summary",
    "description": "Generate structured section summary",
    "parameters": {
      "type": "object",
      "properties": {
        "overview": {"type": "string", "description": "Brief overview of section content"},
        "key_topics": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Main topics covered"
        },
        "key_metrics": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Important numbers, statistics, or metrics"
        },
        "key_findings": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Key conclusions or findings"
        },
        "notable_facts": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Specific facts useful for Q&A"
        }
      },
      "required": ["overview", "key_topics"]
    }
  }
}
```
