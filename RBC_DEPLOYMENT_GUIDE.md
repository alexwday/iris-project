# IRIS FastAPI Deployment Guide for RBC Environment

This guide walks you through deploying the IRIS FastAPI application in your RBC environment after cloning from GitHub.

## Prerequisites

- Access to RBC development/production environment
- Python 3.8+ installed
- Git access to clone the repository (or project zip file)
- Network access to required APIs and databases
- VS Code or text editor for configuration
- SSL certificate file (`rbc-ca-bundle.cer`) - included in project files

## Step 1: Clone and Setup Repository

### 1.1 Get the Project Files
```bash
# Option A: Clone the repository
git clone <your-repo-url> iris-project
cd iris-project

# Option B: If you received a zip file
unzip iris-project.zip
cd iris-project
```

### 1.2 Create Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate     # On Windows
```

### 1.3 Install Dependencies
```bash
# Install the package and dependencies
pip install -e .

# Verify installation
pip list | grep fastapi
pip list | grep uvicorn
```

## Step 2: Environment Configuration

### 2.1 Create Environment File
```bash
# Copy the example environment file
cp .env.example .env

# Edit the environment file with VS Code (recommended)
code .env

# Alternative: Use default Mac text editor
# open -e .env
```

### 2.2 Configure Environment Variables
Edit your `.env` file with RBC-specific values:

```bash
# IRIS Project Environment Configuration (RBC Environment)

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
IRIS_ENVIRONMENT=rbc

# ==========================================
# API ENDPOINTS
# ==========================================
IRIS_RBC_BASE_URL=https://perf-apigw-int.saifg.rbc.com/JLCO/llm-control-stack/v1

# ==========================================
# DATABASE CONFIGURATION
# ==========================================
IRIS_DB_HOST=<your-rbc-db-host>
IRIS_DB_PORT=5432
IRIS_DB_NAME=maven-finance
IRIS_DB_USER=<your-rbc-db-user>
IRIS_DB_PASSWORD=<your-rbc-db-password>

# ==========================================
# OAUTH CONFIGURATION
# ==========================================
IRIS_OAUTH_URL=<your-rbc-oauth-url>
IRIS_OAUTH_CLIENT_ID=<your-rbc-client-id>
IRIS_OAUTH_CLIENT_SECRET=<your-rbc-client-secret>

# ==========================================
# SSL CONFIGURATION
# ==========================================
IRIS_SSL_CERT_FILENAME=rbc-ca-bundle.cer
IRIS_SSL_CHECK_CERT_EXPIRY=true
IRIS_SSL_EXPIRY_WARNING_DAYS=30

# ==========================================
# REQUEST CONFIGURATION
# ==========================================
IRIS_REQUEST_TIMEOUT=180
IRIS_MAX_RETRY_ATTEMPTS=3
IRIS_RETRY_DELAY_SECONDS=2

# ==========================================
# MODEL CONFIGURATION
# ==========================================
IRIS_MODEL_SMALL=gpt-4o-mini-2024-07-18
IRIS_MODEL_LARGE=gpt-4o-2024-05-13
IRIS_MODEL_EMBEDDING=text-embedding-3-large

IRIS_MODEL_SMALL_PROMPT_COST=0.00016238
IRIS_MODEL_SMALL_COMPLETION_COST=0.00065175
IRIS_MODEL_LARGE_PROMPT_COST=0.00064952
IRIS_MODEL_LARGE_COMPLETION_COST=0.00260748
IRIS_MODEL_EMBEDDING_PROMPT_COST=0.0001
IRIS_MODEL_EMBEDDING_COMPLETION_COST=0.0001

# ==========================================
# CONVERSATION CONFIGURATION
# ==========================================
IRIS_MAX_HISTORY_LENGTH=10
IRIS_INCLUDE_SYSTEM_MESSAGES=false

# ==========================================
# LOGGING CONFIGURATION
# ==========================================
IRIS_LOG_LEVEL=INFO
IRIS_TOKEN_PREVIEW_LENGTH=7
IRIS_SHOW_USAGE_SUMMARY=true

# ==========================================
# PROCESS MONITORING
# ==========================================
IRIS_PROCESS_MONITOR_MODEL_NAME=iris
```

### 2.3 Verify SSL Certificate
```bash
# Verify the SSL certificate is included in the project
ls -la iris/src/initial_setup/rbc-ca-bundle.cer

# The certificate should already be included in your project files
```

## Step 3: Validate Configuration

**Important**: These tests must be run in order as OAuth requires SSL to be set up first.

### 3.1 Test Configuration Loading
```bash
python3 -c "
from iris.src.initial_setup.env_config import config
print('Environment:', config.ENVIRONMENT)
print('Database Host:', config.DB_HOST)
print('OAuth URL:', config.OAUTH_URL)
print('SSL Certificate:', config.SSL_CERT_FILENAME)
if config.validate():
    print('✅ Configuration is valid!')
else:
    print('❌ Configuration validation failed!')
"
```

### 3.2 Test Database Connection
```bash
python3 -c "
from iris.src.initial_setup.db_config import connect_to_db
conn = connect_to_db()
if conn:
    print('✅ Database connection successful!')
    conn.close()
else:
    print('❌ Database connection failed!')
"
```

### 3.3 Test SSL Setup
```bash
python3 -c "
from iris.src.initial_setup.ssl import setup_ssl
import os
try:
    cert_path = setup_ssl()
    print(f'✅ SSL setup successful: {cert_path}')
    print(f'SSL_CERT_FILE environment variable: {os.environ.get(\"SSL_CERT_FILE\", \"Not set\")}')
    print(f'REQUESTS_CA_BUNDLE environment variable: {os.environ.get(\"REQUESTS_CA_BUNDLE\", \"Not set\")}')
except Exception as e:
    print(f'❌ SSL setup failed: {e}')
"
```

### 3.4 Test OAuth (with SSL)
```bash
python3 -c "
from iris.src.initial_setup.ssl import setup_ssl
from iris.src.initial_setup.oauth import setup_oauth
try:
    # Setup SSL first (required for OAuth)
    ssl_path = setup_ssl()
    print(f'✅ SSL setup successful: {ssl_path}')
    
    # Now test OAuth
    token = setup_oauth()
    print(f'✅ OAuth successful (token length: {len(token)})')
except Exception as e:
    print(f'❌ OAuth test failed: {e}')
    print('Note: OAuth requires SSL certificate and valid RBC credentials')
"
```

### 3.5 Comprehensive Integration Test
```bash
# Test all components together in the correct order
python3 -c "
from iris.src.initial_setup.env_config import config
from iris.src.initial_setup.ssl import setup_ssl
from iris.src.initial_setup.oauth import setup_oauth
from iris.src.initial_setup.db_config import connect_to_db

print('=== IRIS Configuration Test ===')
print(f'Environment: {config.ENVIRONMENT}')
print()

try:
    # Step 1: Validate configuration
    print('1. Testing configuration...')
    if config.validate():
        print('✅ Configuration is valid')
    else:
        print('❌ Configuration validation failed')
        exit(1)
    
    # Step 2: Setup SSL
    print('\\n2. Setting up SSL...')
    ssl_path = setup_ssl()
    print(f'✅ SSL configured: {ssl_path}')
    
    # Step 3: Test OAuth
    print('\\n3. Testing OAuth...')
    token = setup_oauth()
    print(f'✅ OAuth successful (token length: {len(token)})')
    
    # Step 4: Test database
    print('\\n4. Testing database connection...')
    conn = connect_to_db()
    if conn:
        print('✅ Database connection successful')
        conn.close()
    else:
        print('❌ Database connection failed')
        
    print('\\n=== All tests passed! IRIS is ready to deploy. ===')
    
except Exception as e:
    print(f'\\n❌ Test failed: {e}')
    print('\\nPlease check your .env file and ensure all RBC values are correct.')
    exit(1)
"
```

## Step 4: Start the API Server

### 4.1 Development Mode (with auto-reload)
```bash
# Start the development server
uvicorn iris.src.api:app --host 0.0.0.0 --port 8000 --reload

# The API will be available at:
# http://localhost:8000
# API docs at: http://localhost:8000/docs
```

### 4.2 Production Mode
```bash
# Start production server with multiple workers
uvicorn iris.src.api:app --host 0.0.0.0 --port 8000 --workers 4

# Or using Gunicorn for better production performance
gunicorn iris.src.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4.3 Background Service (systemd)
Create a systemd service file `/etc/systemd/system/iris-api.service`:

```ini
[Unit]
Description=IRIS FastAPI Application
After=network.target

[Service]
Type=exec
User=<your-user>
Group=<your-group>
WorkingDirectory=/path/to/iris-project
Environment=PATH=/path/to/iris-project/venv/bin
ExecStart=/path/to/iris-project/venv/bin/uvicorn iris.src.api:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable iris-api
sudo systemctl start iris-api
sudo systemctl status iris-api
```

## Step 5: Test the Deployment

### 5.1 Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "rbc",
  "version": "1.0.0"
}
```

### 5.2 Test Chat Endpoint
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What are the latest tax regulations?"}
    ],
    "stream": false
  }'
```

### 5.3 Run Comprehensive Tests
```bash
# Run the test script
python3 test_api.py
```

### 5.4 Access API Documentation
Open your browser to:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Step 6: Production Considerations

### 6.1 Security
- Ensure `.env` file has restricted permissions: `chmod 600 .env`
- Consider using a secrets management system instead of `.env` files
- Set up proper firewall rules for the API port
- Consider using HTTPS with proper SSL certificates

### 6.2 Monitoring
- Set up log rotation for application logs
- Monitor API response times and error rates
- Set up health check monitoring
- Monitor database connection pool usage

### 6.3 Performance
- Tune the number of workers based on your server specs
- Consider using a reverse proxy (nginx) in front of uvicorn
- Set up database connection pooling if needed
- Monitor memory usage and adjust as necessary

### 6.4 Backup and Recovery
- Ensure your `.env` file is backed up securely
- Document your deployment configuration
- Test recovery procedures

## Troubleshooting

### Common Issues:

1. **Import Errors**:
   ```bash
   # Make sure you're in the right directory and virtual environment
   cd iris-project
   source venv/bin/activate
   pip install -e .
   ```

2. **SSL Certificate Issues**:
   ```bash
   # Check certificate path and permissions
   ls -la iris/src/initial_setup/rbc-ca-bundle.cer
   # Ensure the file is readable
   ```

3. **Database Connection Issues**:
   - Verify database host, port, and credentials in `.env`
   - Check network connectivity to database
   - Verify database user permissions

4. **OAuth Issues**:
   - Verify OAuth URL, client ID, and client secret
   - Check network connectivity to OAuth provider
   - Verify client credentials are valid

5. **Port Already in Use**:
   ```bash
   # Find what's using port 8000
   lsof -i :8000
   # Kill the process or use a different port
   uvicorn iris.src.api:app --host 0.0.0.0 --port 8001
   ```

### Logs:
- Application logs are written to stderr by default
- For production, consider redirecting to files:
  ```bash
  uvicorn iris.src.api:app --host 0.0.0.0 --port 8000 > /var/log/iris/api.log 2>&1
  ```

## Support

If you encounter issues:
1. Check the application logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test individual components (database, OAuth, SSL) separately
4. Consult the API documentation at `/docs` endpoint

## Next Steps

Once deployed successfully:
- Set up monitoring and alerting
- Configure log aggregation
- Set up automated deployment pipelines
- Document operational procedures
- Train team members on API usage