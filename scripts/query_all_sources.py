#\!/usr/bin/env python
"""
Script to query all document sources in the database.
"""
import sys
import os
import psycopg2
from tabulate import tabulate  # Import the function directly

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from iris.src.initial_setup.db_config import get_db_params


def query_all_sources():
    """
    Query all document sources in the database and display detailed information.
    """
    # Get database parameters
    db_params = get_db_params("local")

    # Initialize connection and cursor variables
    conn = None
    cursor = None

    try:
        # Connect to database
        print(f"Connecting to {db_params['dbname']} at {db_params['host']}:{db_params['port']}...")
        conn = psycopg2.connect(**db_params)
        print("Connected successfully\! 🎉")

        # Create a cursor
        cursor = conn.cursor()

        # Get all document sources
        cursor.execute(
            "SELECT DISTINCT document_source FROM apg_catalog ORDER BY document_source"
        )
        sources = [row[0] for row in cursor.fetchall()]
        
        print(f"\nFound {len(sources)} document sources: {', '.join(sources)}")
        
        # For each source, show catalog entries
        for source in sources:
            print(f"\n{'=' * 80}")
            print(f"DOCUMENTS IN '{source.upper()}' DATABASE")
            print(f"{'=' * 80}\n")
            
            # Get catalog entries for this source
            cursor.execute(
                """
                SELECT id, document_type, document_name, document_description
                FROM apg_catalog
                WHERE document_source = %s
                ORDER BY document_type, document_name
                """,
                (source,)
            )
            
            documents = cursor.fetchall()
            
            # Format as table
            table_data = []
            for doc in documents:
                doc_id, doc_type, doc_name, doc_desc = doc
                # Truncate description if too long
                if doc_desc and len(doc_desc) > 60:
                    doc_desc = doc_desc[:57] + "..."
                table_data.append([doc_id, doc_type, doc_name, doc_desc])
            
            headers = ["ID", "Type", "Name", "Description"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            # For each document, show its sections
            for doc in documents:
                doc_id, doc_type, doc_name, _ = doc
                
                print(f"\nSections for {doc_name} (ID: {doc_id}):")
                
                # Get sections for this document
                cursor.execute(
                    """
                    SELECT section_id, section_name, section_summary
                    FROM apg_content
                    WHERE document_source = %s AND document_name = %s
                    ORDER BY section_id
                    """,
                    (source, doc_name)
                )
                
                sections = cursor.fetchall()
                
                # Format as table
                section_data = []
                for section in sections:
                    section_id, section_name, section_summary = section
                    section_name = section_name if section_name else "Main Section"
                    # Truncate summary if too long
                    if section_summary and len(section_summary) > 60:
                        section_summary = section_summary[:57] + "..."
                    elif not section_summary:
                        section_summary = "No summary"
                    section_data.append([section_id, section_name, section_summary])
                
                section_headers = ["Section ID", "Section Name", "Summary"]
                print(tabulate(section_data, headers=section_headers, tablefmt="simple"))
                print()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    query_all_sources()
