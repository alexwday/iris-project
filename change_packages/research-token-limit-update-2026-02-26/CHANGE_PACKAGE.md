# Research Token Limit Update Package

Date: 2026-02-26

## Scope
This package updates `MODEL_MAX_TOKENS` from `4096` to `16384` in two deep-research subagent files.

## File Updates

### 1) `services/src/agent/tools/file_research_subagent.py`

Replace this block:
```python
MODEL_CAPABILITY = "small"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.2
```

With:
```python
MODEL_CAPABILITY = "small"
MODEL_MAX_TOKENS = 16384
MODEL_TEMPERATURE = 0.2
```

### 2) `services/src/agent/tools/metadata_subagent.py`

Replace this block:
```python
MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 4096
MODEL_TEMPERATURE = 0.2
```

With:
```python
MODEL_CAPABILITY = "large"
MODEL_MAX_TOKENS = 16384
MODEL_TEMPERATURE = 0.2
```

## Included Updated Files
- `files/services/src/agent/tools/file_research_subagent.py`
- `files/services/src/agent/tools/metadata_subagent.py`
