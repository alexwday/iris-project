# IRIS Project Restructuring Plan

## Executive Summary

This document outlines the proposed restructuring of the IRIS (Intelligent Retrieval & Interaction System) project to align with IT's requested three-folder architecture: **classes**, **assets**, and **services**.

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
├── classes/                  # 🧠 Business Logic & Core Functionality
├── assets/                   # 📄 Static Resources & Configuration
└── services/                 # 🔌 External Integrations & APIs
```

---

## 📁 Detailed Folder Structure

### 🧠 **CLASSES** - Business Logic & Domain Models

Contains all core business logic, agent implementations, and data models.

```
classes/
├── agents/
│   ├── core/                     # Main pipeline agents
│   │   ├── router.py            # Determines query routing
│   │   ├── clarifier.py         # Refines research goals
│   │   ├── planner.py           # Selects databases
│   │   ├── summarizer.py        # Synthesizes responses
│   │   └── direct_response.py   # Handles conversational queries
│   │
│   └── database/                # Specialized database agents
│       ├── internal/            # 13 internal data sources
│       │   ├── capm.py         # Corporate Accounting Policies
│       │   ├── wiki.py         # APG Wiki entries
│       │   ├── cheatsheets.py  # Quick reference guides
│       │   ├── memos.py        # Internal accounting memos
│       │   ├── par.py          # Project approval requests
│       │   ├── aio.py          # Auditor independence
│       │   ├── icfr.py         # Internal controls
│       │   ├── esg.py          # ESG guidance
│       │   ├── compliance.py   # Compliance policies
│       │   ├── reporting.py    # External reporting
│       │   ├── standards.py    # Global finance standards
│       │   ├── management.py   # Management reporting
│       │   └── controls.py     # Process and controls
│       │
│       └── external/            # 4 external data sources
│           ├── ey.py           # EY IFRS guidance
│           ├── iasb.py         # IASB standards
│           ├── kpmg.py         # KPMG IFRS guidance
│           └── pwc.py          # PwC IFRS guidance
│
├── models/                      # Data structures
│   ├── conversation.py         # Conversation models
│   ├── agent_response.py       # Response structures
│   └── database_query.py       # Query/result models
│
└── orchestration/              # Pipeline coordination
    └── chat_model.py          # Main orchestration logic
```

### 📄 **ASSETS** - Static Resources & Configuration

Contains all non-code resources: prompts, configurations, and schemas.

```
assets/
├── prompts/
│   ├── global/                  # System-wide prompts
│   │   ├── database_statement.py    # Database descriptions
│   │   ├── fiscal_statement.py      # Fiscal calendar info
│   │   ├── project_statement.py     # Project context
│   │   └── restrictions_statement.py # Compliance rules
│   │
│   ├── agent_prompts/           # Agent-specific prompts
│   │   ├── router_settings.py       # Router configuration
│   │   ├── clarifier_settings.py    # Clarifier templates
│   │   ├── planner_settings.py      # Planner instructions
│   │   ├── summarizer_settings.py   # Summary templates
│   │   └── direct_response_settings.py
│   │
│   └── database_prompts/        # Database agent prompts
│       ├── catalog_selection/   # Document selection prompts
│       │   ├── internal_capm_catalog.py
│       │   ├── internal_wiki_catalog.py
│       │   └── ... (one per subagent)
│       │
│       └── content_synthesis/   # Content synthesis prompts
│           ├── internal_capm_synthesis.py
│           ├── internal_wiki_synthesis.py
│           └── ... (one per subagent)
│
├── configs/                     # Configuration files
│   ├── environment.py          # Environment detection
│   ├── database.py             # Database connections
│   ├── logging.py              # Logging configuration
│   ├── oauth.py                # OAuth settings
│   └── ssl.py                  # SSL certificates
│
└── schemas/                    # Data definitions
    └── database_catalog.py     # Database metadata
```

### 🔌 **SERVICES** - External Integrations & APIs

Contains all external-facing code and service integrations.

```
services/
├── api/
│   ├── main.py                 # FastAPI application
│   └── endpoints/              # API endpoints
│       ├── chat.py            # Chat endpoints
│       ├── health.py          # Health checks
│       └── metrics.py         # Usage metrics
│
├── connectors/
│   ├── openai_connector.py    # OpenAI API wrapper
│   └── database/              # Database connections
│       └── postgres.py        # PostgreSQL adapter
│
├── monitoring/
│   └── process_monitor.py     # Performance tracking
│
└── utilities/                 # Shared utilities
    ├── streaming.py          # Response streaming
    ├── error_handling.py     # Error management
    ├── token_counter.py      # Usage tracking
    └── auth_utils.py         # Authentication helpers
```

---

## 🔄 Migration Benefits

### For Development Team
- ✅ **Preserved Architecture**: Agent pipeline remains intact
- ✅ **Clear Organization**: Related files grouped logically
- ✅ **Easier Testing**: Business logic separated from infrastructure
- ✅ **Better Modularity**: Clear boundaries between components

### For IT Operations
- ✅ **Deployment Flexibility**: Can deploy/scale folders independently
- ✅ **Security Isolation**: Business logic separate from external services
- ✅ **Resource Management**: Static assets can be cached/CDN-hosted
- ✅ **Service Monitoring**: All integrations in one place

### For Maintenance
- ✅ **Simplified Updates**: Update prompts without touching code
- ✅ **Configuration Management**: All configs in one location
- ✅ **Dependency Tracking**: Clear separation of concerns
- ✅ **Version Control**: Easier to track changes by type

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

## 📞 Questions?

This restructuring maintains IRIS's intelligent agent architecture while providing IT with the organized structure they need for deployment and management.

**Key Contact**: [Your Name]  
**Review Date**: [Date]  
**Implementation Target**: [Target Date]