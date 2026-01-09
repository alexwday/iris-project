#!/usr/bin/env python3
"""
Populate doc_refresh prompts into PostgreSQL prompts table.

All prompts use COSTAR format with XML tags:
- Context: Background information
- Objective: Task to accomplish
- Style: Writing style/approach
- Tone: Tone of communication
- Audience: Target audience
- Response: Output format

Usage:
    python populate_doc_refresh_prompts.py
"""

import os
import psycopg2
from psycopg2.extras import execute_values

# Database connection
DB_HOST = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
DB_PORT = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
DB_NAME = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
DB_USER = os.getenv("VECTOR_POSTGRES_DB_USERNAME", "alexwday")
DB_PASS = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")

# =============================================================================
# PROMPTS IN COSTAR FORMAT WITH XML TAGS
# =============================================================================

PROMPTS = [
    # -------------------------------------------------------------------------
    # CLASSIFY DOCUMENT
    # -------------------------------------------------------------------------
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "classify_document",
        "version": "1.0.0",
        "description": "Classify document structure type (chapters, sections, topic_based, semantic)",
        "system_prompt": """<context>
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
Respond with valid JSON only. No additional text.
</response>""",
        "user_prompt": """<task>
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
{{
    "structure_type": "chapters|sections|topic_based|semantic",
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation of classification",
    "has_toc": true/false,
    "toc_sections": ["List of section titles from ToC if found, otherwise empty"]
}}
</output_format>""",
    },
    # -------------------------------------------------------------------------
    # DETECT SECTIONS BATCH
    # -------------------------------------------------------------------------
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "detect_sections_batch",
        "version": "1.0.0",
        "description": "Detect level-1 section breaks in a batch of pages",
        "system_prompt": """<context>
You are a document structure analysis expert. You identify major section boundaries in documents. You are processing a batch of pages from a larger document and must find where new sections begin.
</context>

<objective>
Find ALL level-1 (major) section or chapter breaks within this batch of pages.
</objective>

<style>
Thorough, systematic, precise. Scan every page for section headers. Report exact page numbers and titles.
</style>

<tone>
Professional, methodical, detail-oriented.
</tone>

<audience>
Document processing pipeline building a section index.
</audience>

<response>
Respond with valid JSON only. No additional text.
</response>""",
        "user_prompt": """<task>
Find ALL major section/chapter breaks in this batch of pages.
</task>

<document_info>
<structure_type>{structure_type}</structure_type>
<previous_context>{previous_context}</previous_context>
<page_range start="{start_page}" end="{end_page}"/>
</document_info>

<pages>
{pages_content}
</pages>

<structure_guidance type="{structure_type}">
{structure_guidance}
</structure_guidance>

<instructions>
1. Scan through EVERY page in this batch
2. Find ALL level-1 (major) section/chapter headers
3. Report exact page numbers where sections start
4. Include exact title as written in document
5. Only include LEVEL 1 sections (NOT subsections like "1.1", "2.1")
6. For numbered sections, only include top-level: "1 Introduction", "2 Methods" etc.
</instructions>

<output_format>
{{
    "continued_section_title": "Title of section continued from previous batch (or null)",
    "section_breaks": [
        {{
            "page_number": <page number within {start_page}-{end_page}>,
            "title": "Exact section title as it appears"
        }}
    ]
}}
</output_format>""",
    },
    # -------------------------------------------------------------------------
    # CONSOLIDATE STRUCTURE
    # -------------------------------------------------------------------------
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "consolidate_structure",
        "version": "1.0.0",
        "description": "Consolidate and validate detected sections, enforce 100-page max",
        "system_prompt": """<context>
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
Respond with valid JSON only. No additional text.
</response>""",
        "user_prompt": """<task>
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
{{
    "sections": [
        {{
            "page_number": <page number>,
            "title": "Corrected/finalized title"
        }}
    ],
    "corrections_made": [
        "List of corrections or splits made"
    ]
}}
</output_format>""",
    },
    # -------------------------------------------------------------------------
    # SUMMARIZE SECTION
    # -------------------------------------------------------------------------
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "summarize_section",
        "version": "1.0.0",
        "description": "Generate comprehensive summary for a document section",
        "system_prompt": """<context>
You are a document summarization expert. You create comprehensive summaries that capture the key topics, concepts, and conclusions of document sections. Your summaries are used for chapter selection during retrieval.
</context>

<objective>
Create a detailed 2-4 paragraph summary that enables understanding the section without reading it.
</objective>

<style>
Comprehensive, informative, structured. Cover main topics, key points, important data, and relationships to the broader document.
</style>

<tone>
Professional, academic, thorough.
</tone>

<audience>
Retrieval system that will use summaries to select relevant sections for user queries.
</audience>

<response>
Respond with valid JSON only. No additional text.
</response>""",
        "user_prompt": """<task>
Summarize this section of the document.
</task>

<section_info>
<title>{section_title}</title>
<path>{section_path}</path>
<pages start="{page_start}" end="{page_end}"/>
</section_info>

<section_content>
{section_content}
</section_content>

<instructions>
1. Identify the main topics and concepts covered
2. Extract key points and conclusions
3. Note important data, figures, or findings
4. Explain how this section relates to the broader document
5. Make the summary detailed enough to understand the section without reading it
6. Include terminology and concepts that users might search for
</instructions>

<output_format>
{{
    "summary": "2-4 paragraph comprehensive summary of the section"
}}
</output_format>""",
    },
    # -------------------------------------------------------------------------
    # ANALYZE SUBSECTIONS
    # -------------------------------------------------------------------------
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "analyze_subsections",
        "version": "1.0.0",
        "description": "Break a section into logical subsections with page ranges and summaries",
        "system_prompt": """<context>
You are a document structure analysis expert. You break larger sections into logical subsections to enable more granular retrieval. You identify natural break points within content.
</context>

<objective>
Identify subsections within this section, with page ranges and brief summaries.
</objective>

<style>
Analytical, granular, organized. Find natural divisions based on headers, topic shifts, or numbered parts.
</style>

<tone>
Professional, systematic, precise.
</tone>

<audience>
Document processing pipeline that needs granular section structure for retrieval.
</audience>

<response>
Respond with valid JSON only. No additional text.
</response>""",
        "user_prompt": """<task>
Analyze this section and break it into logical subsections.
</task>

<section_info>
<title>{section_title}</title>
<path>{section_path}</path>
<pages start="{page_start}" end="{page_end}"/>
</section_info>

<section_content>
{section_content}
</section_content>

<instructions>
1. Identify natural break points within the content
   - Headers or subheaders
   - Topic shifts
   - Numbered parts or steps
2. Create clear, descriptive subsection titles
3. Determine page ranges for each subsection
4. Provide a brief 1-2 sentence summary for each subsection
</instructions>

<constraints>
- Each subsection must be at least 1 page
- For short sections (1-3 pages), 1 subsection covering all content is fine
- For longer sections, aim for 3-10 subsections based on natural divisions
- Page ranges must be within {page_start}-{page_end}
- Page ranges must not overlap
</constraints>

<output_format>
{{
    "subsections": [
        {{
            "title": "Descriptive subsection title",
            "page_start": <start page>,
            "page_end": <end page>,
            "summary": "Brief 1-2 sentence summary of this subsection's content"
        }}
    ]
}}
</output_format>""",
    },
    # -------------------------------------------------------------------------
    # LINK SUBSECTIONS
    # -------------------------------------------------------------------------
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "link_subsections",
        "version": "1.0.0",
        "description": "Identify relationships between subsections for co-retrieval",
        "system_prompt": """<context>
You are a document relationship analysis expert. You identify meaningful relationships between sections that should be retrieved together. You understand prerequisite knowledge, complementary topics, and cross-references.
</context>

<objective>
Identify which subsections are related and should be retrieved together during search.
</objective>

<style>
Analytical, relationship-focused, selective. Only identify genuinely meaningful relationships.
</style>

<tone>
Professional, thoughtful, discriminating.
</tone>

<audience>
Retrieval system that will fetch related sections together.
</audience>

<response>
Respond with valid JSON only. No additional text.
</response>""",
        "user_prompt": """<task>
Identify relationships between subsections in this document.
</task>

<all_subsections>
{all_subsections}
</all_subsections>

<relationship_types>
<type>Subsections that define terms/concepts used in another</type>
<type>Subsections that provide prerequisite knowledge</type>
<type>Subsections covering complementary aspects of the same topic</type>
<type>Subsections that reference each other</type>
</relationship_types>

<instructions>
1. For EACH subsection, identify up to 3 other subsections that are highly related
2. Consider semantic relationships, not just sequential proximity
3. Only include genuinely related subsections
4. Provide brief reasoning for each relationship
5. It's okay for a subsection to have 0 related subsections
</instructions>

<constraints>
- Maximum 3 related subsections per subsection
- Do not include sequential relationships unless semantically meaningful
- Relationships should be meaningful for retrieval
</constraints>

<output_format>
{{
    "relationships": [
        {{
            "subsection_id": "<id of the subsection>",
            "related_subsection_ids": ["<id1>", "<id2>", "<id3>"],
            "reasoning": "Brief explanation of why these are related"
        }}
    ]
}}
</output_format>""",
    },
]

# =============================================================================
# STRUCTURE GUIDANCE (separate entries for each type)
# =============================================================================

STRUCTURE_GUIDANCE_PROMPTS = [
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "structure_guidance_chapters",
        "version": "1.0.0",
        "description": "Guidance for detecting sections in chapter-structured documents",
        "system_prompt": None,
        "user_prompt": """For CHAPTERS structure:
- Look for explicit chapter headers (Chapter X, Part X, numbered divisions)
- Only capture chapter-level headers (NOT sections within chapters)
- Examples: "Chapter 1: Introduction", "Part II: Analysis", "Module 3"
- May have chapter numbers, roman numerals, or named parts""",
    },
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "structure_guidance_sections",
        "version": "1.0.0",
        "description": "Guidance for detecting sections in section-structured documents",
        "system_prompt": None,
        "user_prompt": """For SECTIONS structure (academic papers, reports):
- Find ONLY top-level numbered sections: "1 Introduction", "2 Methods", "3 Results"
- Do NOT include subsections like "1.1", "2.1", "2.2" - those will be detected later
- Also find standalone headers: "Abstract", "References", "Appendix", "Acknowledgments"
- Example level 1 sections: Abstract, 1 Introduction, 2 Background, 3 Methods, 4 Experiments, 5 Results, 6 Conclusion, References""",
    },
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "structure_guidance_topic_based",
        "version": "1.0.0",
        "description": "Guidance for detecting sections in topic-based documents",
        "system_prompt": None,
        "user_prompt": """For TOPIC_BASED structure:
- Look for clear major topic transitions in the content
- Create meaningful titles that describe each major topic
- Aim for sections of roughly 20-50 pages each (but max 100 pages)
- If content naturally divides into fewer sections, that's fine
- Use semantic cues like introductions of new subjects or concepts""",
    },
    {
        "model": "doc_refresh",
        "layer": "stage_3",
        "name": "structure_guidance_semantic",
        "version": "1.0.0",
        "description": "Guidance for detecting sections in semantic-flow documents",
        "system_prompt": None,
        "user_prompt": """For SEMANTIC structure:
- Look for major semantic shifts in the content
- Aim for sections of roughly 30-50 pages each (but max 100 pages)
- Create descriptive titles based on content themes
- If no clear breaks exist, create logical divisions at natural pause points
- Consider argument progression, narrative shifts, or thematic changes""",
    },
]


def main():
    """Insert doc_refresh prompts into database."""
    print("Connecting to database...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )
    cursor = conn.cursor()

    # Delete existing doc_refresh prompts
    print("Removing existing doc_refresh prompts...")
    cursor.execute("DELETE FROM prompts WHERE model = 'doc_refresh'")
    deleted = cursor.rowcount
    print(f"  Deleted {deleted} existing prompts")

    # Insert new prompts
    print("Inserting new prompts...")
    all_prompts = PROMPTS + STRUCTURE_GUIDANCE_PROMPTS

    for prompt in all_prompts:
        cursor.execute(
            """
            INSERT INTO prompts (model, layer, name, version, description, system_prompt, user_prompt)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                prompt["model"],
                prompt["layer"],
                prompt["name"],
                prompt["version"],
                prompt["description"],
                prompt["system_prompt"],
                prompt["user_prompt"],
            ),
        )
        print(f"  Inserted: {prompt['layer']}/{prompt['name']}")

    conn.commit()
    print(f"\nInserted {len(all_prompts)} prompts successfully!")

    # Verify
    cursor.execute("SELECT layer, name, version FROM prompts WHERE model = 'doc_refresh' ORDER BY layer, name")
    rows = cursor.fetchall()
    print("\nVerification - doc_refresh prompts in database:")
    for row in rows:
        print(f"  {row[0]}/{row[1]} (v{row[2]})")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
