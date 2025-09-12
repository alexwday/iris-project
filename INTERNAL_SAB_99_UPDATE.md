# Internal SAB 99 Database Addition

## Overview
Adding internal_sab_99 database for SAB 99 materiality assessment memos - documents that justify materiality assessments for financial statement errors >$120MM.

---

## File Updates

### 1. Database Router - `/services/src/agents/database_subagents/database_router.py`

**Location**: Line 63, inside INTERNAL_DATABASES dictionary

**Full Context**:
```python
INTERNAL_DATABASES = {
    "internal_par": "internal_par",
    "internal_esg": "internal_esg",
    "internal_capm": "internal_capm",
    "internal_aio": "internal_aio",
    "internal_cheatsheets": "internal_cheatsheets",
    "internal_ext_reporting_and_disclosure": "internal_ext_reporting_and_disclosure",
    "internal_global_finance_standards": "internal_global_finance_standards",
    "internal_management_reporting": "internal_management_reporting",
    "internal_memos": "internal_memos",
    "internal_process_and_controls": "internal_process_and_controls",
    "internal_wiki": "internal_wiki",
    "internal_sab_99": "internal_sab_99",  # <-- ADD THIS LINE
}
```

**Just the New Code**:
```python
    "internal_sab_99": "internal_sab_99",
```

**Why**: Routes queries to catalog_search subagent for processing SAB 99 documents.

---

### 2. Database Statement - `/services/src/global_prompts/database_statement.py`

**Location**: Line 92, after internal_process_and_controls entry in AVAILABLE_DATABASES

**Full Context**:
```python
    "internal_process_and_controls": {
        "name": "Internal Process and Controls Policies",
        "description": "RBC's policies on general ledger naming conventions, intra-group account procedures, internal controls over financial reporting (ICFR), and the Enterprise Internal Control Management Policy (ICMP) aligned with frameworks like COSO, SOX, and NI 52-109.",
        "query_type": "semantic search",  # Assuming semantic search
        "content_type": "policies and procedures / internal controls / compliance",
        "use_when": "Tier 1 (Domain Specific): Questions about GL naming, intra-group account reconciliation, ICFR requirements (SOX/NI 52-109), or the overall ICMP framework (COSO). **Strategy:** Query for specific policy numbers (FIN-ACC-22, FIN-ACC-201), control frameworks, or process details. **Query:** Use terms like 'GL naming convention', 'intra-group accounts', 'ICFR', 'SOX', 'NI 52-109', 'ICMP', 'COSO framework', 'FIN-ACC-22', 'FIN-ACC-201'.",
    },
    "internal_sab_99": {  # <-- ADD THIS ENTIRE BLOCK
        "name": "SAB 99 Materiality Assessment Memos",
        "description": "Internal documents justifying the materiality assessment of financial statement errors, as guided by SEC Staff Accounting Bulletin No. 99. These memos are completed when financial statement errors exceed $120MM and include root cause analysis, control assessment, qualitative factor analysis, and remediation plans.",
        "query_type": "semantic search",
        "content_type": "materiality assessment memos / error analysis / remediation documentation",
        "use_when": "Tier 1 (Domain Specific): Questions about materiality assessments for financial statement errors, SAB 99 compliance, errors exceeding $120MM threshold, qualitative materiality factors, or error remediation. **Strategy:** Query when statement relates to materiality determinations, quantitative/qualitative assessment factors, error evaluation, control deficiencies related to material errors, or corrective action plans. **Query:** Use terms like 'SAB 99', 'materiality assessment', 'financial statement error', '$120MM threshold', 'quantitative materiality', 'qualitative factors', 'root cause analysis', 'control deficiency', 'remediation plan', 'error correction', 'restatement assessment', 'immaterial misstatement', 'intentional misstatement', 'earnings management'.",
    },
```

**Just the New Code**:
```python
    "internal_sab_99": {
        "name": "SAB 99 Materiality Assessment Memos",
        "description": "Internal documents justifying the materiality assessment of financial statement errors, as guided by SEC Staff Accounting Bulletin No. 99. These memos are completed when financial statement errors exceed $120MM and include root cause analysis, control assessment, qualitative factor analysis, and remediation plans.",
        "query_type": "semantic search",
        "content_type": "materiality assessment memos / error analysis / remediation documentation",
        "use_when": "Tier 1 (Domain Specific): Questions about materiality assessments for financial statement errors, SAB 99 compliance, errors exceeding $120MM threshold, qualitative materiality factors, or error remediation. **Strategy:** Query when statement relates to materiality determinations, quantitative/qualitative assessment factors, error evaluation, control deficiencies related to material errors, or corrective action plans. **Query:** Use terms like 'SAB 99', 'materiality assessment', 'financial statement error', '$120MM threshold', 'quantitative materiality', 'qualitative factors', 'root cause analysis', 'control deficiency', 'remediation plan', 'error correction', 'restatement assessment', 'immaterial misstatement', 'intentional misstatement', 'earnings management'.",
    },
```

**Why**: Provides metadata for agents to understand when and how to query this database.

---

### 3. UI Interface - `/chat_interface.html`

**Location**: Line 573-576, between Process & Controls and Wiki checkboxes

**Full Context**:
```html
                            <div class="checkbox-item">
                                <input type="checkbox" id="internal_process_and_controls" value="internal_process_and_controls" checked>
                                <label for="internal_process_and_controls">Process & Controls</label>
                            </div>
                            <div class="checkbox-item">  <!-- ADD THESE 4 LINES -->
                                <input type="checkbox" id="internal_sab_99" value="internal_sab_99" checked>
                                <label for="internal_sab_99">SAB 99 Memos</label>
                            </div>
                            <div class="checkbox-item">
                                <input type="checkbox" id="internal_wiki" value="internal_wiki" checked>
                                <label for="internal_wiki">Wiki</label>
                            </div>
```

**Just the New Code**:
```html
                            <div class="checkbox-item">
                                <input type="checkbox" id="internal_sab_99" value="internal_sab_99" checked>
                                <label for="internal_sab_99">SAB 99 Memos</label>
                            </div>
```

**Why**: Adds UI checkbox so users can include/exclude SAB 99 database in searches.

---

### 4. UI Count Update - `/chat_interface.html`

**Location**: Line 525

**Full Context**:
```html
                    <div class="selected-count" id="selectedCount">All databases (14)</div>
```

**Change**: Updated from `(13)` to `(14)`

**Why**: Reflects correct total database count in initial display.

---

## Database Population Requirements

After these code changes, you need to:

1. **Insert catalog records** in `apg_catalog` table:
   - Set `document_source = 'internal_sab_99'`
   - Include document_name, document_description, file_link
   - Generate document_description_embedding for similarity search

2. **Insert content** in `apg_content` table:
   - Link to catalog entries via foreign key
   - Include actual SAB 99 memo content

---

## Summary

- **What**: Added internal_sab_99 database support
- **Where**: Router mapping, database config, UI checkbox  
- **Result**: System can now query SAB 99 materiality assessment memos via catalog_search subagent