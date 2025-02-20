#!/usr/bin/env python3
import os
import sys
import httpx
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))
from src.core.dependencies import DatabaseError, get_supabase_config

async def run_migration(client: httpx.AsyncClient, sql_file: Path) -> None:
    """Run a single migration file"""
    print(f"Running migration: {sql_file.name}")
    
    try:
        # Read and execute the SQL file
        sql = sql_file.read_text()
        
        # Split the SQL into individual statements
        statements = sql.split(';')
        
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
                
            # Execute the statement using the REST API
            response = await client.post(
                '/rest/v1/rpc/exec',
                json={'sql': stmt}
            )
            response.raise_for_status()
            
        print(f"✓ Completed migration: {sql_file.name}")
        
    except Exception as e:
        print(f"✗ Failed migration {sql_file.name}: {str(e)}")
        raise

async def main():
    # Load environment variables
    load_dotenv()
    
    try:
        # Get Supabase configuration
        config = get_supabase_config()
        
        # Create HTTP client
        async with httpx.AsyncClient(
            base_url=config['url'],
            headers={
                'apikey': config['key'],
                'Authorization': f'Bearer {config["key"]}'
            }
        ) as client:
            # Get all migration files
            migrations_dir = Path(__file__).parent.parent / 'migrations'
            sql_files = sorted([
                f for f in migrations_dir.glob('*.sql')
                if f.name[0].isdigit()  # Only numbered migrations
            ])
            
            if not sql_files:
                print("No migration files found!")
                return
            
            # Run each migration in order
            for sql_file in sql_files:
                await run_migration(client, sql_file)
                
            print("\nAll migrations completed successfully!")
            
    except Exception as e:
        print(f"\nError running migrations: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
