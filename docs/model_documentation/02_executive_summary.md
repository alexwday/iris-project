# 2. Executive Summary

**Model ID:** IRIS-001

IRIS (Intelligent Research and Information System) is an advanced AI-powered research and response system initially designed for RBC's Accounting Policy Group and now expanded to support the broader CFO Group. It combines a sophisticated agent-based architecture with a comprehensive knowledge base to provide intelligent, accurate responses to finance and accounting policy inquiries through a Retrieval-Augmented Generation (RAG) approach.

## Business Context and Purpose

IRIS serves the broader CFO Group by providing a centralized platform for finance and accounting policy inquiries, enabling users to obtain accurate, policy-compliant guidance through natural language conversations. While initially focused on accounting policies for APG, the system has evolved to address a wider range of finance-related policy information across the CFO Group.

The system is designed to analyze incoming queries to determine the appropriate processing path and research relevant finance and accounting policies, standards, and guidance across multiple internal and external sources. It generates comprehensive, properly cited responses with appropriate disclaimers, supporting both straightforward inquiries and complex finance/accounting policy questions. This centralized approach allows for the addition of new databases to the existing model framework rather than building each individual RAG database as a separate chatbot, significantly improving efficiency and scalability in accessing critical financial policy information throughout the organization.

## Modeling Approach

IRIS implements a sophisticated agent-based architecture that processes queries through two primary paths. The Direct Response Path handles queries that can be answered using only conversation history, following a minimal processing pipeline from Router to Direct Response Agent. For more complex inquiries, the Research Path activates a full processing pipeline: Router → Clarifier → Planner → Database Subagents → Summarizer.

The system operates on a retrieval-augmented generation (RAG) framework, combining specialized agents with access to both internal RBC accounting knowledge and external authoritative sources. This approach ensures that responses are grounded in documented policies rather than generated from the LLM's general knowledge, providing reliable and traceable information for finance professionals.

## Key Model Features

At the core of IRIS is a modular Agent-based architecture designed for specialized reasoning tasks. The Agent Router functions as the system gateway, determining the optimal processing path for each query. For research-intensive queries, the Agent Clarifier ensures sufficient context is available, while the Agent Planner strategically selects appropriate knowledge sources based on query analysis.

Specialized Database Subagents retrieve information from various sources using one of five distinct retrieval methodologies specifically engineered for different document types. These methodologies include: **Catalog Search - Small**, used for standard documents (PDFs, DOCX files), employing a two-stage process with document catalog retrieval and LLM-based selection; **Catalog Search - Large**, optimized for large documents with distinct sections/chapters, employing a three-stage process that includes section-level selection; **Catalog Search - Excel**, a custom approach for tabular data that preserves structured information from spreadsheets; **Catalog Search - Vision**, a specialized method for infographics and visual content which uses vision models to extract information; and **Semantic Search - Large**, used for very large reference documents, employing vector-based similarity search with embedding technology.

The subagents can process queries in two distinct modes based on user intent. In **Metadata Search** mode, when users ask what documents are available on a topic, the system returns only document names and descriptions without retrieving full content or invoking the Summarizer. Conversely, in **Research Mode**, when users request specific information on a topic, the system retrieves and processes the actual document content to generate comprehensive responses.

For research-based queries, the Agent Summarizer synthesizes findings into coherent, cited responses. The entire system is supported by comprehensive process monitoring that tracks execution stages, token usage, and performance metrics to ensure operational reliability.

## Knowledge Sources

The model accesses various knowledge sources structured in a tiered approach, with internal RBC documentation serving as primary authoritative sources. These include Corporate Accounting Policy Manuals, APG Cheat Sheet Infographics, APG Wiki Entries, Internal Accounting Memos, Project Approval Request Guidance, Internal Control over Financial Reporting Policy, and additional specialized internal knowledge bases. To supplement these, IRIS also integrates external sources including IASB Standards and Interpretations as well as guidance from select accounting firms (EY, KPMG, and PwC). This hierarchical approach ensures that internal policies take precedence while leveraging industry standards when appropriate.

## Notable Limitations and Weaknesses

IRIS operates within specific boundaries that define its capabilities and limitations. The system can only provide information based on available knowledge sources and cannot leverage the LLM's general knowledge, which ensures responses are policy-compliant but limits coverage to documented topics. It is purpose-built for finance and accounting policy guidance and not designed for general-purpose uses or providing legal, tax, or regulatory filing advice. The quality of responses depends heavily on the availability and quality of source documents, with finite context windows limiting the amount of information processed in a single interaction. As with all LLM-based systems, there remains a risk of generating plausible-sounding but incorrect information, which necessitates appropriate disclaimers and verification statements for all responses.

## Human-in-the-Loop and Risk Mitigation

IRIS implements a strong human-in-the-loop approach to ensure appropriate use. System access is strictly controlled through Active Directory groups, with users granted permissions to specific databases based on their role and responsibilities. Before using the system, all users must review and accept terms and conditions that outline the system's capabilities and limitations.

The Maven user interface incorporates clear warnings about the importance of verifying information received, with appropriate disclaimers embedded in all responses. The system provides source references for all information, enabling users to verify content against original documents. By design, IRIS explicitly identifies situations where it cannot provide reliable information, preventing users from acting on incomplete or uncertain guidance. This multi-layered approach to risk mitigation ensures that the system serves as a research aid rather than replacing human judgment in critical finance decisions.

## Compliance Framework

IRIS is not used for any regulatory purposes but functions as a search tool for users to retrieve information from documents. All outputs must be verified by users based on the source references provided. The system complies with RBC's Generative AI policies and Data Loss Prevention (DLP) requirements, ensuring appropriate handling of internal information.

The system incorporates multiple safeguards to clearly indicate when information represents general guidance rather than definitive advice and recommend verification with domain specialists before implementation. It maintains confidentiality of internal policies, identifies and refuses to answer queries outside its scope, and provides appropriate confidence signaling based on source authority and consensus. These mechanisms ensure that IRIS operates within established compliance frameworks and supports proper governance of financial information.

## Model Materiality and Risk Assessment

IRIS is expected to deliver significant productivity benefits by providing faster access to finance and accounting policy information across the CFO Group. By implementing robust access controls, clear usage guidelines, and comprehensive documentation practices, the system demonstrates an ACCEPTABLE risk profile for internal usage, with an overall uncertainty level of ±10.4%. The system's design prioritizes accuracy and transparency, with clear attribution to source documentation and appropriate limitations on scope. These features, combined with ongoing monitoring and regular performance assessment, ensure that IRIS delivers value while maintaining the high standards required for financial information systems within RBC.
