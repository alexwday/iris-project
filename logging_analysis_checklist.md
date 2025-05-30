# IRIS Project - Logging Security Analysis Checklist

**Analysis Date:** May 30, 2025  
**Context:** Internal enterprise deployment with controlled access  
**Purpose:** Complete security audit of ALL logging statements  

## Progress Summary
- **Total Files:** 89
- **Completed:** 53
- **Files with Logging:** 31
- **Total Logging Statements:** 641
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

#### [x] iris/src/agents/agent_planner/planner_settings.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 23: `import logging`
  - Line 34: `logger = logging.getLogger(__name__)`
  - Line 234: `logger.debug("Planner agent settings initialized")`
- **Security Assessment:** SAFE - Only logs initialization of module settings; no sensitive data exposed
- **Notes:** Provides a debug log confirming planner agent settings initialization

### AGENT ROUTER

#### [x] iris/src/agents/agent_router/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/agent_router/router.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 18: `import logging`
  - Line 33: `logger = logging.getLogger(__name__)`
  - Line 77: `logger.info(f"Getting routing decision using model: {MODEL_NAME}")`
  - Line 78: `logger.info("Initiating Router API call")`
  - Line 106: `logger.warning(f"Expected tool call but received content: {content_returned[:100]}...")`
  - Line 134: `logger.info(f"Routing decision: {function_name}")`
  - Line 140: `logger.error(f"Error getting routing decision: {str(e)}", exc_info=True)`
- **Security Assessment:** SAFE - Only logs routing decisions, info and error details; no sensitive data exposed
- **Notes:** Provides operational visibility into routing logic, tool call initiation, and error handling.

#### [x] iris/src/agents/agent_router/router_settings.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 22: `import logging`
  - Line 30: `logger = logging.getLogger(__name__)`
  - Line 328: `logger.debug("Router agent settings initialized")`
- **Security Assessment:** SAFE - Only logs initialization of module settings; no sensitive data exposed
- **Notes:** Provides debug log confirming router agent settings initialization

### AGENT SUMMARIZER

#### [x] iris/src/agents/agent_summarizer/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/agent_summarizer/summarizer.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 17: `import logging`
  - Line 33: `logger = logging.getLogger(__name__)`
  - Line 76: `logger.info(f"Generating final summary for scope: {scope}")`
  - Line 88: `logger.error(f"Failed to get model configuration: {config_err}", exc_info=True)`
  - Line 136: `logger.info(f"Generating streaming research summary using model: {model_name}")`
  - Line 139: `logger.info(f"Summarizing detailed research from {len(aggregated_detailed_research)} databases.")`
  - Line 142: `logger.info("Initiating Summarizer stream API call")`
  - Line 167: `logger.info("Summary stream finished.")`
  - Line 172: `logger.warning("Usage details not found in summary stream.")`
  - Line 176: `logger.error(f"Error generating streaming research summary: {str(e)}", exc_info=True)`
  - Line 186: `logger.warning("Summarizer called with 'metadata' scope, which is not actively handled here anymore.")`
  - Line 194: `logger.error(error_msg)`
- **Security Assessment:** SAFE - Only logs summary generation progress, info, warnings, and errors; no sensitive data exposed
- **Notes:** Critical for tracking summary generation flow, progress metrics, and error handling in the summarizer agent.

#### [x] iris/src/agents/agent_summarizer/summarizer_settings.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 22: `import logging`
  - Line 33: `logger = logging.getLogger(__name__)`
  - Line 341: `logger.debug("Summarizer agent settings initialized")`
- **Security Assessment:** SAFE - Only logs module initialization of summarizer settings; no sensitive data exposed
- **Notes:** Provides a debug log confirming summarizer agent settings initialization

### DATABASE SUBAGENTS

#### [x] iris/src/agents/database_subagents/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/database_subagents/database_router.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 22: `import logging`
  - Line 46: `logger = logging.getLogger(__name__)`
  - Line 82: `logger.info(f"Routing query (sync) to database: {database} with scope: {scope}")`
  - Line 85: `logger.debug(f"Using process monitor stage name: {stage_name}")`
  - Line 94: `logger.error(error_msg)`
  - Line 119: `logger.debug(f"Successfully imported module: {module_path}")`
  - Line 123: `logger.error(error_msg)`
  - Line 137: `logger.debug(f"Calling query_database_sync for {database}")`
  - Line 183: `logger.error(error_msg, exc_info=True)`
  - Line 207: `logger.error(error_msg, exc_info=True)`
- **Security Assessment:** SAFE - Only logs routing operations, debug details, and errors; no sensitive data exposed
- **Notes:** Centralizes database query routing with detailed logging for tracing and error diagnostics.

### EXTERNAL EY

#### [x] iris/src/agents/database_subagents/external_ey/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/database_subagents/external_ey/content_synthesis_prompt.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Defines prompt templates for EY guidance synthesis; no logging used.

#### [x] iris/src/agents/database_subagents/external_ey/subagent.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 13: `import logging`
  - Line 49: `logger = logging.getLogger(__name__)`
  - Line 87: `logger.info(f"Generating embedding for query: '{query}'...")`
  - Line 115: `logger.debug(f"Embedding Usage details: {usage_details}")`
  - Line 119: `logger.debug("call_llm did not return usage_details")`
  - Line 128: `logger.info("Embedding generated successfully.")`
  - Line 131: `logger.error("No embedding data received from API.", extra={"api_response": response})`
  - Line 139: `logger.error(f"Failed to generate embedding: {e}", exc_info=True)`
  - Line 152: `logger.info(f"Performing Initial Vector Search (Retrieving Top {initial_k}){log_doc_filter}")`
  - Line 178: `logger.info(f"Found {len(results_raw)} results via vector search.")`
  - Line 189: `logger.error(f"Vector search failed: {e}", exc_info=True)`
  - Line 200: `logger.info(f"Filtering {len(results)} results by summary relevance using {RELEVANCE_MODEL_CAPABILITY}")`
  - Line 215: `logger.warning(f"Skipping result index {i} due to missing id or chapter_summary.")`
  - Line 220: `logger.warning("No valid summaries found for relevance check.")`
  - Line 265: `logger.info(f"Calling {RELEVANCE_MODEL_CAPABILITY} for summary relevance check...")`
  - Line 276: `logger.debug(f"Relevance Check Usage details for {DATABASE_NAME}: {usage_details}")`
  - Line 281: `logger.debug("call_llm did not return usage_details")`
  - Line 300: `logger.info("Summary relevance check successful.")`
  - Line 302: `logger.error(f"Failed to decode JSON response from relevance check: {e}. Response: {response_content}", exc_info=True)`
  - Line 306: `logger.error(f"Invalid JSON structure from relevance check: {e}. Response: {response_content}")`
  - Line 310: `logger.error("Invalid or empty response received from relevance check LLM.", extra={"api_response": response})`
  - Line 316: `logger.error(f"Error during relevance check LLM call: {e}", exc_info=True)`
  - Line 329: `logger.info(f"Filtering out chunk ID {chunk_id} (summary deemed irrelevant).")`
  - Line 330: `logger.info(f"Finished summary filtering. Kept {len(filtered_results)} results, removed {removed_count}.")`
  - Line 345: `logger.info(f"Reranking by Importance & Sorting (Factor: {importance_factor})")`
  - Line 352: `logger.warning(f"Skipping unexpected item type in reranking: {type(item)}")`
  - Line 366: `logger.warning(f"Could not calculate score for Chunk {item.get('id', 'N/A')} due to invalid numeric values. Setting new_score to 0. Error: {e}")`
  - Line 399: `logger.info(f"Finished reranking and sorting {len(final_reranked_list)} items.")`
  - Line 401: `logger.info("\n--- Importance Reranking Results ---\n" + tabulate(rerank_log_data, headers=headers_rerank, tablefmt="grid"))`
  - Line 403: `logger.info("\n--- Importance Reranking Results ---")`
  - Line 404: `logger.info(f"NewRank: {row[0]}, OrigRank: {row[1]}, ID: {row[2]}, OrigScore: {row[3]}, Importance: {row[4]}, NewScore: {row[5]}")`
  - Line 416: `logger.info(f"Expanding sections by token count (Top {top_k_rank} < {top_k_tokens} tokens, Others < {general_tokens} tokens)")`
  - Line 487: `logger.error(f"Failed to fetch/process expansion for section {section_key}: {e}", exc_info=True)`
  - Line 496: `logger.info("\n--- Section Expansion Log ---\n" + tabulate(expansion_log_data, headers=headers_expansion, tablefmt="grid"))`
  - Line 498: `logger.info("\n--- Section Expansion Log ---")`
  - Line 501: `logger.info(f"Finished section expansion. Intermediate count: {len(processed_results)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 537: `logger.info(f"Filling sequence gaps (Max Gap: {max_seq_gap} sequences)")`
  - Line 570: `logger.info("Not enough items with sequence numbers to check for gaps.")`
  - Line 611: `logger.error(f"Failed to fetch/process gap fill between seq {last_item_info['max_seq']} and {current_item_info['min_seq']}: {e}", exc_info=True)`
  - Line 624: `logger.info("\n--- Sequence Gap Filling Log ---\n" + tabulate(gap_log_data, headers=headers_gaps, tablefmt="grid"))`
  - Line 626: `logger.info("\n--- Sequence Gap Filling Log ---")`
  - Line 629: `logger.info(f"Finished sequence gap filling. Result count: {len(final_processed_results)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 635: `logger.info("Formatting Final Results as Cards for LLM")`
  - Line 677: `logger.debug(f"Formatting Card {i+1}: Group of {len(item['chunks'])} chunks (Section: {record_for_metadata.get('section_hierarchy', 'N/A')})")`
  - Line 686: `logger.warning(f"Skipping unexpected item type during formatting: {type(item)}")`
  - Line 691: `logger.warning(f"Skipping Card {i+1} due to missing metadata or content.")`
  - Line 717: `logger.info(f"Formatted {final_item_count} cards.")`
  - Line 728: `logger.info(f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}")`
  - Line 789: `logger.debug(f"Received tool arguments string: {arguments_str}")`
  - Line 807: `logger.error(f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}")`
  - Line 810: `logger.error(f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}")`
  - Line 813: `logger.error(f"Unexpected tool called: {tool_call.function.name}")`
  - Line 828: `logger.warning(f"LLM returned content instead of tool call: {content[:200]}...")`
  - Line 834: `logger.error("No tool call or content received from LLM for synthesis.")`
  - Line 838: `logger.error(f"Exception during final response synthesis: {e}", exc_info=True)`
  - Line 871: `logger.info("Database connection successful and pgvector registered.")`
  - Line 958: `logger.info(f"Captured {len(initial_chunk_ids)} initial chunk IDs for research scope.")`
  - Line 1099: `logger.info(f"Querying {DATABASE_NAME} database: '{query}' with scope: {scope}")`
  - Line 1102: `logger.debug(f"Using process monitor stage name: {stage_name}")`
  - Line 1127: `logger.error(f"Error adding LLM usage details to process monitor for stage {stage_name}: {monitor_err}", exc_info=True)`
  - Line 1150: `logger.error(f"Error during external_ey query execution: {str(e)}", exc_info=True)`
  - Line 1175: `logger.info(f"external_ey query completed in {duration:.2f} seconds.")`
- **Security Assessment:** SAFE - Only logs embedding generation, search operations, filtering, reranking, expansion, and synthesis progress; no sensitive data exposed
- **Notes:** Comprehensive internal monitoring of all steps in the EY subagent pipeline, invaluable for debugging search, processing, and synthesis without leaking sensitive information.

### EXTERNAL IASB

#### [x] iris/src/agents/database_subagents/external_iasb/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/database_subagents/external_iasb/content_synthesis_prompt.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Provides prompt templates for IASB content synthesis; no logging used.

#### [x] iris/src/agents/database_subagents/external_iasb/subagent.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 13: `import logging`
  - Line 49: `logger = logging.getLogger(__name__)`
  - Line 94: `logger.info(f"Generating embedding for query: '{query}'...")`
  - Line 122: `logger.debug(f"Embedding Usage details: {usage_details}")`
  - Line 126: `logger.debug("call_llm did not return usage_details")`
  - Line 135: `logger.info("Embedding generated successfully.")`
  - Line 138: `logger.error("No embedding data received from API.", extra={"api_response": response})`
  - Line 145: `logger.error(f"Failed to generate embedding: {e}", exc_info=True)`
  - Line 159: `logger.info(f"Performing Initial Vector Search (Retrieving Top {initial_k}){log_doc_filter}")`
  - Line 185: `logger.info(f"Found {len(results_raw)} results via vector search.")`
  - Line 195: `logger.error(f"Vector search failed: {e}", exc_info=True)`
  - Line 207: `logger.info(f"Filtering {len(results)} results by summary relevance using {RELEVANCE_MODEL_CAPABILITY}")`
  - Line 223: `logger.warning(f"Skipping result index {i} due to missing id or chapter_summary.")`
  - Line 227: `logger.warning("No valid summaries found for relevance check.")`
  - Line 272: `logger.info(f"Calling {RELEVANCE_MODEL_CAPABILITY} for summary relevance check...")`
  - Line 281: `logger.debug(f"Relevance Check Usage details for {DATABASE_NAME}: {usage_details}")`
  - Line 284: `logger.debug("call_llm did not return usage_details")`
  - Line 303: `logger.info("Summary relevance check successful.")`
  - Line 306: `logger.error(f"Failed to decode JSON response from relevance check: {e}. Response: {response_content}", exc_info=True)`
  - Line 310: `logger.error(f"Invalid JSON structure from relevance check: {e}. Response: {response_content}")`
  - Line 313: `logger.error("Invalid or empty response received from relevance check LLM.", extra={"api_response": response})`
  - Line 319: `logger.error(f"Error during relevance check LLM call: {e}", exc_info=True)`
  - Line 333: `logger.info(f"Filtering out chunk ID {chunk_id} (summary deemed irrelevant).")`
  - Line 334: `logger.info(f"Finished summary filtering. Kept {len(filtered_results)} results, removed {removed_count}.")`
  - Line 349: `logger.info(f"Reranking by Importance & Sorting (Factor: {importance_factor})")`
  - Line 356: `logger.warning(f"Skipping unexpected item type in reranking: {type(item)}")`
  - Line 369: `logger.warning(f"Could not calculate score for Chunk {item.get('id', 'N/A')} due to invalid numeric values. Setting new_score to 0. Error: {e}")`
  - Line 403: `logger.info(f"Finished reranking and sorting {len(final_reranked_list)} items.")`
  - Line 405: `logger.info("\n--- Importance Reranking Results ---\n" + tabulate(rerank_log_data, headers=headers_rerank, tablefmt="grid"))`
  - Line 407: `logger.info("\n--- Importance Reranking Results ---")`
  - Line 420: `logger.info(f"Expanding sections by token count (Top {top_k_rank} < {top_k_tokens} tokens, Others < {general_tokens} tokens)")`
  - Line 490: `logger.error(f"Failed to fetch/process expansion for section {section_key}: {e}", exc_info=True)`
  - Line 500: `logger.info("\n--- Section Expansion Log ---\n" + tabulate(expansion_log_data, headers=headers_expansion, tablefmt="grid"))`
  - Line 502: `logger.info("\n--- Section Expansion Log ---")`
  - Line 505: `logger.info(f"Finished section expansion. Intermediate count: {len(processed_results)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 541: `logger.info(f"Filling sequence gaps (Max Gap: {max_seq_gap} sequences)")`
  - Line 573: `logger.info("Not enough items with sequence numbers to check for gaps.")`
  - Line 615: `logger.error(f"Failed to fetch/process gap fill between seq {last_item_info['max_seq']} and {current_item_info['min_seq']}: {e}", exc_info=True)`
  - Line 628: `logger.info("\n--- Sequence Gap Filling Log ---\n" + tabulate(gap_log_data, headers=headers_gaps, tablefmt="grid"))`
  - Line 630: `logger.info("\n--- Sequence Gap Filling Log ---")`
  - Line 633: `logger.info(f"Finished sequence gap filling. Result count: {len(final_processed_results)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 639: `logger.info("Formatting Final Results as Cards for LLM")`
  - Line 681: `logger.debug(f"Formatting Card {i+1}: Group of {len(item['chunks'])} chunks (Section: {record_for_metadata.get('section_hierarchy', 'N/A')})")`
  - Line 687: `logger.warning(f"Skipping unexpected item type during formatting: {type(item)}")`
  - Line 693: `logger.warning(f"Skipping Card {i+1} due to missing metadata or content.")`
  - Line 723: `logger.info(f"Formatted {final_item_count} cards.")`
  - Line 734: `logger.info(f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}")`
  - Line 792: `logger.debug(f"Received tool arguments string: {arguments_str}")`
  - Line 810: `logger.error(f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}")`
  - Line 813: `logger.error(f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}")`
  - Line 816: `logger.error(f"Unexpected tool called: {tool_call.function.name}")`
  - Line 831: `logger.warning(f"LLM returned content instead of tool call: {content[:200]}...")`
  - Line 837: `logger.error("No tool call or content received from LLM for synthesis.")`
  - Line 841: `logger.error(f"Exception during final response synthesis: {e}", exc_info=True)`
  - Line 961: `logger.info("Database connection successful and pgvector registered.")`
  - Line 1056: `logger.info(f"Captured {len(ids_for_doc)} initial chunk IDs for doc {doc_id} (research scope).")`
  - Line 1076: `logger.info(f"Collected {len(initial_chunk_ids)} total initial chunk IDs for research scope across all IASB sources.")`
  - Line 1077: `logger.info(f"Collected {len(final_chunk_ids)} total final chunk IDs for research scope across all IASB sources.")`
  - Line 1080: `logger.info(f"Formatting combined {len(all_processed_results)} processed items from all IASB sources.")`
  - Line 1092: `logger.error(f"Invalid scope '{scope}' provided to {DATABASE_NAME} subagent.")`
  - Line 1100: `logger.error(f"Database error during {DATABASE_NAME} query (Scope: {scope}): {db_err}", exc_info=True)`
  - Line 1108: `logger.error(f"Connection error for {DATABASE_NAME} (Scope: {scope}): {conn_err}", exc_info=True)`
  - Line 1115: `logger.error(f"Unexpected error querying {DATABASE_NAME} database (Scope: {scope}): {e}", exc_info=True)`
  - Line 1131: `logger.error(f"Reached end of _query_database_logic unexpectedly for scope '{scope}' in {DATABASE_NAME}.")`
  - Line 1159: `logger.info(f"Querying {DATABASE_NAME} database: '{query}' with scope: {scope}")`
  - Line 1162: `logger.debug(f"Using process monitor stage name: {stage_name}")`
  - Line 1207: `logger.error(f"Error during {DATABASE_NAME} query execution: {str(e)}", exc_info=True)`
  - Line 1232: `logger.info(f"{DATABASE_NAME} query completed in {duration:.2f} seconds.")`
- **Security Assessment:** SAFE - Only logs embedding generation, search operations, filtering, reranking, expansion, and synthesis progress; no sensitive data exposed
- **Notes:** Comprehensive internal monitoring of all steps in the IASB subagent pipeline, invaluable for debugging search, processing, and synthesis without leaking sensitive information.

### EXTERNAL KPMG

#### [x] iris/src/agents/database_subagents/external_kpmg/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/database_subagents/external_kpmg/content_synthesis_prompt.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Defines prompt templates for KPMG guidance synthesis; no logging used.

#### [x] iris/src/agents/database_subagents/external_kpmg/subagent.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:**
  - Line 13: `import logging`
  - Line 49: `logger = logging.getLogger(__name__)`
  - Line 87: `logger.info(f"Generating embedding for query: '{query}'...")`
  - Line 115: `logger.debug(f"Embedding Usage details: {usage_details}")`
  - Line 119: `logger.debug("call_llm did not return usage_details")`
  - Line 128: `logger.info("Embedding generated successfully.")`
  - Line 131: `logger.error("No embedding data received from API.", extra={"api_response": response})`
  - Line 139: `logger.error(f"Failed to generate embedding: {e}", exc_info=True)`
  - Line 152: `logger.info(f"Performing Initial Vector Search (Retrieving Top {initial_k}){log_doc_filter}")`
  - Line 178: `logger.info(f"Found {len(results_raw)} results via vector search.")`
  - Line 189: `logger.error(f"Vector search failed: {e}", exc_info=True)`
  - Line 200: `logger.info(f"Filtering {len(results)} results by summary relevance using {RELEVANCE_MODEL_CAPABILITY}")`
  - Line 215: `logger.warning(f"Skipping result index {i} due to missing id or chapter_summary.")`
  - Line 220: `logger.warning("No valid summaries found for relevance check.")`
  - Line 265: `logger.info(f"Calling {RELEVANCE_MODEL_CAPABILITY} for summary relevance check...")`
  - Line 276: `logger.debug(f"Relevance Check Usage details for {DATABASE_NAME}: {usage_details}")`
  - Line 281: `logger.debug("call_llm did not return usage_details")`
  - Line 300: `logger.info("Summary relevance check successful.")`
  - Line 302: `logger.error(f"Failed to decode JSON response from relevance check: {e}. Response: {response_content}", exc_info=True)`
  - Line 306: `logger.error(f"Invalid JSON structure from relevance check: {e}. Response: {response_content}")`
  - Line 310: `logger.error("Invalid or empty response received from relevance check LLM.", extra={"api_response": response})`
  - Line 316: `logger.error(f"Error during relevance check LLM call: {e}", exc_info=True)`
  - Line 329: `logger.info(f"Filtering out chunk ID {chunk_id} (summary deemed irrelevant).")`
  - Line 334: `logger.info(f"Finished summary filtering. Kept {len(filtered_results)} results, removed {removed_count}.")`
  - Line 345: `logger.info(f"Reranking by Importance & Sorting (Factor: {importance_factor})")`
  - Line 352: `logger.warning(f"Skipping unexpected item type in reranking: {type(item)}")`
  - Line 366: `logger.warning(f"Could not calculate score for Chunk {item.get('id', 'N/A')} due to invalid numeric values. Setting new_score to 0. Error: {e}")`
  - Line 399: `logger.info(f"Finished reranking and sorting {len(final_reranked_list)} items.")`
  - Line 401: `logger.info("\n--- Importance Reranking Results ---\n" + tabulate(rerank_log_data, headers=headers_rerank, tablefmt="grid"))`
  - Line 403: `logger.info("\n--- Importance Reranking Results ---")`
  - Line 404: `logger.info(f"NewRank: {row[0]}, OrigRank: {row[1]}, ID: {row[2]}, OrigScore: {row[3]}, Importance: {row[4]}, NewScore: {row[5]}")`
  - Line 419: `logger.info(f"Expanding sections by token count (Top {top_k_rank} < {top_k_tokens} tokens, Others < {general_tokens} tokens)")`
  - Line 483: `logger.error(f"Failed to fetch/process expansion for section {section_key}: {e}", exc_info=True)`
  - Line 492: `logger.info("\n--- Section Expansion Log ---\n" + tabulate(expansion_log_data, headers=headers_expansion, tablefmt="grid"))`
  - Line 494: `logger.info("\n--- Section Expansion Log ---")`
  - Line 498: `logger.info(f"Finished section expansion. Intermediate count: {len(processed_results)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 534: `logger.info(f"Filling sequence gaps (Max Gap: {max_seq_gap} sequences)")`
  - Line 567: `logger.info("Not enough items with sequence numbers to check for gaps.")`
  - Line 608: `logger.error(f"Failed to fetch/process gap fill between seq {last_item_info['max_seq']} and {current_item_info['min_seq']}: {e}", exc_info=True)`
  - Line 621: `logger.info("\n--- Sequence Gap Filling Log ---\n" + tabulate(gap_log_data, headers=headers_gaps, tablefmt="grid"))`
  - Line 623: `logger.info("\n--- Sequence Gap Filling Log ---")`
  - Line 627: `logger.info(f"Finished sequence gap filling. Result count: {len(final_results_with_gaps)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 632: `logger.info("Formatting Final Results as Cards for LLM")`
  - Line 674: `logger.debug(f"Formatting Card {i+1}: Group of {len(item['chunks'])} chunks (Section: {record_for_metadata.get('section_hierarchy', 'N/A')})")`
  - Line 682: `logger.warning(f"Skipping unexpected item type during formatting: {type(item)}")`
  - Line 687: `logger.warning(f"Skipping Card {i+1} due to missing metadata or content.")`
  - Line 714: `logger.info(f"Formatted {final_item_count} cards.")`
  - Line 725: `logger.info(f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}")`
  - Line 783: `logger.debug(f"Received tool arguments string: {arguments_str}")`
  - Line 801: `logger.error(f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}")`
  - Line 803: `logger.error(f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}")`
  - Line 807: `logger.error(f"Unexpected tool called: {tool_call.function.name}")`
  - Line 822: `logger.warning(f"LLM returned content instead of tool call: {content[:200]}...")`
  - Line 828: `logger.error("No tool call or content received from LLM for synthesis.")`
  - Line 832: `logger.error(f"Exception during final response synthesis: {e}", exc_info=True)`
  - Line 865: `logger.info("Database connection successful and pgvector registered.")`
  - Line 894: `logger.info(f"Captured {len(initial_chunk_ids)} initial chunk IDs for metadata scope.")`
  - Line 1086: `logger.info(f"Querying {DATABASE_NAME} database: '{query}' with scope: {scope}")`
  - Line 1089: `logger.debug(f"Using process monitor stage name: {stage_name}")`
  - Line 1113: `logger.error(f"Error adding LLM usage details to process monitor for stage {stage_name}: {monitor_err}", exc_info=True)`
  - Line 1134: `logger.error(f"Error during {DATABASE_NAME} query execution: {str(e)}", exc_info=True)`
  - Line 1159: `logger.info(f"{DATABASE_NAME} query completed in {duration:.2f} seconds.")`
- **Security Assessment:** SAFE - Only logs embedding generation, search operations, filtering, reranking, expansion, and synthesis progress; no sensitive data exposed
- **Notes:** Comprehensive internal monitoring of all steps in the KPMG subagent pipeline, invaluable for debugging search, processing, and synthesis without leaking sensitive information.

### EXTERNAL PWC

#### [x] iris/src/agents/database_subagents/external_pwc/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/database_subagents/external_pwc/content_synthesis_prompt.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Defines prompt templates for PwC guidance synthesis; no logging used.

#### [x] iris/src/agents/database_subagents/external_pwc/subagent.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 87: `logger.info(f"Generating embedding for query: '{query}'...")`
  - Line 115: `logger.debug(f"Embedding Usage details: {usage_details}")`
  - Line 119: `logger.debug("call_llm did not return usage_details")`
  - Line 128: `logger.info("Embedding generated successfully.")`
  - Line 131: `logger.error("No embedding data received from API.", extra={"api_response": response})`
  - Line 152: `logger.info(f"Performing Initial Vector Search (Retrieving Top {initial_k}){log_doc_filter}")`
  - Line 156: `logger.error("Cannot perform vector search without embedding.")`
  - Line 178: `logger.info(f"Found {len(results_raw)} results via vector search.")`
  - Line 189: `logger.error(f"Vector search failed: {e}", exc_info=True)`
  - Line 200: `logger.info(f"Filtering {len(results)} results by summary relevance using {RELEVANCE_MODEL_CAPABILITY}")`
  - Line 215: `logger.warning(f"Skipping result index {i} due to missing id or chapter_summary.")`
  - Line 220: `logger.warning("No valid summaries found for relevance check.")`
  - Line 265: `logger.info(f"Calling {RELEVANCE_MODEL_CAPABILITY} for summary relevance check...")`
  - Line 274: `logger.debug(f"Relevance Check Usage details for {DATABASE_NAME}: {usage_details}")`
  - Line 278: `logger.debug("call_llm did not return usage_details")`
  - Line 296: `logger.info("Summary relevance check successful.")`
  - Line 298: `logger.error(f"Failed to decode JSON response from relevance check: {e}. Response: {response_content}", exc_info=True)`
  - Line 303: `logger.error(f"Invalid JSON structure from relevance check: {e}. Response: {response_content}")`
  - Line 312: `logger.error(f"Error during relevance check LLM call: {e}", exc_info=True)`
  - Line 326: `logger.info(f"Filtering out chunk ID {chunk_id} (summary deemed irrelevant).")`
  - Line 327: `logger.info(f"Finished summary filtering. Kept {len(filtered_results)} results, removed {removed_count}.")`
  - Line 329: `logger.warning("Skipping summary filtering due to errors in relevance check.")`
  - Line 342: `logger.info(f"Reranking by Importance & Sorting (Factor: {importance_factor})")`
  - Line 349: `logger.warning(f"Skipping unexpected item type in reranking: {type(item)}")`
  - Line 362: `logger.warning(f"Could not calculate score for Chunk {item.get('id', 'N/A')} due to invalid numeric values. Setting new_score to 0. Error: {e}")`
  - Line 396: `logger.info(f"Finished reranking and sorting {len(final_reranked_list)} items.")`
  - Line 398: `logger.info("\n--- Importance Reranking Results ---\n" + tabulate(rerank_log_data, headers=headers_rerank, tablefmt="grid"))`
  - Line 400: `logger.info("\n--- Importance Reranking Results ---")`
  - Line 401: `for row in rerank_log_data: logger.info(f"NewRank: {row[0]}, OrigRank: {row[1]}, ID: {row[2]}, OrigScore: {row[3]}, Importance: {row[4]}, NewScore: {row[5]}")`
  - Line 413: `logger.info(f"Expanding sections by token count (Top {top_k_rank} < {top_k_tokens} tokens, Others < {general_tokens} tokens)")`
  - Line 483: `logger.error(f"Failed to fetch/process expansion for section {section_key}: {e}", exc_info=True)`
  - Line 493: `logger.info("\n--- Section Expansion Log ---\n" + tabulate(expansion_log_data, headers=headers_expansion, tablefmt="grid"))`
  - Line 495: `logger.info("\n--- Section Expansion Log ---")`
  - Line 496: `for row in expansion_log_data: logger.info(f"ID: {row[0]}, Rank: {row[1]}, Tokens: {row[2]}, Threshold: {row[3]}, Action: {row[4]}, Added: {row[5]}")`
  - Line 498: `logger.info(f"Finished section expansion. Intermediate count: {len(processed_results)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 515: `logger.debug(f"Filtering out single chunk ID {chunk_id} (Rank: {item.get('rank', 'N/A')}) included in group.")`
  - Line 520: `logger.warning(f"Unexpected item type during final expansion filtering: {type(item)}")`
  - Line 523: `logger.info(f"Finished filtering expanded singles. Removed {skipped_singles}. Final count: {len(final_processed_results)}")`
  - Line 534: `logger.info(f"Filling sequence gaps (Max Gap: {max_seq_gap} sequences)")`
  - Line 566: `logger.info("Not enough items with sequence numbers to check for gaps.")`
  - Line 608: `logger.error(f"Failed to fetch/process gap fill between seq {last_item_info['max_seq']} and {current_item_info['min_seq']}: {e}", exc_info=True)`
  - Line 621: `logger.info("\n--- Sequence Gap Filling Log ---\n" + tabulate(gap_log_data, headers=headers_gaps, tablefmt="grid"))`
  - Line 623: `logger.info("\n--- Sequence Gap Filling Log ---")`
  - Line 624: `for row in gap_log_data: logger.info(f"Between: {row[0]}, And: {row[1]}, Seq Gap: {row[2]}, Action: {row[3]}, Added: {row[4]}")`
  - Line 626: `logger.info(f"Finished sequence gap filling. Result count: {len(final_results_with_gaps)}. Added {len(added_chunk_ids)} new chunks.")`
  - Line 632: `logger.info("Formatting Final Results as Cards for LLM")`
  - Line 651: `logger.warning(f"Found {len(items_without_sequence)} items without sequence numbers, placing them at the end.")`
  - Line 656: `logger.error(f"Error sorting results before formatting: {sort_err}. Proceeding with unsorted results.", exc_info=True)`
  - Line 674: `logger.debug(f"Formatting Card {i+1}: Group of {len(item['chunks'])} chunks (Section: {record_for_metadata.get('section_hierarchy', 'N/A')})")`
  - Line 681: `logger.debug(f"Formatting Card {i+1}: Single Chunk ID {record_for_metadata.get('id', 'N/A')}")`
  - Line 683: `logger.warning(f"Skipping unexpected item type during formatting: {type(item)}")`
  - Line 687: `logger.warning(f"Skipping Card {i+1} due to missing metadata or content.")`
  - Line 714: `logger.info(f"Formatted {final_item_count} cards.")`
  - Line 725: `logger.info(f"Generating Final Response from Processed Chunks using {RESPONSE_MODEL_CAPABILITY}")`
  - Line 755: `logger.info(f"Calling {RESPONSE_MODEL_CAPABILITY} for final response synthesis...")`
  - Line 764: `logger.debug(f"Synthesis Usage details: {usage_details}")`
  - Line 768: `logger.debug("call_llm did not return usage_details")`
  - Line 783: `logger.debug(f"Received tool arguments string: {arguments_str}")`
  - Line 788: `logger.info(f"Successfully parsed synthesis tool call for {DATABASE_NAME}.")`
  - Line 801: `logger.error(f"Missing required keys ('status_summary', 'detailed_research_report') in parsed tool arguments from LLM: {arguments}")`
  - Line 804: `logger.error(f"Failed to parse tool arguments JSON: {json_err}. Arguments: {arguments_str}")`
  - Line 807: `logger.error(f"Unexpected tool called: {tool_call.function.name}")`
  - Line 822: `logger.warning(f"LLM returned content instead of tool call: {content[:200]}...")`
  - Line 828: `logger.error("No tool call or content received from LLM for synthesis.")`
  - Line 832: `logger.error(f"Exception during final response synthesis: {e}", exc_info=True)`
  - Line 865: `logger.info("Database connection successful and pgvector registered.")`
  - Line 884: `logger.info(f"Processing '{scope}' scope for {DATABASE_NAME}")`
  - Line 891: `logger.info(f"No initial vector search results for metadata query in {DATABASE_NAME}.")`
  - Line 905: `logger.warning(f"Skipping record due to missing fields: {record.get('id')}")`
  - Line 928: `logger.info(f"Returning {len(metadata_response)} unique sections for metadata scope from {DATABASE_NAME}.")`
  - Line 934: `logger.info(f"Processing '{scope}' scope for {DATABASE_NAME}")`
  - Line 948: `logger.info(f"Captured {len(initial_chunk_ids)} initial chunk IDs for research scope.")`
  - Line 1001: `logger.info(f"Collected {len(final_chunk_ids)} final chunk IDs for research scope.")`
  - Line 1015: `logger.error(f"Invalid scope '{scope}' provided to {DATABASE_NAME} subagent.")`
  - Line 1023: `logger.error(f"Database error during {DATABASE_NAME} query (Scope: {scope}): {db_err}", exc_info=True)`
  - Line 1031: `logger.error(f"Connection error for {DATABASE_NAME} (Scope: {scope}): {conn_err}", exc_info=True)`
  - Line 1038: `logger.error(f"Unexpected error querying {DATABASE_NAME} database (Scope: {scope}): {e}", exc_info=True)`
  - Line 1050: `logger.info("Database connection closed.")`
  - Line 1053: `logger.error(f"Reached end of _query_database_logic unexpectedly for scope '{scope}' in {DATABASE_NAME}.")`
  - Line 1081: `logger.info(f"Querying {DATABASE_NAME} database: '{query}' with scope: {scope}")`
  - Line 1084: `logger.debug(f"Using process monitor stage name: {stage_name}")`
  - Line 1108: `logger.error(f"Error adding LLM usage details to process monitor for stage {stage_name}: {monitor_err}", exc_info=True)`
  - Line 1129: `logger.error(f"Error during {DATABASE_NAME} query execution: {str(e)}", exc_info=True)`
  - Line 1154: `logger.info(f"{DATABASE_NAME} query completed in {duration:.2f} seconds.")`
- **Security Assessment:** SAFE - Logs operational pipeline steps, performance metrics, error conditions, and debugging data without exposing sensitive data or credentials.
- **Notes:** Essential for tracing embedding generation, vector search, LLM filtering, reranking, section expansion, gap filling, formatting, and synthesis phases; invaluable for debugging subagent operations in PwC guidance processing.

### INTERNAL AIO

#### [x] iris/src/agents/database_subagents/internal_aio/__init__.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Standard Python package initialization file with no logging.

#### [x] iris/src/agents/database_subagents/internal_aio/catalog_selection_prompt.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Provides prompt templates for AIO catalog selection; no logging used.

#### [x] iris/src/agents/database_subagents/internal_aio/content_synthesis_prompt.py
- **Status:** COMPLETED
- **Has Logging:** NO
- **Logging Statements:** None found
- **Security Assessment:** N/A - No logging statements present
- **Notes:** Defines prompt templates for AIO content synthesis; no logging used.

#### [x] iris/src/agents/database_subagents/internal_aio/subagent.py
- **Status:** COMPLETED
- **Has Logging:** YES
- **Logging Statements:** 
  - Line 79: `logger.info(f"Fetching full AIO catalog (environment: {config.ENVIRONMENT})")`
  - Line 83: `logger.error("Failed to connect to database for AIO catalog")`
  - Line 104: `logger.info(f"Retrieved {len(catalog_records)} AIO catalog entries from database")`
  - Line 108: `logger.error(f"Error fetching AIO catalog from database: {str(e)}")`
  - Line 119: `logger.info(f"Fetching AIO content for documents: {doc_ids}")`
  - Line 121: `logger.warning("No AIO document IDs to fetch")`
  - Line 126: `logger.error("Failed to connect to database for AIO content")`
  - Line 143: `logger.info(f"Found {len(doc_names)} AIO documents for IDs: {doc_ids}")`
  - Line 167: `logger.info(f"Retrieved AIO content for {len(result)} documents from database")`
  - Line 169: `logger.error(f"Error fetching AIO document content from database: {str(e)}")`
  - Line 198: `logger.error(f"Error: {llm_err}", exc_info=True)`
  - Line 224: `logger.info("Forcing non-streaming mode for tool call.")`
  - Line 236: `logger.debug(f"Usage details for {database_name}: {usage_details}")`
  - Line 241: `logger.debug("call_llm did not return usage_details")`
  - Line 244: `logger.error(f"call_llm failed: {llm_err}", exc_info=True)`
  - Line 249: `logger.debug("Returning raw response object and usage details for tool call.")`
  - Line 257: `logger.error("Invalid response structure received for tool call.")`
  - Line 270: `logger.warning("LLM response message content was missing or None.")`
  - Line 273: `logger.error("LLM response object or choices attribute missing/empty.")`
  - Line 275: `logger.debug("Returning extracted content string and usage details for standard completion.")`
  - Line 291: `logger.info("Selecting relevant AIO documents from catalog")`
  - Line 298: `logger.info(f"Initiating AIO Document Selection API call (DB: {database_name})")`
  - Line 312: `logger.debug(f"Document selection usage: {selection_usage}")`
  - Line 320: `logger.error("get_completion failed during document selection: {selection_response_str}")`
  - Line 331: `logger.info(f"LLM selected AIO document IDs: {selected_ids}")`
  - Line 334: `logger.error("LLM response was valid JSON but not a list of strings: {selection_response_str}")`
  - Line 339: `logger.error("Could not extract AIO document IDs from response using fallback regex: {valid_ids}")`
  - Line 353: `logger.warning("LLM did not select any relevant documents from the catalog based on the query.")`
  - Line 357: `logger.error(f"Error during LLM AIO document selection: {str(e)}")`
  - Line 360: `logger.error(f"No documents provided for {database_name} synthesis.")`
  - Line 400: `logger.info(f"Synthesizing response and status for {database_name} using tool call.")`
  - Line 413: `logger.warning(f"No documents provided for {database_name} synthesis.")`
  - Line 423: `logger.info(f"Initiating AIO Synthesis API call (DB: {database_name})")`
  - Line 443: `logger.debug(f"Research synthesis usage: {synthesis_usage}")`
  - Line 451: `logger.error("get_completion failed for {database_name} synthesis: {synthesis_response_str}")`
  - Line 470: `logger.debug(f"Received tool arguments string: {arguments_str}")`
  - Line 477: `logger.info(f"Successfully parsed synthesis tool call for {database_name}.")`
  - Line 489: `logger.error(f"Missing required keys in parsed tool arguments for {database_name}: {arguments}")`
  - Line 497: `logger.error(f"Failed to parse tool arguments JSON for {database_name}: {json_err}. Arguments: {arguments_str}")`
  - Line 505: `logger.error(f"Unexpected tool called for {database_name}: {tool_call.function.name}")`
  - Line 513: `logger.error("No tool call received from LLM for {database_name} synthesis, despite being requested.")`
  - Line 526: `logger.warning(f"LLM returned content instead of tool call: {content[:200]}...")`
  - Line 539: `logger.error("Error during synthesis tool call for {database_name}: {str(e)}")`
  - Line 565: `logger.info(f"Querying Internal AIO database (sync): '{query}' with scope: {scope}")`
  - Line 574: `logger.debug(f"Using process monitor stage name: {stage_name}")`
  - Line 580: `logger.info(f"Retrieved {len(catalog)} total AIO catalog entries")`
  - Line 597: `logger.info(f"LLM selected {len(selected_doc_ids)} relevant AIO document IDs: {selected_doc_ids}")`
  - Line 622: `logger.info(f"Returning {len(selected_items)} selected AIO metadata items.")`
  - Line 655: `logger.info(f"Retrieved content for {len(documents)} AIO documents for research.")`
  - Line 676: `logger.error(f"Invalid scope provided to internal_aio subagent: {scope}")`
  - Line 681: `logger.error(error_msg, exc_info=True)`
- **Security Assessment:** SAFE - Logs catalog retrieval, content fetching, LLM calls, selections, and synthesis operations without exposing sensitive data or credentials.
- **Notes:** Essential for tracing async AIO pipeline steps: catalog fetch, document selection, content retrieval, and research synthesis; invaluable for debugging internal AIO subagent operations.

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
