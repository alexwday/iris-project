# Bug Fix Implementation Guide

## Bug #1: APG Catalog Search Not Respecting Filtered Databases

### Description
The APG catalog similarity search returns documents from ALL databases in the system, even when the user only has access to a filtered subset. This causes the planner to receive document recommendations from databases the user cannot access.

### Code Changes

#### Change 1.1: Add Database Filter Parameter
**File:** `services/src/chat_model/model.py`  
**Lines:** 120-122

**ORIGINAL:**
```python
def search_apg_catalog_by_embedding(
    research_statement: str, token: Optional[str] = None, top_k: int = 5
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
```

**UPDATED:**
```python
def search_apg_catalog_by_embedding(
    research_statement: str, token: Optional[str] = None, top_k: int = 5,
    available_databases: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
```

**Reason:** Add optional parameter to receive the filtered list of databases.

---

#### Change 1.2: Filter SQL Query by Available Databases
**File:** `services/src/chat_model/model.py`  
**Lines:** 160-172

**ORIGINAL:**
```python
        # Perform vector search against apg_catalog table
        sql = """
            SELECT
                document_source,
                document_description,
                document_type,
                document_name,
                1 - (document_usage_embedding <=> %s::vector) AS similarity_score
            FROM apg_catalog
            WHERE document_usage_embedding IS NOT NULL
            ORDER BY similarity_score DESC
            LIMIT %s;
        """
```

**UPDATED:**
```python
        # Perform vector search against apg_catalog table
        if available_databases:
            # Build the IN clause for filtering by document_source
            db_sources = list(available_databases.keys())
            placeholders = ', '.join(['%s'] * len(db_sources))
            sql = f"""
                SELECT
                    document_source,
                    document_description,
                    document_type,
                    document_name,
                    1 - (document_usage_embedding <=> %s::vector) AS similarity_score
                FROM apg_catalog
                WHERE document_usage_embedding IS NOT NULL
                    AND document_source IN ({placeholders})
                ORDER BY similarity_score DESC
                LIMIT %s;
            """
            params = [query_embedding] + db_sources + [top_k]
        else:
            # No filtering - original query
            sql = """
                SELECT
                    document_source,
                    document_description,
                    document_type,
                    document_name,
                    1 - (document_usage_embedding <=> %s::vector) AS similarity_score
                FROM apg_catalog
                WHERE document_usage_embedding IS NOT NULL
                ORDER BY similarity_score DESC
                LIMIT %s;
            """
            params = [query_embedding, top_k]
```

**Reason:** Add WHERE clause to filter results by document_source when available_databases is provided.

---

#### Change 1.3: Use Dynamic Parameters
**File:** `services/src/chat_model/model.py`  
**Line:** 174

**ORIGINAL:**
```python
        cursor.execute(sql, [query_embedding, top_k])
```

**UPDATED:**
```python
        cursor.execute(sql, params)
```

**Reason:** Use the dynamic params list that includes database filters when applicable.

---

#### Change 1.4: Pass Available Databases to Function
**File:** `services/src/chat_model/model.py`  
**Lines:** 985-987

**ORIGINAL:**
```python
                apg_catalog_results, apg_catalog_usage = search_apg_catalog_by_embedding(
                    research_statement, token, top_k=5
                )
```

**UPDATED:**
```python
                apg_catalog_results, apg_catalog_usage = search_apg_catalog_by_embedding(
                    research_statement, token, top_k=5, available_databases=available_databases
                )
```

**Reason:** Pass the filtered available_databases to ensure search only returns accessible documents.

---

## Bug #2: Hardcoded Database Names in Agent Prompts

### Description
The planner agent prompt contains hardcoded database names in examples (e.g., `internal_accounting`, `internal_independence`). These examples may reference databases that users don't have access to, causing confusion.

### Code Changes

#### Change 2.1: Remove Hardcoded Database Names from Example 7
**File:** `services/src/agents/agent_planner/planner_prompt.yaml`  
**Lines:** 185-187

**ORIGINAL:**
```yaml
  Example 7 - Specific file query with APG context: "Tell me about the IFRS 16 lease accounting guide"
  APG Context shows: Document "IFRS 16 Lease Accounting Implementation Guide" with 0.92 similarity from internal_accounting database
  → Target: 1 database (internal_accounting) - APG catalog shows clear single document match
```

**UPDATED:**
```yaml
  Example 7 - Specific file query with APG context: "Tell me about the IFRS 16 lease accounting guide"
  APG Context shows: Document "IFRS 16 Lease Accounting Implementation Guide" with 0.92 similarity from an accounting policy database
  → Target: 1 database (the source database from APG catalog) - APG catalog shows clear single document match
```

**Reason:** Replace specific database name with generic description to avoid referencing inaccessible databases.

---

#### Change 2.2: Remove Hardcoded Database Names from Example 8
**File:** `services/src/agents/agent_planner/planner_prompt.yaml`  
**Lines:** 189-191

**ORIGINAL:**
```yaml
  Example 8 - Multiple relevant documents: "What are the independence requirements for audit partners?"
  APG Context shows: Multiple documents with 0.7+ similarity across internal_independence and internal_policy databases
  → Target: 2 databases (internal_independence, internal_policy) - APG catalog shows relevant content in both
```

**UPDATED:**
```yaml
  Example 8 - Multiple relevant documents: "What are the independence requirements for audit partners?"
  APG Context shows: Multiple documents with 0.7+ similarity across independence and policy databases
  → Target: 2 databases (the source databases from APG catalog) - APG catalog shows relevant content in both
```

**Reason:** Use generic descriptions instead of specific database names for universal applicability.

---

## Testing Checklist

1. **Bug #1 Testing:**
   - Test with users having limited database access (e.g., only 2-3 databases)
   - Verify APG catalog search returns only documents from accessible databases
   - Confirm backward compatibility when available_databases is None

2. **Bug #2 Testing:**
   - Verify planner agent still correctly interprets examples with generic descriptions
   - Confirm no other agent prompts contain hardcoded database names

## Important Notes

- All changes are backward compatible with optional parameters
- The APG catalog search function is in `model.py`, NOT `semantic_search/subagent.py`
- Only the planner prompt YAML contains hardcoded database names