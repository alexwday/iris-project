# 5. Model Development Data

## 5.1 Data Validity and Sources

The IRIS system retrieves information from a collection of internal and external accounting and finance knowledge sources stored in a PostgreSQL database. This section describes the data used by the system, its sources, and processing methods.

### Data Coverage and Scope

IRIS accesses data covering several key domains. These include **Internal RBC Policies**, such as Corporate Accounting Policy Manuals (CAPMs), process documentation, and control frameworks. The scope also extends to **Accounting Guidelines**, encompassing CFO and APG-developed guides, cheatsheets, and wiki entries. Furthermore, **Internal Documentation** like accounting memos, project approval requests, and finance-related guidance is covered. The system also processes information related to **Financial Reporting**, including management reporting policies and external reporting requirements. Finally, it incorporates **Accounting Standards**, such as IFRS standards and interpretations from select accounting firms (EY, KPMG, PwC). This domain-focused coverage enables IRIS to address finance and accounting inquiries relevant to the CFO Group.

### Data Storage and Management

The system stores processed documents in a PostgreSQL database with a structured schema designed to support both catalog-based and semantic search approaches. The database consists of several primary tables.

First, the **apg_catalog** table serves as a Document Metadata Repository.
```sql
CREATE TABLE apg_catalog (
    -- System Fields
    id SERIAL PRIMARY KEY,                        -- Auto-incrementing unique identifier
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- When the record was added to the database
    
    -- Document Identification Fields
    document_source VARCHAR(100) NOT NULL,        -- Source of the document (e.g., 'internal_capm', 'external_iasb')
    document_type VARCHAR(100) NOT NULL,          -- Type of document (e.g., 'capm', 'infographic', 'memo')
    document_name VARCHAR(255) NOT NULL,          -- Formatted document name (e.g., 'IFRS 9 - Financial Instruments')
    
    -- Scope Fields
    document_description TEXT,                    -- Original AI-generated description of document usage/scope
    document_usage TEXT,                          -- Field for LLM selection/usage guidance
    
    -- Refresh Metadata Fields
    date_created TIMESTAMP WITH TIME ZONE,        -- Original document creation date
    date_last_modified TIMESTAMP WITH TIME ZONE,  -- Date the document was last modified
    file_name VARCHAR(255),                       -- Full filename with extension (e.g., 'IFRS9_Financial_Instruments.pdf')
    file_type VARCHAR(50),                        -- File extension/type (e.g., '.pdf', '.docx', '.xlsx')
    file_size BIGINT,                             -- Size of the file in bytes
    file_path VARCHAR(1000),                      -- Full system path to the original file
    file_link VARCHAR(1000)                       -- URL or NAS path to the file
)
```

Second, the **apg_content** table is used for Document Content Storage.
```sql
CREATE TABLE apg_content (
    -- System Fields
    id SERIAL PRIMARY KEY,                        -- Auto-incrementing unique identifier
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- When the record was added to the database
    
    -- Document Reference Fields (matching catalog)
    document_source VARCHAR(100) NOT NULL,        -- Source of the document (matches apg_catalog)
    document_type VARCHAR(100) NOT NULL,          -- Type of document (matches apg_catalog)
    document_name VARCHAR(255) NOT NULL,          -- Document name (matches apg_catalog)
    
    -- Content Fields
    section_id INTEGER NOT NULL,                  -- Ordered sequence number within the document
    section_name VARCHAR(500),                    -- Title of the section/chapter
    section_summary TEXT,                         -- AI-generated summary of the section
    section_content TEXT NOT NULL                 -- The actual content of the section
)
```

Third, the **iris_textbook_database** table functions as a Vector Embeddings Store.
```sql
CREATE TABLE iris_textbook_database (
  -- SYSTEM FIELDS
  id SERIAL PRIMARY KEY,  -- Unique identifier for each chunk
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- Record creation timestamp

  -- STRUCTURAL POSITIONING FIELDS
  document_id TEXT,                 -- E.g., "IFRS_Handbook_2023" or "EY_GAAP_Guide_2024"
  chapter_number INT,              -- E.g., 4
  section_number INT,              -- E.g., 2
  part_number INT,                 -- E.g., 1
  sequence_number INT,             -- E.g., 14 (position in chunk order)

  -- CHAPTER-LEVEL METADATA
  chapter_name TEXT,               -- E.g., "Leases" or "Revenue Recognition"
  chapter_tags TEXT[],             -- E.g., {"Financial_Instruments", "Disclosure_Requirements"}
  chapter_summary TEXT,            -- E.g., "This chapter explains revenue recognition..."
  chapter_token_count INT,         -- Total token count across the full chapter

  -- SECTION-LEVEL PAGINATION & IMPORTANCE
  section_start_page INT,          -- E.g., 142 (start page of section)
  section_end_page INT,            -- E.g., 143 (end page of section)
  section_importance_score FLOAT,  -- E.g., 0.85 (importance of this section)
  section_token_count INT,         -- Total token count for this section

  -- SECTION-LEVEL METADATA
  section_hierarchy TEXT,          -- E.g., "Chapter 4 > Section 4.2 > Subsection 4.2.3"
  section_title TEXT,              -- E.g., "Identification of Separate Performance Obligations"
  section_standard TEXT,           -- E.g., "IFRS", "US_GAAP", "AASB"
  section_standard_codes TEXT[],   -- E.g., {"IFRS 16", "IAS 17", "IFRS 9"}
  section_references TEXT[],       -- E.g., {"Section 3.4", "IAS 36 Para 12-15"}

  -- CONTENT & EMBEDDING
  content TEXT NOT NULL,           -- The actual textbook content in this chunk
  embedding VECTOR(2000),          -- OpenAI's text-embedding-3-large model vector
  text_search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
)
```

Finally, the **process_monitor_logs** table is a Performance Monitoring and Logging System.
```sql
CREATE TABLE process_monitor_logs (
    -- Core Fields
    log_id BIGSERIAL PRIMARY KEY,                -- Auto-incrementing unique ID for each log entry
    run_uuid UUID NOT NULL,                      -- Unique ID generated for each model invocation
    model_name VARCHAR(100) NOT NULL,            -- Identifier for the model
    stage_name VARCHAR(100) NOT NULL,            -- Name of the specific process stage
    stage_start_time TIMESTAMPTZ NOT NULL,       -- Timestamp when the stage began
    stage_end_time TIMESTAMPTZ,                  -- Timestamp when the stage ended
    duration_ms INT,                             -- Duration of the stage in milliseconds
    llm_calls JSONB,                             -- JSON array storing details for LLM calls
    total_tokens INT,                            -- Sum of total tokens from all llm_calls
    total_cost DECIMAL(12, 6),                   -- Sum of costs from all llm_calls
    status VARCHAR(255),                         -- Outcome/Status of the stage
    decision_details TEXT,                       -- Specific outputs or decisions
    error_message TEXT,                          -- Detailed error message if the stage failed
    log_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP -- Timestamp when log row was created
)
```
This `process_monitor_logs` table serves as an output destination where the model automatically logs performance metrics after each component execution, rather than an input source for the model.

### Data Processing Framework

The document processing framework transforms source documents into formats optimized for the different retrieval methods. This involves several steps: **Source Identification**, where documents are identified and retrieved from designated Network Attached Storage (NAS) locations; **Format Conversion**, where documents from various formats (PDF, Word, Excel, images) are converted to standardized markdown text; **Structure Preservation**, ensuring document hierarchies, sections, and relationships are maintained during processing; **Metadata Generation**, where document and section summaries are created to support retrieval decisions; and **Storage Optimization**, where content is stored in appropriate database tables based on document type.

#### Metadata Generation Process

Each pipeline type employs a specialized metadata generation approach. For **Catalog Search - Small**, GPT-4o is used to generate document usage summaries and descriptions, creating concise overviews of document purpose and applicability. This focuses on document-level metadata to support catalog selection and produces standardized metadata fields for consistent retrieval. The **Catalog Search - Large** pipeline includes all metadata generation from Catalog Search Small and additionally generates summaries for each defined section and chapter. This creates hierarchical metadata reflecting document structure and enables more granular selection by allowing LLMs to refine searches to specific sections. Both **Catalog Search - Excel & Vision** pipelines follow the same metadata generation approach as Catalog Search Small. For Excel, tabular structure is preserved with appropriate metadata, and for Vision, the Qwen2 model is used to extract and describe visual content before metadata generation. The **Semantic Search - Large** pipeline employs an extensive recursive metadata generation process. It first generates comprehensive metadata at the chapter level, including chapter summaries, applicable accounting standards, and key concepts and terminology. This chapter-level context is then used to recursively generate metadata for individual sections, such as section summaries, contextual tags, importance scores, and hierarchical positioning. This rich metadata supports vector search, reranking, and context expansion operations.

For documents requiring semantic search capabilities, additional processing generates vector embeddings using the text-embedding-3-large model (3072 dimensions) to support similarity-based retrieval.

## 5.2 Document Processing Pipelines

IRIS uses five specialized document processing pipelines, each optimized for specific document types and formats. These pipelines transform source documents into formats suitable for efficient retrieval.

### Document Processing Approaches

The **Catalog Search - Small** pipeline is designed for standard documents (e.g., Project Approval Requests). It converts documents to markdown format, keeps documents whole without chunking, and generates document-level summaries for catalog selection. This approach is suitable for documents under 10,000 tokens.

The **Catalog Search - Large** pipeline is intended for large documents with distinct sections (e.g., Corporate Accounting Policy Manuals). It converts documents to markdown format, splits documents into logical sections based on headings, and creates both document-level and section-level summaries. This enables a two-stage retrieval process involving document selection followed by section selection.

For Excel spreadsheets (e.g., Wiki entries), the **Catalog Search - Excel** pipeline converts spreadsheet content to markdown while preserving table structures. It processes each relevant row or group of rows as a separate entry and standardizes formatting for numerical data and table layouts.

The **Catalog Search - Vision** pipeline handles infographics and visual content (e.g., cheatsheets). It uses the Qwen2 vision model to process image content into structured markdown, extracting text, visual elements, and structural information. These results are combined into a single structured document with proper formatting.

Lastly, the **Semantic Search - Large** pipeline is for very large reference materials (e.g., IFRS Standards). It extracts text while preserving document structure and identifies chapters and sections with hierarchical relationships. The pipeline creates optimally sized chunks for semantic search and generates comprehensive metadata at the chapter level, including summaries, key concepts, applicable accounting standards, and usage guidance. This chapter-level metadata is then used as context to recursively generate section-level metadata such as summaries, contextual tags, importance scores, and hierarchical positioning information. Vector embeddings are generated using the text-embedding-3-large model configured for 2000 dimensions, and both content and metadata are stored to support reranking and context expansion.

### Document Transformation Process

The document processing workflow includes several key transformation steps. **Format Standardization** involves converting diverse document formats into consistent markdown text, preserving essential formatting elements like headings, tables, and lists, and ensuring consistent rendering across different document types. **Structure Preservation** focuses on maintaining document hierarchies and section relationships, preserving heading levels to reflect document organization, and retaining connections between related document sections. **Metadata Enrichment** includes extracting and storing document and section metadata, generating AI-powered summaries using GPT-4o for retrieval optimization, preserving source information and hierarchical relationships, creating recursive metadata structures for semantic search documents, and building cross-referencing systems between related content sections. Finally, **Retrieval Optimization** tailors the process for different search types. For catalog-based retrieval, it generates high-quality document descriptions and usage summaries, creates section-level summaries for large documents to enable refined selection, and structures metadata fields to support LLM-based document selection. For semantic search, it creates vector embeddings of document chunks using text-embedding-3-large, generates positional and hierarchical metadata for reranking and context expansion, implements importance scoring to prioritize more relevant sections, preserves parent-child relationships between document sections, and pre-calculates token counts to optimize context usage.

## 5.3 System Inputs and Database Structure

IRIS operates primarily on conversation history and content retrieved from its database structure. This section details the database design and inputs used by the system.

### Database Structure

The PostgreSQL database consists of three primary tables that store the knowledge IRIS uses.

The **apg_catalog** table stores metadata about available knowledge sources. Its purpose is to hold information about document origin, purpose, and searchable descriptions. Key fields include `document_source`, `document_name`, `document_type`, and `document_description`.

The **apg_content** table stores the actual document content and section summaries. It is used primarily for catalog-based search methods. Key fields are `document_source`, `document_name`, `section_id`, `section_name`, `section_summary`, and `section_content`.

The **iris_textbook_database** table stores vector representations for semantic search. It contains rich metadata at chapter and section levels to support recursive context expansion, including structural positioning data (chapter, section, part numbers), and information about applicable standards and references. Key fields include `embedding` (vector), `content`, `section_hierarchy`, and `section_importance_score`. This table utilizes PostgreSQL vector extensions for similarity searching.

### Input Processing Flow

The IRIS agent architecture processes inputs through a sequential pipeline. The **Initial Input** to the system is the complete conversation history, including the current user query and all previous exchanges. During **Router Processing**, the Agent Router analyzes the conversation to determine whether to use only conversation context (Direct Response path) or to retrieve information from databases (Research path). For the **Research Processing** path, the system evaluates context sufficiency using the Agent Clarifier, determines relevant knowledge sources via the Agent Planner, retrieves information using appropriate search methods through Database Subagents, and finally synthesizes findings into coherent responses with the Agent Summarizer. Throughout this flow, **Specialized Prompting** is employed, where each agent uses carefully designed system prompts customized for its specific function, guiding the LLM's behavior and output format.

### Model-Specific Inputs

The IRIS system primarily processes three types of inputs. First is the **Conversation History**, which includes complete user-system interaction records, the current query, all previous exchanges, session context, and follow-up information. Second are the **PostgreSQL Database Tables**, providing structured document content from `apg_content`, document metadata from `apg_catalog`, and vector embeddings with rich metadata from `iris_textbook_database`. Third, **Specialized Prompts** are used, which are system prompts customized for each agent, containing specific function-oriented instructions and response format guidelines.

Each component in the IRIS pipeline processes these inputs in specialized ways. The Agent Router processes conversation history to determine the processing path. The Agent Clarifier analyzes conversation context to ensure sufficient information. The Agent Planner evaluates research needs to select appropriate knowledge sources. Database Subagents query PostgreSQL tables using specialized retrieval methods. The Agent Summarizer integrates database findings into coherent responses.

For semantic search capabilities, the embedding generation process uses the text-embedding-3-large model configured to generate 2000-dimensional vectors (rather than its maximum 3072 dimensions) to fit PostgreSQL database limits, creating efficient vector representations of document chunks for similarity-based retrieval.

## 5.4 Data Assumptions and Limitations

The IRIS system operates under several data-related assumptions and limitations that affect its performance and usage scope.

### Key Data Assumptions

| Assumption | Description | Impact |
|------------|-------------|--------|
| Document Authority | Internal RBC policies are considered more authoritative than external sources | Ensures organizational standards are prioritized |
| Content Correctness | Documents in designated storage locations are assumed to be correct and authoritative | Enables efficient processing without additional validation steps |
| Source Completeness | The knowledge base is assumed to contain all relevant policy documentation | Critical for providing comprehensive responses |
| Document Structure | Higher-level document sections are assumed to contain more important policy statements | Influences retrieval and ranking algorithms |
| Query Context | User intent is assumed to remain consistent within a conversation | Enables effective follow-up handling |

### Data Limitations

| Limitation | Description | Impact on Usage |
|------------|-------------|----------------|
| Content Currency | Lag between document updates and database refresh | Responses may not reflect very recent policy changes |
| Visual Content Processing | Limited ability to fully capture complex tables, charts, and financial diagrams | Some visual information may be simplified or summarized |
| Information Boundaries | System can only access information in its knowledge base | Cannot leverage information beyond processed documents |
| Calculation Handling | Unable to execute or validate accounting calculations in source materials | Cannot verify calculation results or run new scenarios |
| Language Support | Optimized for English content with limited multilingual capabilities | May not fully process non-English segments in documents |

### Future Improvements

The IRIS system is designed for continuous improvement. Planned enhancements include regular **Documentation Updates**, such as refresh cycles to incorporate policy changes and expansion of the knowledge base to cover additional finance domains. Additionally, **Processing Enhancements** are planned, focusing on improvements to visual content processing for complex financial diagrams and better preservation of document relationships and cross-references.

The system's modular design allows for component-level improvements without requiring complete system redesign.
