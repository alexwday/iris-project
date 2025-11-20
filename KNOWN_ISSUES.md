# Known Issues in IT-Provided `services/src`

We cannot modify files under `services/src`, so the following bugs remain in
IT's codebase. Keep these limitations in mind when running locally.

## Critical Bugs

1. **Undefined `APP_ID` constant** – `services/src/reporting/reporting.py:52`
   references `APP_ID`, but the symbol is never defined. We shim a global value
   via `config/config.py`, yet IT still needs to fix their source.
2. **`HTTPException` returned instead of raised** –
   `services/src/auth/auth_security.py:45` and `:89` return an `HTTPException`
   object. Later code assumes a `requests.Response` and calls `.json()`, which
   would crash if auth middleware were enabled.
3. **Invalid JSON indexing in PII handler** –
   `services/src/auth/auth_security.py:150` and `:156` index `[0]` into the
   response body, assuming it is a list. Many REST services return dicts, so the
   current logic would raise `TypeError`.

## Workarounds

- Avoid calling `Reporting.add_user_feedback_to_reporting_db()` until IT fixes
  the undefined `APP_ID` usage.
- Keep the FastAPI app unauthenticated in local development (do not wire
  `validate_token` from `auth_security.py`).
- Keep PII detection disabled locally; enabling it requires IT to fix the JSON
  handling bug and provide real service endpoints.

## SSL Requirement

IT's `construct_dsn()` in `services/src/initial_setup/db_config.py` hardcodes
`sslmode=require`. If your local Postgres instance does not support SSL, the
app will not connect. Options:

1. Enable SSL support on your local database.
2. Run against an environment that already exposes SSL-enabled hosts.
3. (Not recommended) fork IT's source and relax the SSL requirement, which
   would violate the "do not modify `services/src`" constraint.

Use the following snippet to verify SSL locally once credentials are available:

```bash
python - <<'PY'
from services.src.initial_setup.db_config import connect_to_db

conn = connect_to_db()
if conn:
    print("✓ Database connection successful (SSL working)")
    conn.close()
else:
    print("✗ Database connection failed. Verify SSL support and credentials.")
PY
```

If the connection fails, confirm that your `.env` contains valid host/user
settings and that the target database accepts SSL connections.
