# -*- coding: utf-8 -*-
import dataiku
import pandas as pd
import psycopg2
import psycopg2.extras

# Register UUID adapter for PostgreSQL
psycopg2.extras.register_uuid()

# Hardcoded database connection parameters
# IMPORTANT: Replace these with your actual database credentials
DB_HOST = "your-postgres-host.rbc.com"
DB_PORT = "5432"
DB_NAME = "maven-finance"
DB_USER = "your-db-user"
DB_PASSWORD = "your-db-password"

# SSL Options - Try different configurations if certificate access is denied
# Option 1: Disable SSL (not recommended for production)
# sslmode = "disable"

# Option 2: Use SSL without certificate validation
# sslmode = "require"

# Option 3: Use SSL with full verification (requires certificate file access)
# sslmode = "verify-full"
# sslcert = "/path/to/client-cert.pem"
# sslkey = "/path/to/client-key.pem"
# sslrootcert = "/path/to/ca-cert.pem"

print(f"Connecting to PostgreSQL: host={DB_HOST}, port={DB_PORT}, dbname={DB_NAME}, user={DB_USER}")

try:
    # Create connection with SSL disabled
    # WARNING: This is not secure for production use
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode='disable'  # Disable SSL to avoid certificate permission issues
    )
    
    print("Database connection successful")
    
    # Query the apg_catalog table
    query = """
    SELECT * FROM apg_catalog
    ORDER BY id
    """
    
    # Read data into pandas DataFrame
    output_df = pd.read_sql_query(query, conn)
    
    print(f"Successfully read {len(output_df)} rows from apg_catalog table")
    print(f"Columns: {list(output_df.columns)}")
    
    # Close connection
    conn.close()
    print("Database connection closed")
    
except Exception as e:
    print(f"Error: {str(e)}")
    raise

# Write recipe outputs
output = dataiku.Dataset("output")
output.write_with_schema(output_df)

print("Recipe completed successfully")