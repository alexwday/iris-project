#!/usr/bin/env python
"""
Script to insert test data into local PostgreSQL database for the IRIS project.
"""
import sys
import os
import psycopg2
from datetime import datetime

# Connection parameters for local PostgreSQL
LOCAL_DB_PARAMS = {
    "host": "localhost",
    "port": "5432",
    "dbname": "maven-finance",
    "user": "iris_dev",
    "password": "",  # No password needed for local development
}


def insert_test_data():
    """
    Insert test data into the database.
    """
    # Initialize connection and cursor variables
    conn = None
    cursor = None

    try:
        # Connect to database
        print(
            f"Connecting to {LOCAL_DB_PARAMS['dbname']} at {LOCAL_DB_PARAMS['host']}:{LOCAL_DB_PARAMS['port']}..."
        )
        conn = psycopg2.connect(**LOCAL_DB_PARAMS)
        print("Connected successfully! 🎉")

        # Create a cursor
        cursor = conn.cursor()

        # Clear existing data
        print("Clearing existing data...")
        cursor.execute(
            "TRUNCATE TABLE apg_catalog, apg_content RESTART IDENTITY CASCADE;"
        )

        # Insert catalog records
        print("Inserting catalog records...")
        catalog_records = [
            (
                "internal_wiki",
                "ifrs_standard",
                "IFRS_15_Revenue",
                "IFRS 15 Revenue from Contracts with Customers: Addresses the principles for recognizing revenue from contracts with customers. Establishes a five-step model for revenue recognition.",
                datetime.fromisoformat("2025-03-27 13:52:12-04:00"),
                datetime.fromisoformat("2025-03-27 13:52:12-04:00"),
                "IFRS_15_Revenue.md",
                ".md",
                "//wiki/finance/standards/",
            ),
            (
                "internal_wiki",
                "ifrs_standard",
                "IAS_12_IncomeTaxes",
                "IAS 12 Income Taxes: Prescribes the accounting treatment for income taxes. Addresses the current and future tax consequences of transactions and events.",
                datetime.fromisoformat("2025-03-27 13:52:12-04:00"),
                datetime.fromisoformat("2025-03-27 13:52:12-04:00"),
                "IAS_12_IncomeTaxes.md",
                ".md",
                "//wiki/finance/standards/",
            ),
            (
                "internal_wiki",
                "internal_memo",
                "Q1_2025_Financial_Analysis",
                "Internal analysis of Q1 2025 financial performance across business units. Includes variance analysis and forecasting adjustments.",
                datetime.fromisoformat("2025-03-27 13:52:12-04:00"),
                datetime.fromisoformat("2025-03-27 13:52:12-04:00"),
                "Q1_2025_Financial_Analysis.md",
                ".md",
                "//wiki/finance/memos/",
            ),
        ]

        for record in catalog_records:
            cursor.execute(
                """
                INSERT INTO apg_catalog 
                (document_source, document_type, document_name, document_description, 
                date_created, date_last_modified, file_name, file_type, file_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                record,
            )

        # Insert content records
        print("Inserting content records...")
        content_records = [
            # IFRS 15 Records
            (
                "internal_wiki",
                "ifrs_standard",
                "IFRS_15_Revenue",
                0,
                None,
                None,
                """# Record Information

- **Year:** 15
- **Published:** 2014

# Standards and Classification

- **IFRS Standard 15**: Revenue from Contracts with Customers

This standard establishes a comprehensive framework for determining when to recognize revenue and how much revenue to recognize. The core principle is that an entity should recognize revenue to depict the transfer of promised goods or services to customers in an amount that reflects the consideration to which the entity expects to be entitled in exchange for those goods or services.""",
            ),
            (
                "internal_wiki",
                "ifrs_standard",
                "IFRS_15_Revenue",
                1,
                "Five-Step Model",
                "The five-step model for revenue recognition under IFRS 15",
                """# Five-Step Model for Revenue Recognition

1. **Identify the contract(s) with a customer**
2. **Identify the performance obligations in the contract**
3. **Determine the transaction price**
4. **Allocate the transaction price to the performance obligations**
5. **Recognize revenue when (or as) the entity satisfies a performance obligation**

This model applies to all contracts with customers except leases, insurance contracts, financial instruments, and certain non-monetary exchanges.""",
            ),
            # IAS 12 Records
            (
                "internal_wiki",
                "ifrs_standard",
                "IAS_12_IncomeTaxes",
                0,
                None,
                None,
                """# Record Information

- **Year:** 12
- **Revised:** 2023

# Standards and Classification

- **IAS 12**: Income Taxes

This standard prescribes the accounting treatment for income taxes. It addresses both current tax and deferred tax consequences.""",
            ),
            # Q1 2025 Financial Analysis Records
            (
                "internal_wiki",
                "internal_memo",
                "Q1_2025_Financial_Analysis",
                0,
                None,
                None,
                """# Record Information

- **Quarter:** Q1
- **Year:** 2025
- **Department:** Finance

# Executive Summary

This document presents the financial analysis for Q1 2025. Key performance indicators show a 12% increase in revenue compared to the previous quarter, with operating margin improving by 2.5 percentage points.""",
            ),
            (
                "internal_wiki",
                "internal_memo",
                "Q1_2025_Financial_Analysis",
                1,
                "Revenue Analysis",
                "Breakdown of Q1 2025 revenue by business unit and product line",
                """# Revenue Analysis

## Business Unit Performance
- **North America**: $245.6M (+15.2% YoY)
- **EMEA**: $198.3M (+8.7% YoY)
- **APAC**: $156.9M (+22.3% YoY)

## Product Line Performance
- **Enterprise Solutions**: $312.4M (+18.1% YoY)
- **Consumer Products**: $189.5M (+5.3% YoY)
- **Professional Services**: $98.9M (+12.8% YoY)""",
            ),
            (
                "internal_wiki",
                "internal_memo",
                "Q1_2025_Financial_Analysis",
                2,
                "Cost Structure",
                "Analysis of Q1 2025 cost structure and efficiency metrics",
                """# Cost Structure Analysis

## Operating Expenses
- **Cost of Goods Sold**: $285.3M (47.5% of revenue)
- **R&D**: $84.7M (14.1% of revenue)
- **Sales & Marketing**: $95.2M (15.8% of revenue)
- **G&A**: $42.6M (7.1% of revenue)

## Efficiency Metrics
- **Gross Margin**: 52.5% (+1.8pp YoY)
- **Operating Margin**: 15.5% (+2.5pp YoY)
- **Net Margin**: 12.3% (+1.9pp YoY)""",
            ),
        ]

        for record in content_records:
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
        print("Data insertion completed successfully! 🎉")

        # Verify the inserted data
        cursor.execute("SELECT COUNT(*) FROM apg_catalog")
        catalog_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM apg_content")
        content_count = cursor.fetchone()[0]

        print(f"Inserted {catalog_count} records into apg_catalog")
        print(f"Inserted {content_count} records into apg_content")

        # Show catalog records
        print("\nCatalog records:")
        cursor.execute(
            "SELECT id, document_source, document_type, document_name FROM apg_catalog"
        )
        for row in cursor.fetchall():
            print(f"  - ID {row[0]}: {row[1]} / {row[2]} / {row[3]}")

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
