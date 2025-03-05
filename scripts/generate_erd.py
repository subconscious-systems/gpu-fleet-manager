#!/usr/bin/env python3
"""
Generate Entity Relationship Diagram (ERD) for GPU Fleet Manager Database

This script generates an ERD visualization from the database schema.
It outputs a visual diagram showing tables, relationships, and fields.

Requirements:
- Python 3.7+
- psycopg2
- eralchemy2

Usage:
    python generate_erd.py [output_file]

Arguments:
    output_file - Optional output file path (default: erd_output.png)
"""

import os
import sys
import argparse
from urllib.parse import urlparse
from eralchemy2 import render_er

def get_connection_string_from_env():
    """Get database connection string from environment variables."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse the URL to get components
    url = urlparse(database_url)
    
    # Construct a SQLAlchemy connection string
    if url.scheme == 'postgres' or url.scheme == 'postgresql':
        # Handle Supabase connection string (which might include sslmode)
        query = url.query.split('&')
        query_dict = {k: v for k, v in [q.split('=') for q in query if '=' in q]}
        
        # Construct SQLAlchemy connection string
        conn_str = f"postgresql://{url.username}:{url.password}@{url.hostname}:{url.port}/{url.path.lstrip('/')}"
        
        # Add SSL mode if present
        if 'sslmode' in query_dict:
            conn_str += f"?sslmode={query_dict['sslmode']}"
        
        return conn_str
    else:
        # Return the URL as is for other database types
        return database_url

def generate_erd(output_file='erd_output.png'):
    """Generate ERD from database schema."""
    try:
        # Get connection string from environment variable
        conn_str = get_connection_string_from_env()
        
        # Define table exclusion pattern (system tables, etc.)
        exclude_tables = [
            'pg_%', 'sql_%',             # PostgreSQL system tables
            'auth.%',                    # Supabase auth schema tables
            'storage.%',                 # Supabase storage schema tables
            'information_schema.%',      # Information schema tables
            'extensions'                 # PostgreSQL extensions
        ]
        
        # Build exclusion string
        exclude_str = ','.join(f"'{pattern}'" for pattern in exclude_tables)
        
        # Generate ERD
        # Note: We're specifying schema='public' to only get tables in the public schema
        render_er(conn_str, output_file, exclude_tables=exclude_str)
        
        print(f"ERD generated successfully: {output_file}")
        
    except Exception as e:
        print(f"Error generating ERD: {e}")
        sys.exit(1)

def main():
    """Parse arguments and generate ERD."""
    parser = argparse.ArgumentParser(description='Generate ERD for GPU Fleet Manager database')
    parser.add_argument('output_file', nargs='?', default='erd_output.png',
                        help='Output file path (default: erd_output.png)')
    args = parser.parse_args()
    
    generate_erd(args.output_file)

if __name__ == '__main__':
    main()
