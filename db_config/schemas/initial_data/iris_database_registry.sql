-- IRIS Database Registry Initial Data
-- Generated: 2026-04-22T15:33:13.328216
-- 
-- Import with: psql -f iris_database_registry.sql
-- Or run in pgAdmin/DBeaver
--
-- Note: Uses ON CONFLICT to handle re-runs safely

BEGIN;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'external_ey',
    'EY IFRS Guidance',
    'External accounting guidance and interpretations from EY, including insights, disclosure checklists, and clarifications on the application of IFRS standards.',
    '**Content:** External accounting guidance and interpretations from EY, including insights, disclosure checklists, and clarifications on the application of IFRS standards.

**Tier/Priority:** EXTERNAL SUPPLEMENTARY - Third-party interpretations that support but do not replace official standards.

**Usage Guidance:** Consult when explicitly requested by user OR when internal sources are insufficient and an external perspective would help. Use to supplement internal knowledge, fill gaps, or get external interpretation. Particularly useful for disclosure examples and checklists. Internal RBC guidance should remain preferred for policy questions.

**When to Select:** Explicit requests for EY guidance, external/third-party interpretations, IFRS disclosure checklists, disclosure examples, or when internal sources lack sufficient detail on practical application.

**Query Tips:** Use standard numbers (IFRS 15, IAS 38), technical terms, specific paragraphs.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What does EY''s guidance say about IFRS 16 lease modification accounting?","What disclosure requirements does EY highlight for financial instrument classification?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_APG_EXTERNAL_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    false,
    10,
    8,
    2,
    3,
    100,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    5,
    20,
    20,
    15,
    8,
    3,
    3
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'external_iasb',
    'International Accounting Standards Board (IASB)',
    'The official IFRS standards, interpretations (IFRICs/SICs), guidance, illustrative examples, and the basis for conclusions, serving as an authoritative source for IFRS-related queries.',
    '**Content:** The official IFRS standards, interpretations (IFRICs/SICs), guidance, illustrative examples, and the basis for conclusions, serving as the authoritative source for IFRS-related queries.

**Tier/Priority:** EXTERNAL AUTHORITATIVE - Official IFRS source text and interpretations.

**Usage Guidance:** Consult when the request needs exact IFRS wording, specific paragraphs, or authoritative external standard text. Select when explicitly requested by user OR when internal sources are insufficient/unclear on the standard requirements. Use for official standard text or interpretations. Prefer internal RBC guidance for policy questions.

**When to Select:** Explicit mentions of IFRS/IAS/IFRIC/SIC numbers, requests for official standard language, citations, paragraph references, or when internal sources lack clarity on what the standard actually requires.

**Query Tips:** Use standard numbers (IFRS 15, IAS 38), interpretations (IFRIC/SIC), technical terms, specific paragraphs.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["Under IFRS, what are examples of temporary differences that lead to a deferred tax liability?","Under IFRS, what are the presentation requirements for compound financial instruments? Please specify the relevant standard and sections."]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_APG_EXTERNAL_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    false,
    10,
    8,
    2,
    3,
    100,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    5,
    20,
    20,
    15,
    8,
    3,
    3
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_aio',
    'Auditor Independence Office Policy Documents',
    'RBC''s internal policies, procedures, and FAQs focused on maintaining auditor independence, including guidelines for business and financial relationships with external auditors.',
    '**Content:** RBC''s internal policies, procedures, and FAQs focused on maintaining auditor independence, including guidelines for business and financial relationships with external auditors.

**Tier/Priority:** DOMAIN EXPERT - Specialized guidance for auditor independence requirements and controls.

**Usage Guidance:** Use for determining permissible relationships, approvals, disclosures, and procedural steps that preserve auditor independence for external auditor engagements.

**When to Select:** Queries mentioning auditor independence, external auditor engagements, restricted services, business/financial relationship approvals, joint marketing/co-branding rules, or required documentation for independence.

**Query Tips:** Use RBC terms and reference AIO processes/workflows. Include terms like ''auditor independence'', ''external auditor'', ''business relationship'', ''financial relationship'', ''restricted services''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What type of business relationships are acceptable with an external auditor?","What types of financial information are required to be disclosed to external parties?","What arrangements are prohibited under joint marketing and co-branding with external auditors?","What are examples of external parties?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_capm',
    'Corporate Accounting Policy Manuals',
    'RBC''s comprehensive accounting policies, detailing recognition, measurement, disclosure, and compliance requirements under IFRS and U.S. GAAP frameworks.',
    '**Content:** RBC''s comprehensive accounting policies covering recognition, measurement, disclosure, and compliance requirements under IFRS and U.S. GAAP frameworks. This is the official RBC policy manual.

**Tier/Priority:** PRIMARY SOURCE - Authoritative RBC accounting policy manual; default source for accounting determinations.

**Usage Guidance:** Use for definitive RBC-required accounting treatment, recognition thresholds, measurement rules, and disclosure obligations; rely on this for policy wording, required controls, and governance. Always check US GAAP flags when dual-GAAP treatment may apply.

**When to Select:** Queries asking for RBC policy, acceptable accounting treatment, required disclosures, IFRS/U.S. GAAP application at RBC, or approval/exception conditions for accounting topics.

**Query Tips:** Use RBC terms and policy areas. Check US GAAP flags for dual-reporting considerations.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What is the IFRS and U.S. GAAP difference on firm commitment related to hedging?","Is a call option in a financial instrument an embedded derivative?","What threshold is considered to be probable under IFRS?","What are the main criteria to derecognize a financial asset under IFRS?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    15,
    1,
    3,
    200,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    5,
    20,
    200,
    20,
    10,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_cheatsheets',
    'APG Cheatsheets',
    'Concise, 1-2 page summaries and infographics on specific accounting topics, offering quick, visual guidance for key concepts and policies.',
    '**Content:** APG Cheatsheets - concise 1-2 page summaries and infographics on specific accounting topics, offering quick visual guidance for key concepts and policies. Contains decision trees, checklists, flowcharts, and visual summaries that distill complex topics into scannable formats.

**Tier/Priority:** SUPPLEMENTARY SOURCE (Visual Quick Reference) - APG infographics that supplement core policy with visual aids for common accounting topics.

**Usage Guidance:** Contains visual quick references for frequently asked accounting topics. Use when a scannable visual format would be helpful - decision trees, checklists, or infographic summaries. Best for well-established topics where APG has created visual aids to provide definitions and overviews.

**When to Select:** Questions seeking: visual decision aids, checklists for accounting determinations, flowcharts for classification or recognition decisions, or quick visual summaries of common accounting topics.

**Query Tips:** Use concise, topic-focused queries suitable for semantic search.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["Is there a decision tree for determining lease classification?","Is there a flowchart for financial asset derecognition?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_APG_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_esg',
    'Internal ESG Guidance',
    'RBC''s policies and frameworks for ESG disclosures, including the ESG Materiality Framework and guidance on evaluating changes to prior period ESG information, aligned with global standards like ISSB and CSRD.',
    '**Content:** RBC''s policies and frameworks for ESG disclosures, including the ESG Materiality Framework and guidance on evaluating changes to prior period ESG information aligned with ISSB and CSRD expectations.

**Tier/Priority:** DOMAIN EXPERT - Specialized ESG reporting policy and disclosure guidance.

**Usage Guidance:** Use for ESG reporting requirements, materiality assessments, treatment of prior period changes, and alignment with external ESG frameworks.

**When to Select:** Queries about ESG materiality thresholds, handling prior period ESG adjustments, required ESG metrics/disclosures, ISSB or CSRD alignment, or treatment of ESG measurement uncertainty.

**Query Tips:** Use terms like ''ESG materiality'', ''prior period ESG'', ''ISSB alignment'', ''CSRD'', ''ESG metrics'', ''sustainability report'', ''measurement uncertainty''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["If something isn''t material should it still go into the Sustainability Report?","Is there a threshold for materiality?","How to treat measurement uncertainty in the ESG framework?","What are the ESG guidelines for revising materiality from prior reporting periods?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_ext_reporting_and_disclosure',
    'External Reporting and Disclosure Policies',
    'RBC''s guidelines on material information disclosure, subsidiary reporting, trading revenue classification, and auditor independence, ensuring compliance with regulatory frameworks like OSFI, FRTB, and SEC standards.',
    '**Content:** RBC''s guidelines on material information disclosure, subsidiary reporting, trading revenue classification, and auditor independence to ensure compliance with regulatory frameworks such as OSFI, FRTB, and SEC standards.

**Tier/Priority:** DOMAIN EXPERT - Specialized policies for external reporting and disclosure controls.

**Usage Guidance:** Use for determining disclosure obligations, authorized spokesperson rules, trading revenue classification criteria, and requirements for engaging external auditors to maintain compliance.

**When to Select:** Queries about material or non-material disclosure protocols, subsidiary or trading activity reporting, quiet period or spokesperson restrictions, trading revenue classification under FRTB/SEC expectations, auditor engagement and independence controls, or references to policies such as LAW-8, FIN-ACC-217, FIN-ACC-212, or FIN-ACC-213.

**Query Tips:** Use terms like ''material information'', ''disclosure policy'', ''subsidiary reporting'', ''trading revenue'', ''FRTB'', ''auditor engagement'', ''auditor independence'', ''FIN-ACC-217'', ''FIN-ACC-212'', ''FIN-ACC-213''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["According to the disclosure policy: Who are authorized spokespersons?","What guidelines should be followed for announcements that are not material?","Can an RBC employee speak at a conference during quiet period?","Which teams must review forward-looking information before it''s disclosed?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_global_finance_standards',
    'Global Financial Standards',
    'RBC''s policies on currency reporting, resident/non-resident splits, foreign exchange (FX) position accounts, the Global Chart of Accounts structure, and the Global Rates policy, ensuring consistency and compliance in financial reporting across the organization.',
    '**Content:** RBC''s policies on currency reporting, resident/non-resident splits, foreign exchange (FX) position accounts, the Global Chart of Accounts structure, and the Global Rates policy to ensure consistent financial reporting.

**Tier/Priority:** DOMAIN EXPERT - Specialized standards for global finance reporting consistency.

**Usage Guidance:** Use for guidance on currency and residency reporting rules, FX position account setup, chart of accounts structure, and required FX rates used in reporting.

**When to Select:** Queries about currency reporting standards, resident versus non-resident requirements, FX position account usage, chart of accounts design or abbreviations, mandated global FX rates, or references to standards such as FIN-ACC-14 or FIN-ACC-10.

**Query Tips:** Use terms like ''currency reporting'', ''resident reporting'', ''FX position account'', ''chart of accounts'', ''global FX rates'', ''FIN-ACC-14'', ''FIN-ACC-10''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What are the minimum standards for Non-Interest Expenses in COA reporting?","What is RBC''s global FX rate policy?","What are examples of regulatory reports RBC provides OSFI?","What are requirements for resident and non-resident transactions?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_intragroup_memos',
    'Intragroup Reconciliation Memos',
    'Documentation regarding the permanent material intergroup revenue breaks, including reconciliation analysis and entity-level break identification.',
    '**Content:** Documentation of permanent material intergroup revenue breaks, including reconciliation analysis and entity-level break identification.

**Tier/Priority:** DOMAIN EXPERT - Specialized guidance for intergroup reconciliation and permanent break handling.

**Usage Guidance:** Use for questions on classifying, documenting, and explaining intergroup revenue discrepancies, including entity attribution and reconciliation procedures.

**When to Select:** Queries mentioning intergroup/IG reconciliation, permanent revenue breaks, entity-level discrepancies, OU/CPOU/LE/CE codes, or procedures for analyzing and documenting revenue breaks.

**Query Tips:** Use terms like ''IG'', ''intergroup'', ''breaks'', ''revenue breaks'', ''permanent breaks'', ''insurance break'', ''OU'', ''CPOU'', ''LE'', ''CE'', ''intergroup reconciliation''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["Which Intragroup Reconciliation breaks relate to RBC Insurance, and what is the amount related to each?","How many Intragroup Reconciliation breaks relate to timing differences, and what are the reasons for these timing differences?","Which Intragroup Reconciliation breaks relate to human error?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_INTRAGROUP_MEMOS_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_management_reporting',
    'Management Reporting Policies & Guidance',
    'RBC''s policies and guidelines on management reporting frameworks, including performance metrics (ROE, RORC), intra-group transactions, funds transfer pricing, tax allocation, and average balance reporting in compliance with SEC Regulation S-K.',
    '**Content:** RBC''s policies and guidelines on management reporting frameworks, including performance metrics (ROE, RORC), intra-group transactions, funds transfer pricing, tax allocation, and average balance reporting in compliance with SEC Regulation S-K.

**Tier/Priority:** DOMAIN EXPERT - Specialized guidance for management reporting policies and metrics.

**Usage Guidance:** Use for methodology and process details around management reporting metrics, intra-group treatment, funds transfer pricing, tax allocation, and average balance requirements.

**When to Select:** Queries about ROE or RORC calculation, the management reporting framework, intra-group charge treatment, funds transfer pricing processes, tax allocation rules, or average balance reporting requirements under SEC Regulation S-K.

**Query Tips:** Use terms like ''management reporting'', ''performance metrics'', ''ROE'', ''RORC'', ''intra-group'', ''funds transfer pricing'', ''tax allocation'', ''average balance reporting'', ''SEC Regulation S-K''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What are the major performance measurements for management reporting at RBC?","What are the processes for funds transfer pricing?","How are FTE numbers calculated?","How does RBC do rounding for management reporting purposes?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_memos',
    'APG Internal Accounting Memos',
    'Detailed technical analyses on complex accounting topics, written by RBC finance teams and approved by the Accounting Policy Group (APG), offering in-depth guidance on specific issues.',
    '**Content:** Formal internal accounting memos written by RBC finance teams and approved by the Accounting Policy Group (APG). Each memo documents detailed technical analyses of specific accounting issues, capturing the question raised, alternatives considered, reasoning applied, and the final decision/resolution.

**Tier/Priority:** SUPPLEMENTARY SOURCE (Formal Analysis) - APG-approved memos that supplement core policy with documented reasoning on specific accounting issues.

**Usage Guidance:** Contains formal documented decisions on complex or judgmental accounting matters. Use when you need the reasoning behind an accounting treatment, precedent for similar situations, or understanding of alternatives that were considered and rejected. These represent formally approved APG positions with full technical analysis.

**When to Select:** Questions seeking: documented rationale for accounting treatments, precedent on complex transactions, formal APG decisions on judgmental matters, analysis of why a particular approach was chosen, or historical decisions on accounting issues that required formal resolution.

**Query Tips:** Focus on application scenarios, specific conclusions, and industry/scenario terms.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What was APG''s conclusion on hedge accounting for cross-currency swaps?","How did APG resolve the accounting treatment for modified debt instruments?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_APG_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_pafe',
    'Planning Analytics for Excel (PAfE) User Guide',
    'Comprehensive user documentation for IBM''s Planning Analytics for Excel add-in, covering connection management, report creation, data manipulation, and formula usage for accessing TM1/EPM multidimensional financial data within Microsoft Excel.',
    '**Content:** Comprehensive user documentation for IBM''s Planning Analytics for Excel add-in, covering connection management, report creation, data manipulation, and formula usage for accessing TM1/EPM multidimensional financial data within Microsoft Excel.

**Tier/Priority:** DOMAIN EXPERT - Specialized guidance for Planning Analytics for Excel usage and support.

**Usage Guidance:** Use for operational instructions, feature explanations, and troubleshooting when working with PAfE/TM1/EPM data connections, reports, and Excel-based analytics.

**When to Select:** Queries referencing PAfE or Planning Analytics features, TM1/EPM connections, report types (Exploration/Quick/Dynamic/Custom), DBRW/TM1RPTVIEW/TM1RPTROW formulas, MDX queries, subset editor usage, sandbox features, or migration from Perspectives.

**Query Tips:** Use terms like ''PAfE'', ''Planning Analytics'', ''TM1'', ''EPM connection'', ''Dynamic Report'', ''Quick Report'', ''Exploration Report'', ''DBRW formula'', ''MDX query'', ''subset viewer'', ''cube data'', ''Perspectives migration'', ''websheet'', ''sandbox'', ''Set Editor''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What is a DBRA formula in PAfE?","How do I Recalculate a PAfE report?","How do I connect to PAfE?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_par',
    'Project Approval Request Guidance',
    'RBC''s internal policies and interpretations specifically related to Project Approval Requests (PAR), including workflow, processes, and compliance requirements.',
    '**Content:** RBC''s internal policies and interpretations for Project Approval Requests (PAR), including workflow, processes, and compliance requirements.

**Tier/Priority:** DOMAIN EXPERT - Specialized guidance for PAR governance and approvals.

**Usage Guidance:** Use for approval level rules, required documentation, workflow steps, and governance expectations for PAR submissions.

**When to Select:** Queries mentioning PAR approval thresholds, required meetings or governance steps, addendum requirements, workflow roles, or compliance obligations for project approvals.

**Query Tips:** Use RBC terms and reference PAR processes/workflows. Include terms like ''PAR'', ''project approval'', ''approval level'', ''addendum'', ''GE meeting'', ''GOCx meeting''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What would the approval level be if I had a Contract PAR greater than $200MM?","Who is responsible for the fulfillment of all monitoring, reporting, and follow up of the PAR?","According to RBC PAR when is an addendum required?","How do I know if my PAR requires a GE or GOCx meeting?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_pega_attestation',
    'PEGA Attestation',
    'RBC''s policies, procedures, and training materials for the PEGA-based General Ledger attestation process, including the Enterprise GL Attestation Policy, SOD requirements, BRAG methodology, and comprehensive user guidance for monthly balance sheet reconciliations and attestations.',
    '**Content:** RBC''s comprehensive framework for General Ledger attestation including the Enterprise GL Attestation Policy, PEGA system user guides, and FAQs. Covers monthly attestation requirements, Standards of Documentation (SOD) preparation, risk-based review processes, BRAG reconciliation assessments, aging analysis, and governance structures for ensuring balance sheet accuracy.

**Tier/Priority:** PRIMARY SOURCE - Authoritative RBC GL attestation policy and procedural guidance.

**Usage Guidance:** Use for definitive requirements on GL reconciliations, attestation statuses, SOD components, review frequencies, PEGA system navigation, and compliance with RBC''s financial control framework. Essential for understanding monthly attestation deadlines, ownership hierarchies, and escalation procedures.

**When to Select:** Queries about GL attestation requirements, SOD preparation standards, PEGA workflow processes, attestation status definitions (FR/RWE/RPI/NR), BRAG assessments, second-level review requirements, aging thresholds, clearings/transitory account treatment, or references to policies such as FIN-ACC-300-EN.

**Query Tips:** Use terms like ''GL attestation'', ''PEGA'', ''SOD'', ''reconciliation'', ''BRAG'', ''attestation status'', ''Fully Reconciled'', ''RWE'', ''Not Reconciled'', ''second level review'', ''aging'', ''clearings accounts'', ''transitory accounts'', ''attestation deadline'', ''Controller freeze''.',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What are the SOD preparation requirements for GL attestation?","What do the BRAG reconciliation assessment statuses mean?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_process_and_controls',
    'Internal Process and Controls Policies',
    'RBC''s policies on general ledger naming conventions, intra-group account procedures, internal controls over financial reporting (ICFR), and the Enterprise Internal Control Management Policy (ICMP) aligned with frameworks like COSO, SOX, and NI 52-109.',
    '**Content:** RBC''s policies on general ledger naming conventions, intra-group account procedures, internal controls over financial reporting (ICFR), and the Enterprise Internal Control Management Policy (ICMP) aligned with COSO, SOX, and NI 52-109 frameworks.

**Tier/Priority:** DOMAIN EXPERT - Specialized guidance for internal controls and process standards.

**Usage Guidance:** Use for control framework expectations, GL naming standards, intra-group reconciliation processes, and ICFR/ICMP requirements tied to regulatory frameworks.

**When to Select:** Queries about GL naming conventions, intra-group account handling, ICFR testing or documentation under SOX or NI 52-109, ICMP control activities, COSO alignment, or references to policies such as FIN-ACC-22 or FIN-ACC-201.

**Query Tips:** Use terms like ''GL naming convention'', ''intra-group accounts'', ''ICFR'', ''SOX'', ''NI 52-109'', ''ICMP'', ''COSO framework'', ''FIN-ACC-22'', ''FIN-ACC-201''.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What are the requirements of RBC''s internal controls policy?","What is the top down risk based approach in the ICFR policy?","What are the standardized abbreviations for the Chart of Accounts?","How does RBC apply its ICMP policy for Control Activities?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_reg_reporting_info',
    'Regulatory Reporting Return Templates',
    'Sample templates and specifications for all regulatory returns (M4, Z4, R2, I3, GR, GQ, T2, S1, E3, C3, C1, A4, A2, N3, J2, B2, and others), with each return''s template stored as an individual sheet-level document plus summary and checklist sheets.',
    '**Content:** Regulatory reporting return templates where each document represents a single return template sheet (for example M4, Z4, R2, I3 Consolidated, I3 CAD, I3 USD, QS STC 2025, GR, GQ, T2, S1 STC 2025, E3, C3, CS3 STC 2025, C1, A4, A2, AS STC 2025, E2, ES STC 2025, N3, J2, B2, and others). Includes a summary/checklist sheet listing all return codes and names, and a list of returns sheet with return-specific details.

**Tier/Priority:** DOMAIN EXPERT - Specialized regulatory reporting source for return template lookup, field definitions, and reporting structure reference.

**Usage Guidance:** Use this database to look up specific regulatory return templates, understand return structures and fields, compare returns, or find which returns cover specific reporting areas. Each sheet is processed as an independent document with cross-references to related sheets in the same workbook.

**When to Select:** Queries about regulatory return templates, return field definitions, return structures, reporting codes, or questions like "what does return M4 contain" or "which returns cover capital adequacy".

**Query Tips:** Include return codes (M4, Z4, R2, I3, etc.), return names, field names, reporting area terms (capital, liquidity, leverage, credit risk), and regulatory framework references (OSFI, Basel, STC).

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What fields are in the M4 regulatory return?","Which regulatory returns cover capital adequacy?","What is the structure of the I3 Consolidated return?","What returns are related to liquidity reporting?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    25,
    1,
    3,
    10,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    20,
    20,
    10,
    3,
    2,
    2,
    2
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_sab_99',
    'SAB 99 Memos',
    'Internal documents justifying the materiality assessment of financial statement errors, as guided by SEC Staff Accounting Bulletin No. 99. These memos are completed when financial statement errors exceed $120MM and include root cause analysis, control assessment, qualitative factor analysis, and remediation plans.',
    '**Content:** Internal SAB 99 memos — materiality assessment memos written under SEC Staff Accounting Bulletin No. 99 — stored as individual memo documents, typically one memo per financial statement error exceeding the $120MM threshold.

**Repository organization and source folder context:** The source repository organizes SAB 99 memos into fiscal-quarter subfolders (for example, `Q3 2024`, `Q4 2024`). That folder name is searchable source-folder metadata and is injected by the doc_refresh pipeline into retrieval artifacts. It identifies where the memo was stored in the repository, not necessarily the fiscal period or periods discussed in the memo itself. A memo filed under `Q2 2025` may analyze `Q1 2025`, multiple periods, or historical items. During ingestion and retrieval:

- `document_name` is prefixed with the folder context (for example, `[Q3 2024] Deposit Reconciliation Memo.pdf`)
- `document_summary` includes a "Source Folder Context" block naming the folder path
- `document_description` and `document_usage` are prefixed with the folder context
- full-document retrieval preserves that folder context alongside the memo content

Treat the folder context as meaningful searchable metadata for storage-location queries and memo-set scoping. Do NOT assume the folder label alone defines the memo''s covered period or substantive scope. There is no separate quarterly Excel summary file required for folder-level retrieval.

**Memo content:** Each SAB 99 memo contains the long-form narrative documentation for a single error, including detailed root cause analysis, detailed remediation plan text, qualitative factor analysis, control deficiency narrative, and any cited references or supporting memos. The generated metadata and excerpts may also surface short-form identifying fields useful for retrieval and enumeration, such as memo title, SAB ID when present, brief description, root cause (short form), status, review status, $ impact, segment, region, classifications, contacts, and references. The memo itself remains the source of truth.

**Primary vs. fallback guidance:** For storage-folder-scoped or category-scoped queries, first use source folder context to identify the relevant memo set (for example, memos stored under folder context `Q3 2024`). If the question asks only for identifying or short-form fields that appear in document metadata, summaries, descriptions, usage text, or excerpts, metadata-first retrieval may be sufficient. If the user is asking about the memo''s actual covered period or the error period discussed in the memo, do not assume the folder context alone proves that substantive period. For folder-scoped completeness requests such as "list every memo in Q2 2025", "summarize each Q2 2025 memo", "count the Q2 2025 memos", or "what is the root cause of each memo in the Q2 2025 folder", treat source folder context as a filter to apply during database-wide review of the catalog rather than as a shortcut that justifies researching only a selected subset of files. Fall back to full memo content when the query requires long-form narrative content that is not captured in the metadata or excerpts, such as the full remediation plan narrative, the detailed qualitative factor analysis section, or specific controls cited in the memo text.

**Terminology:** This database concerns two related but distinct concepts that must not be conflated.

- **SAB 99** stands for **SEC Staff Accounting Bulletin No. 99**, the SEC guidance under which these memos are prepared. The individual documents in this database are "SAB 99 memos" — internal materiality assessment memos written for financial statement errors that exceed the $120MM threshold. Either "SAB 99" or "SEC Staff Accounting Bulletin No. 99" is acceptable in research statements and responses; use whichever reads more naturally.

- **SUMs** (occasionally written as "SUM") is the internal abbreviation for the **Summary of Uncorrected Misstatements** process — the internal workflow for identifying and tracking uncorrected misstatements in the financial statements. SAB 99 memos document the materiality assessments of errors surfaced through the SUMs process. Users often refer loosely to the errors or their corresponding memos as "SUMs", so when a user asks about "SUMs" they are typically asking about the uncorrected misstatements documented in SAB 99 memos. Always expand the acronym to "Summary of Uncorrected Misstatements" in research statements.

- **Do not conflate SAB 99 and SUMs.** SAB 99 is the SEC regulatory framework and refers to the type of memo in this database. SUMs is the internal process that identifies uncorrected misstatements, which may then become the subject of SAB 99 memos. They are related but not synonyms — SAB 99 is the regulatory framework governing the memos, SUMs is the underlying workflow that generates the findings the memos assess.

**Tier/Priority:** DOMAIN EXPERT - Specialized documentation for SAB 99 materiality assessments.

**Usage Guidance:** The individual SAB 99 memo documents are the primary source. Use source folder context to scope storage-folder memo sets, then use document metadata/excerpts for structured or short-form questions and the full memo text for narrative questions. For content-period questions, rely on the memo content and extracted fields, not the folder label alone.

Prioritize memo metadata plus source folder context for queries about:
- Enumeration: "which SABs are stored under the Q4 2025 folder", "list the memos in the Q3 2024 folder"
- Root cause (short form): "what are the root causes of the memos in the Q4 2025 folder", "which memos in the Q3 2024 folder had EUDA-related root causes"
- Status / review: "which memos in the Q4 2025 folder are still open", "what is the review status of each memo in the Q3 2024 folder"
- $ impact: "which memos in the Q4 2025 folder exceeded $200MM", "what is the aggregate $ impact for the memos stored under Q3 2024"
- Classifications: "which memos in the Q4 2025 folder are historical vs current", "which memos in the Q3 2024 folder affected the P&L vs the balance sheet"
- Flags: "which memos in the Q4 2025 folder have a SOX deficiency flag", "which memos in the Q3 2024 folder require control assessment"
- Segment / region: "which memos in the Q4 2025 folder affected the Retail segment", "which memos in the Q3 2024 folder are from the US region"
- Brief description / summary: "give me a one-line summary of each memo in the Q4 2025 folder"
- Contacts / references: "who are the contacts for each memo in the Q3 2024 folder"

For queries phrased as "in the Q2 2025 folder", include every memo stored there even if the memo text references Q1 2025 or another period. Only treat quarter labels as substantive period filters when the query explicitly asks about the period discussed in the memo, not merely the folder where the memo is stored.

Fall back to full memo content when the query needs long-form narrative content that is NOT captured in the metadata or excerpts, such as:
- The full remediation plan narrative ("describe the detailed remediation steps for memo X")
- The detailed qualitative factor analysis section ("walk me through the qualitative factor analysis for each Q3 memo")
- Specific controls or memos cited in the memo text ("what internal controls did the deposit reconciliation memo cite")
- Paragraph-level explanations or rationales beyond the short-form summary

Important: do NOT confuse short-form metadata with long-form narrative. Metadata or excerpts may capture a short categorical root cause (for example, "EUDA spreadsheet error in manual reconciliation"), but the memo body contains the multi-paragraph detailed root cause analysis. A query asking "what is the root cause of each Q4 memo" may be satisfied from metadata/excerpts if that short-form field is present. A query asking "walk me through the detailed root cause analysis section for each Q4 memo" requires the full memo text.

**When to Select:** Queries about SAB 99 memos, materiality evaluations under SEC Staff Accounting Bulletin No. 99, the Summary of Uncorrected Misstatements (SUMs) process, the $120MM materiality threshold, storage-folder-scoped memo sets identified by source folder context, per-memo metadata (root cause, status, $ impact, segment, region, classifications, SOX deficiency flag, control assessment flag, contacts, references, internal/external, historical/current, retrospective/prospective, BS/P&L/SCF/disclosure area, annual-only flag), per-memo narrative analysis (full root cause analysis, detailed remediation plans, qualitative factor analysis, control deficiency narrative), quarterly aggregations, theme analysis across multiple memos, or documentation of immaterial versus material misstatements.

**Query Tips:** Use precise terminology: "SAB 99" or "SEC Staff Accounting Bulletin No. 99" refers to the regulatory framework and the memo type; "Summary of Uncorrected Misstatements" (preferred over the "SUMs" acronym) refers to the internal process that identifies misstatements. Distinguish between storage-folder queries ("memos in the Q3 2024 folder", "stored under Q4 2025", "source folder context") and substantive period queries ("memos about Q3 2024", "errors from Q4 2025"). Relevant search terms include: "SAB 99", "SAB 99 memo", "SEC Staff Accounting Bulletin No. 99", "materiality assessment", "Summary of Uncorrected Misstatements", "SUMs process", "uncorrected misstatement", "SAB ID", "memo status", "review status", "$ impact", "error amount", "segment", "region", "internal/external", "historical/current", "retrospective/prospective", "balance sheet impact", "P&L impact", "cash flow statement impact", "disclosure impact", "annual-only disclosure", "SOX deficiency", "SOX deficiency flag", "control assessment", "control assessment flag", "contacts", "references", "financial statement error", "$120MM threshold", "quantitative materiality", "qualitative factors", "root cause", "root cause analysis", "control deficiency", "remediation plan", "error correction", "restatement assessment", "immaterial misstatement", "intentional misstatement", "earnings management", "quarterly SAB 99 memos", "Q3 2024", "Q4 2025", "source folder context", "stored under", "filed under", "quarter folder", "per-folder SAB 99 listing".

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What is the most common root cause?","How many errors impacted Deposits?","How many have EUDA related issues?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_SAB99_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_sox',
    'Internal SOX Controls',
    'RBC''s SOX controls inventory, where each document represents an individual control with associated attributes such as control objective, process area, systems, and testing context.',
    '**Content:** Internal SOX controls repository where each document represents a single control record (for example control ID, control statement, process area, system references, and related control metadata).

**Tier/Priority:** DOMAIN EXPERT - Specialized internal controls source for SOX control lookup and analysis.

**Usage Guidance:** Use this database to find controls by process, system, keyword, or control characteristics. Best for questions that need sets of controls matching criteria (for example process ownership, system association, or text mentions).

**When to Select:** Queries such as: all controls under a specific process area, controls mentioning a specific term, controls involving a specific system, or control discovery/filtering questions.

**Query Tips:** Include process names, system names, control IDs, and targeted terms (for example ''SOX'', ''access review'', ''change management'', ''SAP'', ''revenue'', ''financial reporting'').

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["What are all the SOX controls under the Procure to Pay process?","What are all the controls that mention access reviews?","What controls involve the SAP system?","Which SOX controls relate to change management?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_FINANCE_ASSIST','G_CxONE_CL_DEV_Admin']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    20,
    40,
    1,
    5,
    10,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    20,
    20,
    10,
    6,
    3,
    2,
    2
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO iris_database_registry (db_source, db_name, db_summary, db_description, search_modes, catalog_config, semantic_config, metadata_config, sample_questions, enabled, ad_groups, query_type, content_type, use_when, display_order, is_internal, batch_size, max_selected_files, top_chunks_in_catalog_selection, top_chunks_in_metadata_research, page_threshold_for_full_content, enable_db_wide_deep_research, metadata_context_fields, max_parallel_files, max_chunks_per_file, max_pages_for_full_context, max_primary_section_page_count, max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages)
VALUES (
    'internal_wiki',
    'APG Wiki',
    'RBC-specific accounting compilations and guidance for unique transactions, providing detailed interpretations and applications of accounting standards tailored to RBC''s business scenarios.',
    '**Content:** APG Wiki containing Q&A-style knowledge base entries - questions received by the Accounting Policy Group and their researched resolutions. Provides RBC-specific accounting compilations, detailed interpretations, and application guidance for unique transactions tailored to RBC''s business scenarios. Covers a broad range of accounting questions from simple to moderately complex.

**Tier/Priority:** SUPPLEMENTARY SOURCE (Q&A Knowledge Base) - APG Q&A entries that supplement core policy with practical answers to accounting questions.

**Usage Guidance:** Contains practical answers to accounting questions that APG has addressed over time. Use when looking for how APG has resolved specific accounting questions. Provides concise Q&A-style resolutions rather than lengthy formal documentation. Especially useful for specific transaction types or application examples.

**When to Select:** Questions about: how RBC/APG has handled specific accounting scenarios, practical resolutions to accounting questions, APG guidance on day-to-day accounting issues, or answers to common accounting questions.

**Query Tips:** Focus on application scenarios, specific conclusions, and industry/scenario terms.

**Query Type:** semantic search',
    ARRAY['catalog','semantic']::text[],
    NULL,
    NULL,
    NULL,
    '["How does RBC account for government grants under IFRS?","What is APG''s guidance on capitalizing internally developed software?"]'::jsonb,
    true,
    ARRAY['APP_0MF0_MAVEN_APG_IRIS']::text[],
    'semantic search',
    'general content',
    NULL,
    100,
    true,
    10,
    10,
    1,
    3,
    150,
    true,
    ARRAY['document_summary','document_description','document_usage']::text[],
    10,
    20,
    150,
    10,
    5,
    4,
    5
)
ON CONFLICT (db_source) DO UPDATE SET
    db_name = EXCLUDED.db_name,
    db_summary = EXCLUDED.db_summary,
    db_description = EXCLUDED.db_description,
    search_modes = EXCLUDED.search_modes,
    catalog_config = EXCLUDED.catalog_config,
    semantic_config = EXCLUDED.semantic_config,
    metadata_config = EXCLUDED.metadata_config,
    sample_questions = EXCLUDED.sample_questions,
    enabled = EXCLUDED.enabled,
    ad_groups = EXCLUDED.ad_groups,
    query_type = EXCLUDED.query_type,
    content_type = EXCLUDED.content_type,
    use_when = EXCLUDED.use_when,
    display_order = EXCLUDED.display_order,
    is_internal = EXCLUDED.is_internal,
    batch_size = EXCLUDED.batch_size,
    max_selected_files = EXCLUDED.max_selected_files,
    top_chunks_in_catalog_selection = EXCLUDED.top_chunks_in_catalog_selection,
    top_chunks_in_metadata_research = EXCLUDED.top_chunks_in_metadata_research,
    page_threshold_for_full_content = EXCLUDED.page_threshold_for_full_content,
    enable_db_wide_deep_research = EXCLUDED.enable_db_wide_deep_research,
    metadata_context_fields = EXCLUDED.metadata_context_fields,
    max_parallel_files = EXCLUDED.max_parallel_files,
    max_chunks_per_file = EXCLUDED.max_chunks_per_file,
    max_pages_for_full_context = EXCLUDED.max_pages_for_full_context,
    max_primary_section_page_count = EXCLUDED.max_primary_section_page_count,
    max_subsection_page_count = EXCLUDED.max_subsection_page_count,
    max_neighbour_chunks = EXCLUDED.max_neighbour_chunks,
    max_gap_fill_pages = EXCLUDED.max_gap_fill_pages,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Inserted/Updated 19 database registry entries
