# Metadata Subagent Batching Architecture

## Overview

This document describes the architecture for handling databases with large numbers of documents (5 to 300+) in the metadata subagent. The design uses dynamic thresholds and batching to ensure consistent decision-making and efficient processing.

## Key Design Principles

1. **Single Decision Point**: Make metadata vs deep research decision ONCE upfront, not per-batch
2. **Dynamic Summary Selection**: Use full summaries for smaller DBs, condensed for larger
3. **Consistent Batching**: Process documents in fixed-size batches (50 docs)
4. **Reuse Existing Infrastructure**: Build on current embedding and LLM call patterns

---

## Configuration Constants

```python
# Thresholds
DECISION_PHASE_FULL_SUMMARY_THRESHOLD = 100  # Use full summaries if < 100 docs
BATCH_SIZE = 50  # Documents per batch

# Limits
MAX_DOCUMENTS_FOR_DECISION = 300  # Max docs in decision phase
MAX_DOCUMENTS_FOR_DEEP_RESEARCH = 20  # Max docs selected for file research
```

---

## Phase 1: Research Mode Decision

### Document Count Check

```python
def _get_decision_summary_type(doc_count: int) -> str:
    """Determine which summary type to use for decision phase."""
    if doc_count < DECISION_PHASE_FULL_SUMMARY_THRESHOLD:
        return "full"  # Use document_summary column
    else:
        return "condensed"  # Use condensed_summary column
```

### SQL Query for Decision Phase

```sql
-- Dynamic column selection based on threshold
SELECT
    document_id,
    db_source,
    document_name,
    document_type,
    CASE
        WHEN :use_full = TRUE THEN document_summary
        ELSE condensed_summary
    END AS summary_for_decision,
    1 - (summary_embedding <=> :embedding::vector) AS similarity_score
FROM iris_document_metadata
WHERE summary_embedding IS NOT NULL
    AND db_source = :db_source
ORDER BY similarity_score DESC
LIMIT :max_docs
```

### LLM Tool Call for Decision

```python
DECISION_TOOL = {
    "type": "function",
    "function": {
        "name": "decide_research_mode",
        "description": "Decide how to research this database based on document summaries",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["metadata_synthesis", "deep_research"],
                    "description": "metadata_synthesis: Can answer from summaries. deep_research: Need full document content."
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of why this mode was chosen"
                },
                "relevant_document_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "IDs of most relevant documents (for deep_research mode)"
                }
            },
            "required": ["mode", "reasoning"]
        }
    }
}
```

---

## Phase 2A: Metadata Synthesis Path

When `mode == "metadata_synthesis"`:

### Step 1: Batch Documents

```python
def _create_batches(documents: List[Dict], batch_size: int = 50) -> List[List[Dict]]:
    """Split documents into batches."""
    return [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
```

### Step 2: Process Each Batch

For each batch of 50 documents:
1. Fetch FULL summaries (document_summary column)
2. Fetch top K chunks per document (for additional context)
3. Call LLM to generate batch research response

```python
BATCH_SYNTHESIS_TOOL = {
    "type": "function",
    "function": {
        "name": "synthesize_batch_research",
        "description": "Generate research findings from this batch of documents",
        "parameters": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "string",
                    "description": "Research findings from these documents"
                },
                "key_documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "document_id": {"type": "integer"},
                            "relevance": {"type": "string", "enum": ["high", "medium", "low"]}
                        }
                    },
                    "description": "Documents that contributed to findings"
                }
            },
            "required": ["findings", "key_documents"]
        }
    }
}
```

### Step 3: Synthesize All Batches

After all batches processed, combine into final response:

```python
FINAL_SYNTHESIS_TOOL = {
    "type": "function",
    "function": {
        "name": "synthesize_final_response",
        "description": "Combine batch findings into final database research response",
        "parameters": {
            "type": "object",
            "properties": {
                "research_response": {
                    "type": "string",
                    "description": "Complete research response for this database"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence in the completeness of this response"
                },
                "key_document_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Most important documents for citations"
                }
            },
            "required": ["research_response", "confidence", "key_document_ids"]
        }
    }
}
```

---

## Phase 2B: Deep Research Path

When `mode == "deep_research"`:

### Step 1: Use Selected Documents

The decision phase already identified `relevant_document_ids`. Limit to MAX_DOCUMENTS_FOR_DEEP_RESEARCH (20).

### Step 2: Trigger File Research Subagent

Pass selected documents to file_research_subagent.py (existing Stage 2 of cascading retrieval).

---

## Database Schema Changes

### Add condensed_summary Column

```sql
ALTER TABLE iris_document_metadata
ADD COLUMN condensed_summary TEXT;

COMMENT ON COLUMN iris_document_metadata.condensed_summary IS
    'Short 1-2 sentence summary for decision phase when document count is high';
```

### Populate During Document Processing

When documents are processed:
1. Generate full `document_summary` (existing)
2. Generate `condensed_summary` (new - ~50 words max)

---

## New Prompts Required

### 1. Research Mode Decision Prompt

**prompt_type**: `subagent`
**prompt_name**: `metadata_research_decision`

```yaml
system_prompt: |
  You are a research assistant deciding how to investigate a database.

  Based on the document summaries provided, determine:
  1. Can the research question be answered from these summaries alone?
  2. Or do you need to read the full document content?

  Choose "metadata_synthesis" if summaries contain enough information.
  Choose "deep_research" if you need specific details from documents.

user_prompt: |
  Research Statement: {{research_statement}}

  Database: {{db_source}}
  Document Count: {{document_count}}

  {{document_summaries}}

  Based on these summaries, decide how to proceed with research.
```

### 2. Batch Synthesis Prompt

**prompt_type**: `subagent`
**prompt_name**: `metadata_batch_synthesis`

```yaml
system_prompt: |
  You are synthesizing research findings from a batch of documents.
  Extract relevant information that answers the research question.
  Note which documents provided the most relevant information.

user_prompt: |
  Research Statement: {{research_statement}}

  Batch {{batch_number}} of {{total_batches}}

  Documents in this batch:
  {{batch_documents}}

  Generate research findings from these documents.
```

### 3. Final Synthesis Prompt

**prompt_type**: `subagent`
**prompt_name**: `metadata_final_synthesis`

```yaml
system_prompt: |
  You are combining research findings from multiple batches into a final response.
  Create a comprehensive answer that synthesizes all batch findings.
  Identify the most important documents for citation.

user_prompt: |
  Research Statement: {{research_statement}}

  Database: {{db_source}}

  Batch Findings:
  {{batch_findings}}

  Synthesize these into a final research response.
```

---

## Implementation Order

### Step 1: Schema Update
1. Add `condensed_summary` column to `iris_document_metadata`
2. Update document processing to generate condensed summaries

### Step 2: New Prompts
1. Create `metadata_research_decision` prompt
2. Create `metadata_batch_synthesis` prompt
3. Create `metadata_final_synthesis` prompt
4. Add tool definitions to prompts table

### Step 3: Refactor metadata_subagent.py

```
Current Structure:
├── query_metadata_sync()
├── _fetch_documents_by_similarity()
├── _fetch_top_chunks()
├── _analyze_metadata_with_llm()
└── _build_result()

New Structure:
├── query_metadata_sync()           # Entry point (modified)
├── _get_document_count()           # NEW: Count docs for threshold
├── _fetch_decision_summaries()     # NEW: Get summaries for decision
├── _decide_research_mode()         # NEW: LLM decision call
├── _process_metadata_synthesis()   # NEW: Orchestrate batching
│   ├── _create_batches()           # NEW: Split docs
│   ├── _process_batch()            # NEW: Single batch LLM call
│   └── _synthesize_batches()       # NEW: Combine batch responses
├── _process_deep_research()        # NEW: Trigger file research
└── _build_result()                 # Modified for new response format
```

### Step 4: Update File Research Integration
1. Ensure file_research_subagent can receive pre-selected document IDs
2. Update database_router.py to handle new flow

### Step 5: Testing
1. Test with small DB (< 100 docs) - should use full summaries
2. Test with large DB (100-300 docs) - should use condensed summaries
3. Test batching with 150 docs (3 batches)
4. Test deep research path selection

---

## Flow Diagram

```
query_metadata_sync(research_statement, db_source, query_context)
    │
    ├── _get_document_count(db_source)
    │       │
    │       └── Returns: count (e.g., 150)
    │
    ├── _fetch_decision_summaries(db_source, embedding, count)
    │       │
    │       ├── If count < 100: SELECT document_summary
    │       └── If count >= 100: SELECT condensed_summary
    │       │
    │       └── Returns: List[{document_id, summary, similarity}]
    │
    ├── _decide_research_mode(research_statement, summaries)
    │       │
    │       ├── LLM call with decide_research_mode tool
    │       └── Returns: {mode, reasoning, relevant_document_ids?}
    │
    │   ┌────────────────────────────────────────────┐
    │   │ mode == "metadata_synthesis"                │
    │   │                                             │
    │   ├── _process_metadata_synthesis()             │
    │   │       │                                     │
    │   │       ├── _create_batches(docs, 50)        │
    │   │       │       └── [[doc1..50], [doc51..100], [doc101..150]]
    │   │       │                                     │
    │   │       ├── For each batch:                  │
    │   │       │   └── _process_batch()              │
    │   │       │       ├── Fetch FULL summaries     │
    │   │       │       ├── Fetch top chunks         │
    │   │       │       └── LLM synthesis            │
    │   │       │                                     │
    │   │       └── _synthesize_batches()            │
    │   │           └── Combine all batch findings   │
    │   │                                             │
    │   └── Returns: research_response               │
    │                                                │
    │   ┌────────────────────────────────────────────┐
    │   │ mode == "deep_research"                    │
    │   │                                             │
    │   ├── _process_deep_research()                 │
    │   │       │                                     │
    │   │       └── Returns document IDs for         │
    │   │           file_research_subagent           │
    │   │                                             │
    │   └── Returns: {needs_deep_research: True,     │
    │                 selected_documents: [...]}     │
    └────────────────────────────────────────────────┘
```

---

## Token Budget Estimates

### Decision Phase
- Condensed summary: ~50 words × 300 docs = 15,000 words ≈ 20K tokens
- Full summary: ~200 words × 100 docs = 20,000 words ≈ 27K tokens
- Well within context limits for decision

### Batch Processing (50 docs per batch)
- Full summary: ~200 words × 50 docs = 10,000 words ≈ 13K tokens
- Top chunks: ~500 words × 50 docs = 25,000 words ≈ 33K tokens
- Total per batch: ~46K tokens (manageable for large context models)

### Final Synthesis
- Batch findings: ~500 words × 6 batches (300 docs) = 3,000 words ≈ 4K tokens
- Very efficient final step

---

## Success Criteria

1. ✅ Single consistent decision (no per-batch mode switching)
2. ✅ Dynamic summary selection based on document count
3. ✅ Efficient batching for large databases
4. ✅ Preserves existing small-database performance
5. ✅ Maintains reference tracking for citations
6. ✅ Integrates with existing file research subagent
