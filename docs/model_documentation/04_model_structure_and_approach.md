# 4. Model Structure and Approach

**Model Name:** IRIS (Intelligent Research and Information System)
**Model ID:** IRIS-001

## 4.1 Approach Selection

IRIS leverages large language models for both generative capabilities and embedding functions within a Retrieval-Augmented Generation (RAG) framework. Our approach to model selection was primarily driven by the models available within RBC's infrastructure. Key considerations included the limitation to models available through RBC's Lumina portal (such as GPT-3.5, GPT-4, GPT-4-turbo, GPT-4o-mini, and GPT-4o), the availability of on-premises options like Llama, Qwen, and Cohere for specific use cases, and the decision not to train our own models, focusing instead on the optimal use of commercial options. Performance on public benchmarks and leaderboards (e.g., MMLU, TruthfulQA), context window length requirements for handling large documents, and processing speed and cost efficiency were also important factors.

Validation was conducted through internal testing, which involved providing initial samples to the APG team for feedback and conducting internal reviews to confirm model sufficiency. This process also included an assessment of response quality and accuracy for finance-specific queries, alongside an evaluation of citation quality and source attribution.

Based on these constraints and evaluations, we selected GPT-4o-mini for quick decision-making and contexts where all necessary information is provided, GPT-4o for more important decisions and final response generation, and text-embedding-3-large for our embedding model. For visual content processing, such as infographics and images, we employ an on-premises hosted version of Qwen2 7B VL. For external data that cannot be redistributed, we use an on-premises version of Cohere command-north-large.

IRIS implements a modular, agent-based architecture with a hybrid RAG approach. The system processes user queries through a sequential pipeline with two primary processing paths. The **Direct Response Path** is utilized for queries that can be answered using only conversation history, following a streamlined process from the Agent Router directly to the Agent Direct Response. For more complex queries requiring database research, the **Research Path** is activated, engaging a full processing pipeline: Agent Router → Agent Clarifier → Agent Planner → Database Subagents → Agent Summarizer.

Our agent-based approach was designed to be both conversational, using conversation history for context, and autonomous, searching specific databases as needed instead of all content at once. The architecture enables strategic querying of selected databases rather than querying all databases for every question, significantly improving efficiency and relevance.

After experimenting with multiple Retrieval-Augmented Generation (RAG) methods, we developed a hybrid approach. This involves five distinct document processing pipelines for input. The **Catalog Search - Small** pipeline is the standard for processing normal documents like PDFs and DOCX files, converting content to markdown and generating metadata. The **Catalog Search - Vision** pipeline is specialized for processing infographics and visual documents, using the Qwen2 vision model to extract text, diagrams, and visual elements into markdown. A **Catalog Search - Excel** pipeline provides a custom method for converting Excel spreadsheets with structured data into markdown documents while preserving table formatting. For large documents with distinct sections, the **Catalog Search - Large** pipeline creates both document-level and section-level summaries. Lastly, the **Semantic Search - Large** pipeline is designed for very large reference documents and includes chunking, embedding generation, and metadata enrichment.

Complementing these input pipelines are three specific retrieval methods. **Catalog Search - Small** is used for documents processed through the Small, Vision, or Excel pipelines (typically under 10,000 tokens); in this method, entire documents are sent within the context window rather than being chunked, and the model selects relevant documents from a catalog based on descriptions and metadata. For larger documents with distinct sections, **Catalog Search - Large** implements a two-stage retrieval process where the model first selects relevant documents from a catalog and then identifies specific sections within those documents. For very large reference documents like accounting standards, **Semantic Search - Large** implements vector embedding similarity search with sophisticated reranking and section expansion, performing similarity matching with query embeddings, reranking results based on relevance criteria, and expanding selected sections to maintain context.

We select the optimal input pipeline and retrieval method for each database based on document type and structure. This multi-tiered approach allows us to handle various document types optimally rather than applying a one-size-fits-all solution, resulting in more accurate and relevant responses.

We evaluated several alternative approaches before selecting our hybrid architecture. A **Basic RAG** approach was considered, but standard retrieval-augmented generation doesn't apply equally well to varying document types; tuning for one database might work well but wouldn't be an apply-all solution, and this approach would also require querying all databases for every question rather than strategic querying. A **Pure LLM Approach**, using a large language model alone, would risk providing information not backed by official policy documentation and make source attribution difficult, rendering it inappropriate for financial policy guidance where attribution is essential. Finally, a **Single-Stage Processing** or non-agent approach would limit the system's ability to make strategic decisions about information retrieval and would reduce transparency in the reasoning process.

The selected approach aligns with the model's purpose of providing accurate, policy-compliant guidance based on authorized knowledge sources while maintaining transparency and efficiency.

### IRIS Models

IRIS employs several specialized model types for different components of the system.

**Primary Agent Models (IRIS Core):**

The **Generative Model for Complex Reasoning is OpenAI GPT-4o**. Its purpose is for complicated decision-making within agents like the router and planner, and for final response generation to users. This large-scale multimodal model accepts text inputs and produces text outputs with state-of-the-art reasoning capabilities. It has a context length of 128k tokens and operates on Text/Text input and output modalities.

For **Efficient Processing, OpenAI GPT-4o-mini** is used. Its purpose is for quick, straightforward decisions and for extracting content from source documents to feed the summarizer agent. It is a smaller, more efficient version of GPT-4o with good performance on simpler tasks, also featuring a 128k token context length and Text/Text input/output modalities.

The **Embedding Model is OpenAI text-embedding-3-large**. It serves the purpose of generating vector representations of text for semantic search capabilities. Its use cases include all semantic search databases (external_ey, external_iasb, external_pwc, external_kpmg). It produces 3072-dimensional embeddings, configured to 2000 dimensions for PostgreSQL compatibility, and is optimized for text similarity and retrieval tasks.

**Database Refresh Pipeline Models:**

The **Vision Processing Model is Qwen2**. Its purpose is to process infographics and visual documents in the catalog search - vision pipeline. This vision language model can analyze images and extract structured information. It is used to convert APG cheatsheets and other visual documents into textual Markdown format, with Image/Text input and output modalities.

For **External Data Processing, Cohere command-north-large** is utilized. Its purpose is to generate metadata and summaries for external data sources. This on-premises deployed model processes external content while maintaining data privacy. It is used in refresh pipelines to process external IFRS guidance documents from accounting firms, operating on Text/Text input and output modalities.

These models were selected based on their strong performance on finance-specific benchmarks and their ability to provide reliable outputs while mitigating misinformation risks compared to smaller or less capable models.

## 4.2 Model Inputs

IRIS uses a streamlined input approach centered around conversation history and structured database content. The key inputs include the complete **Conversation History**, which encompasses the current user query and all previous exchanges. This history provides essential context for understanding the current query and enables continuity in multi-turn conversations, especially for follow-up questions or references to previously discussed topics. Additionally, the system connects directly to **PostgreSQL Database Content**, utilizing tables (as defined in the `postgres_schema.sql` file) that store processed document content and metadata. These tables provide the knowledge base from which relevant information is retrieved during the research process. Throughout the processing pipeline, carefully crafted **Specialized System Prompts** are injected to guide each LLM component; these prompts define the role and expected output format for each agent and vary based on the specific task, such as routing, clarification, or planning.

The agent architecture processes the conversation history by strategically injecting specialized system prompts at each stage and incorporating relevant content retrieved from the PostgreSQL database as context for the LLM. This approach allows the system to maintain conversation context while providing accurate, document-grounded responses to finance and accounting policy inquiries.

Our solution leverages industry best practices and public benchmarking/leaderboard results to select appropriate models and approaches. The hybrid approach, with its flexible document processing and retrieval methods, worked effectively with minimal adjustments beyond tuning prompts and optimizing database storage.

## 4.3 Assumptions and Limitations (Restrictions) of Model Methodology

### Key Assumptions in the Modeling Approach

#### Table 7: Model Methodology Assumptions

| Model ID | Name | Description and Rationale | Materiality (Impact on Model Outputs) | Business Driven (Qualitative) or Quantitative Methodology Driven |
|----------|------|---------------------------|--------------------------------------|----------------------------------------------------------------|
| IRIS-001 | Incorrect Content | Users accept that generated content might be inaccurate or false and verify important information with domain specialists | Low | Qualitative |
| IRIS-001 | Source Authority | Information from internal policy documents is assumed to be accurate and authoritative | High | Business Driven |
| IRIS-001 | Query Classification | The router agent can effectively categorize queries as requiring research or direct response | Medium | Quantitative Methodology Driven |
| IRIS-001 | Source Selection | The planner agent can effectively identify the most relevant databases for a given query | Medium | Quantitative Methodology Driven |

### Limitations of the Modeling Approach

While our generative model is chosen based on its strong reasoning capabilities, it is not without limitations. There are instances when the model may not fully grasp extremely specialized finance or accounting concepts. However, these instances are not very frequent, and users are made aware of the risks and limitations through the Maven user interface.

### Assumptions and Conditions for Revisiting

Assumptions made for the model's efficacy are designed to bolster its reliability and quality of outputs across finance and accounting policy contexts. These assumptions will be scrutinized if significant changes to the knowledge base structure or content occur, if new types of documents with different formatting or organization are added, or if the system expands to new subject domains beyond finance and accounting. Furthermore, changes in user requirements or usage patterns, or advances in LLM capabilities that enable new approaches, would also trigger a review of these assumptions.

### Confidentiality and Information Filtering

Our models operate within RBC's secure environment, and data is not modified before being processed by the ML models. The data (queries and responses) are kept for audit and monitoring purposes. No user query data is used for model training.

### Design Approach

Our approach focused on implementing best practices from industry trends and leveraging techniques that have demonstrated success in public benchmarks and leaderboards. Rather than conducting extensive comparative testing, we selected approaches that aligned with our document types and system requirements. The hybrid approach with specialized processing pipelines required minimal tuning to achieve satisfactory results, with most adjustments focused on prompt engineering and database optimization.

### Table 8: Model Methodology Limitations (Restrictions)

| Model ID | Name | Description | Impact on Business Use(s) | Monitoring Description (if applicable) | Monitoring Accountable (if applicable) | Monitoring Frequency (if applicable) |
|----------|------|-------------|--------------------------|--------------------------------------|--------------------------------------|-------------------------------------|
| IRIS-001 | Knowledge Boundaries | The model will not have access to information beyond its available knowledge sources | Low, as the model will acknowledge when information is not found in available sources | Process monitoring tracks database search results | CFO Technology Team | Continuous |
| IRIS-001 | Context Window Limitation | Each agent has a finite context window that limits the amount of information it can process at once | Low, as the model implements chunking techniques | Token usage monitoring | CFO Technology Team | Continuous |
| IRIS-001 | Hallucination Risk | As with all LLM-based systems, there is a risk of generating plausible-sounding but incorrect information | Medium, mitigated by citations and verification | Random spot-checks of responses | CFO Content Team | Monthly |
| IRIS-001 | Response Latency | Complex research queries that search multiple databases can take longer to process | Low, as progress updates are provided | Process monitoring of stage durations | CFO Technology Team | Continuous |
