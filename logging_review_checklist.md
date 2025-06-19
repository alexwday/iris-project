# Logging Review Checklist

## Context
This file tracks our systematic review of logging statements throughout the IRIS project. We're going through each file to analyze what's logged at each level (DEBUG/INFO/WARNING/ERROR/CRITICAL) to decide what to keep, change, or remove.

**Goal:** Clean up logging levels, remove noise, and ensure appropriate log levels are used consistently.

## Files to Review (excluding subagents)

### Status Legend:
- [ ] Not started
- [x] Completed
- [WIP] Work in progress

### **Main Application Files:**
- [x] 1. `/services/src/api.py` - FastAPI endpoints (SKIPPED - local testing only)
- [ ] 2. `/services/src/chat_model/model.py` - Main workflow orchestration

### **Initial Setup Files:**
- [ ] 3. `/services/src/initial_setup/db_config.py` - Database configuration
- [ ] 4. `/services/src/initial_setup/process_monitor_setup.py` - Process monitoring
- [ ] 5. `/services/src/initial_setup/env_config.py` - Environment configuration
- [ ] 6. `/services/src/initial_setup/conversation_setup.py` - Conversation setup
- [ ] 7. `/services/src/initial_setup/ssl_setup.py` - SSL configuration
- [ ] 8. `/services/src/initial_setup/oauth_setup.py` - OAuth setup

### **Agent Files:**
- [ ] 9. `/services/src/agents/agent_router/router.py` - Request routing
- [ ] 10. `/services/src/agents/agent_clarifier/clarifier.py` - Query clarification
- [ ] 11. `/services/src/agents/agent_planner/planner.py` - Task planning
- [ ] 12. `/services/src/agents/agent_summarizer/summarizer.py` - Response summarization
- [ ] 13. `/services/src/agents/agent_direct_response/response_from_conversation.py` - Direct responses
- [ ] 14. `/services/src/agents/database_subagents/database_router.py` - Database routing

### **Agent Settings Files:**
- [ ] 15. `/services/src/agents/agent_router/router_settings.py`
- [ ] 16. `/services/src/agents/agent_clarifier/clarifier_settings.py`
- [ ] 17. `/services/src/agents/agent_planner/planner_settings.py`
- [ ] 18. `/services/src/agents/agent_summarizer/summarizer_settings.py`
- [ ] 19. `/services/src/agents/agent_direct_response/response_settings.py`

### **LLM Connector:**
- [ ] 20. `/services/src/llm_connectors/rbc_openai.py` - OpenAI API interface

### **Global Prompts Files:**
- [ ] 21. `/services/src/global_prompts/database_statement.py`
- [ ] 22. `/services/src/global_prompts/restrictions_statement.py`
- [ ] 23. `/services/src/global_prompts/project_statement.py`
- [ ] 24. `/services/src/global_prompts/fiscal_statement.py`

## Review Notes

### File 1: `/services/src/api.py`
**Status:** Not started
**Notes:** (To be filled during review)

---

*This checklist will be updated as we progress through each file.*