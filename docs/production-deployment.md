# IRIS Production Deployment Guide

This guide provides comprehensive instructions for deploying the IRIS system in production environments, covering setup, configuration, validation, and monitoring procedures.

## Overview

The IRIS production deployment process encompasses environment setup, configuration management, dependency installation, service configuration, and comprehensive testing procedures. This guide ensures reliable deployment across RBC production environments while maintaining security, performance, and monitoring standards. The deployment includes the FastAPI backend service, database connectivity, authentication systems, and web-based chat interface components.

## Key Components

* **FastAPI Backend**: Main API service handling chat requests and agent orchestration
* **Database Infrastructure**: PostgreSQL connections for data storage and process monitoring
* **Authentication Systems**: OAuth integration for secure API access in RBC environments
* **SSL/TLS Configuration**: Certificate management for secure communications
* **Web Chat Interface**: Browser-based user interface for system interaction
* **Monitoring and Logging**: Comprehensive operational monitoring and log management

## Core Functions/Classes

### Repository Setup and Environment Configuration

#### Purpose
Establishes the foundational project structure and Python environment required for IRIS deployment.

#### Key Steps
* Repository cloning and file organization
* Python virtual environment creation and activation
* Dependency installation and verification
* Environment variable configuration and validation

### Configuration Management

#### Purpose
Manages environment-specific configuration including database credentials, API endpoints, and authentication settings.

#### Key Components
* Environment file creation and editing (.env configuration)
* RBC-specific endpoint and credential configuration
* SSL certificate setup and validation
* OAuth client configuration for secure API access

### Service Deployment and Testing

#### Purpose
Deploys the IRIS FastAPI service and validates all system components through comprehensive testing procedures.

#### Key Components
* FastAPI server deployment with uvicorn/gunicorn
* Health check validation and API endpoint testing
* Chat interface deployment and functionality verification
* Systemd service configuration for production environments

## Configuration

Production deployment configuration managed through environment variables:

* **Environment Detection**: `IRIS_ENVIRONMENT=rbc` for production RBC deployment
* **API Endpoints**: RBC-specific base URLs for LLM API access
* **Database Configuration**: PostgreSQL connection parameters and credentials
* **Authentication Settings**: OAuth client ID, secret, and endpoint configuration
* **SSL Configuration**: Certificate file paths and validation settings
* **Model Configuration**: LLM model names, costs, and capability mappings
* **Monitoring Settings**: Process monitoring, logging levels, and usage tracking

## Usage Examples

### Basic Deployment Commands
```bash
# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with RBC-specific values

# Start production server
uvicorn iris.src.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production Service Configuration
```bash
# Create systemd service
sudo systemctl enable iris-api
sudo systemctl start iris-api
sudo systemctl status iris-api
```

### Validation Testing
```bash
# Test health endpoint
curl -X GET "http://localhost:8000/health"

# Test chat functionality
python3 test_api.py
```

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
from iris.src.initial_setup.ssl_setup import setup_ssl
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
from iris.src.initial_setup.ssl_setup import setup_ssl
from iris.src.initial_setup.oauth_setup import setup_oauth
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
from iris.src.initial_setup.ssl_setup import setup_ssl
from iris.src.initial_setup.oauth_setup import setup_oauth
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

The test suite includes:

#### Health Check Test
```bash
🔍 Testing Health Endpoint...
Status Code: 200
Response: {
  "status": "healthy",
  "environment": "rbc",
  "version": "1.0.0"
}
✅ Health check passed!
```

#### Chat Endpoint Tests
- **Simple Chat**: Tests non-streaming responses
- **Streaming Chat**: Tests real-time streaming responses  
- **Multi-turn Conversation**: Tests conversation history handling
- **FastAPI Test Client**: Internal testing via FastAPI test client

#### cURL Examples
The test script also provides ready-to-use cURL commands for manual testing.

### 5.4 Launch Chat Interface

Once API tests pass, launch the web chat interface:

```bash
# Open the chat interface in your browser
open chat_interface.html
# Or on Linux: xdg-open chat_interface.html
# Or on Windows: start chat_interface.html
```

#### Chat Interface Features
- 🎯 **Clean Design**: OpenAI-inspired interface
- 🌊 **Real-time Streaming**: Live responses as they're generated
- 📝 **Markdown Support**: Rich text rendering for responses
- 📱 **Mobile Responsive**: Works on all devices
- 🔍 **Connection Status**: Shows API connectivity status
- ⌨️ **Keyboard Shortcuts**: Enter to send, Shift+Enter for new line

#### Chat Interface Configuration
The chat interface connects to `http://localhost:8000` by default.

To change the API URL, edit `chat_interface.html`:

```javascript
this.apiUrl = 'http://your-api-server:8000';
```

### 5.5 Complete Testing Workflow

Follow this sequence to verify everything works:

1. **Start Server**: API server running on port 8000
2. **Run Tests**: `python3 test_api.py` - all tests pass ✅
3. **Launch Chat**: Open `chat_interface.html` in browser
4. **Test Conversation**: Ask IRIS about financial policies
5. **Verify Streaming**: Confirm responses stream in real-time
6. **Check Markdown**: Verify rich text formatting works

## Step 6: System Verification

### Run System Checks
Test the system with a simple query to verify streaming response:

```bash
python -c "
from iris.src.chat_model.model import model
conversation = {'messages': [{'role': 'user', 'content': 'Test query'}]}
print('Testing IRIS system...')
for chunk in model(conversation):
    print(chunk, end='')
print('\nSystem check complete.')
"
```

This will run through the complete agent pipeline and display the streaming response in the terminal.

## Step 7: Launch Web Interface

### Start the Server (if not already running)
```bash
python start_server.py
```

The web interface will be available at `http://localhost:8000`

### Test the Interface
1. Open your browser and navigate to `http://localhost:8000`
2. Test the system with various queries to ensure proper functionality
3. Verify that streaming responses work correctly in the web interface

### Access API Documentation
Open your browser to:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

The system is now ready for use. The web interface provides an easy way to interact with the IRIS system and test its capabilities.