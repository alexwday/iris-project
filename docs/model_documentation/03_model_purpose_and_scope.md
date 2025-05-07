# 3. Model Purpose and Scope

**Model Name:** IRIS (Intelligent Research and Information System)
**Model ID:** IRIS-001

## 3.1 Model Purpose and Use

IRIS was initially designed to serve as an intelligent research and response system for RBC's Accounting Policy Group (APG) but has evolved to support the broader CFO Group. The primary purpose of IRIS is to provide accurate, policy-compliant guidance in response to finance and accounting policy inquiries through natural language conversations.

The model utilizes a sophisticated agent-based architecture with a Retrieval-Augmented Generation (RAG) approach to analyze inquiries and determine whether to respond based on conversation context alone or to perform targeted research across specific documentation sources. This dual-path approach allows IRIS to provide both quick responses to straightforward queries and comprehensive, researched answers to complex finance and accounting policy questions. The centralized architecture enables the addition of new knowledge sources without rebuilding the entire system, creating a scalable platform for organization-wide finance and accounting guidance.

IRIS performs several key functions throughout its operational pipeline. The process begins with the Agent Router, which analyzes user inquiries to determine if they can be answered directly from conversation history or if they require database research. For queries following the research path, the Agent Clarifier evaluates contextual sufficiency, either requesting essential missing information or creating a comprehensive research statement. Subsequently, the Agent Planner selects the most relevant databases to query based on this research statement. Database Subagents then access the appropriate knowledge sources using one of three specialized retrieval methods tailored to document types: Catalog Search - Small, Catalog Search - Large, or Semantic Search - Large. Finally, the Agent Summarizer integrates findings from multiple sources into coherent, properly cited responses, complete with appropriate disclaimers and source attributions.

The model delivers significant value to RBC by providing centralized access to finance and accounting policy information across multiple sources, ensuring consistent, policy-compliant guidance with proper citations and disclaimers. This approach substantially reduces the time needed to retrieve relevant finance and accounting information while offering comprehensive coverage of both internal RBC finance policies and selected external standards. By streamlining information access, IRIS enhances productivity for finance professionals across the CFO Group, supporting more efficient decision-making processes while ensuring compliance with established policies and standards.

### Table 4: Model Dependencies

| Base Model ID | Upstream Model(s) | Interdependent Model(s) | Downstream Model(s) |
|---------------|-------------------|------------------------|---------------------|
| IRIS-001 | N/A | N/A | N/A |

## 3.2 Scope of Application

The target scope of IRIS is for use across the CFO Group within RBC. It is designed to provide information and guidance within the domains of finance and accounting policy, with content coverage spanning a comprehensive range of internal and external resources.

The system's content scope encompasses internal RBC finance and accounting policies and procedures, CFO and APG-developed guides, cheatsheets, and wikis, as well as internal accounting memos and project approval requests. It also covers financial reporting and control documentation, management reporting policies and guidelines, IFRS standards and interpretations, and accounting firm guidance on IFRS application from EY, KPMG, and PwC. This diverse content base enables IRIS to address a wide range of finance and accounting information needs.

IRIS is designed to handle various query types. These include definitional queries about finance and accounting concepts, questions about policy application and interpretation, and requests for specific standard references. The system can also process inquiries about financial treatment for specific scenarios, conduct metadata searches for available documents on particular topics, and provide guidance on financial reporting requirements. This versatility makes it a comprehensive research tool for finance and accounting professionals.

The system serves RBC CFO Group members exclusively. Access is managed through Active Directory groups, with permissions to specific databases granted based on user roles and requirements. This controlled access model ensures appropriate information security while making relevant resources available to those who need them.

IRIS focuses specifically on accounting and finance domains, operating within RBC's internal environment. The system concentrates on accounting policies and standards relevant to the organization's financial reporting practices. It does not access real-time financial data or transaction systems, focusing instead on policy documents and interpretive guidance.

## 3.3 Model Outputs

IRIS produces text responses to user inquiries through a structured processing pipeline, with output characteristics varying based on the processing path selected for each query. This design allows the system to tailor its responses to the specific information needs of users while maintaining consistency in quality and format.

For the Direct Response Path, outputs consist of text responses based solely on conversation context, structured with clear sections and appropriate headings. These responses are limited to information that can be confidently inferred from the conversation history, providing quick answers to straightforward queries without unnecessary database access.

The Research Path generates more comprehensive outputs. These begin with research plans that show selected knowledge sources and provide progress updates during the research process. The final responses include citations to specific policies, standards, or guidelines, structured content with appropriate headings and sections, clear source attributions for transparency, confidence signaling based on source authority and consensus, and required disclaimers about verification and implementation. This detailed approach ensures that complex queries receive thorough, well-documented responses.

For Metadata Search requests, the system produces lists of relevant documents found in selected databases. These lists include document names and descriptions along with source database attributions, enabling users to discover and access relevant policy documents directly. Unlike research queries, metadata searches bypass the Summarizer agent, directly returning document listings without processing the full content.

All IRIS outputs share common characteristics designed to ensure their utility and reliability. They are delivered in markdown format with a clear and professional tone, and are properly structured with organizational headings to enhance readability. The content maintains compliance with internal standards for accounting guidance while being transparent about sources and confidence levels. Each response explicitly addresses limitations and verification requirements, ensuring users understand the appropriate use context for the information provided.

Performance requirements for model outputs include accurate information retrieval from appropriate knowledge sources, proper citation of relevant policies and standards, clear distinction between high and low confidence information, inclusion of all required disclaimers and verification statements, and compliance with established quality guidelines for structure and formatting. These requirements ensure that IRIS outputs consistently meet the needs of finance professionals while maintaining appropriate risk controls.

### Table 5: Approved Model Outputs

| Model ID | Output | Detailed Description | Model Use | Business Purpose | Region of Use | User |
|----------|--------|---------------------|-----------|-----------------|---------------|------|
| IRIS-001 | Text Responses to Finance and Accounting Policy Inquiries | Natural language responses to user inquiries, including appropriate citations, disclaimers, and structured content based on available knowledge sources | Internal - Decision Support | Finance and Accounting Policy Guidance | Global | RBC CFO Group Members |

## 3.4 Compliance with Regulations, Policies, and Procedures

### 3.4.1 Internal Policies

IRIS is not used for regulatory purposes but functions primarily as a search tool for users to retrieve information from documents. All outputs require verification by users based on the source references provided.

As an internal knowledge retrieval and synthesis system for finance and accounting policy guidance, IRIS helps users locate information about established financial and accounting standards and principles that RBC follows. These include International Financial Reporting Standards (IFRS), International Accounting Standards (IAS), IFRS Interpretations Committee (IFRIC) interpretations, Standing Interpretations Committee (SIC) interpretations, and US Generally Accepted Accounting Principles (GAAP) where applicable.

The system includes built-in features to support proper information usage. These features include direct access to source documentation, clearly identified citations to relevant standards, required disclaimers regarding verification, and identification of queries outside its scope. These help users efficiently locate relevant guidance while setting appropriate expectations for system outputs.

### 3.4.2 Access Controls and Requirements

IRIS complies with RBC's Generative AI policies and Data Loss Prevention (DLP) requirements. Access to the system is controlled through Active Directory groups, with permissions to specific databases granted based on user roles.

The system adheres to RBC's guidance on Generative AI from T&O, CISO, and Compliance, including the RBC CISO Directive on Generative AI.

Output quality standards are maintained through structured requirements. These ensure all responses include appropriate disclaimers, follow established formatting guidelines, use consistent citation formats for finance and accounting standards, and clearly indicate confidence levels based on source authority. These standards help maintain consistency and reliability across system outputs.

Operational requirements include access controls based on authorized user roles, process monitoring for system performance and usage, and regular validation of knowledge sources for accuracy and currency. These controls ensure the system operates reliably while supporting the information needs of the CFO Group.
