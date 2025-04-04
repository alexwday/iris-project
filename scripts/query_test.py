#!/usr/bin/env python
"""
Script to test querying the local PostgreSQL database.
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from iris.src.initial_setup.db_config import connect_to_db, check_tables_exist


def test_database_query():
    """
    Test querying the database for internal_wiki documents.
    """
    # Connect to database
    conn = connect_to_db("local")

    if not conn:
        print("Failed to connect to database!")
        return

    try:
        # Check if tables exist
        tables = check_tables_exist(conn)
        print(f"Found tables: {tables}")

        # Query documents by source
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT document_source, document_type, document_name, document_description
                FROM apg_catalog
                WHERE document_source = 'internal_wiki'
            """
            )

            print("\nDocuments with source 'internal_wiki':")
            for row in cur.fetchall():
                print(f"  - {row[1]}: {row[2]}")
                print(f"    Description: {row[3][:50]}...")

            # Query document content
            cur.execute(
                """
                SELECT c.document_name, ct.section_id, ct.section_name, ct.section_summary
                FROM apg_catalog c
                JOIN apg_content ct ON 
                    c.document_source = ct.document_source AND
                    c.document_type = ct.document_type AND
                    c.document_name = ct.document_name
                WHERE c.document_source = 'internal_wiki'
                ORDER BY c.document_name, ct.section_id
            """
            )

            print("\nDocument sections:")
            for row in cur.fetchall():
                doc_name = row[0]
                section_id = row[1]
                section_name = row[2] if row[2] else "Main Section"
                section_summary = row[3][:50] + "..." if row[3] else "No summary"

                print(f"  - {doc_name}, Section {section_id}: {section_name}")
                print(f"    Summary: {section_summary}")

    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    test_database_query()
