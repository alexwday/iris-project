# IRIS Project Restructuring Plan

## Executive Summary

This document outlines the proposed restructuring of the IRIS (Intelligent Retrieval & Interaction System) project to align with IT's requested three-folder architecture: **classes**, **routers**, and **services**.

---

## 🎯 Restructuring Goals

1. **Maintain functional integrity** while reorganizing the codebase
2. **Improve deployment flexibility** for IT operations
3. **Preserve the agent-based architecture** that makes IRIS effective
4. **Create clear separation** between business logic, resources, and integrations

---

## 📊 Current vs Proposed Structure

### Current Structure (Agent-Centric)
```
iris/src/
├── agents/                    # 6 core agents + 22 database subagents
├── chat_model/               # Orchestration layer
├── global_prompts/           # Shared prompts
├── initial_setup/            # Configuration & setup
├── llm_connectors/           # OpenAI integration
└── api.py                    # REST endpoint
```

### Proposed Structure (Three-Folder Architecture)
```
iris/
├── classes/                  # 📊 Data Models & Domain Entities
├── routers/                  # 🌐 API Endpoints & Request Handling
└── services/                 # 🧠 Business Logic & Integrations
```

---

## 📁 Detailed Folder Structure

### 📊 **CLASSES** - Data Models & Domain Entities

Contains all data structures, domain models, and entity definitions used throughout the application.

```
classes/
├── models/                      # Pydantic models & schemas
│   ├── conversation.py         # Conversation request/response models
│   ├── agent_models.py         # Agent-specific data models
│   ├── database_query.py       # Database query/result models
│   └── research_models.py      # Research planning & results
│
├── entities/                    # Domain entities
│   ├── user.py                # User entity
│   ├── session.py             # Session management
│   └── usage_metrics.py       # Token usage tracking
│
├── schemas/                    # Database schemas
│   ├── database_catalog.py    # Database metadata definitions
│   └── document_schema.py     # Document structure schemas
│
└── constants/                  # Application constants
    ├── agent_types.py         # Agent type enumerations
    ├── database_names.py      # Database identifiers
    └── prompt_templates.py    # Template string constants
```

### 🌐 **ROUTERS** - API Endpoints & Request Handling

Contains all API route definitions, request handlers, and HTTP-specific logic.

```
routers/
├── main.py                     # FastAPI app initialization
├── chat.py                     # Main chat endpoints
│   ├── POST /chat             # Process chat request
│   ├── POST /chat/stream      # Streaming chat response
│   └── GET /chat/history      # Retrieve chat history
│
├── research.py                 # Research-specific endpoints
│   ├── POST /research/query   # Direct research query
│   ├── GET /research/status   # Check research status
│   └── GET /research/sources  # List available sources
│
├── admin.py                    # Administrative endpoints
│   ├── GET /admin/metrics     # Usage metrics
│   ├── GET /admin/logs        # System logs
│   └── POST /admin/refresh    # Refresh configurations
│
├── health.py                   # Health & monitoring
│   ├── GET /health            # Basic health check
│   ├── GET /health/detailed   # Detailed system status
│   └── GET /health/database   # Database connectivity
│
└── middleware/                 # HTTP middleware
    ├── authentication.py      # OAuth/API key validation
    ├── error_handler.py       # Global error handling
    ├── logging.py             # Request/response logging
    └── rate_limiting.py       # Rate limit enforcement
```

### 🧠 **SERVICES** - Business Logic & Integrations

Contains all business logic, agent implementations, external integrations, and service layers.

```
services/
├── agents/                     # Agent implementations
│   ├── core/                  # Main pipeline agents
│   │   ├── router_agent.py    # Query routing logic
│   │   ├── clarifier_agent.py # Research clarification
│   │   ├── planner_agent.py   # Database selection
│   │   ├── summarizer_agent.py # Response synthesis
│   │   └── direct_response_agent.py # Conversational responses
│   │
│   └── database/              # Database subagents
│       ├── internal/          # Internal source agents
│       │   ├── capm_agent.py  # CAPM queries
│       │   ├── wiki_agent.py  # Wiki queries
│       │   └── ... (other internal agents)
│       │
│       └── external/          # External source agents
│           ├── ey_agent.py    # EY guidance
│           ├── iasb_agent.py  # IASB standards
│           └── ... (other external agents)
│
├── orchestration/             # Workflow orchestration
│   ├── chat_orchestrator.py   # Main chat workflow
│   ├── research_pipeline.py   # Research coordination
│   └── agent_coordinator.py   # Agent pipeline management
│
├── integrations/              # External service connectors
│   ├── openai_service.py      # OpenAI API integration
│   ├── database_service.py    # PostgreSQL operations
│   └── oauth_service.py       # OAuth authentication
│
├── config/                    # Configuration services
│   ├── environment_config.py  # Environment settings
│   ├── database_config.py     # Database connections
│   ├── logging_config.py      # Logging setup
│   └── ssl_config.py          # SSL certificates
│
├── prompts/                   # Prompt management
│   ├── global_prompts.py      # System-wide prompts
│   ├── agent_prompts.py       # Agent-specific prompts
│   └── database_prompts.py    # Database query prompts
│
└── utilities/                 # Shared utilities
    ├── streaming.py           # Response streaming
    ├── error_handling.py      # Error management
    ├── token_counter.py       # Usage tracking
    └── process_monitor.py     # Performance monitoring
```

---

## 🔄 Migration Benefits

### For Development Team
- ✅ **Standard Architecture**: Follows common FastAPI/microservice patterns
- ✅ **Clear Separation**: Models, routes, and business logic clearly divided
- ✅ **Testability**: Each layer can be tested independently
- ✅ **Type Safety**: Models in one place for consistent typing

### For IT Operations
- ✅ **API-First Design**: All endpoints clearly defined in routers
- ✅ **Service Isolation**: Business logic separate from HTTP layer
- ✅ **Scalability**: Services can be deployed as microservices
- ✅ **Monitoring**: Clear entry points for request tracking

### For Maintenance
- ✅ **Industry Standard**: New developers will recognize the pattern
- ✅ **Clear Dependencies**: Routers → Services → Classes
- ✅ **Easy Updates**: Can modify API without touching business logic
- ✅ **Swagger/OpenAPI**: Auto-documentation from router definitions

---

## 📋 Implementation Checklist

- [ ] Create new folder structure
- [ ] Move files according to mapping
- [ ] Update all import statements
- [ ] Add `__init__.py` files where needed
- [ ] Update configuration paths
- [ ] Test agent pipeline functionality
- [ ] Update deployment scripts
- [ ] Document new import patterns
- [ ] Create migration guide for team

---

## 🚀 Next Steps

1. **Review & Feedback**: Share with team for input
2. **Pilot Migration**: Test with one agent first
3. **Automated Scripts**: Create migration scripts
4. **Gradual Rollout**: Migrate in phases
5. **Testing Suite**: Ensure all tests pass
6. **Documentation**: Update all technical docs

---

## 📞 Key Architecture Notes

### Classes/Routers/Services Pattern
This is a standard **3-Layer Architecture** commonly used in modern API development:

1. **Classes Layer** (Data/Domain)
   - Pure data structures with no business logic
   - Reusable across different services
   - Framework-agnostic models

2. **Routers Layer** (Presentation/API)
   - HTTP-specific logic only
   - Request validation and response formatting
   - Authentication and authorization
   - No business logic - just orchestration

3. **Services Layer** (Business/Application)
   - All business logic and rules
   - Agent implementations
   - External integrations
   - Database operations

This pattern ensures:
- **Separation of Concerns**: Each layer has a specific responsibility
- **Testability**: Mock any layer for testing
- **Flexibility**: Change API without touching business logic
- **Scalability**: Services can become microservices

**Key Contact**: [Your Name]  
**Review Date**: [Date]  
**Implementation Target**: [Target Date]