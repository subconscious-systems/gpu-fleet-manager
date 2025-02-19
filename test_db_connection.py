import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Get database connection parameters from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set")
    exit(1)

# Connect to the database
try:
    print("Attempting to connect to database...")
    connection = psycopg2.connect(DATABASE_URL)
    print("Connection successful!")
    
    # Create a cursor to execute SQL queries
    cursor = connection.cursor()
    
    # Example query
    print("Executing test query...")
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Current Time:", result)

    # Test database version
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("PostgreSQL version:", db_version)

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("Connection closed successfully.")

except Exception as e:
    print(f"Failed to connect: {e}")
    print("\nTroubleshooting tips:")
    print("1. Check if your .env file exists and contains the correct credentials")
    print("2. Verify that you can connect to the database using psql or another tool")
    print("3. Check if the database is accessible from your current network")
    print("4. Verify that the database user has the necessary permissions")
