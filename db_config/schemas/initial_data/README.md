# IRIS Initial Data

Generated: 2026-01-19 10:36:44

## Contents

| File | Description | Import Method |
|------|-------------|---------------|
| `iris_prompts.sql` | 8 IRIS prompts (SQL INSERT) | `psql -f iris_prompts.sql` |
| `iris_prompts.csv` | 8 IRIS prompts (CSV) | pgAdmin Import or `\copy` |
| `iris_database_registry.sql` | 16 database configs (SQL INSERT) | `psql -f iris_database_registry.sql` |
| `iris_database_registry.csv` | 16 database configs (CSV) | pgAdmin Import or `\copy` |

## Recommended Import Order

1. Create tables first using schema files in parent directory
2. Import `iris_database_registry.sql` (registry must exist before documents)
3. Import `iris_prompts.sql`

## SQL Files (Recommended)

The `.sql` files use `INSERT ... ON CONFLICT DO UPDATE` syntax, making them:
- Safe to re-run multiple times
- Self-contained with all escaping handled
- Wrapped in transactions for atomicity

```bash
# Import both tables
psql -h <host> -p <port> -d <database> -f iris_database_registry.sql
psql -h <host> -p <port> -d <database> -f iris_prompts.sql
```

## CSV Files

For GUI tools like pgAdmin or DBeaver:
1. Right-click table → Import/Export
2. Select CSV file
3. Ensure column mapping matches

For psql `\copy`:
```bash
\copy iris_database_registry FROM 'iris_database_registry.csv' WITH (FORMAT csv, HEADER true)
\copy prompts(model,layer,name,version,description,system_prompt,user_prompt,tool_definition) FROM 'iris_prompts.csv' WITH (FORMAT csv, HEADER true)
```

## Notes

- Prompts include only `model='iris'` entries (doc_refresh prompts excluded)
- JSONB columns are properly escaped in all formats
- Array columns use PostgreSQL array literal format `{val1,val2}`
