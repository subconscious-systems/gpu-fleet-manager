# Database Migrations

This directory contains database migrations for the GPU Fleet Manager.

## Structure

- Migrations are numbered sequentially (e.g., `001_`, `002_`, etc.)
- Each migration has an "up" SQL file for applying changes
- Migrations are applied in order based on their numeric prefix

## Running Migrations

1. Log in to your Supabase dashboard
2. Navigate to the SQL Editor
3. Copy the contents of each migration file in order
4. Execute each migration file using the SQL Editor
5. Verify that the tables and policies were created successfully

## Creating New Migrations

1. Create a new SQL file in this directory with the next sequential number
2. Add your SQL statements to create/modify tables
3. Test the migration locally before applying to production
4. Document any manual steps or considerations in the migration file

## Important Notes

- Always backup the database before running migrations
- Test migrations in a development environment first
- Some migrations may require downtime or coordination with the team
- Row Level Security (RLS) policies should be carefully reviewed
- Keep track of which migrations have been applied in each environment
