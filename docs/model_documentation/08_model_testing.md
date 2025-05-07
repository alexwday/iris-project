# 8. Model Testing

**Model Name:** IRIS (Intelligent Research and Information System)
**Model ID:** IRIS-001

This section documents the testing methodology and results used to validate the IRIS system. The testing focused on evaluating the system's ability to retrieve relevant information from knowledge sources and generate appropriate responses across a range of finance and accounting policy queries. Supporting test artifacts, including test questions, APG feedback, quantitative results, and APG signoff documentation, are available in designated SharePoint folders. Test questions can be found at `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/TestQuestions/`, APG feedback at `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/APGFeedback/`, quantitative results at `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/QuantitativeResults/`, and APG signoff at `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/APGSignoff/`.

## 8.1 Testing Approach

The IRIS testing strategy centered on an iterative, database-by-database development and testing approach, with a focus on ensuring that the agent-based architecture and knowledge retrieval mechanisms functioned correctly to produce accurate, policy-compliant responses.

### 8.1.1 Query Dataset Development

Two distinct query sets were developed for comprehensive testing. The first set consisted of **APG-Focused Queries**, approximately 50 example queries provided by the Accounting Policy Group (APG), specifically targeting accounting policy databases. The second set, **CFO-Focused Queries**, comprised approximately 50 additional queries curated by the internal team, designed to test broader CFO group databases. These queries were deliberately created to cover common inquiry types and critical finance and accounting areas across all integrated knowledge sources. The complete set of test queries used for system validation is available in the SharePoint folder: `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/TestQuestions/`.

### 8.1.2 Iterative Testing and Development Process

Testing and development were conducted through an incremental, database-by-database approach. The **Method Development Phase** involved developing an initial retrieval method for a single database, generating test outputs for APG review, collecting and analyzing feedback, and implementing enhancements based on this feedback. This process was repeated until performance was satisfactory for that database. During the **Method Expansion Phase**, when integrating a new database, the existing method was tested first. If performance was insufficient, a new method was developed, leading to the creation of three distinct retrieval methods and five data processing pipelines. Each new method underwent the same iterative feedback and enhancement process. Finally, the **Comprehensive Testing Phase** was conducted once all databases and methods were implemented. APG databases received final signoff from the APG team, while non-APG databases were evaluated with detailed scoring metrics, and results were aggregated into a comprehensive evaluation report.

This development approach ensured that each database and retrieval method was optimized for the specific document types it contained. Testing was conducted using the Dataiku implementation, which has been made available to business users for providing feedback.

### 8.1.3 Testing Methodology

The testing process involved structured evaluation across multiple dimensions. Test questions were submitted to the model through the Dataiku interface. For each question, evaluators recorded database selection accuracy (did the system select the appropriate database(s)?), document selection accuracy (did the system retrieve the relevant documents?), response quality (overall score of the generated response), and paragraph-level feedback (detailed comments on each section of the response). All results were documented in Excel templates for consistent evaluation. These results were then aggregated to calculate performance metrics and identify improvement areas. Additional negative testing specifically probed system boundaries and restrictions to ensure appropriate guardrails were functioning.

## 8.2 Testing Results

### 8.2.1 Key Performance Metrics

The final comprehensive testing phase yielded specific performance metrics for the non-APG databases. The **Overall Performance Score** was 89.6% based on reviewer evaluations. **Database Selection Accuracy** reached 99.4% in selecting the appropriate knowledge source(s). **Document Selection Accuracy** was 97.7% in retrieving relevant documents from selected databases. **Answer Accuracy** was calculated at 94.2% based on reviewer comments and evaluation notes. Complete quantitative test results and detailed metrics are available in the SharePoint folder: `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/QuantitativeResults/`.

For APG databases, the evaluation process involved direct feedback and signoff rather than numerical scoring. The APG team provided expected answers for each test question and evaluated whether the system outputs met these expectations. Final signoff was received for all 50 APG test questions, confirming satisfactory performance. Final APG signoff documentation is available in the SharePoint folder: `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/APGSignoff/`.

Given the shared retrieval methods between APG and non-APG databases, and the positive feedback from both evaluation processes, the system demonstrates consistently strong performance across all knowledge sources.

### 8.2.2 Identified Issues and Resolutions

Through the iterative testing process, several issues were identified and addressed. Detailed feedback from APG reviewers, including issue reports and suggested improvements, is available in the SharePoint folder: `https://rbcds.sharepoint.com/sites/IRISProject/Shared Documents/TestArtifacts/APGFeedback/`.

An issue of **Unsolicited IFRS vs. GAAP Comparisons** arose where the system included these comparisons even when not requested, making responses unnecessarily long. This was resolved by enhancing prompt instructions for the CAPM subagent to focus only on the standard relevant to the query (defaulting to IFRS if none specified) and actively filter out information about other standards unless explicitly requested.

**Incomplete Answers Due to Sequential Database Processing** was another problem, where responses sometimes contained information only from one database (e.g., CAPM) when relevant information also existed in others (e.g., APG Wiki). The resolution involved implementing parallel database querying and updating the Summarizer agent to synthesize findings from all sources into a comprehensive response.

An **Overly Verbose Response Format** was observed, with responses including excessive internal processing details like "Thought", "Clarify", "Researching", making outputs long and difficult to follow. This was addressed by eliminating internal "thinking" steps from display, streamlining clarification and research status updates, and configuring the Summarizer to generate only the final, synthesized report.

**Incorrect Handling of Finance-Related Queries** occurred when basic finance concept definitions were sometimes answered directly without database research, risking responses based on the model's training data. The resolution was to update the Router agent to explicitly route all finance-related queries (including basic definitions) to the research path, and enhance the Direct Response agent to refuse answering finance queries without prior research results.

There were instances of **Missing Critical Information**, where specific, critical pieces of information (like conditions or criteria) were sometimes missing from responses. This was resolved by enhancing prompts for subagents to accurately extract specific conditions or tests, and for the Summarizer to preserve these details in the final synthesis.

**Unnecessary Detail in Responses** was an issue where, even when asking about specific aspects (e.g., classification of financial assets), responses included details on unrelated aspects (e.g., measurement, impairment). The resolution was to implement adaptive synthesis logic to match the scope of the response to the specific user request, providing concise answers for targeted questions.

**Inconsistent Spacing/Formatting** in responses showed inconsistencies in spacing, indentation, and Markdown usage. This was addressed by enhancing formatting instructions for the Summarizer agent with explicit guidelines for handling headings, lists, paragraph spacing, and proper Markdown structure.

Finally, **Incorrect Labeling of Source Authority** occurred when external firm guidance (EY, KPMG, PwC) was incorrectly labeled as "authoritative," a designation reserved for standards bodies like IASB. The resolution was to update source descriptions to clearly label external firm guidance as "External Supplementary" and IASB as "External Authoritative," ensuring correct source hierarchy understanding.

### 8.2.3 User Interface Issues Addressed

Several issues related to the user interface were also identified and addressed. An **Inability to Scroll During Response Streaming** prevented users from scrolling up to view previous messages during response generation; this was resolved by modifying the UI code to allow scrolling during streaming while maintaining auto-scroll after completion. **Non-functional Feedback Controls**, specifically thumbs up/down icons that didn't function in the test environment, were clarified as features planned for the production implementation. Regarding **Graphical Content Display**, users requested the ability to see actual graphical cheat sheets rather than text descriptions; the resolution involved implementing multi-pass vision preprocessing to extract detailed content from graphical elements while acknowledging the current text-only display limitation.

## 8.3 Implementation of Feedback

The feedback collection and implementation process was systematic and thorough. **Feedback Collection** involved gathering detailed comments from APG reviewers for each test query, documenting performance across multiple dimensions in Excel templates, and categorizing issues by frequency and impact. For **Issue Prioritization**, high-impact issues affecting response accuracy were addressed first, widespread issues affecting multiple queries were prioritized, and UI/UX enhancements were scheduled according to their impact on usability. The **Implementation Approach** involved refining system components through targeted prompt engineering, implementing core architectural changes (e.g., parallel database querying), and developing UI enhancements in coordination with front-end teams. Finally, **Verification** included targeted testing for each implemented fix, re-testing previously problematic queries to confirm improvements, and re-running full test suites to ensure no regression.

This systematic approach to feedback implementation ensured continuous improvement of the system throughout the development cycle.

## 8.4 Model Components Validation

While IRIS doesn't implement custom model training, it leverages pre-trained models in specific ways. The testing validated the effectiveness of these model components.

### 8.4.1 Pre-trained Models Performance

The performance of **GPT-4o and GPT-4o-mini**, which serve as the primary reasoning engines, was confirmed. Testing showed they effectively interpret user queries, generate appropriate research statements, accurately select relevant documents from catalog descriptions, generate coherent, well-structured responses, and maintain appropriate limitations and disclaimers. The **Embedding Model (text-embedding-3-large)**, used for semantic search, was verified for high-quality semantic similarity matching, effective ranking of relevant documents, and an appropriate balance between precision and recall. The **Qwen2 Vision Model**, for processing visual documents, demonstrated accurate text extraction from visual elements, proper interpretation of charts and tables, and effective conversion of visual information to structured text. The **Cohere command-north-large** model, used for database refresh pipelines, was validated for effective processing of external IFRS guidance, proper metadata generation, and data privacy preservation.

The performance of these pre-trained components was deemed satisfactory for production use based on the query testing results, with no formal pre-testing required due to reliance on established benchmarking statistics that demonstrate sufficient capabilities.

### 8.4.2 Retrieval Method Validation

Each retrieval method was validated for its specific use case through the iterative testing process. **Catalog Search - Small** demonstrated effectiveness for standard documents. **Catalog Search - Large** proved appropriate for larger documents with distinct sections. **Catalog Search - Excel** successfully handled structured data from Excel. **Catalog Search - Vision** verified its ability to extract information from visual documents. **Semantic Search - Large** confirmed effectiveness for very large reference documents.

These methods were selected based on document characteristics and evolved through the iterative testing process, with each method optimized for specific document types and structures.

### 8.4.3 Guardrail Testing

Negative testing was conducted to verify the system's ability to recognize and appropriately respond to out-of-scope queries. These tests confirmed that the system correctly identifies queries outside its knowledge domain, provides appropriate disclaimers when queries cannot be answered, maintains proper boundaries regarding financial advice and regulatory guidance, and consistently includes required disclaimer statements in messages.

This testing validated that the safety guardrails implemented in the system function as intended, ensuring appropriate use within defined boundaries.

## 8.5 Current Implementation and Future Integration

The IRIS system has been implemented in Dataiku as a Dash web application for initial testing and feedback. This implementation has been made available to business users for evaluation and has undergone multiple rounds of refinement based on their feedback.

The current status of the system includes a functional implementation in the Dataiku environment with all agent components operational. All database connections have been established and validated with proper access controls. Business users have provided feedback on performance and response quality, which has been incorporated into refinements. Planning for Maven integration is underway, with the IRIS code being prepared for integration into the Maven UI, aiming for a working demonstration in the Maven development environment by June 2025.

The Maven integration will maintain the same core functionality with no code changes to the underlying model. The integration will primarily focus on adapting the API interface to work within the Maven ecosystem while using the same PostgreSQL database for knowledge retrieval.

## 8.6 Testing Limitations

It is important to acknowledge several limitations in the testing approach. Formal blind testing with independent evaluators was not conducted due to resource constraints; testing relied on the same teams involved in development. Extensive statistical validation was not performed, given the system's nature as a RAG implementation rather than a custom-trained model. Alternative RAG architectures or methods were not explicitly tested as comparisons, as method selection was based on prior experience and project requirements. Extensive load or stress testing to identify performance boundaries was not conducted, though basic functionality was confirmed. Testing relied on available subject matter experts rather than a formal, diverse panel of evaluators. Finally, testing has been conducted primarily in the Dataiku environment, with full Maven integration testing pending.

These limitations are considered acceptable given the nature of the project and its intended use as an internal tool with human oversight.

## 8.7 Testing Conclusions

The testing conducted for the IRIS system provides reasonable confidence in its ability to serve its intended purpose. The system's **Core Functionality** effectively retrieves relevant information and generates appropriate responses, supported by quantitative metrics (99.4% database selection, 97.7% document selection, 94.2% answer accuracy). Regarding **Knowledge Boundaries**, negative testing confirmed the system appropriately identifies when information is outside its knowledge base and provides disclaimers. The **Response Quality**, after iterative improvements, reached a level deemed acceptable for production use, evidenced by formal APG signoff and an overall performance score of 89.6%. Furthermore, the system's **Document Integration** capability, through the database refresh process, allows it to incorporate new documents and remain current as policies evolve.

Based on the testing results, the IRIS system is considered suitable for deployment as a finance and accounting policy guidance tool, with the understanding that human oversight remains essential for verifying responses on critical matters. The feedback collection mechanism and ongoing monitoring will support continuous improvement as the system is used in practice.
