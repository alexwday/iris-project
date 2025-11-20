# Quick Start Guide - Testing on Work Computer

## Prerequisites
- Git repo pulled
- Python virtual environment
- Database credentials configured

## Setup Steps

### 1. Pull Latest Code
```bash
cd /path/to/iris-project
git pull origin main
```

### 2. Activate Virtual Environment
```bash
source venv/bin/activate
# or on Windows: venv\Scripts\activate
```

### 3. Configure Database Credentials
Edit `.env` file with your actual database credentials:
```bash
# Update these lines in .env:
VECTOR_POSTGRES_DB_HOST=your_actual_db_host
VECTOR_POSTGRES_DB_USERNAME=your_actual_username  
VECTOR_POSTGRES_DB_PASSWORD=your_actual_password
VECTOR_POSTGRES_DB_PORT=5432  # or your actual port
```

### 4. Test Database Connection
```bash
python -c "from services.src.initial_setup.db_config import connect_to_db; conn = connect_to_db(); print('✓ Database connected!' if conn else '✗ Connection failed'); conn.close() if conn else None"
```

Expected output: `✓ Database connected!`

### 5. Test Compatibility Layer
```bash
python -c "
from config.config import Config
from classes.exceptions.pii_exception import PIIException
from m9db.database import SessionLocal
print('✓ All compatibility modules imported successfully')
print('✓ Server ready to start')
"
```

### 6. Start FastAPI Server
```bash
python start_server.py
```

Expected output:
```
🚀 Starting IRIS FastAPI Server...
📱 Chat Interface: Open chat_interface.html in your browser
📋 API Docs: http://localhost:8000/docs
🔍 Health Check: http://localhost:8000/health
```

### 7. Test Health Endpoint
Open browser or run:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","environment":"rbc","version":"1.0.0"}
```

### 8. Test API Documentation
Open in browser:
```
http://localhost:8000/docs
```

You should see interactive API documentation with:
- POST /chat
- GET /health
- GET /

### 9. Test Chat Endpoint (Optional)
Using the /docs interface, or:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "test"}],
    "stream": false
  }'
```

## Troubleshooting

### Database Connection Fails
- **SSL Error**: Database requires SSL. This is expected (IT's code enforces `sslmode=require`)
- **Host not found**: Check `VECTOR_POSTGRES_DB_HOST` in `.env`
- **Auth failed**: Check username/password in `.env`

### Import Errors
- Run: `pip install -e ".[dev]"` to ensure all dependencies installed
- Verify you're in the virtual environment

### Server Won't Start
1. Check no other process is using port 8000:
   ```bash
   lsof -i :8000  # MacOS/Linux
   netstat -ano | findstr :8000  # Windows
   ```
2. Check logs for specific error
3. Verify all compatibility modules import (step 5 above)

## What's Different from Before

The compatibility layer handles IT's infrastructure dependencies:
- ✅ Config wrapper (`config/config.py`)
- ✅ PII exception stub (`classes/exceptions/`)
- ✅ Reporting database mock (`m9db/`)
- ✅ APP_ID bug workaround (builtins patch)

**You don't need to modify any `services/src` files.**

## Known Limitations (See KNOWN_ISSUES.md)
- Authentication is DISABLED (no token validation)
- PII detection is DISABLED (no scanning)  
- Reporting database is MOCKED (logs only, no persistence)
- All databases accessible (no AD group restrictions)

These are intentional for local development.

---

*Last Updated: 2025-11-20*
