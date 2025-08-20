#!/usr/bin/env python3
"""
Script to identify and clean invalid vectors in the iris_semantic_search table.
This will help fix the NULL vector_score issue.
"""

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from services.src.initial_setup.env_config import config
from services.src.initial_setup.db_config import connect_to_db

def clean_invalid_vectors():
    """Identify and clean invalid vectors that cause NULL distances."""
    
    print("=" * 80)
    print("CLEANING INVALID VECTORS IN iris_semantic_search")
    print("=" * 80)
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        print("❌ Failed to connect to database")
        return
    
    # Register pgvector
    register_vector(conn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        # Step 1: Count total rows
        print("\n1. CHECKING CURRENT STATE")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(embedding) as rows_with_embedding,
                COUNT(CASE WHEN embedding IS NULL THEN 1 END) as rows_without_embedding
            FROM iris_semantic_search;
        """)
        
        stats = cur.fetchone()
        print(f"Total rows: {stats['total_rows']}")
        print(f"Rows with embeddings: {stats['rows_with_embedding']}")
        print(f"Rows without embeddings: {stats['rows_without_embedding']}")
        
        # Step 2: Identify invalid vectors
        print("\n2. IDENTIFYING INVALID VECTORS")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                id,
                document_id,
                chunk_number,
                substring(embedding::text, 1, 100) as embedding_preview
            FROM iris_semantic_search
            WHERE 
                embedding IS NOT NULL
                AND embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf'
            LIMIT 10;
        """)
        
        invalid_rows = cur.fetchall()
        
        if invalid_rows:
            print(f"❌ Found {len(invalid_rows)} rows with invalid vectors (showing first 10):")
            for row in invalid_rows:
                print(f"  ID {row['id']}: doc={row['document_id']}, chunk={row['chunk_number']}")
                print(f"    Preview: {row['embedding_preview']}...")
            
            # Step 3: Count total invalid vectors
            cur.execute("""
                SELECT COUNT(*) as invalid_count
                FROM iris_semantic_search
                WHERE 
                    embedding IS NOT NULL
                    AND embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf';
            """)
            
            invalid_count = cur.fetchone()['invalid_count']
            print(f"\nTotal invalid vectors found: {invalid_count}")
            
            # Step 4: Fix invalid vectors
            print("\n3. CLEANING INVALID VECTORS")
            print("-" * 40)
            
            response = input(f"Do you want to set these {invalid_count} invalid vectors to NULL? (y/n): ")
            
            if response.lower() == 'y':
                cur.execute("""
                    UPDATE iris_semantic_search
                    SET embedding = NULL
                    WHERE 
                        embedding IS NOT NULL
                        AND embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf';
                """)
                
                updated_count = cur.rowcount
                conn.commit()
                
                print(f"✅ Successfully cleaned {updated_count} invalid vectors")
            else:
                print("⏭️  Skipping cleanup")
        else:
            print("✅ No invalid vectors found!")
        
        # Step 5: Check for dimension mismatches
        print("\n4. CHECKING DIMENSION CONSISTENCY")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                array_length(embedding::real[], 1) as dimensions,
                COUNT(*) as count
            FROM iris_semantic_search
            WHERE embedding IS NOT NULL
            GROUP BY dimensions
            ORDER BY count DESC;
        """)
        
        dim_results = cur.fetchall()
        
        if dim_results:
            print("Dimension distribution:")
            for row in dim_results:
                print(f"  {row['dimensions']} dimensions: {row['count']} rows")
            
            # Check if any have wrong dimensions
            wrong_dim_count = sum(row['count'] for row in dim_results if row['dimensions'] != 2000)
            if wrong_dim_count > 0:
                print(f"\n⚠️  Found {wrong_dim_count} vectors with incorrect dimensions (should be 2000)")
                
                response = input(f"Do you want to set these to NULL? (y/n): ")
                
                if response.lower() == 'y':
                    cur.execute("""
                        UPDATE iris_semantic_search
                        SET embedding = NULL
                        WHERE 
                            embedding IS NOT NULL
                            AND array_length(embedding::real[], 1) != 2000;
                    """)
                    
                    updated_count = cur.rowcount
                    conn.commit()
                    
                    print(f"✅ Successfully nullified {updated_count} vectors with wrong dimensions")
        
        # Step 6: Test vector search after cleanup
        print("\n5. TESTING VECTOR SEARCH")
        print("-" * 40)
        
        # Create a test vector
        test_vector = [0.1] * 2000
        
        cur.execute("""
            SELECT 
                id,
                CASE 
                    WHEN embedding IS NULL THEN NULL
                    WHEN embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf' THEN NULL
                    ELSE 1 - (embedding::vector <=> %s::vector)
                END AS vector_score
            FROM iris_semantic_search
            WHERE 
                embedding IS NOT NULL
                AND NOT embedding::text ~ 'NaN|Infinity|-Infinity|Inf|-Inf'
                AND array_length(embedding::real[], 1) = 2000
            ORDER BY vector_score DESC NULLS LAST
            LIMIT 5;
        """, (test_vector,))
        
        results = cur.fetchall()
        
        if results:
            print("✅ Vector search is now working! Top 5 results:")
            for row in results:
                score = row['vector_score']
                if score is not None:
                    print(f"  ID {row['id']}: score={score:.4f}")
                else:
                    print(f"  ID {row['id']}: score=NULL (still has issues)")
        else:
            print("❌ No valid vectors found for testing")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print("\nThe subagent.py has been updated to handle invalid vectors automatically.")
    print("Future searches will exclude any remaining invalid vectors.")

if __name__ == "__main__":
    clean_invalid_vectors()