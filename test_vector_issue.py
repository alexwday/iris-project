#!/usr/bin/env python3
"""
Diagnostic script to test vector similarity issue in iris_semantic_search table.
This will help identify why cosine distance returns NULL.
"""

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
import json
import numpy as np
from services.src.initial_setup.env_config import config
from services.src.initial_setup.db_config import connect_to_db

def diagnose_vector_issue():
    """Diagnose why vector similarity returns NULL."""
    
    print("=" * 80)
    print("VECTOR SIMILARITY DIAGNOSTIC TEST")
    print("=" * 80)
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    # Register pgvector
    register_vector(conn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    print("\n1. CHECKING TABLE STRUCTURE")
    print("-" * 40)
    
    # Check both tables' embedding column types
    for table in ['iris_textbook_database', 'iris_semantic_search']:
        cur.execute("""
            SELECT 
                column_name,
                data_type,
                udt_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'embedding';
        """, (table,))
        
        result = cur.fetchone()
        if result:
            print(f"{table}:")
            print(f"  column_name: {result['column_name']}")
            print(f"  data_type: {result['data_type']}")
            print(f"  udt_name: {result['udt_name']}")
        else:
            print(f"{table}: No embedding column found")
    
    print("\n2. CHECKING VECTOR DATA FORMAT")
    print("-" * 40)
    
    # Get sample vectors from both tables
    for table in ['iris_textbook_database', 'iris_semantic_search']:
        print(f"\n{table}:")
        
        # Get a sample embedding
        cur.execute(f"""
            SELECT 
                id,
                embedding,
                embedding IS NULL as is_null,
                pg_typeof(embedding) as pg_type
            FROM {table}
            WHERE embedding IS NOT NULL
            LIMIT 1;
        """)
        
        row = cur.fetchone()
        if row:
            print(f"  ID: {row['id']}")
            print(f"  Is NULL: {row['is_null']}")
            print(f"  PG Type: {row['pg_type']}")
            
            # Try to get the raw vector data
            if row['embedding']:
                # Convert to string to see format
                embedding_str = str(row['embedding'])
                print(f"  Embedding preview: {embedding_str[:100]}...")
                
                # Try to get dimensions
                try:
                    cur.execute(f"""
                        SELECT array_length(embedding::real[], 1) as dimensions
                        FROM {table}
                        WHERE id = %s;
                    """, (row['id'],))
                    dim_result = cur.fetchone()
                    if dim_result:
                        print(f"  Dimensions: {dim_result['dimensions']}")
                except Exception as e:
                    print(f"  Could not get dimensions: {e}")
        else:
            print("  No rows with embeddings found")
    
    print("\n3. TESTING VECTOR SIMILARITY CALCULATION")
    print("-" * 40)
    
    # Create a test query vector (2000 dimensions of 0.1)
    test_vector = [0.1] * 2000
    
    # Test on working table first
    print("\nTesting on iris_textbook_database (working):")
    try:
        cur.execute("""
            SELECT 
                id,
                1 - (embedding <=> %s::vector) as similarity,
                embedding <=> %s::vector as distance
            FROM iris_textbook_database
            WHERE embedding IS NOT NULL
            LIMIT 3;
        """, (test_vector, test_vector))
        
        results = cur.fetchall()
        for row in results:
            print(f"  ID {row['id']}: similarity={row['similarity']}, distance={row['distance']}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test on broken table
    print("\nTesting on iris_semantic_search (broken):")
    try:
        cur.execute("""
            SELECT 
                id,
                1 - (embedding <=> %s::vector) as similarity,
                embedding <=> %s::vector as distance
            FROM iris_semantic_search
            WHERE embedding IS NOT NULL
            LIMIT 3;
        """, (test_vector, test_vector))
        
        results = cur.fetchall()
        for row in results:
            sim = row['similarity']
            dist = row['distance']
            print(f"  ID {row['id']}: similarity={sim}, distance={dist}")
            if sim is None:
                print("    ⚠️  NULL similarity detected!")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n4. CHECKING VECTOR VALIDITY")
    print("-" * 40)
    
    # Check if vectors contain invalid values (NaN, Inf)
    for table in ['iris_semantic_search']:
        print(f"\nChecking {table} for invalid values:")
        
        # Get a raw embedding and check its content
        cur.execute(f"""
            SELECT 
                id,
                embedding::text as embedding_text
            FROM {table}
            WHERE embedding IS NOT NULL
            LIMIT 1;
        """)
        
        row = cur.fetchone()
        if row:
            embedding_text = row['embedding_text']
            # Check for NaN or Inf in the text representation
            if 'NaN' in embedding_text:
                print(f"  ⚠️  Found NaN in embedding!")
            if 'Inf' in embedding_text or 'inf' in embedding_text:
                print(f"  ⚠️  Found Infinity in embedding!")
            
            # Try to parse and validate
            try:
                # Remove brackets and split
                values_str = embedding_text.strip('[]')
                values = [float(v) for v in values_str.split(',')]
                
                # Check for invalid values
                nan_count = sum(1 for v in values if np.isnan(v))
                inf_count = sum(1 for v in values if np.isinf(v))
                
                print(f"  Parsed {len(values)} values")
                print(f"  NaN count: {nan_count}")
                print(f"  Inf count: {inf_count}")
                
                if nan_count > 0 or inf_count > 0:
                    print("  ❌ INVALID VALUES FOUND - This causes NULL distances!")
                else:
                    print("  ✅ All values are valid numbers")
                    
                # Show value range
                valid_values = [v for v in values if not np.isnan(v) and not np.isinf(v)]
                if valid_values:
                    print(f"  Value range: [{min(valid_values):.6f}, {max(valid_values):.6f}]")
                    
            except Exception as e:
                print(f"  Could not parse embedding: {e}")
    
    print("\n5. ATTEMPTING FIX")
    print("-" * 40)
    
    # Check if we can fix by re-casting
    print("\nTrying to identify the exact issue...")
    
    cur.execute("""
        SELECT 
            id,
            substring(embedding::text, 1, 200) as embedding_start
        FROM iris_semantic_search
        WHERE embedding IS NOT NULL
        LIMIT 5;
    """)
    
    for row in cur.fetchall():
        print(f"\nID {row['id']}:")
        print(f"  Start of embedding: {row['embedding_start']}...")
        
        # Check if it looks like a valid vector format
        if row['embedding_start'].startswith('[') and ',' in row['embedding_start']:
            print("  ✅ Format looks correct")
        else:
            print("  ❌ Format looks incorrect")
    
    # Close connection
    cur.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_vector_issue()