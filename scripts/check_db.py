#!/usr/bin/env python
"""
Script to check the database connection and current data in tables.
"""
import sys
import os
import psycopg2

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from iris.src.initial_setup.db_config import get_db_params

def check_database():
    """
    Check database connection and current data.
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
        print("Connected successfully! 🎉")
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Check catalog records
        cursor.execute("SELECT COUNT(*) FROM apg_catalog")
        catalog_count = cursor.fetchone()[0]
        print(f"Current apg_catalog record count: {catalog_count}")
        
        # Check content records
        cursor.execute("SELECT COUNT(*) FROM apg_content")
        content_count = cursor.fetchone()[0]
        print(f"Current apg_content record count: {content_count}")
        
        # Show summary of document sources
        cursor.execute("SELECT document_source, COUNT(*) FROM apg_catalog GROUP BY document_source")
        sources = cursor.fetchall()
        print("\nDocument sources in apg_catalog:")
        for source, count in sources:
            print(f"  - {source}: {count} records")
        
        # Show sample records
        if catalog_count > 0:
            print("\nSample record from apg_catalog:")
            cursor.execute("SELECT * FROM apg_catalog LIMIT 1")
            sample = cursor.fetchone()
            print(f"  ID: {sample[0]}")
            print(f"  Created at: {sample[1]}")
            print(f"  Document source: {sample[2]}")
            print(f"  Document type: {sample[3]}")
            print(f"  Document name: {sample[4]}")
            print(f"  Document description: {sample[5]}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    check_database()