<!-- omit in toc -->
# Astro Telescope Database

PostgreSQL database schema and migrations for the Astro telescope observation system.

<!-- omit in toc -->
## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Directory Structure](#directory-structure)
- [Quick Start](#quick-start)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Start PostgreSQL](#2-start-postgresql)
  - [3. Install Dependencies](#3-install-dependencies)
  - [4. Configure Database Connection](#4-configure-database-connection)
  - [5. Run Migrations](#5-run-migrations)
- [Usage](#usage)
  - [Running Migrations](#running-migrations)
  - [Checking Status](#checking-status)
  - [Command-Line Options](#command-line-options)
  - [Environment Variables](#environment-variables)
- [Creating Migrations](#creating-migrations)
  - [Migration Naming Convention](#migration-naming-convention)
  - [Creating a New Migration](#creating-a-new-migration)
  - [Migration Best Practices](#migration-best-practices)
- [AfterMigrate Scripts](#aftermigrate-scripts)
- [SQL Templating](#sql-templating)
  - [Using Template Variables](#using-template-variables)
  - [Template Variables in Seeds](#template-variables-in-seeds)
  - [Notes on Templating](#notes-on-templating)
- [Seed Data](#seed-data)
  - [Loading Seed Data](#loading-seed-data)
- [Database Schema](#database-schema)
  - [Current Schema (v001)](#current-schema-v001)
    - [`users` Table](#users-table)
    - [`observations` Table](#observations-table)
- [Migration Tracking](#migration-tracking)
- [Troubleshooting](#troubleshooting)
  - ["Migration failed" Error](#migration-failed-error)
  - [Checksum Mismatch Warning](#checksum-mismatch-warning)
  - [Database Connection Errors](#database-connection-errors)
- [Docker Setup](#docker-setup)
  - [Basic Usage](#basic-usage)
  - [Running pgAdmin (Optional)](#running-pgadmin-optional)
  - [Docker Environment Variables](#docker-environment-variables)
  - [Docker Compose Features](#docker-compose-features)
  - [Using with Migration Tool](#using-with-migration-tool)
  - [Troubleshooting Docker](#troubleshooting-docker)
- [Integration with Backend](#integration-with-backend)
- [Contributing](#contributing)

## Overview

This repository contains SQL migration scripts and tools to create and maintain the database schema. It uses a custom migration tool with Flyway-like features, designed to be language-agnostic and database-engineer friendly.

## Features

- ✅ **Pure SQL migrations** - Write standard PostgreSQL SQL
- ✅ **Alphabetical ordering** - Migrations run in alphabetical order (supports version prefixes like v0.1.0_)
- ✅ **Automatic database creation** - Creates the database if it doesn't exist
- ✅ **AfterMigrate scripts** - Run scripts after successful migrations (like updating statistics)
- ✅ **Seed data loading** - Load test/development data with the `seed` command
- ✅ **SQL templating** - Use environment variables in SQL with `${VAR_NAME}` syntax
- ✅ **Migration tracking** - Keeps history of applied migrations with checksums
- ✅ **Dry-run mode** - Preview migrations before applying
- ✅ **Checksum validation** - Prevents modification of already-applied migrations

## Directory Structure

```
database/
├── migrate.py              # Migration tool
├── requirements.txt        # Python dependencies (just psycopg2)
├── docker-compose.yml      # PostgreSQL container setup
├── .env.example           # Environment variable template
├── .dockerignore          # Docker build exclusions
├── migrations/            # Migration scripts (alphabetically ordered)
│   └── v0.1.0_initial_schema.sql
├── afterMigrate/          # Scripts run after each migration
│   └── update_statistics.sql
└── seeds/                 # Optional seed data for dev/testing
    └── sample_data.sql
```

## Quick Start

### 1. Prerequisites

**Option A: Local PostgreSQL**
- Python 3.8+
- PostgreSQL 12+
- Access to create databases on PostgreSQL server

**Option B: Docker (Recommended)**
- Python 3.8+
- Docker and Docker Compose

### 2. Start PostgreSQL

**Option A: Using Docker Compose (Recommended)**

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Check if it's running
docker-compose ps

# View logs
docker-compose logs -f postgres

# Stop when done
docker-compose down
```

The database will be available at `localhost:5432` with credentials from `.env`.

**Option B: Use existing PostgreSQL installation**

Skip this step if you already have PostgreSQL running.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Database Connection

Copy `.env.example` to `.env` and update with your database credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=astro_telescope
DB_USER=postgres
DB_PASSWORD=your_password_here

# Optional: Custom template variables for SQL files
# APP_SCHEMA=public
# DEFAULT_TABLESPACE=pg_default
```

### 5. Run Migrations

```bash
# Preview migrations (dry-run)
uv run migrate.py migrate --dry-run

# Apply migrations
uv run migrate.py migrate

# Check migration status
uv run migrate.py info

# Load seed data (optional, for development)
uv run migrate.py seed
```

## Usage

### Running Migrations

The migration tool will:
1. Create the database if it doesn't exist
2. Create the `schema_migrations` tracking table
3. Apply pending migrations in order
4. Run afterMigrate scripts
5. Record checksums to prevent tampering

```bash
# Run all pending migrations
uv run migrate.py migrate

# Preview what would be applied
uv run migrate.py migrate --dry-run
```

### Checking Status

```bash
uv run migrate.py info
```

Output:
```
📊 Migration Status
   Database: astro_telescope

✅ Applied migrations: 1
   ✅ V001: initial schema

⏳ Pending migrations: 0
   Database is up to date!
```

### Command-Line Options

```bash
python migrate.py <command> [OPTIONS]

Commands:
  migrate    Run pending migrations
  seed       Load seed data from seeds/ directory
  info       Show migration status

Options:
  --dry-run              Preview migrations without applying
  --host HOST           Database host (default: localhost)
  --port PORT           Database port (default: 5432)
  --database DB         Database name (required)
  --user USER           Database user (required)
  --password PASS       Database password (required)
  --migrations-dir DIR  Migrations directory (default: ./migrations)
  --after-migrate-dir   AfterMigrate scripts directory (default: ./afterMigrate)
  --seeds-dir DIR       Seeds directory (default: ./seeds)
```

### Environment Variables

Instead of command-line options, you can use environment variables:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=astro_telescope
export DB_USER=postgres
export DB_PASSWORD=secret

python migrate.py migrate
```

Or use a `.env` file (recommended for local development).

## Creating Migrations

### Migration Naming Convention

Migrations are executed in **alphabetical order**. You can use any naming convention as long as the files sort correctly:

**Recommended pattern:** `vX.Y.Z_description.sql`

- `vX.Y.Z` = Version prefix (e.g., v0.1.0, v0.2.0, v1.0.0)
- `description` = Brief description using underscores
- `.sql` = SQL file extension

**Examples:**
- ✅ `v0.1.0_initial_schema.sql`
- ✅ `v0.2.0_add_user_roles.sql`
- ✅ `v0.3.0_create_indexes.sql`
- ✅ `v1.0.0_production_ready.sql`
- ✅ `2024-11-12_add_telescope_table.sql` (date-based also works)
- ❌ `init.sql` (too vague, won't sort properly with others)
- ❌ `migration.py` (wrong - must be .sql)

The tool doesn't enforce a specific format - as long as your files sort alphabetically in the order you want them executed, any naming scheme works.

### Creating a New Migration

1. Determine the next version number (e.g., v0.2.0 if v0.1.0 exists)
2. Create a new file in `migrations/` directory
3. Write your SQL DDL statements
4. Test with `--dry-run` first

**Example:** `migrations/v0.2.0_add_telescope_table.sql`

```sql
-- Add telescope equipment tracking table

CREATE TABLE telescopes (
    id SERIAL PRIMARY KEY,
    telescope_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'available',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telescopes_status ON telescopes(status);

-- Add telescope reference to observations
ALTER TABLE observations
    ADD COLUMN telescope_id INTEGER REFERENCES telescopes(id);

CREATE INDEX idx_observations_telescope_id ON observations(telescope_id);
```

### Migration Best Practices

✅ **DO:**
- Use transactions implicitly (each migration runs in a transaction)
- Add indexes for foreign keys and frequently queried columns
- Include comments explaining complex logic
- Use `IF NOT EXISTS` for idempotent operations when safe
- Add constraints to enforce data integrity
- Document your changes in comments

❌ **DON'T:**
- Modify already-applied migrations (checksum validation will catch this)
- Put multiple unrelated changes in one migration
- Forget to test with `--dry-run` first
- Use application-specific logic (keep it pure SQL)

## AfterMigrate Scripts

Scripts in `afterMigrate/` run after every successful migration. Use them for:

- Updating table statistics (`ANALYZE`)
- Refreshing materialized views
- Running maintenance tasks
- Updating sequences

**Example:** `afterMigrate/update_statistics.sql`

```sql
-- Update statistics for query planner
ANALYZE users;
ANALYZE observations;
```

AfterMigrate scripts:
- Run in alphabetical order
- Don't block migration on failure (errors are logged but don't stop the process)
- Are not versioned or tracked (they run every time)
- Support template variables just like migrations

## SQL Templating

You can use environment variables in your SQL files using the `${VARIABLE_NAME}` syntax. This is useful for environment-specific values.

### Using Template Variables

Add variables to your `.env` file:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=astro_telescope
DB_USER=postgres
DB_PASSWORD=secret

# Custom template variables
APP_SCHEMA=public
DEFAULT_TABLESPACE=pg_default
MAX_CONNECTIONS=100
```

Then use them in your SQL files:

```sql
-- migrations/v0.2.0_add_config_table.sql

CREATE TABLE ${APP_SCHEMA}.app_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) TABLESPACE ${DEFAULT_TABLESPACE};

-- Set database connection limit
ALTER DATABASE ${DB_NAME} SET max_connections = ${MAX_CONNECTIONS};
```

When the migration runs, `${APP_SCHEMA}` will be replaced with `public`, `${DEFAULT_TABLESPACE}` with `pg_default`, etc.

### Template Variables in Seeds

Seed files also support templating:

```sql
-- seeds/test_data.sql

INSERT INTO users (user_id, username, email)
VALUES ('test_001', '${TEST_USER_NAME}', '${TEST_USER_EMAIL}');
```

`.env`:
```env
TEST_USER_NAME=test_user
TEST_USER_EMAIL=test@example.com
```

### Notes on Templating

- All environment variables are available as template variables
- Template variables are case-sensitive
- If a variable is not found, it's left as-is in the SQL
- Variables are substituted before execution
- Works in migrations, afterMigrate scripts, and seed files

## Seed Data

The `seeds/` directory contains optional SQL scripts for populating development/test databases.

**These should NOT be run in production!**

### Loading Seed Data

**Using the migration tool (recommended):**

```bash
# Preview seed data
python migrate.py seed --dry-run

# Load seed data
python migrate.py seed
```

**Using psql directly:**

```bash
# Connect to database
psql -h localhost -U postgres -d astro_telescope

# Load seed data
\i seeds/sample_data.sql
```

Or using psql from command line:
```bash
psql -h localhost -U postgres -d astro_telescope -f seeds/sample_data.sql
```

**Note:** The migration tool's `seed` command:
- Executes seed files in alphabetical order
- Supports template variables
- Provides better error handling and progress feedback
- Works consistently across platforms

## Database Schema

### Current Schema (v001)

#### `users` Table
Stores application users who can submit telescope observations.

| Column      | Type         | Description                    |
|-------------|--------------|--------------------------------|
| id          | SERIAL       | Primary key                    |
| user_id     | VARCHAR(255) | Unique external user ID        |
| username    | VARCHAR(255) | User display name              |
| email       | VARCHAR(255) | User email address             |
| is_active   | BOOLEAN      | Whether account is active      |
| created_at  | TIMESTAMP    | Record creation time           |
| updated_at  | TIMESTAMP    | Last update time (auto-update) |

**Indexes:**
- `idx_users_user_id` on `user_id`
- `idx_users_username` on `username`
- `idx_users_email` on `email`
- `idx_users_is_active` on `is_active` (partial index for active users)

#### `observations` Table
Stores telescope observation requests and configurations.

| Column              | Type              | Description                           |
|---------------------|-------------------|---------------------------------------|
| id                  | SERIAL            | Primary key                           |
| observation_id      | VARCHAR(255)      | Unique observation identifier         |
| user_id             | INTEGER           | Foreign key to users table            |
| target_name         | VARCHAR(255)      | Name of observation target            |
| observation_object  | VARCHAR(255)      | Object being observed                 |
| ra                  | DOUBLE PRECISION  | Right Ascension (0-360°)              |
| dec                 | DOUBLE PRECISION  | Declination (-90 to 90°)              |
| center_frequency    | DOUBLE PRECISION  | Center frequency in MHz               |
| rf_gain             | DOUBLE PRECISION  | RF gain in dB                         |
| if_gain             | DOUBLE PRECISION  | IF gain in dB                         |
| bb_gain             | DOUBLE PRECISION  | Baseband gain in dB                   |
| observation_type    | VARCHAR(100)      | Type of observation                   |
| integration_time    | DOUBLE PRECISION  | Integration time in seconds           |
| output_filename     | VARCHAR(1000)     | Output file name                      |
| status              | VARCHAR(50)       | Status (pending/running/completed...) |
| submitted_at        | TIMESTAMP         | Submission timestamp                  |
| completed_at        | TIMESTAMP         | Completion timestamp (nullable)       |
| created_at          | TIMESTAMP         | Record creation time                  |
| updated_at          | TIMESTAMP         | Last update time (auto-update)        |

**Constraints:**
- `ra` must be between 0 and 360
- `dec` must be between -90 and 90
- `center_frequency` must be positive
- `integration_time` must be positive
- `status` must be one of: 'pending', 'running', 'completed', 'failed', 'cancelled'

**Indexes:**
- `idx_observations_observation_id` on `observation_id`
- `idx_observations_user_id` on `user_id`
- `idx_observations_status` on `status`
- `idx_observations_submitted_at` on `submitted_at`
- `idx_observations_target_name` on `target_name`
- `idx_observations_user_status` on `(user_id, status)` (composite)

**Triggers:**
- Auto-updates `updated_at` timestamp on record modification

## Migration Tracking

The tool creates a `schema_migrations` table to track applied migrations:

| Column          | Type         | Description                     |
|-----------------|--------------|---------------------------------|
| installed_rank  | SERIAL       | Order of installation           |
| script          | VARCHAR(1000)| Script filename (unique)        |
| description     | VARCHAR(200) | Migration description           |
| checksum        | VARCHAR(32)  | MD5 checksum of migration file  |
| installed_by    | VARCHAR(100) | Database user who ran migration |
| installed_on    | TIMESTAMP    | Installation timestamp          |
| execution_time  | INTEGER      | Execution time in milliseconds  |
| success         | BOOLEAN      | Whether migration succeeded     |

**Never modify this table manually!**

## Troubleshooting

### "Migration failed" Error

If a migration fails:
1. Check the error message for SQL syntax errors
2. The failed migration is recorded in `schema_migrations` with `success = FALSE`
3. Fix the SQL in your migration file
4. The checksum will have changed, so you may need to manually remove the failed entry:
   ```sql
   DELETE FROM schema_migrations WHERE script = 'vX.Y.Z_migration_name.sql' AND success = FALSE;
   ```
5. Run migrations again

### Checksum Mismatch Warning

If you see "Checksum mismatch" warnings:
- This means a migration file was modified after being applied
- **This is not allowed!** Migrations should be immutable
- If you need to make changes, create a new migration that alters the schema

### Database Connection Errors

```bash
# Test connection manually
psql -h localhost -U postgres -d postgres

# Check PostgreSQL is running
# On Windows: Check Services
# On Linux: systemctl status postgresql
# On macOS: brew services list
```

## Docker Setup

The project includes a Docker Compose configuration for easy PostgreSQL setup.

### Basic Usage

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Check status
docker-compose ps

# View logs
docker-compose logs -f postgres

# Stop database
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

### Running pgAdmin (Optional)

pgAdmin is included for database management through a web UI:

```bash
# Start PostgreSQL and pgAdmin
docker-compose --profile tools up -d

# Access pgAdmin at http://localhost:5050
# Default credentials: admin@astro.local / admin (from .env)
```

To connect to the database in pgAdmin:
1. Open http://localhost:5050
2. Add new server:
   - **Name**: Astro DB
   - **Host**: postgres (container name)
   - **Port**: 5432
   - **Username**: postgres (from .env)
   - **Password**: your password (from .env)

### Docker Environment Variables

Configure in `.env`:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=astro_telescope
DB_USER=postgres
DB_PASSWORD=your_secure_password

# pgAdmin (optional)
PGADMIN_EMAIL=admin@astro.local
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050
```

### Docker Compose Features

- **PostgreSQL 16 Alpine** - Lightweight, fast startup
- **Persistent volumes** - Data survives container restarts
- **Health checks** - Ensures database is ready before dependent services start
- **Custom network** - Isolated network for database services
- **pgAdmin included** - Optional web-based database management
- **Environment variable support** - Easy configuration

### Using with Migration Tool

The migration tool works seamlessly with Docker:

```bash
# Start database
docker-compose up -d postgres

# Wait for database to be ready (check health)
docker-compose ps

# Run migrations
uv run migrate.py migrate

# Load seed data
uv run migrate.py seed

# Check status
uv run migrate.py info
```

### Troubleshooting Docker

**Port already in use:**
```bash
# Change DB_PORT in .env to a different port (e.g., 5433)
DB_PORT=5433

# Restart containers
docker-compose down
docker-compose up -d
```

**Database not accessible:**
```bash
# Check if container is running
docker-compose ps

# Check logs for errors
docker-compose logs postgres

# Verify health status
docker inspect astro-telescope-db | grep -A 10 Health
```

**Reset database completely:**
```bash
# Stop and remove everything including data
docker-compose down -v

# Start fresh
docker-compose up -d postgres
python migrate.py migrate
```

## Integration with Backend

The backend service (`backend/` repository) should:

1. **NOT** run migrations automatically on startup
2. Connect to the already-migrated database using SQLAlchemy
3. Define SQLModel models that match this schema
4. Keep models in sync with database schema manually

To add a new column:
1. Create migration in `database/` repo
2. Update SQLModel model in `backend/` repo
3. Deploy database changes first, then backend

## Contributing

When adding new migrations:

1. Pull latest changes from main branch
2. Determine next migration number
3. Create migration file with proper naming
4. Test locally with `--dry-run`
5. Test actual migration on local database
6. Commit migration file
7. Document schema changes in this README
