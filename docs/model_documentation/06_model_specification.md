# 6. Model Specification

This section describes the IRIS model methodologies and processing components, focusing on the agent-based architecture, query processing mechanisms, and mathematical foundations of information retrieval and synthesis.

## 6.1 Agent Architecture

The IRIS system implements a modular, pipeline-based architecture consisting of specialized AI agents that process user queries through a structured workflow. The overall architecture contains two primary processing paths managed by a central model orchestration engine.

### 6.1.1 Processing Pathways

IRIS features two main processing pathways. The **Direct Response Path** is employed for queries that can be answered using only conversation history. Its processing sequence is `agent_router` → `agent_direct_response`, and it is optimized for contextual queries that do not require additional research. The **Research Path** is utilized for queries requiring database research. Its processing sequence is `agent_router` → `agent_clarifier` → `agent_planner` → `database_subagents` → `agent_summarizer`, implementing a comprehensive retrieval-augmented generation approach.

### 6.1.2 Agent Components and Functions

| Agent | Function | Mathematical/Algorithm Basis |
|-------|----------|------------------------------|
| Router Agent | Determines processing path based on query analysis | Classification algorithm using transformer-based embeddings with context-aware decision boundary |
| Clarifier Agent | Assesses query context sufficiency and creates research statements | Information-theoretic query expansion with controlled relevance parameters |
| Planner Agent | Selects optimal databases for query execution | Multi-class relevance scoring with database-specific prior weightings |
| Database Subagents | Retrieve and pre-process information from various data sources | Implemented through five distinct processing methodologies (detailed in Section 6.2) |
| Summarizer Agent | Integrates findings and generates coherent responses | Multi-document extraction-abstraction mechanism with attention-based relevance weighting |
| Direct Response Agent | Generates responses using only conversation history | Constrained inference with context-window utilization optimization |

### 6.1.3 System Integration

The central chat model orchestration component (`model.py`) serves as the integration hub. It manages system initialization and configuration, query routing based on router agent decisions, and both sequential and parallel agent execution flow. Additionally, it handles result aggregation and presentation, as well as process monitoring and error handling.

## 6.2 Database Retrieval Methodologies

The IRIS system implements five distinct database retrieval methodologies, each optimized for different types of source documents.

### 6.2.1 Catalog Search - Small

The **Mathematical Specification** for Catalog Search - Small involves a two-stage selection with catalog prioritization. The document assessment function is $R_{LLM}(d, q) \rightarrow \{d_1, d_2, ..., d_n\}$, representing LLM-selected documents. Document selection is modeled as $D_{selected} = LLM_{select}(catalog, q)$, where the LLM selects documents based on title and description. Response synthesis is defined as $R_{synthesis} = LLM_{synthesize}(\{content(d) | d \in D_{selected}\}, q)$.

**Implementation** begins with **Catalog Retrieval**, querying PostgreSQL for document metadata using SQL like:
```sql
SELECT id, document_name, document_description
FROM apg_catalog
WHERE document_source = 'internal_par'
ORDER BY document_name;
```
Next is **Document Selection**, an LLM-based selection process (GPT-4o-mini with temperature 0.2) where the catalog is formatted with document IDs, names, and descriptions, passed to the LLM with a selection prompt, and a JSON list of document IDs is parsed (with fallback regex extraction if JSON parsing fails). **Content Retrieval** then fetches complete document content for selected IDs using SQL:
```sql
SELECT section_id, section_name, section_content
FROM apg_content
WHERE document_source = 'internal_par'
AND document_name = %s
ORDER BY section_id;
```
Finally, **Response Synthesis** generates a research report using a tool call (GPT-4o with temperature 0.2). Documents are formatted with a hierarchical structure (`# Document Name` → `## Section Name` → Content), and the tool call returns both `status_summary` and `detailed_research`, with citations including document name and section name.

This methodology is **applied** to standard documents (PDF, DOCX) with simple structures, such as those in the `internal_par` and `internal_process_and_controls` example databases.

### 6.2.2 Catalog Search - Large

The **Mathematical Specification** for Catalog Search - Large employs a three-stage hierarchical selection using LLM judgment. Document selection is $D_{selected} = LLM_{select}(catalog, q)$, where the LLM selects relevant documents. Section selection for each $d \in D_{selected}$ is $S_{selected,d} = LLM_{select}(sections(d), q)$. Final synthesis is $R_{synthesis} = LLM_{synthesize}(\{content(s) | s \in \bigcup_{d \in D_{selected}} S_{selected,d}\}, q)$.

**Implementation** starts with **Catalog Retrieval** using the same SQL query pattern as Catalog Search - Small, but for CAPM sources. **Document Selection** is also LLM-based (GPT-4o-mini with temperature 0.2), following the same process as Catalog Search - Small to return a list of document IDs. An additional intermediate step is **Section Summary Retrieval**:
```sql
SELECT section_id, section_name, section_summary
FROM apg_content
WHERE document_source = 'internal_capm'
AND document_name = %s
ORDER BY section_id;
```
**Section Selection** is then performed by an LLM (GPT-4o-mini) to choose specific sections by formatting document sections and their summaries; the LLM selects specific section IDs for each document based on relevance to the query, returning a dictionary mapping document names to lists of section IDs. **Content Retrieval** fetches only these selected sections:
```sql
SELECT section_id, section_name, section_content
FROM apg_content
WHERE document_source = 'internal_capm'
AND document_name = %s
AND section_id IN (%s, %s, ...)
ORDER BY section_id;
```
**Response Synthesis** uses the same tool-calling approach as Catalog Search - Small.

This method is **applied** to large documents with distinct sections/chapters, for example, databases like `internal_capm` and `internal_global_finance_standards`.

### 6.2.3 Catalog Search - Excel

The **Mathematical Specification** for Catalog Search - Excel involves table preprocessing with row-level document conversion. Each row or grouping $r$ is transformed into a document $d_r$ by the function $T_{excel}(r) = d_r$. Document selection occurs through LLM assessment: $D_{selected} = LLM_{select}(catalog, q)$, where each catalog entry represents a processed row or table.

**Implementation** involves **Pre-Processing** where Excel files are processed during database creation: Excel content is extracted and converted to Markdown format, with each table or logical row grouping becoming a separate document, and tables preserved with Markdown formatting. After pre-processing, the **Database Query** implementation is the same as Catalog Search - Small, involving document selection via LLM from the catalog and content retrieval for selected documents, followed by response synthesis using a GPT-4o tool call.

This methodology is **applied** to Excel spreadsheets and tabular data, such as in the `internal_wiki` and `internal_management_reporting` example databases.

### 6.2.4 Catalog Search - Vision

The **Mathematical Specification** for Catalog Search - Vision uses image-to-text conversion via a multi-pass vision transformer. Image content extraction is $T_{vision}(i) = d_i$, where $i$ is an image and $d_i$ is the extracted text document. Document selection is through LLM assessment: $D_{selected} = LLM_{select}(catalog, q)$.

**Implementation** includes **Pre-Processing** where infographics are processed during database creation. Images are processed via the Qwen2 vision model in multi-pass mode, with multiple extraction passes for text, tables, charts, and diagrams. Content is converted to structured Markdown format, and each infographic becomes a document in the database. After pre-processing, the **Database Query** implementation is identical to Catalog Search - Small: document selection via LLM from the catalog (GPT-4o-mini), content retrieval for selected documents, and response synthesis using a GPT-4o tool call (temperature 0.2).

This approach is **applied** to infographics and image-based documents, with `internal_cheatsheets` being an example database.

### 6.2.5 Semantic Search - Large

The **Mathematical Specification** for Semantic Search - Large involves vector-based similarity search with token-aware chunking. Chunk embedding is $E(c) = \vec{v_c}$, where $c$ is a chunk and $\vec{v_c}$ is its embedding vector. Query embedding is $E(q) = \vec{v_q}$. Initial similarity scoring is $sim(c, q) = 1 - (c.embedding <=> q.embedding)$ using the PostgreSQL vector operator. Initial chunk selection is $C_{initial}(q) = top\_k(C, sim, k)$, where $k = 20$ (INITIAL_K constant). Relevance filtering is $C_{filtered} = \{c \in C_{initial} | LLM_{relevance}(c.summary, q) = 1\}$. Importance reranking uses the score $score(c) = sim(c, q) \cdot (1 + IMPORTANCE\_FACTOR \cdot c.importance\_score)$, where $IMPORTANCE\_FACTOR = 0.2$. Section expansion occurs for sections with tokens $\leq THRESHOLD$ (with different thresholds based on rank). Gap filling addresses sequence gaps where $0 < gap \leq MAX\_SEQUENCE\_GAP$ (where $MAX\_SEQUENCE\_GAP = 8$).

**Implementation** starts with **Query embedding generation** using text-embedding-3-large (2000 dimensions) to create a dense vector representation of the query. This is followed by an **Initial vector similarity search** to retrieve the top-20 (INITIAL_K) most similar chunks by cosine similarity using the PostgreSQL vector extension with the query:
```sql
SELECT c.*, 1 - (c.embedding <=> %s::vector) AS vector_score
FROM iris_textbook_database c
WHERE c.document_id = %s
ORDER BY vector_score DESC
LIMIT %s;
```
Next, **Summary relevance filtering** involves LLM-based classification (GPT-4o-mini, temperature 0.2) of chunk summaries as relevant (1) or irrelevant (0), removing irrelevant chunks while keeping the original rank order. **Importance-based reranking** applies the formula $score = vector\_score \cdot (1 + 0.2 \cdot section\_importance\_score)$, sorts results by this new score, and assigns a new rank. **Section expansion by token count** expands sections if their token count is ≤ 8000 tokens for the top 5 ranked chunks, or ≤ 4000 tokens for other chunks, fetching all chunks from the same section and grouping them. **Sequence gap filling** identifies and fills sequence gaps between consecutive chunks ≤ 8 sequence numbers by retrieving intermediate chunks and assigning importance scores based on averaging adjacent chunks. Finally, **Card formatting and response synthesis** formats all chunks into "cards" with metadata and content, and generates a comprehensive research report using GPT-4o (temperature 0.7), ensuring inline citations from the source material.

This method is **applied** to very large documents and external sources, such as the `external_ey`, `external_iasb`, `external_kpmg`, and `external_pwc` example databases.

## 6.3 Model Decision Processes

### 6.3.1 Router Decision

The **Mathematical Specification** for the Router Decision is a binary classification: $f_{route}(q, c) \in \{direct, research\}$, where $q$ is the query and $c$ is the conversation context.
**Implementation** takes the user query and conversation history as input. The process involves LLM-based analysis using GPT-4o-mini with structured tool output, at a temperature of 0.1 (low randomness for consistency). The output is the function name to invoke (`response_from_conversation` or `research_from_database`).

### 6.3.2 Clarifier Decision

The **Mathematical Specification** for the Clarifier Decision involves a context sufficiency assessment: $sufficiency(q, c) \in [0, 1]$, and research formulation: $r = formulate(q, c)$ if $sufficiency(q, c) > \theta_{context}$.
**Implementation** uses the user query, conversation history, and router decision as input. The process is an LLM-based analysis using GPT-4o with structured output. The output can be context questions (if context is insufficient), a research statement (if context is sufficient), and the research scope (`metadata` or `research`).

### 6.3.3 Database Selection

The **Mathematical Specification** for Database Selection uses multi-class relevance scoring: $relevance(db, r) \in [0, 1]$ for each database $db$. Selection is $DB_{selected} = \{db \in DB | relevance(db, r) > \theta_{relevance}\}$.
**Implementation** takes the research statement from the clarifier as input. The process is an LLM-based analysis using GPT-4o-mini with structured output, at a temperature of 0.2 (low randomness with slight variability). The output is a list of selected databases to query.

### 6.3.4 Response Synthesis

The **Mathematical Specification** for Response Synthesis is a multi-document extraction-abstraction: $synthesis(retrieved\_content, r)$, where $retrieved\_content$ represents the aggregated results from database queries.
**Implementation** uses the detailed research from multiple database subagents as input. The process is an LLM-based synthesis using GPT-4o, with a temperature of 0.4 (balanced between creativity and consistency). The output is a coherent, cited research summary.

## 6.4 Model Parameters and Retrieval Specifications

The IRIS system utilizes specific model configurations and retrieval parameters tailored to optimize performance across different agent functions.

### 6.4.1 Language Model Parameters

For **GPT-4o-mini**, parameters include its use for the Router Agent, Planner Agent, Direct Response Agent, and Document/Section Selection tasks. The temperature is set between 0.1-0.2 for low randomness to ensure consistent decision-making. Its primary application is for classification, decision-making, and selection tasks.

For **GPT-4o**, parameters dictate its use for the Clarifier Agent, Summarizer Agent, and Database Subagent content synthesis. The temperature is task-dependent, ranging from 0.3-0.7, with higher values for creative synthesis. Its primary application is for complex reasoning and content generation tasks.

For **Text-Embedding-3-Large**, parameters specify its use for vector embeddings in the semantic search methodology. It employs 2,000 dimensions for high-dimensional, accurate similarity matching. Its primary application is vector database search and similarity matching.

### 6.4.2 Retrieval Parameters

| Retrieval Method | Parameter | Implementation Approach |
|------------------|-----------|-------------------------|
| **Catalog Search - Small** | Document Selection | LLM-based relevance assessment of document summaries using GPT-4o-mini |
| | Selection Guidance | Prompted with specific criteria for relevance, prioritizing documents directly addressing the query |
| | Max Documents | Explicitly limited to 5 documents maximum per prompt instruction |
| **Catalog Search - Large** | Document Selection | LLM-based two-stage selection process (documents, then sections) |
| | Selection Guidance | Prompted to select based on document descriptions with specific evaluation criteria |
| | Max Documents | Explicitly limited to 5 documents maximum per prompt instruction |
| **Catalog Search - Excel** | Row/Table Selection | LLM-based relevance assessment of tabular data summaries |
| | Selection Guidance | Prompted with dual criteria: 5 document max for specific queries, up to 15 for general listing queries |
| | Format Preservation | Preserves table structure in Markdown format for synthesis |
| **Catalog Search - Vision** | Image Selection | LLM-based selection of infographics based on extracted text summaries |
| | Selection Guidance | Prompted with specific relevance criteria prioritizing documents addressing the query directly |
| | Max Documents | Explicitly limited to 5 documents maximum per prompt instruction |
| | Visual Content Handling | Multi-pass vision processing with selective extraction of text, tables and figures |
| **Semantic Search - Large** | Initial Vector Search | Document-specific vector searches with exact per-source thresholds:<br>• IASB: IAS (20), IFRS (20), IFRICS (10), SIC (10)<br>• EY: Single search (20)<br>• KPMG: Single search (20)<br>• PwC: Single search (20) |
| | Reranking Method | Multi-factor reranking combining vector similarity with content importance (importance_factor=0.2) |
| | Final Selection | Per-document selection and processing before final aggregation:<br>• Relevance filtering of summaries<br>• Section expansion (top 5 ranks ≤ 8000 tokens, others ≤ 4000 tokens)<br>• Sequence gap filling (gaps ≤ 8) |
| | Token Budget | Dynamic adjustment based on content relevance (typically 4,000-8,000 tokens) |

The catalog search methods (small, large, excel, vision) rely on LLM-driven selection from document/section summaries without explicit numerical thresholds, instead using comparative relevance assessment through prompt engineering. The semantic search method combines explicit vector similarity search with additional reranking and selection parameters optimized through empirical testing.

## 6.5 Numerical Methods and Approximations

### 6.5.1 Tokenization

IRIS uses the `tiktoken` (cl100k_base) tokenizer. Token thresholds are managed for context window optimization through dynamic truncation. Chat history maintains the last 10 messages within the token limit, and document chunking aims for 250-750 tokens per chunk, depending on semantic boundaries.

### 6.5.2 Token-Aware Chunking Algorithm

Section-aware chunking implements a numerical approximation for optimal information density through a hierarchical sectional chunking process.
The **Mathematical Formulation** considers a document $D$ with sections $S = \{s_1, s_2, ..., s_n\}$. For each section $s_i$, its token count is $T(s_i)$. Threshold parameters are $T_{min} = 250$ and $T_{max} = 750$. The chunking process involves merging sections $s_i$ with $s_{i+1}$ if $T(s_i) < T_{min}$ and $T(s_i) + T(s_{i+1}) \leq T_{max}$. If $T(s_i) > T_{max}$, it's split into subsections $\{s_{i,1}, ..., s_{i,k}\}$ such that $T_{min} \leq T(s_{i,j}) \leq T_{max}$. If $T_{min} \leq T(s_i) \leq T_{max}$, it's maintained as a standalone chunk.

The **Implementation Process** involves the system traversing the document structure hierarchically, calculating precise token counts with `tiktoken` for each section. Section boundaries are preserved where possible for semantic coherence. When sections exceed the maximum token threshold, splitting occurs at paragraph boundaries. Sections below the minimum threshold are merged with adjacent sections, with merged sections continuously evaluated against the maximum threshold. The final chunking preserves the document's logical flow while maintaining optimal chunk sizes.

This approach balances information density with semantic coherence, ensuring that related content remains together while maintaining manageable chunk sizes for embedding and retrieval.

### 6.5.3 Embedding Batch Processing

To optimize embedding generation, the system implements vector batch processing through a parallelized computation architecture.
The **Mathematical Formulation** takes a set of chunks $C = \{c_1, ..., c_m\}$ and a batch size $B = 50$. $C$ is partitioned into batch sets $B_i = \{c_{i \cdot B + 1}, ..., c_{min((i+1) \cdot B, m)}\}$. The embedding function $E$ is applied to each batch: $E(B_i) = \{E(c) | c \in B_i\}$. The complete embedding set is $E(C) = \bigcup E(B_i)$.

The **Implementation Process** divides the total chunk collection into batches of 50. Each batch is submitted to the embedding API as a single request. The text-embedding-3-large model processes each chunk in the batch. Returned embeddings are stored with their corresponding chunk IDs. The system monitors embedding generation for quality and consistency, and embeddings are stored in the PostgreSQL database using the pgvector extension.

This batched approach significantly improves throughput by reducing API overhead while maintaining embedding quality and consistency.

### 6.5.4 Similarity Scoring

Vector similarity is calculated using cosine similarity:

$$sim(v_1, v_2) = \frac{v_1 \cdot v_2}{||v_1|| \cdot ||v_2||}$$

Where $v_1$ and $v_2$ are embedding vectors for chunks or queries.

## 6.6 Process Monitoring and Metrics

The system implements comprehensive process monitoring to track performance.

### 6.6.1 Metrics Collection

Metrics collected include stage-based timing metrics for each component in the processing pipeline, token usage statistics for cost analysis, API response times, and completion rates and error conditions.

### 6.6.2 Metric Storage

All metrics are stored in the PostgreSQL database in the `process_monitor_logs` table. This allows for historical analysis, performance optimization, cost attribution, and system reliability monitoring.

### 6.6.3 Performance Optimization Feedback Loop

The process monitoring system enables continuous system refinement. This is achieved through the identification of bottlenecks in the processing pipeline, analysis of token usage patterns to optimize costs, correlation of success/failure rates with specific query types, and fine-tuning of model parameters based on performance metrics.
