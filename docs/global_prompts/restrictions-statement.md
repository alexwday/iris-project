# Restrictions Statement (`iris/src/global_prompts/restrictions_statement.py`)

This module provides statements about output restrictions and guidelines that should be applied across all agent responses for compliance and quality control. It ensures consistent behavior, appropriate disclaimers, and quality standards throughout the IRIS system.

## Overview

This module generates comprehensive compliance and quality control statements for the IRIS system. It provides standardized restrictions, guidelines, and confidence signaling frameworks that ensure all agent responses maintain professional standards, appropriate disclaimers, and consistent quality. The module serves as a foundational component for maintaining compliance across all agent interactions while ensuring transparency about information confidence levels.

## Key Components

* **`restrictions_statement.py`**: Main module containing compliance restrictions, quality guidelines, and confidence signaling generation

## Core Functions/Classes

### `get_compliance_restrictions()`

#### Purpose
Generates comprehensive compliance restrictions in XML format that all agents must follow for legal, regulatory, and data sourcing compliance.

#### Parameters
* No parameters required

#### Returns
* **str**: XML-formatted compliance restrictions statement

#### Workflow
1. **Generate Legal Disclaimers**: Create disclaimers for legal/tax/regulatory advice limitations
2. **Add Verification Requirements**: Include requirements for RBC Finance specialist verification
3. **Set Confidentiality Rules**: Define internal use only restrictions
4. **Define Scope Boundaries**: Establish out-of-scope handling procedures
5. **Enforce Data Sourcing**: Specify exclusive use of provided context only

#### Error Handling
* **Exception**: Generic exception handling with logging, returns basic fallback disclaimer

### `get_quality_guidelines()`

#### Purpose
Generates quality standards in XML format that establish consistent formatting, citation, and content requirements for all agent outputs.

#### Parameters
* No parameters required

#### Returns
* **str**: XML-formatted quality guidelines statement

#### Workflow
1. **Set Structural Standards**: Define clear formatting requirements with headings and sections
2. **Establish Citation Rules**: Specify precise citation format for policies and standards
3. **Define Content Standards**: Set requirements for complex topics, examples, and language clarity
4. **Add Source Attribution**: Require noting sources consulted from provided context

#### Error Handling
* **Exception**: Generic exception handling with logging, returns basic quality requirements

### `get_confidence_signaling()`

#### Purpose
Generates guidelines in XML format for indicating confidence levels in responses based on source quality, consistency, and availability of information.

#### Parameters
* No parameters required

#### Returns
* **str**: XML-formatted confidence signaling guidelines

#### Workflow
1. **Define Confidence Levels**: Establish four confidence levels (high, medium, low, no confidence)
2. **Set Usage Criteria**: Specify when to use each confidence level based on source agreement and quality
3. **Provide Signal Examples**: Include sample language for each confidence level
4. **Format Guidelines**: Structure as XML with clear examples for each level

#### Error Handling
* **Exception**: Generic exception handling with logging, returns basic confidence signaling reminder

### `get_restrictions_statement()`

#### Purpose
Generates a comprehensive statement combining all compliance restrictions, quality guidelines, and confidence signaling in a single XML-formatted block for agent prompts.

#### Parameters
* No parameters required

#### Returns
* **str**: XML-formatted combined restrictions and guidelines statement

#### Workflow
1. **Get Compliance Restrictions**: Call get_compliance_restrictions() to get compliance rules
2. **Get Quality Guidelines**: Call get_quality_guidelines() to get quality standards
3. **Get Confidence Signaling**: Call get_confidence_signaling() to get confidence guidelines
4. **Combine Statements**: Merge all three components into unified XML structure
5. **Return Combined Statement**: Provide complete statement for agent prompt inclusion

#### Error Handling
* **Exception**: Generic exception handling with logging, returns basic combined fallback statement

## Configuration

No external configuration required. The module uses hardcoded compliance and quality control definitions:

* **Compliance Restrictions**: Fixed legal disclaimers, verification requirements, and data sourcing rules
* **Quality Guidelines**: Standard formatting, citation, and content quality requirements
* **Confidence Signaling**: Predefined confidence levels with usage criteria and example language

## Usage Examples

### Individual Components
```python
from iris.src.global_prompts.restrictions_statement import (
    get_compliance_restrictions,
    get_quality_guidelines,
    get_confidence_signaling
)

# Get specific components
compliance = get_compliance_restrictions()
quality = get_quality_guidelines()
confidence = get_confidence_signaling()
```

### Combined Statement
```python
from iris.src.global_prompts.restrictions_statement import get_restrictions_statement

# Get comprehensive restrictions
all_restrictions = get_restrictions_statement()
```

### Integration in Agent Prompts
```python
# In agent system prompt construction
from iris.src.global_prompts.restrictions_statement import get_restrictions_statement

system_prompt = f"""
[Agent-specific context]

{get_restrictions_statement()}

[Agent-specific instructions]
"""
```

## Integration Points

This module is used throughout the IRIS system:

### All Agent Types
* **Router Agent**: Ensures compliant routing decisions
* **Clarifier Agent**: Maintains compliance during query refinement
* **Planner Agent**: Ensures compliant database selection
* **Database Subagents**: Enforces compliance during research synthesis
* **Summarizer Agent**: Maintains compliance during final synthesis
* **Direct Response Agent**: Ensures conversational responses remain compliant

### Quality Assurance
* **Consistent Standards**: All agents follow same quality guidelines
* **Compliance Monitoring**: Restrictions help prevent non-compliant outputs
* **User Expectations**: Sets appropriate expectations for system capabilities

## Key Enforcement Areas

### Data Sourcing Control
* **Strict Source Control**: Only provided context used for responses
* **No External Knowledge**: Prevents AI hallucination or unsourced information
* **Conversation Continuity**: Maintains source traceability in conversations

### Professional Standards
* **Appropriate Disclaimers**: Ensures professional accountability
* **Specialist Consultation**: Directs users to appropriate experts
* **Scope Boundaries**: Maintains system focus on finance policy

### Quality Consistency
* **Structural Standards**: Consistent response formatting
* **Citation Requirements**: Proper attribution of sources
* **Confidence Transparency**: Clear indication of information reliability

## Dependencies

* **logging**: For error handling and debugging

## Error Handling

Comprehensive error handling approach:

* **Exception in get_compliance_restrictions**: Catches all exceptions during compliance statement generation and returns basic disclaimer fallback
* **Exception in get_quality_guidelines**: Catches all exceptions during quality guidelines generation and returns basic formatting requirements
* **Exception in get_confidence_signaling**: Catches all exceptions during confidence guidelines generation and returns basic confidence reminder
* **Exception in get_restrictions_statement**: Catches all exceptions during combined statement generation and returns basic combined fallback
* **Logging**: All errors are logged with appropriate context for debugging
* **Fallback Behavior**: System continues with basic guidance even if full statement generation fails

## Security Considerations

* **No External Input**: Module only uses hardcoded content, no user input processing required
* **No Sensitive Data**: Only processes compliance and quality guidelines without sensitive information
* **Static Content**: Uses predefined restrictions and guidelines, no external data sources
* **Safe Fallbacks**: Fallback statements provide essential compliance guidance without exposing sensitive details

## Performance Notes

* **Lightweight Operations**: Simple string formatting and concatenation with minimal processing overhead
* **No Caching Required**: Statement generation is fast enough to perform on-demand for each request
* **Memory Efficient**: Uses basic string operations and predefined content blocks
* **No Network Dependencies**: All operations performed locally using hardcoded content

---

This module ensures all IRIS agents maintain consistent compliance, quality, and professional standards while providing clear guidance for appropriate confidence signaling based on source quality.