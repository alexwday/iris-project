# IRIS Project - Logging Security Analysis Checklist

**Analysis Date:** May 30, 2025  
**Context:** Internal enterprise deployment with controlled access  
**Purpose:** Complete security audit of ALL logging statements  

## Progress Summary
- **Total Files:** 89
- **Completed:** 31
- **Files with Logging:** 20
- **Total Logging Statements:** 265
- **Security Issues:** 0

---

## File Analysis Checklist

### CORE APPLICATION FILES

#### [x] iris/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/api.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 25: `import logging`
  - Line 36: `logger = logging.getLogger(__name__)`
  - Line 80: `logger.error("Failed to import chat model. Make sure to add the async wrapper to model.py")`
  - Line 89: `logger.error("Failed to import streaming chat model")`
  - Line 155: `logger.error(f"Streaming error: {str(e)}", exc_info=True)`
  - Line 170: `logger.info(f"Received chat request with {len(request.messages)} messages, stream={request.stream}")`
  - Line 180: `logger.info("Returning streaming response")`
  - Line 191: `logger.info("Returning complete response")`
  - Line 195: `logger.info("Chat request processed successfully")`
  - Line 199: `logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)`
  - Line 220: `logger.error(f"Health check failed: {str(e)}")`
  - Line 244: `logger.info("Starting IRIS Chat API...")`
  - Line 251: `logger.info(f"IRIS Chat API started successfully in {config.ENVIRONMENT} environment")`
  - Line 254: `logger.error(f"Startup failed: {str(e)}")`
  - Line 263: `logger.info("Shutting down IRIS Chat API...")`
- **Security Assessment:** SAFE - Only logs operational details and error messages; no sensitive data exposed
- **Notes:** Critical for API monitoring, startup diagnostics, request handling, and error debugging.

#### [x] setup.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard package setup file with no logging.

#### [x] start_server.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 14: `print("🚀 Starting IRIS FastAPI Server...")`
  - Line 15: `print("📱 Chat Interface: Open chat_interface.html in your browser")`
  - Line 16: `print("📋 API Docs: http://localhost:8001/docs")`
  - Line 17: `print("🔍 Health Check: http://localhost:8001/health")`
  - Line 18: `print("\n⚠️  Make sure your environment variables are set:")`
  - Line 19: `print("   - IRIS_DB_HOST")`
  - Line 20: `print("   - IRIS_OAUTH_TOKEN (or relevant auth)")`
  - Line 21: `print("\n🛑 Press Ctrl+C to stop the server\n")`
- **Security Assessment:** SAFE - Only prints operational instructions and environment variable names, no sensitive data exposed
- **Notes:** Useful for developers to start the server and view interface URLs and required environment variables.

#### [x] test_api.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 25: `print("🔍 Testing Health Endpoint...")`
  - Line 30: `print(f"Status Code: {response.status_code}")`
  - Line 31: `print(f"Response: {json.dumps(response.json(), indent=2)}")`
  - Line 34: `print("✅ Health check passed!")`
  - Line 36: `print("❌ Health check failed!")`
  - Line 39: `print(f"❌ Health check error: {e}")`
  - Line 41: `print("-" * 50)`
  - Line 45: `print("💬 Testing Chat Endpoint...")`
  - Line 56: `print(f"Sending request: {json.dumps(test_conversation, indent=2)}")`
  - Line 67: `print(f"Status Code: {response.status_code}")`
  - Line 68: `print(f"Response Time: {(end_time - start_time):.2f} seconds")`
  - Line 72: `print("✅ Chat request successful!")`
  - Line 73: `print(f"Response: {result.get('response', 'No response')[:200]}...")`
  - Line 74: `print(f"Agent Used: {result.get('agent_used', 'Unknown')}")`
  - Line 75: `print(f"Processing Time: {result.get('processing_time_ms', 0)}ms")`
  - Line 76: `print(f"Run UUID: {result.get('run_uuid', 'None')}")`
  - Line 79: `print(f"Token Usage: {result['token_usage']}")`
  - Line 81: `print("❌ Chat request failed!")`
  - Line 82: `print(f"Error: {response.text}")`
  - Line 85: `print(f"❌ Chat request error: {e}")`
  - Line 87: `print("-" * 50)`
  - Line 91: `print("🌊 Testing Streaming Chat Endpoint...")`
  - Line 102: `print(f"Sending streaming request: {json.dumps(test_conversation, indent=2)}")`
  - Line 113: `print(f"Status Code: {response.status_code}")`
  - Line 116: `print("✅ Streaming request successful!")`
  - Line 117: `print("📡 Streaming response chunks:")`
  - Line 118: `print("-" * 40)`
  - Line 123: `print(chunk, end='', flush=True)`
  - Line 126: `print(f"\n\n⏱️ Streaming completed in {(end_time - start_time):.2f} seconds")`
  - Line 128: `print("❌ Streaming request failed!")`
  - Line 129: `print(f"Error: {response.text}")`
  - Line 132: `print(f"❌ Streaming request error: {e}")`
  - Line 134: `print("-" * 50)`
  - Line 138: `print("🔄 Testing Multi-turn Conversation...")`
  - Line 159: `print("✅ Multi-turn conversation successful!")`
  - Line 160: `print(f"Response: {result.get('response', 'No response')[:200]}...")`
  - Line 162: `print("❌ Multi-turn conversation failed!")`
  - Line 163: `print(f"Error: {response.text}")`
  - Line 166: `print(f"❌ Multi-turn conversation error: {e}")`
  - Line 168: `print("-" * 50)`
  - Line 172: `print("📋 cURL Examples:")`
  - Line 173: `print("\n1. Health Check:")`
  - Line 174: `print(f"curl -X GET \"{API_BASE_URL}/health\"")`
  - Line 176: `print("\n2. Simple Chat:")`
  - Line 177: `print(f\"\"\"curl -X POST \"{API_BASE_URL}/chat\" \\`)`
  - Line 186: `print("\n3. Streaming Chat:")`
  - Line 187: `print(f\"\"\"curl -X POST \"{API_BASE_URL}/chat\" \\`)`
  - Line 196: `print("\n4. Multi-turn Chat:")`
  - Line 197: `print(f\"\"\"curl -X POST \"{API_BASE_URL}/chat\" \\`)`
  - Line 208: `print("-" * 50)`
  - Line 212: `print("🧪 Testing with FastAPI Test Client...")`
  - Line 222: `print(f"Health check status: {response.status_code}")`
  - Line 231: `print(f"Chat test status: {response.status_code}")`
  - Line 234: `print("✅ FastAPI test client works!")`
  - Line 236: `print(f"❌ FastAPI test client error: {response.text}")`
  - Line 239: `print("⚠️  FastAPI test client not available (API not importable or dependencies missing)")`
  - Line 241: `print(f"❌ FastAPI test client error: {e}")`
  - Line 243: `print("-" * 50)`
  - Line 247: `print("🚀 IRIS API Testing Suite")`
  - Line 248: `print("=" * 50)`
  - Line 254: `print(f"✅ API server is running at {API_BASE_URL}")`
  - Line 256: `print(f"⚠️  API server responded with status {response.status_code}")`
  - Line 258: `print(f"❌ Cannot connect to API server at {API_BASE_URL}")`
  - Line 259: `print("Make sure to start the server first:")`
  - Line 260: `print("uvicorn iris.src.api:app --host 0.0.0.0 --port 8000")`
  - Line 263: `print("=" * 50)`
  - Line 273: `print("🏁 Testing completed!")`
- **Security Assessment:** SAFE - Only prints test outcomes and example commands; no sensitive data exposed
- **Notes:** Provides developers with test results and sample usage for health, chat, streaming, multi-turn, cURL, and FastAPI client tests.

### CHAT MODEL

#### [x] iris/src/chat_model/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/chat_model/model.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 24: `import logging`
  - Line 63: `logging.getLogger().warning(`
  - Line 100: `logger = logging.getLogger(__name__)`
  - Line 120: `logger.info(`
  - Line 135: `logger.info(f"Thread completed query for database: {db_name}")`
  - Line 159: `logger.error(`
  - Line 192: `logger = logging.getLogger(__name__)`
  - Line 193: `logger.info("Setting up process monitoring")`
  - Line 199: `logger.info(f"Process monitor enabled after enable_monitoring call: {process_monitor.enabled}")`
  - Line 202: `logger.info(f"Generated run UUID: {run_uuid_val}")`
  - Line 205: `logger.info(f"Set run UUID. Current run UUID: {process_monitor.run_uuid}")`
  - Line 208: `logger.info(f"Started monitoring. Start time: {process_monitor.start_time}")`
  - Line 239: `logger.info("Initializing model setup (sync core)...")`
  - Line 252: `logger.warning("No conversation provided.")`
  - Line 259: `logger.info(f"Conversation processed: {len(processed_conversation['messages'])} messages")`
  - Line 261: `logger.warning(f"Invalid conversation format: {str(e)}")`
  - Line 265: `logger.error(f"Error processing conversation: {str(e)}")`
  - Line 270: `logger.warning("Processed conversation is empty.")`
  - Line 278: `logger.info("Getting routing decision...")`
  - Line 289: `logger.info("Using direct response path based on routing decision")`
  - Line 303: `logger.warning("No usage details received from direct_response stream.")`
  - Line 308: `logger.info("Using research path based on routing decision")`
  - Line 310: `logger.info("Clarifying research needs...")`
  - Line 321: `logger.info("Essential context needed, returning context questions")`
  - Line 329: `logger.error("Scope missing from clarifier decision.")`
  - Line 333: `logger.info(f"Research scope determined: {scope}")`
  - Line 335: `logger.info("Creating database selection plan...")`
  - Line 339: `logger.info(f"Database selection plan created with {len(selected_databases)} databases: {selected_databases}")`
  - Line 358: `logger.info("Displayed database selection plan.")`
  - Line 361: `logger.warning("Database selection plan is empty, skipping database search.")`
  - Line 363: `logger.info(f"Starting {len(selected_databases)} database queries concurrently...")`
  - Line 377: `logger.info(f"Submitted {len(futures)} queries to thread pool.")`
  - Line 381: `logger.error(f"Error retrieving result from future: {exc}", exc_info=True)`
  - Line 409: `logger.info(f"Collected {len(file_links)} file links from {db_name}")`
  - Line 412: `logger.debug(f"No file links returned from {db_name}")`
  - Line 417: `logger.info("All concurrent database queries completed processing.")`
  - Line 429: `logger.info("Calling generate_streaming_summary")`
  - Line 438: `logger.warning("No usage details received from summary stream.")`
  - Line 440: `logger.error(f"Error during summarization: {summary_exc}", exc_info=True)`
  - Line 448: `logger.info(f"Checking file links: all_file_links has {len(all_file_links)} items")`
  - Line 455: `logger.debug(f"Processing link: {file_link} for document: {document_name}")`
  - Line 466: `logger.info(f"Yielding HTML link: {html_link.strip()}")`
  - Line 470: `logger.warning("No file links collected from any database")`
  - Line 474: `logger.info(f"Completed process for scope '{scope}'")`
  - Line 502: `logger.info(f"Completed process for scope '{scope}', returning {total_metadata_items} items internally.")`
  - Line 507: `logger.error(f"Unknown routing function: {routing_decision['function_name']}")`
  - Line 516: `logger.error(error_msg, exc_info=True)`
  - Line 523: `logger.warning("Process monitoring end_time was not set before finally block, setting now.")`
  - Line 524: `logger.info(f"Attempting to log process monitor data to database for run {process_monitor.run_uuid}")`
  - Line 526: `logger.info(f"Total stages to log: {len(process_monitor.stages)}")`
  - Line 530: `logger.info(f"Using environment: {config.ENVIRONMENT}")`
  - Line 541: `logger.info("Database connection established")`
  - Line 547: `logger.info(f"process_monitor_logs table exists: {table_exists}")`
  - Line 549: `logger.info("Process monitor data logged to database.")`
  - Line 551: `logger.error(f"Failed to get database connection for logging process monitor data. Environment: {config.ENVIRONMENT}")`
  - Line 555: `logger.error(f"Failed to log process monitor data to database: {log_exc}", exc_info=True)`
  - Line 560: `logger.error(f"Error during DB rollback: {rb_exc}")`
  - Line 581: `logger.error(f"Error closing DB connection: {close_exc}")`
  - Line 598: `logger.warning("Could not calculate legacy debug token totals.")`
  - Line 599: `logger = logging.getLogger(__name__)`
  - Line 604: `logger.debug("Entering synchronous model wrapper.")`
  - Line 607: `logger.debug("Synchronous generator completed.")`
  - Line 634: `logger.error(error_msg, exc_info=True)`
  - Line 635: `logger = logging.getLogger(__name__)`
  - Line 691: `logger.info(f"Processing async request with {len(conversation)} messages")`
- **Security Assessment:** SAFE - Logs operational monitoring, debug and status information only; no sensitive data exposed
- **Notes:** Provides detailed internal monitoring, status updates, and error diagnostics for the async core and sync wrapper, valuable for debugging and tracing execution without exposing secrets.

### GLOBAL PROMPTS

#### [x] iris/src/global_prompts/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard package initialization file with no logging.

#### [x] iris/src/global_prompts/database_statement.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 9: `import logging`
  - Line 13: `logger = logging.getLogger(__name__)`
  - Line 204: `logger.debug("Database statement module initialized")`
- **Security Assessment:** SAFE - Only logs module initialization; no sensitive data exposed
- **Notes:** Provides module load indication and logger setup for database statement utility.

#### [x] iris/src/global_prompts/fiscal_statement.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 8: `import logging`
  - Line 14: `logger = logging.getLogger(__name__)`
  - Line 140: `logger.error(f"Error generating fiscal statement: {str(e)}")`
- **Security Assessment:** SAFE - Only logs error messages for fallback; no sensitive data exposed
- **Notes:** Configures logger for module and logs errors during fiscal statement generation for debugging.

#### [x] iris/src/global_prompts/project_statement.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 8: `import logging`
  - Line 12: `logger = logging.getLogger(__name__)`
  - Line 54: `logger.error(f"Error generating project statement: {str(e)}")`
- **Security Assessment:** SAFE - Only logs error messages on exception; no sensitive data exposed
- **Notes:** Configures module logger and logs errors during project statement generation for debugging.

#### [x] iris/src/global_prompts/restrictions_statement.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 9: `import logging`
  - Line 13: `logger = logging.getLogger(__name__)`
  - Line 56: `logger.error(f"Error generating compliance restrictions: {str(e)}")`
  - Line 88: `logger.error(f"Error generating quality guidelines: {str(e)}")`
  - Line 131: `logger.error(f"Error generating confidence signaling guidelines: {str(e)}")`
  - Line 158: `logger.error(f"Error generating combined restrictions statement: {str(e)}")`
- **Security Assessment:** SAFE - Only logs error messages on exception; no sensitive data exposed
- **Notes:** Provides error logging for fallback in compliance, quality, confidence, and combined restrictions functions.

### INITIAL SETUP

#### [x] iris/src/initial_setup/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard initial setup module importing DB and logging configuration functions; no logging here.

#### [x] iris/src/initial_setup/conversation_setup.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 17: `import logging`
  - Line 28: `logger = logging.getLogger(__name__)`
  - Line 63: `logger.warning(f"Skipping message missing required fields: {msg}")`
  - Line 79: `logger.info(f"Processed conversation: {msg_count} messages filtered to {recent_count} messages")`
  - Line 88: `logger.error(error_msg)`
- **Security Assessment:** SAFE - Logs processing metrics, warnings, and errors; no sensitive data exposed
- **Notes:** Provides visibility into conversation filtering and error handling for debugging and monitoring.

#### [x] iris/src/initial_setup/db_config.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 18: `logger = logging.getLogger(__name__)`
  - Line 25: `logger.debug("Getting database parameters from environment configuration")`
  - Line 36: `logger.info(f"Connecting to database with parameters: host={db_params['host']}, port={db_params['port']}, dbname={db_params['dbname']}, user={db_params['user']}")`
  - Line 39: `logger.info("Database connection successful")`
  - Line 42: `logger.error(f"Error connecting to database: {e}", exc_info=True)`
- **Security Assessment:** SAFE - Logs connection attempts, parameters (excluding credentials), successes, and errors without exposing passwords
- **Notes:** Provides visibility into database connectivity and operational errors for debugging in enterprise environment.

#### [x] iris/src/initial_setup/env_config.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 24: `import logging`
  - Line 35: `logger = logging.getLogger(__name__)`
  - Line 131: `logger.error(f"Missing required environment variables: {', '.join(missing_fields)}")`
  - Line 134: `logger.info("All required configuration values are set")`
  - Line 207: `logger.info(f"Environment configuration loaded for: {config.ENVIRONMENT}")`
  - Line 208: `logger.debug(f"API Base URL: {config.RBC_BASE_URL}")`
  - Line 209: `logger.debug(f"Database Host: {config.DB_HOST}")`
  - Line 210: `logger.debug(f"OAuth URL: {config.OAUTH_URL}")`
- **Security Assessment:** SAFE - Logs configuration load info and validation errors without exposing secrets
- **Notes:** Provides centralized config logging and validation feedback.

#### [x] iris/src/initial_setup/logging_config.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 19: `import logging`
  - Line 42: `root_logger = logging.getLogger()`
  - Line 58: `logging.info("Logging system initialized")`
- **Security Assessment:** SAFE - Logs initialization of central logging system; no sensitive data
- **Notes:** Establishes uniform logging configuration at startup.

#### [x] iris/src/initial_setup/oauth_setup.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 18: `import logging`
  - Line 36: `logger = logging.getLogger(__name__)`
  - Line 53: `logger.info(f"OAuth setup starting with settings from: {__file__}")`
  - Line 58: `logger.error(error_msg)`
  - Line 61: `logger.info(f"OAuth URL endpoint: {OAUTH_URL}")`
  - Line 63: `logger.info(f"Using client ID: {CLIENT_ID[:4]}****")`
  - Line 77: `logger.info(f"Beginning OAuth token request with max {MAX_RETRY_ATTEMPTS} attempts")`
  - Line 84: `logger.info(f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Requesting OAuth token")`
  - Line 92: `logger.info(f"Received response in {attempt_time:.2f} seconds")`
  - Line 109: `logger.info(f"Successfully obtained OAuth token: {token_preview}")`
  - Line 113: `logger.info(f"Total OAuth process completed in {total_time_seconds:.2f} seconds after {attempts} attempt(s)")`
  - Line 121: `logger.warning(f"OAuth token request attempt {attempts} failed after {attempt_time:.2f} seconds: {str(e)}")`
  - Line 126: `logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")`
  - Line 132: `logger.error(f"Failed to obtain OAuth token after {attempts} attempts and {total_time_seconds:.2f} seconds")`
- **Security Assessment:** SAFE - Logs operational monitoring and errors with partial token preview; client secret obscured to first chars
- **Notes:** Provides detailed logging for OAuth token acquisition flow including retries and timing, critical for debugging authentication without exposing full credentials.

#### [x] iris/src/initial_setup/process_monitor_setup.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 27: `logger = logging.getLogger(__name__)`
  - Line 96: `logger.warning(f"Error extracting decision details for stage '{stage_name}': {e}")`
  - Line 104: `logging.getLogger(__name__).info(f"ProcessMonitor initialized with enabled={enabled}")`
  - Line 109: `logger.debug(f"Process monitor run UUID set: {run_uuid}")`
  - Line 114: `logger.debug("Process monitoring started")`
  - Line 118: `logger.debug("Process monitoring ended")`
  - Line 122: `logger.info(f"Logging process monitor data for run_uuid: {self.run_uuid}")`
  - Line 123: `logger.info(f"Number of stages to log: {len(self.stages)}")`
  - Line 124: `logger.info(f"Stage '{stage_name}' - start: {stage.start_time}, end: {stage.end_time}, status: {stage.status}")`
  - Line 133: `logger.error(f"Error preparing stage '{stage.name}' data for DB logging: {e}", exc_info=True)`
  - Line 143: `logger.info(f"Inserting record with stage_name={record[2]}")`
  - Line 145: `logger.error(f"Error inserting record for stage {record[2]}: {record_err}")`
  - Line 147: `logger.info(f"Successfully inserted record for stage {record[2]}")`
  - Line 152: `logger.info(f"Successfully logged {len(records_to_insert)} stages for run_uuid: {self.run_uuid}")`
  - Line 157: `logger.error(f"Database error during process monitor logging for run_uuid {self.run_uuid}: {db_err}", exc_info=True)`
  - Line 165: `logger.debug(f"Started process stage: {stage_name}")`
  - Line 171: `logger.debug(f"Ended process stage: {stage_name} with status: {status}")`
  - Line 176: `logger.warning(f"Attempted to add LLM details to non-existent or disabled stage: {stage_name}")`
  - Line 188: `logger.info(f"Enable_monitoring called with enabled={enabled}. Current state: {process_monitor.enabled}")`
  - Line 191: `logger.info(f"Creating new ProcessMonitor instance with enabled={enabled}")`
  - Line 195: `logger.info("Process monitoring enabled by state change.")`
  - Line 201: `logger.info("Process monitoring explicitly enabled.")`
  - Line 205: `logger.info("Process monitoring was already enabled.")`
  - Line 209: `logger.info("Process monitoring was already disabled.")`
  - Line 212: `logger.info(f"Final process_monitor state: enabled={process_monitor.enabled}")`
- **Security Assessment:** SAFE - Provides detailed internal monitoring logs including warnings, info, and errors; no sensitive data exposed
- **Notes:** Tracks execution stages, timings, database logging, and control-flow for process monitoring.

#### [x] iris/src/initial_setup/ssl_setup.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 21: `import logging`
  - Line 65: `logger.warning("Cryptography library not available, skipping certificate expiry check")`
  - Line 71: `logger.info(f"Checking certificate expiry for: {cert_path}")`
  - Line 88: `logger.error(f"Certificate expired on {expiry_date.strftime('%Y-%m-%d')}")`
  - Line 94: `logger.warning(f"Certificate will expire in {days_until_expiry} days (on {expiry_date.strftime('%Y-%m-%d')})")`
  - Line 100: `logger.info(f"Certificate valid until {expiry_date.strftime('%Y-%m-%d')}")`
  - Line 104: `logger.error(f"Error checking certificate expiry: {str(e)}")`
  - Line 126: `logger.info(f"SSL setup starting with settings from: {__file__}")`
  - Line 127: `logger.info(f"Using certificate directory: {SSL_CERT_DIR}")`
  - Line 128: `logger.info(f"Using certificate filename: {SSL_CERT_FILENAME}")`
  - Line 129: `logger.info(f"Full certificate path: {SSL_CERT_PATH}")`
  - Line 137: `logger.info(f"Certificate file exists at {SSL_CERT_PATH}")`
  - Line 142: `logger.warning(f"Certificate expiry check failed: {str(e)}")`
  - Line 146: `logger.info("Certificate expiry check disabled")`
  - Line 152: `logger.info(f"SSL environment configured successfully. Certificate path: {SSL_CERT_PATH}")`
- **Security Assessment:** SAFE - Logs certificate validation, expiry warnings, and setup flow; no sensitive data exposed
- **Notes:** Ensures SSL certificate integrity and environment configuration, providing operational insights without exposing secrets.

### LLM CONNECTORS

#### [x] iris/src/llm_connectors/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard package initialization file with no logging.

#### [x] iris/src/llm_connectors/rbc_openai.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 20: `import logging`
  - Line 36: `logger = logging.getLogger(__name__)`
  - Line 134: `logger.info(f"Using OAuth token: {token_preview}")`
  - Line 135: `logger.info(f"Using API base URL: {api_base_url}")`
  - Line 153: `logger.info(f"Making {'streaming' if is_streaming else 'non-streaming'} call to model: {model_name}{' with tools' if has_tools else ''} in RBC environment")`
  - Line 163: `logger.info(f"Attempt {attempts}/{MAX_RETRY_ATTEMPTS}: Sending request to OpenAI API")`
  - Line 174: `logger.info(f"API call parameters (excluding message/input content): {safe_params}")`
  - Line 189: `logger.info(f"Calling embeddings endpoint with params: {embedding_params}")`
  - Line 194: `logger.info("Received embedding response.")`
  - Line 200: `logger.info(f"Received {'initial stream chunk' if is_streaming else 'response'} for attempt {attempts} in {attempt_response_time_ms} ms")`
  - Line 229: `logger.info(f"Non-streaming usage: {usage_details}")`
  - Line 241: `logger.warning(f"Call attempt {attempts} failed after {attempt_time_secs:.2f} seconds: {str(e)}")`
  - Line 246: `logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")`
  - Line 250: `logger.error(f"Failed to complete call after {attempts} attempts")`
  - Line 296: `logger.info(f"Stream finished. Final usage: {usage_details}")`
  - Line 300: `logger.warning("Stream finished, but no usage data found in the final chunk. Cannot report usage.")`
- **Security Assessment:** SAFE - Logs operational flow, error and retry information with partial token preview; sensitive values (full token) not exposed
- **Notes:** Provides robust visibility into API calls, retries, performance metrics, and streaming usage without leaking credentials.

### AGENTS

#### [x] iris/src/agents/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard package initialization file with no logging.

### AGENT CLARIFIER

#### [x] iris/src/agents/agent_clarifier/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/agent_clarifier/clarifier.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 19: `import logging`
  - Line 32: `logger = logging.getLogger(__name__)`
  - Line 75: `logger.info(f"Clarifying research needs using model: {MODEL_NAME}")`
  - Line 76: `logger.info("Initiating Clarifier API call")`
  - Line 103: `logger.warning(f"Expected tool call but received content: {content_returned[:100]}...")`
  - Line 144: `logger.warning(f"Scope '{scope}' provided but action is '{action}'. Scope will be ignored.")`
  - Line 150: `logger.info(f"Clarifier decision: {action}")`
  - Line 152: `logger.info(f"Determined scope: {scope}")`
  - Line 153: `logger.info(f"Is continuation: {is_continuation}")`
  - Line 167: `logger.error(f"Error clarifying research needs: {str(e)}", exc_info=True)`
- **Security Assessment:** SAFE - Logs process steps, decisions, and errors without exposing sensitive data
- **Notes:** Provides visibility into clarifier decision-making and error handling for debugging context assessment.

#### [x] iris/src/agents/agent_clarifier/clarifier_settings.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 18: `import logging`
  - Line 23: `logger = logging.getLogger(__name__)`
- **Security Assessment:** SAFE - Only sets up module logger; no sensitive data or runtime logging calls
- **Notes:** Defines clarifier agent model and prompt settings; module-level logger configuration only.

### AGENT DIRECT RESPONSE

#### [x] iris/src/agents/agent_direct_response/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/agent_direct_response/response_from_conversation.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 17: `import logging`
  - Line 25: `logger = logging.getLogger(__name__)`
  - Line 71: `logger.info(f"Generating direct response using model: {MODEL_NAME}")`
  - Line 72: `logger.info("Initiating Direct Response stream API call")`
  - Line 102: `logger.info("Direct response stream finished.")`
  - Line 109: `logger.warning("Usage details not found in direct response stream.")`
  - Line 114: `logger.error(f"Error generating direct response: {str(e)}", exc_info=True)`
- **Security Assessment:** SAFE - Only logs operation flow, warnings, and errors without exposing sensitive data
- **Notes:** Provides visibility into direct response streaming, completion, and error handling for debugging and monitoring.

#### [x] iris/src/agents/agent_direct_response/response_settings.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 21: `import logging`
  - Line 29: `logger = logging.getLogger(__name__)`
  - Line 236: `logger.debug("Direct response agent settings initialized")`
- **Security Assessment:** SAFE - Only logs initial module setup without sensitive data
- **Notes:** Sets up module logger for direct response agent; debug log confirms initialization.

### AGENT PLANNER

#### [x] iris/src/agents/agent_planner/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/agent_planner/planner.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 19: `import logging`
  - Line 34: `logger = logging.getLogger(__name__)`
  - Line 89: `logger.info(f"Creating database selection plan using model: {MODEL_NAME}")`
  - Line 90: `logger.info(f"Is continuation: {is_continuation}")`
  - Line 91: `logger.info("Initiating Planner API call for database selection")`
  - Line 118: `logger.warning(f"Expected tool call but received content: {content_returned[:100]}...")`
  - Line 151: `logger.info(f"Database selection plan created with {len(validated_databases)} databases: {validated_databases}")`
  - Line 159: `logger.error(f"Error creating database selection plan: {str(e)}", exc_info=True)`
- **Security Assessment:** SAFE - Logs status, plan creation, warnings, and errors; no sensitive data exposed
- **Notes:** Provides visibility into planner operations for debugging query plan creation and error handling.

#### [ ] iris/src/agents/agent_planner/planner_settings.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### AGENT ROUTER

#### [ ] iris/src/agents/agent_router/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/agent_router/router.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/agent_router/router_settings.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### AGENT SUMMARIZER

#### [ ] iris/src/agents/agent_summarizer/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/agent_summarizer/summarizer.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/agent_summarizer/summarizer_settings.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### DATABASE SUBAGENTS

#### [ ] iris/src/agents/database_subagents/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/database_router.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### EXTERNAL EY

#### [ ] iris/src/agents/database_subagents/external_ey/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_ey/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_ey/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### EXTERNAL IASB

#### [ ] iris/src/agents/database_subagents/external_iasb/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_iasb/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_iasb/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### EXTERNAL KPMG

#### [ ] iris/src/agents/database_subagents/external_kpmg/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_kpmg/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_kpmg/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### EXTERNAL PWC

#### [ ] iris/src/agents/database_subagents/external_pwc/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_pwc/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/external_pwc/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL AIO

#### [ ] iris/src/agents/database_subagents/internal_aio/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_aio/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_aio/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_aio/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL CAPM

#### [ ] iris/src/agents/database_subagents/internal_capm/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_capm/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_capm/description_condensation_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_capm/section_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_capm/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL CHEATSHEETS

#### [ ] iris/src/agents/database_subagents/internal_cheatsheets/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_cheatsheets/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_cheatsheets/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_cheatsheets/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL COMPLIANCE

#### [ ] iris/src/agents/database_subagents/internal_compliance/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_compliance/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_compliance/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_compliance/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL ESG

#### [ ] iris/src/agents/database_subagents/internal_esg/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_esg/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_esg/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_esg/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL EXT REPORTING AND DISCLOSURE

#### [ ] iris/src/agents/database_subagents/internal_ext_reporting_and_disclosure/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_ext_reporting_and_disclosure/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_ext_reporting_and_disclosure/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_ext_reporting_and_disclosure/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL GLOBAL FINANCE STANDARDS

#### [ ] iris/src/agents/database_subagents/internal_global_finance_standards/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_global_finance_standards/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_global_finance_standards/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_global_finance_standards/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL ICFR

#### [ ] iris/src/agents/database_subagents/internal_icfr/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_icfr/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_icfr/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_icfr/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL MANAGEMENT REPORTING

#### [ ] iris/src/agents/database_subagents/internal_management_reporting/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_management_reporting/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_management_reporting/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_management_reporting/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL MEMOS

#### [ ] iris/src/agents/database_subagents/internal_memos/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_memos/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_memos/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_memos/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL PAR

#### [ ] iris/src/agents/database_subagents/internal_par/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_par/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_par/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_par/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL PROCESS AND CONTROLS

#### [ ] iris/src/agents/database_subagents/internal_process_and_controls/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_process_and_controls/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_process_and_controls/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_process_and_controls/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

### INTERNAL WIKI

#### [ ] iris/src/agents/database_subagents/internal_wiki/__init__.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_wiki/catalog_selection_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_wiki/content_synthesis_prompt.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

#### [ ] iris/src/agents/database_subagents/internal_wiki/subagent.py
- **Status:** PENDING
- **Has Logging:** TBD
- **Logging Statements:** TBD
- **Security Assessment:** TBD
- **Notes:** TBD

---

## Analysis Instructions

### For Each File:
1. **Read the entire file** line by line
2. **Look for ALL logging:**
   - `import logging`
   - `logger = logging.getLogger()`
   - `logging.debug/info/warning/error/critical()`
   - `logger.debug/info/warning/error/critical/exception()`
   - `print()` statements
   - Any other logging frameworks

3. **Update the file entry:**
   - Change `[ ]` to `[x]` 
   - Change **Status:** from `PENDING` to `COMPLETED`
   - Update **Has Logging:** to `YES` or `NO`
   - List **Logging Statements:** with line numbers and exact text
   - Update **Security Assessment:** with `SAFE` or `RISK` and explanation
   - Add **Notes:** with operational value and context

### Example Completed Entry:
```markdown
#### [x] iris/src/api.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 36: `logger = logging.getLogger(__name__)`
  - Line 155: `logger.error(f"Streaming error: {str(e)}")`
  - Line 170: `logger.info(f"Received chat request with {len(request.messages)} messages")`
- **Security Assessment:** SAFE - Only logs request counts and error messages, no sensitive data
- **Notes:** Essential for API monitoring and debugging. Provides operational visibility without exposing credentials.
```

### Security Guidelines:
- **SAFE:** Operational metrics, error messages without sensitive data, system status
- **RISK:** Passwords, full API keys/tokens, PII, database credentials
- **Token Previews:** Mark as SAFE (partial tokens for debugging in internal environment)

---

## Final Security Summary
**TO BE COMPLETED AFTER ALL FILES ANALYZED**

- **Total Logging Statements Found:** [TBD]
- **Files with Security Risks:** [TBD] 
- **Critical Issues:** [TBD]
- **Operational Logging Benefits:** [TBD]
- **Overall Assessment:** [TBD]
