import psycopg2
from dotenv import load_dotenv
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import re

def read_sql_file(filename):
    with open(filename, 'r') as file:
        return file.read()

def split_sql_statements(sql):
    """
    Intelligently split SQL statements handling dollar-quoted strings and regular semicolons.
    Returns a list of individual SQL statements.
    """
    statements = []
    current_statement = []
    lines = sql.split('\n')
    in_dollar_quote = False
    dollar_quote_tag = None

    for line in lines:
        # Handle dollar quotes (e.g., $$ or $tag$)
        if not in_dollar_quote:
            # Look for start of dollar quote
            match = re.match(r'.*(\$\w*\$).*', line)
            if match:
                in_dollar_quote = True
                dollar_quote_tag = match.group(1)
        else:
            # Look for matching end dollar quote
            if dollar_quote_tag in line:
                in_dollar_quote = False
                dollar_quote_tag = None

        current_statement.append(line)

        # Only split on semicolon if we're not inside a dollar quote
        if ';' in line and not in_dollar_quote:
            statements.append('\n'.join(current_statement))
            current_statement = []

    # Add any remaining statement
    if current_statement:
        statements.append('\n'.join(current_statement))

    return [stmt.strip() for stmt in statements if stmt.strip()]

def run_migration():
    # Load environment variables
    load_dotenv()
    
    # Get database connection parameters
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set")
        return
    
    try:
        print("Connecting to database (timeout: 10s)...")
        # Add timeout and application name parameters
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=10,
            application_name='gpu_fleet_migration'
        )
        
        # Set isolation level to AUTOCOMMIT for schema changes
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            print("Reading migration file...")
            sql = read_sql_file('migrations/create_fleet_tables.sql')
            
            # Split the SQL into individual statements using our improved splitter
            statements = split_sql_statements(sql)
            total_statements = len(statements)
            
            print(f"\nExecuting migration ({total_statements} operations)...")
            for i, statement in enumerate(statements, 1):
                if statement.strip():
                    try:
                        print(f"Operation {i}/{total_statements}...", end='', flush=True)
                        cursor.execute(statement)
                        print(" ")
                    except Exception as e:
                        print(f" \nError in statement {i}: {e}")
                        print(f"\nFailed statement:\n{statement}\n")
                        raise
            
            print("\nVerifying tables...")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('gpus', 'jobs')
            """)
            
            tables = cursor.fetchall()
            if tables:
                print("\nCreated tables successfully:")
                for table in tables:
                    print(f"- {table[0]}")
            else:
                print("\nWarning: No tables were created!")
                
                # Get column information for each table
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = '{table[0]}'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                print("  Columns:")
                for col in columns:
                    print(f"    - {col[0]}: {col[1]} (Nullable: {col[2]})")
            
        except Exception as e:
            print(f"\nError during migration: {e}")
            raise
        finally:
            cursor.close()
            
    except psycopg2.OperationalError as e:
        print(f"\nConnection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if the Supabase database is accessible")
        print("2. Verify your DATABASE_URL is correct")
        print("3. Check if you're behind a VPN or firewall")
        print("4. Try connecting via psql to verify credentials")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        raise
    finally:
        print("\nDatabase connection closed.")
        conn.close()

if __name__ == "__main__":
    run_migration()
