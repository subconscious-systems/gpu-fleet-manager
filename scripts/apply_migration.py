#!/usr/bin/env python3
"""
Apply Database Migration to Supabase

This script applies the SQL migration files to your Supabase PostgreSQL database.
It reads the SQL files and executes them against the database using the connection
details from your environment variables.

Requirements:
- Python 3.7+
- psycopg2-binary
- python-dotenv

Usage:
    python apply_migration.py [migration_file]

Arguments:
    migration_file - Optional specific migration file to apply
                     (default: applies all migrations in order)
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from urllib.parse import urlparse
import glob
import re

# Load environment variables
load_dotenv()

def get_connection_from_env():
    """Get database connection from environment variables."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse the URL to get components
    url = urlparse(database_url)
    
    # Connect to the database
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.path.lstrip('/')
    )
    
    # Set isolation level to autocommit
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    return conn

def get_applied_migrations(conn):
    """Get a list of migrations that have already been applied."""
    try:
        cursor = conn.cursor()
        
        # Check if the migrations table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'migrations'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            # Create migrations table if it doesn't exist
            cursor.execute("""
                CREATE TABLE migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            return []
        
        # Get list of applied migrations
        cursor.execute("SELECT name FROM migrations ORDER BY id;")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting applied migrations: {e}")
        return []

def apply_migration(conn, file_path):
    """Apply a single migration file to the database."""
    migration_name = os.path.basename(file_path)
    
    try:
        # Read the SQL file
        with open(file_path, 'r') as f:
            sql = f.read()
        
        cursor = conn.cursor()
        
        # Execute the SQL
        print(f"Applying migration: {migration_name}")
        cursor.execute(sql)
        
        # Record the migration
        cursor.execute(
            "INSERT INTO migrations (name) VALUES (%s);",
            (migration_name,)
        )
        
        print(f"Successfully applied migration: {migration_name}")
        return True
    except Exception as e:
        print(f"Error applying migration {migration_name}: {e}")
        return False

def natural_sort_key(s):
    """Sort migration files naturally (e.g., 001_..., 002_..., etc.)."""
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]

def main():
    """Parse arguments and apply migrations."""
    parser = argparse.ArgumentParser(description='Apply database migrations to Supabase')
    parser.add_argument('migration_file', nargs='?', help='Specific migration file to apply')
    args = parser.parse_args()
    
    try:
        # Connect to the database
        conn = get_connection_from_env()
        
        # Get list of applied migrations
        applied_migrations = get_applied_migrations(conn)
        print(f"Already applied migrations: {applied_migrations}")
        
        if args.migration_file:
            # Apply specific migration file
            if os.path.basename(args.migration_file) in applied_migrations:
                print(f"Migration {args.migration_file} already applied")
            else:
                apply_migration(conn, args.migration_file)
        else:
            # Apply all migrations in order
            migration_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'migrations')
            migration_files = glob.glob(os.path.join(migration_dir, '*.sql'))
            
            # Sort migration files naturally
            migration_files.sort(key=natural_sort_key)
            
            for file_path in migration_files:
                migration_name = os.path.basename(file_path)
                if migration_name in applied_migrations:
                    print(f"Skipping already applied migration: {migration_name}")
                else:
                    success = apply_migration(conn, file_path)
                    if not success:
                        print("Migration failed, stopping.")
                        break
        
        conn.close()
    except Exception as e:
        print(f"Error applying migrations: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
