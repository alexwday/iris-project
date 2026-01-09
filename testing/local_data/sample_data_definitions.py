"""
Sample Data Definitions for Local IRIS Testing

This module defines the sample documents that will be generated for local testing.
Each document has enough structure to exercise the full IRIS pipeline.

The data is designed to be:
- Realistic enough to test all code paths
- Small enough to generate quickly and cheaply
- Diverse enough to test different database types
"""

# =============================================================================
# INTERNAL DATABASE SAMPLES (apg_catalog + apg_content)
# =============================================================================
# These simulate RBC's internal policy documents stored in catalog search databases

INTERNAL_DOCUMENTS = {
    "internal_capm": [
        {
            "document_name": "Revenue Recognition Policy",
            "document_type": "policy",
            "num_pages": 4,
            "theme": "IFRS 15 revenue recognition for software licenses and service contracts",
            "topics": [
                "Scope and applicability",
                "Five-step revenue recognition model",
                "Performance obligations identification",
                "Transaction price allocation"
            ]
        },
        {
            "document_name": "Lease Accounting Policy",
            "document_type": "policy",
            "num_pages": 5,
            "theme": "IFRS 16 lease classification, recognition, and measurement",
            "topics": [
                "Scope and definitions",
                "Lease identification criteria",
                "Lessee accounting model",
                "Lease modifications",
                "Disclosure requirements"
            ]
        },
        {
            "document_name": "Financial Instruments Policy",
            "document_type": "policy",
            "num_pages": 4,
            "theme": "IFRS 9 classification, measurement, and impairment",
            "topics": [
                "Classification of financial assets",
                "Expected credit loss model",
                "Hedge accounting requirements",
                "Fair value measurement"
            ]
        },
    ],
    "internal_par": [
        {
            "document_name": "PAR 2024-001 - Cloud Computing Arrangements",
            "document_type": "memo",
            "num_pages": 3,
            "theme": "Accounting for cloud computing service arrangements",
            "topics": [
                "Background and issue",
                "Analysis and conclusion",
                "Implementation guidance"
            ]
        },
        {
            "document_name": "PAR 2024-002 - Crypto Asset Classification",
            "document_type": "memo",
            "num_pages": 3,
            "theme": "Classification and measurement of cryptocurrency holdings",
            "topics": [
                "Issue identification",
                "Technical analysis",
                "Recommended treatment"
            ]
        },
    ],
}

# =============================================================================
# EXTERNAL DATABASE SAMPLES (iris_semantic_search)
# =============================================================================
# These simulate external guidance documents from EY, PwC, KPMG, IASB

EXTERNAL_DOCUMENTS = {
    "external_ey": [
        {
            "document_id": "EY_FRD_LEASES_2024",
            "source_filename": "EY Financial Reporting Developments - Leases (IFRS 16).pdf",
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_name": "Overview of IFRS 16",
                    "sections": [
                        {
                            "section_number": 1,
                            "section_name": "Introduction and Scope",
                            "page_range": (1, 8),
                            "num_chunks": 3,
                            "theme": "Scope of IFRS 16 and key definitions"
                        },
                        {
                            "section_number": 2,
                            "section_name": "Definition of a Lease",
                            "page_range": (9, 18),
                            "num_chunks": 4,
                            "theme": "Identifying whether a contract contains a lease"
                        },
                    ]
                },
                {
                    "chapter_number": 2,
                    "chapter_name": "Lessee Accounting",
                    "sections": [
                        {
                            "section_number": 1,
                            "section_name": "Initial Recognition and Measurement",
                            "page_range": (19, 30),
                            "num_chunks": 4,
                            "theme": "Right-of-use asset and lease liability recognition"
                        },
                        {
                            "section_number": 2,
                            "section_name": "Subsequent Measurement",
                            "page_range": (31, 42),
                            "num_chunks": 4,
                            "theme": "Depreciation, interest, and remeasurement"
                        },
                    ]
                },
                {
                    "chapter_number": 3,
                    "chapter_name": "Lease Modifications",
                    "sections": [
                        {
                            "section_number": 1,
                            "section_name": "Accounting for Modifications",
                            "page_range": (43, 52),
                            "num_chunks": 3,
                            "theme": "Remeasurement vs separate lease accounting"
                        },
                    ]
                },
            ]
        },
    ],
    "external_pwc": [
        {
            "document_id": "PWC_REVENUE_2024",
            "source_filename": "PwC Guide to Revenue Recognition (IFRS 15).pdf",
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_name": "The Five-Step Model",
                    "sections": [
                        {
                            "section_number": 1,
                            "section_name": "Step 1 - Identify the Contract",
                            "page_range": (1, 12),
                            "num_chunks": 4,
                            "theme": "Contract identification and combination"
                        },
                        {
                            "section_number": 2,
                            "section_name": "Step 2 - Identify Performance Obligations",
                            "page_range": (13, 24),
                            "num_chunks": 4,
                            "theme": "Distinct goods and services analysis"
                        },
                    ]
                },
                {
                    "chapter_number": 2,
                    "chapter_name": "Transaction Price",
                    "sections": [
                        {
                            "section_number": 1,
                            "section_name": "Variable Consideration",
                            "page_range": (25, 36),
                            "num_chunks": 4,
                            "theme": "Estimating variable consideration and constraints"
                        },
                    ]
                },
            ]
        },
    ],
}

# =============================================================================
# CONTENT GENERATION PROMPTS
# =============================================================================
# Templates for generating realistic content with GPT

CATALOG_DESCRIPTION_PROMPT = """Generate a professional 2-3 sentence description for this accounting document.

Document Name: {document_name}
Document Type: {document_type}
Theme: {theme}

The description should:
1. Explain what the document covers
2. Indicate when/why someone would reference it
3. Use professional accounting terminology

Return only the description text, no quotes or formatting."""

CATALOG_USAGE_PROMPT = """Generate a brief "when to use this document" statement for an AI system selecting documents.

Document Name: {document_name}
Theme: {theme}
Topics Covered: {topics}

The usage statement should help an AI decide if this document is relevant to a user query.
Be specific about the accounting topics and standards covered.

Return only the usage text, no quotes or formatting."""

SECTION_CONTENT_PROMPT = """Generate realistic accounting policy content for a section in a corporate accounting manual.

Document: {document_name}
Section: {section_name} (Page {page_number} of {total_pages})
Topic: {topic}
Theme: {theme}

Generate 2-3 paragraphs of professional accounting policy content that:
1. Uses appropriate accounting terminology
2. References relevant IFRS standards where applicable
3. Provides clear guidance that would be useful for accountants
4. Is realistic enough to test a research AI system

Return only the content text, no section headers or formatting."""

SECTION_SUMMARY_PROMPT = """Generate a one-sentence summary of this accounting policy section.

Section Name: {section_name}
Topic: {topic}
Document: {document_name}

Return only the summary sentence."""

CHUNK_CONTENT_PROMPT = """Generate a chunk of accounting guidance content (approximately 400-500 tokens).

Document: {source_filename}
Chapter: {chapter_name}
Section: {section_name}
Page Range: {page_start}-{page_end}
Theme: {theme}
Chunk: {chunk_number} of {total_chunks} in this section

Generate professional accounting guidance that:
1. Provides detailed technical analysis
2. Includes examples where appropriate
3. References specific IFRS paragraphs when relevant
4. Is coherent and could be part of a longer document

Return only the content text."""

CHAPTER_SUMMARY_PROMPT = """Generate a 2-3 sentence summary of this chapter from an accounting guidance document.

Document: {source_filename}
Chapter {chapter_number}: {chapter_name}
Sections covered: {section_names}

Return only the summary text."""
