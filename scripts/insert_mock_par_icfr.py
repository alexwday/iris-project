#\!/usr/bin/env python
"""
Script to insert mock PAR and ICFR test data into PostgreSQL database for the IRIS project.
"""
import sys
import os
import psycopg2
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from iris.src.initial_setup.db_config import get_db_params


def insert_test_data():
    """
    Insert PAR and ICFR test data into the database.
    """
    # Get database parameters
    db_params = get_db_params("local")

    # Initialize connection and cursor variables
    conn = None
    cursor = None

    try:
        # Connect to database
        print(
            f"Connecting to {db_params['dbname']} at {db_params['host']}:{db_params['port']}..."
        )
        conn = psycopg2.connect(**db_params)
        print("Connected successfully\! 🎉")

        # Create a cursor
        cursor = conn.cursor()

        # Insert PAR catalog records
        print("Inserting PAR catalog records...")
        par_catalog_records = [
            (
                "internal_par",
                "approval_guideline",
                "PAR_Standard_Process",
                "Project Approval Request standard process guideline. Details key steps, stakeholder roles, and documentation requirements for project approval submissions.",
                datetime.fromisoformat("2025-02-15 10:30:00-04:00"),
                datetime.fromisoformat("2025-03-10 14:45:22-04:00"),
                "PAR_Standard_Process.md",
                ".md",
                "//par/guidelines/",
            ),
            (
                "internal_par",
                "threshold_policy",
                "PAR_Approval_Thresholds",
                "Financial thresholds and authorization levels for Project Approval Requests. Defines approval requirements based on project size, risk level, and business unit.",
                datetime.fromisoformat("2025-02-18 09:15:00-04:00"),
                datetime.fromisoformat("2025-03-05 11:30:45-04:00"),
                "PAR_Approval_Thresholds.md",
                ".md",
                "//par/policies/",
            ),
            (
                "internal_par",
                "template_guide",
                "PAR_Template_Guide",
                "Guidance for completing the standard Project Approval Request template. Includes section-by-section instructions, examples, and common pitfalls to avoid.",
                datetime.fromisoformat("2025-01-25 13:45:00-04:00"),
                datetime.fromisoformat("2025-03-01 10:20:30-04:00"),
                "PAR_Template_Guide.md",
                ".md",
                "//par/templates/",
            ),
        ]

        for record in par_catalog_records:
            cursor.execute(
                """
                INSERT INTO apg_catalog 
                (document_source, document_type, document_name, document_description, 
                date_created, date_last_modified, file_name, file_type, file_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                record,
            )

        # Insert ICFR catalog records
        print("Inserting ICFR catalog records...")
        icfr_catalog_records = [
            (
                "internal_icfr",
                "policy_manual",
                "ICFR_Framework_Overview",
                "Internal Control over Financial Reporting (ICFR) framework overview. Describes regulatory requirements, control objectives, and RBC's implementation approach.",
                datetime.fromisoformat("2025-01-10 09:00:00-04:00"),
                datetime.fromisoformat("2025-02-28 16:15:20-04:00"),
                "ICFR_Framework_Overview.md",
                ".md",
                "//icfr/framework/",
            ),
            (
                "internal_icfr",
                "control_documentation",
                "ICFR_Control_Documentation_Standards",
                "Standards for documenting financial controls. Includes required elements for control descriptions, test procedures, evidence requirements, and deficiency reporting.",
                datetime.fromisoformat("2025-01-12 11:30:00-04:00"),
                datetime.fromisoformat("2025-02-15 14:45:00-04:00"),
                "ICFR_Control_Documentation_Standards.md",
                ".md",
                "//icfr/standards/",
            ),
            (
                "internal_icfr",
                "testing_guideline",
                "ICFR_Testing_Methodology",
                "Methodology for testing controls effectiveness within the ICFR program. Covers sampling approaches, testing frequency, evidence evaluation, and deficiency assessment.",
                datetime.fromisoformat("2025-01-15 14:15:00-04:00"),
                datetime.fromisoformat("2025-03-01 09:30:40-04:00"),
                "ICFR_Testing_Methodology.md",
                ".md",
                "//icfr/testing/",
            ),
        ]

        for record in icfr_catalog_records:
            cursor.execute(
                """
                INSERT INTO apg_catalog 
                (document_source, document_type, document_name, document_description, 
                date_created, date_last_modified, file_name, file_type, file_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                record,
            )

        # Insert PAR content records
        print("Inserting PAR content records...")
        par_content_records = [
            # PAR Standard Process Records
            (
                "internal_par",
                "approval_guideline",
                "PAR_Standard_Process",
                0,
                "Introduction",
                "Overview of the Project Approval Request process at RBC",
                """# Project Approval Request (PAR) Process Introduction

This document outlines the standard process for Project Approval Requests (PARs) at RBC. The PAR process ensures capital investments and projects align with corporate strategy and financial requirements.

## Purpose

The PAR process provides governance for:
- Strategic alignment of projects with business objectives
- Financial oversight and resource allocation
- Risk assessment and mitigation planning
- Transparency in decision-making
- Accountability for project outcomes""",
            ),
            (
                "internal_par",
                "approval_guideline",
                "PAR_Standard_Process",
                1,
                "Approval Stages",
                "Key stages in the PAR approval workflow",
                """# PAR Approval Stages

The standard PAR process follows these key stages:

## 1. Initial Proposal
- Business unit prepares initial project concept
- High-level scope, objectives, and business case
- Initial cost estimate and timeline
- Preliminary risk assessment

## 2. Detailed PAR Development
- Comprehensive business case with financial analysis
- Detailed project plan and timeline
- Resource requirements and allocation plan
- Risk assessment and mitigation strategies
- Technical feasibility evaluation

## 3. Review and Recommendation
- Business unit review and sign-off
- Finance department validation of financial projections
- Risk and compliance assessment
- Technology and operations review (if applicable)

## 4. Final Approval
- Submission to appropriate approval authority based on thresholds
- Presentation to approval committee
- Decision: Approved, Rejected, or Returned for Revision

## 5. Post-Approval
- Funding release and project initiation
- Regular status reporting requirements
- Change management process for scope/budget changes
- Post-implementation review requirements""",
            ),
            # PAR Approval Thresholds Records
            (
                "internal_par",
                "threshold_policy",
                "PAR_Approval_Thresholds",
                0,
                "Overview",
                "Introduction to approval thresholds for Project Approval Requests",
                """# PAR Approval Thresholds Overview

This document defines the financial thresholds and approval authorities for Project Approval Requests (PARs) at RBC. All capital expenditures and significant projects must follow these approval requirements.

## Purpose

The approval thresholds:
- Ensure appropriate oversight based on project size and risk
- Clarify governance and decision-making authorities
- Promote consistent application of approval requirements
- Support effective capital allocation and governance""",
            ),
            (
                "internal_par",
                "threshold_policy",
                "PAR_Approval_Thresholds",
                1,
                "Financial Thresholds",
                "Threshold amounts and corresponding approval authorities",
                """# Financial Approval Thresholds

Project approval requirements are determined by total project value and categorized as follows:

## Threshold Categories

| Project Value (CAD) | Approval Authority | Documentation Required |
|---------------------|-------------------|------------------------|
| < $100,000 | Business Unit Leader | Simplified PAR Form |
| $100,000 - $500,000 | Group Head/EVP | Standard PAR Package |
| $500,000 - $2,000,000 | Senior EVP/CFO/CRO | Enhanced PAR Package |
| $2,000,000 - $5,000,000 | Executive Committee | Full PAR Package + Presentation |
| > $5,000,000 | Board of Directors | Full PAR Package + Board Presentation |

## Multi-Year Projects
Projects spanning multiple fiscal years require approval based on the total project value, not annual expenditure.

## Technology Projects
Technology projects have additional review requirements through the Technology Investment Committee regardless of financial threshold.""",
            ),
            # PAR Template Guide Records
            (
                "internal_par",
                "template_guide",
                "PAR_Template_Guide",
                0,
                "Introduction",
                "Introduction to the PAR template and its purpose",
                """# PAR Template Guide Introduction

This guide provides instructions for completing the standard Project Approval Request (PAR) template. Following these guidelines ensures consistency and thoroughness in project proposals.

## Template Purpose

The PAR template is designed to:
- Standardize project proposals across the organization
- Ensure all critical aspects of a project are addressed
- Facilitate efficient review and approval processes
- Create a record for post-implementation review
- Support governance and compliance requirements""",
            ),
            (
                "internal_par",
                "template_guide",
                "PAR_Template_Guide",
                1,
                "Executive Summary Section",
                "Guidelines for completing the executive summary section",
                """# Executive Summary Section

The Executive Summary is the most critical section of your PAR as many senior approvers may read only this section.

## Required Elements

1. **Project Purpose (2-3 sentences)**
   - Clearly state what the project will accomplish
   - Highlight primary business objective(s)
   - Avoid technical jargon and acronyms

2. **Strategic Alignment (2-3 sentences)**
   - Explain how the project supports strategic priorities
   - Reference specific corporate or business unit strategies

3. **Financial Summary**
   - Total project cost
   - Key financial metrics (NPV, IRR, Payback Period)
   - High-level cost breakdown

4. **Timeline**
   - Proposed start date
   - Key milestone dates
   - Proposed completion date

5. **Key Benefits**
   - Quantitative benefits (cost savings, revenue generation)
   - Qualitative benefits (improved service, risk reduction)

## Best Practices

- Keep to one page maximum
- Use bullet points for clarity
- Focus on business outcomes, not technical details
- Include key metrics and measures of success
- Highlight critical dependencies or risks""",
            ),
        ]

        for record in par_content_records:
            cursor.execute(
                """
                INSERT INTO apg_content
                (document_source, document_type, document_name, section_id, section_name, section_summary, section_content)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                record,
            )

        # Insert ICFR content records
        print("Inserting ICFR content records...")
        icfr_content_records = [
            # ICFR Framework Overview Records
            (
                "internal_icfr",
                "policy_manual",
                "ICFR_Framework_Overview",
                0,
                "Introduction",
                "Introduction to the ICFR framework and regulatory context",
                """# Internal Control over Financial Reporting (ICFR) Framework

## Introduction

This document provides an overview of RBC's Internal Control over Financial Reporting (ICFR) framework. ICFR encompasses the policies, procedures, and practices designed to provide reasonable assurance regarding the reliability of financial reporting and the preparation of financial statements.

## Regulatory Context

RBC's ICFR program complies with:
- Canadian Securities Administrators' National Instrument 52-109
- Sarbanes-Oxley Act (SOX) Section 404 requirements
- OSFI Corporate Governance Guidelines
- NYSE Listed Company Manual Section 303A

These regulations require management to establish and maintain adequate internal controls over financial reporting and to assess their effectiveness annually.""",
            ),
            (
                "internal_icfr",
                "policy_manual",
                "ICFR_Framework_Overview",
                1,
                "Framework Components",
                "Core components of the ICFR framework based on COSO principles",
                """# ICFR Framework Components

RBC's ICFR framework is based on the Committee of Sponsoring Organizations of the Treadway Commission (COSO) Internal Control - Integrated Framework (2013). The framework consists of five integrated components:

## 1. Control Environment
- Integrity and ethical values
- Board and audit committee oversight
- Organizational structure and reporting lines
- Authority and responsibility assignment
- Personnel competence and accountability
- Performance measures and incentives

## 2. Risk Assessment
- Financial reporting objectives
- Risk identification and analysis
- Fraud risk consideration
- Change management assessment

## 3. Control Activities
- Policy and procedure development
- Control selection and development
- Technology controls implementation
- Deployment through policies and procedures

## 4. Information and Communication
- Relevant information identification
- Internal communication channels
- External communication processes

## 5. Monitoring Activities
- Ongoing and separate evaluations
- Deficiency evaluation and communication
- Remediation tracking and resolution

Each component is supported by principles and points of focus that guide the implementation and assessment of controls.""",
            ),
            # ICFR Control Documentation Standards Records
            (
                "internal_icfr",
                "control_documentation",
                "ICFR_Control_Documentation_Standards",
                0,
                "Documentation Purpose",
                "The purpose and importance of proper control documentation",
                """# Control Documentation Standards

## Purpose of Documentation

Proper documentation of internal controls is essential for:

1. **Compliance Requirements**
   - Meeting regulatory obligations for ICFR assessment
   - Supporting management certification of financial statements
   - Enabling external auditor reliance and testing

2. **Operational Efficiency**
   - Providing clear guidance for control execution
   - Ensuring consistency in control performance
   - Facilitating knowledge transfer and training

3. **Control Effectiveness**
   - Supporting comprehensive risk coverage
   - Enabling gap identification
   - Facilitating remediation of deficiencies

4. **Evidence Collection**
   - Creating standardized evidence requirements
   - Establishing testing criteria
   - Supporting effectiveness conclusions""",
            ),
            (
                "internal_icfr",
                "control_documentation",
                "ICFR_Control_Documentation_Standards",
                1,
                "Documentation Requirements",
                "Required elements for documenting financial controls",
                """# Control Documentation Requirements

All financial controls must include the following documentation elements:

## 1. Control Identification
- **Control ID:** Unique identifier
- **Control Name:** Descriptive title
- **Control Owner:** Position responsible for performance
- **Control Type:** Preventive/Detective, Manual/Automated
- **Control Frequency:** Daily, Weekly, Monthly, Quarterly, Annual
- **Risk Coverage:** Financial assertion(s) addressed

## 2. Control Design
- **Control Objective:** Specific risk(s) addressed
- **Control Description:** Detailed explanation of the control activity
- **Control Procedure:** Step-by-step process for execution
- **Systems Involved:** Applications or systems utilized
- **Input Requirements:** Data or information needed
- **Output/Deliverable:** Result of control execution

## 3. Testing Information
- **Test Approach:** Methods for testing effectiveness
- **Sample Size Requirements:** Based on frequency and population
- **Evidence Requirements:** Specific documentation needed
- **Evaluation Criteria:** Standards for pass/fail determination

## 4. Deficiency Handling
- **Remediation Process:** Steps for addressing failures
- **Compensating Controls:** Alternative controls if applicable
- **Escalation Procedures:** When and how to report issues
- **Impact Assessment:** Criteria for evaluating significance""",
            ),
            # ICFR Testing Methodology Records
            (
                "internal_icfr",
                "testing_guideline",
                "ICFR_Testing_Methodology",
                0,
                "Testing Approach",
                "Overview of the testing methodology for ICFR controls",
                """# ICFR Testing Methodology

## Testing Approach Overview

The testing methodology for Internal Control over Financial Reporting (ICFR) is designed to:
- Evaluate control design effectiveness
- Assess operating effectiveness over time
- Identify and remediate control deficiencies
- Support management's annual assertion on ICFR

## Testing Phases

The ICFR testing program follows these phases:

1. **Planning**
   - Annual risk assessment and scoping
   - Test schedule development
   - Resource allocation
   - Methodology updates and communication

2. **Design Effectiveness Testing**
   - Review of control documentation
   - Walkthrough procedures
   - Design gap identification
   - Remediation of design issues before operating effectiveness testing

3. **Operating Effectiveness Testing**
   - Execution of test procedures
   - Evidence collection and evaluation
   - Deficiency identification and classification
   - Results communication

4. **Reporting and Remediation**
   - Aggregation of test results
   - Deficiency evaluation
   - Remediation plan development
   - Follow-up testing
   - Final reporting to management and Audit Committee""",
            ),
            (
                "internal_icfr",
                "testing_guideline",
                "ICFR_Testing_Methodology",
                1,
                "Sampling Approach",
                "Guidelines for determining appropriate testing sample sizes",
                """# Sampling Approach

## Sample Size Determination

Sample sizes for control testing are based on control frequency and significance:

| Control Frequency | Standard Sample Size | Key Control Sample Size |
|-------------------|----------------------|-------------------------|
| Annual | 1 | 1 |
| Quarterly | 2 | 4 (all quarters) |
| Monthly | 3 | 6 (alternating months) |
| Weekly | 8 | 12 (distributed across year) |
| Daily | 15 | 25 (distributed across year) |

## Sample Selection Methodology

Samples must be selected using these principles:

1. **Representative Selection**
   - Cover the entire testing period
   - Include period-end instances
   - Incorporate high-risk periods (e.g., financial close)

2. **Risk-Based Considerations**
   - Include samples from high-volume periods
   - Select instances following system or process changes
   - Include instances from different operators if control is performed by multiple people

3. **Random Selection**
   - Use statistical randomization where possible
   - Document selection methodology
   - Avoid predictable patterns that might influence control performance

## Documentation Requirements

For each sample tested:
- Date of control execution
- Name of control performer
- Evidence examined
- Test results
- Exceptions noted
- Conclusion on effectiveness""",
            ),
        ]

        for record in icfr_content_records:
            cursor.execute(
                """
                INSERT INTO apg_content
                (document_source, document_type, document_name, section_id, section_name, section_summary, section_content)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                record,
            )

        # Commit the transaction
        conn.commit()
        print("Data insertion completed successfully\! 🎉")

        # Verify the inserted data
        cursor.execute("SELECT document_source, COUNT(*) FROM apg_catalog GROUP BY document_source")
        source_counts = cursor.fetchall()

        print("\nDocument counts by source:")
        for source, count in source_counts:
            print(f"  - {source}: {count} documents")

        cursor.execute("SELECT document_source, COUNT(*) FROM apg_content GROUP BY document_source")
        content_counts = cursor.fetchall()

        print("\nContent section counts by source:")
        for source, count in content_counts:
            print(f"  - {source}: {count} sections")

    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    insert_test_data()
