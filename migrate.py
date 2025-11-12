#!/usr/bin/env python3
"""
PostgreSQL migration tool with Flyway-like features.

Features:
- Alphabetically ordered migrations (v0.1.0_name.sql, etc.)
- AfterMigrate callback scripts
- Automatic database creation
- Migration history tracking
- Seed data loading
- SQL template rendering with environment variables
- Dry-run mode
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


@dataclass
class Migration:
    """Represents a migration file."""

    filename: str
    description: str
    filepath: Path
    checksum: str

    @classmethod
    def from_file(cls, filepath: Path) -> "Migration":
        """Create a Migration from a file path."""
        if not filepath.name.endswith(".sql"):
            raise ValueError(
                f"Invalid migration filename: {filepath.name}. Expected .sql extension"
            )

        # Extract description from filename (remove .sql extension)
        description = filepath.stem.replace("_", " ")

        # Calculate checksum
        checksum = cls._calculate_checksum(filepath)

        return cls(
            filename=filepath.name,
            description=description,
            filepath=filepath,
            checksum=checksum,
        )

    @staticmethod
    def _calculate_checksum(filepath: Path) -> str:
        """Calculate MD5 checksum of file content."""
        import hashlib

        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()


class MigrationRunner:
    """Manages database migrations."""

    SCHEMA_TABLE = "schema_migrations"

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        migrations_dir: Path,
        after_migrate_dir: Optional[Path] = None,
        seeds_dir: Optional[Path] = None,
        template_vars: Optional[dict] = None,
    ):
        """Initialize the migration runner."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.migrations_dir = migrations_dir
        self.after_migrate_dir = after_migrate_dir
        self.seeds_dir = seeds_dir
        self.template_vars = template_vars or {}
        self.conn = None

    def connect(self) -> None:
        """Connect to the database."""
        self.conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def render_sql_template(self, sql_content: str) -> str:
        """Render SQL template with environment variables."""
        if not self.template_vars:
            return sql_content

        # Replace ${VAR_NAME} with values from template_vars
        import re

        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.template_vars:
                return str(self.template_vars[var_name])
            # If variable not found, leave it as-is
            return match.group(0)

        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace_var, sql_content)

    def ensure_database_exists(self) -> bool:
        """Ensure the target database exists, create if it doesn't."""
        # Connect to postgres database to check/create target database
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database="postgres",
                user=self.user,
                password=self.password,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (self.database,)
            )
            exists = cursor.fetchone() is not None

            if not exists:
                print(f"🔨 Creating database '{self.database}'...")
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.database))
                )
                print(f"✅ Database '{self.database}' created successfully")
                cursor.close()
                conn.close()
                return True
            else:
                cursor.close()
                conn.close()
                return False

        except psycopg2.Error as e:
            print(f"❌ Error ensuring database exists: {e}")
            sys.exit(1)

    def initialize_schema_table(self) -> None:
        """Create the schema migrations table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.SCHEMA_TABLE} (
                installed_rank SERIAL PRIMARY KEY,
                script VARCHAR(1000) NOT NULL UNIQUE,
                description VARCHAR(200) NOT NULL,
                checksum VARCHAR(32) NOT NULL,
                installed_by VARCHAR(100) NOT NULL,
                installed_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                execution_time INTEGER NOT NULL,
                success BOOLEAN NOT NULL
            )
        """
        )
        self.conn.commit()
        cursor.close()

    def get_applied_migrations(self) -> dict[str, dict]:
        """Get list of applied migrations from the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT script, description, checksum, installed_on, success
            FROM {self.SCHEMA_TABLE}
            ORDER BY installed_rank
        """
        )
        results = cursor.fetchall()
        cursor.close()

        return {
            row[0]: {
                "description": row[1],
                "checksum": row[2],
                "installed_on": row[3],
                "success": row[4],
            }
            for row in results
        }

    def get_pending_migrations(self) -> list[Migration]:
        """Get list of pending migrations in alphabetical order."""
        # Get all migration files sorted alphabetically
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        all_migrations = [Migration.from_file(f) for f in migration_files]

        # Get applied migrations
        applied = self.get_applied_migrations()

        # Filter to pending only
        pending = []
        for migration in all_migrations:
            if migration.filename not in applied:
                pending.append(migration)
            elif applied[migration.filename]["checksum"] != migration.checksum:
                print(
                    f"⚠️  Warning: Checksum mismatch for migration {migration.filename}"
                )
                print(f"   Applied:  {applied[migration.filename]['checksum']}")
                print(f"   Current:  {migration.checksum}")
                print("   Migration files should not be modified after being applied!")

        return pending

    def apply_migration(self, migration: Migration, dry_run: bool = False) -> bool:
        """Apply a single migration."""
        print(f"\n📝 Applying migration: {migration.description}")
        print(f"   File: {migration.filename}")

        # Read migration SQL
        with open(migration.filepath) as f:
            sql_content = f.read()

        # Render template variables
        sql_content = self.render_sql_template(sql_content)

        if dry_run:
            print("   [DRY RUN] Would execute:")
            print("   " + "-" * 60)
            # Print first 500 chars
            preview = sql_content[:500]
            print("   " + preview.replace("\n", "\n   "))
            if len(sql_content) > 500:
                print("   ...")
            print("   " + "-" * 60)
            return True

        # Execute migration
        start_time = datetime.now()
        cursor = self.conn.cursor()

        try:
            cursor.execute(sql_content)
            self.conn.commit()
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            # Record migration
            cursor.execute(
                f"""
                INSERT INTO {self.SCHEMA_TABLE}
                (script, description, checksum, installed_by, execution_time, success)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    migration.filename,
                    migration.description,
                    migration.checksum,
                    self.user,
                    execution_time,
                    True,
                ),
            )
            self.conn.commit()

            print(f"   ✅ Migration applied successfully ({execution_time}ms)")
            return True

        except psycopg2.Error as e:
            self.conn.rollback()
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            # Record failed migration
            cursor.execute(
                f"""
                INSERT INTO {self.SCHEMA_TABLE}
                (script, description, checksum, installed_by, execution_time, success)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    migration.filename,
                    migration.description,
                    migration.checksum,
                    self.user,
                    execution_time,
                    False,
                ),
            )
            self.conn.commit()

            print(f"   ❌ Migration failed: {e}")
            return False

        finally:
            cursor.close()

    def run_after_migrate_scripts(self, dry_run: bool = False) -> None:
        """Run afterMigrate callback scripts."""
        if not self.after_migrate_dir or not self.after_migrate_dir.exists():
            return

        script_files = sorted(self.after_migrate_dir.glob("*.sql"))
        if not script_files:
            return

        print("\n🔄 Running afterMigrate scripts...")

        for script_file in script_files:
            print(f"   📄 Executing: {script_file.name}")

            with open(script_file) as f:
                sql_content = f.read()

            # Render template variables
            sql_content = self.render_sql_template(sql_content)

            if dry_run:
                print("      [DRY RUN] Would execute afterMigrate script")
                continue

            cursor = self.conn.cursor()
            try:
                cursor.execute(sql_content)
                self.conn.commit()
                print("      ✅ Script executed successfully")
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"      ⚠️  Script failed: {e}")
            finally:
                cursor.close()

    def migrate(self, dry_run: bool = False) -> int:
        """Run all pending migrations."""
        print("🚀 Starting migration process...")
        print(f"   Database: {self.database}")
        print(f"   User: {self.user}")
        print(f"   Migrations directory: {self.migrations_dir}")

        if dry_run:
            print("   Mode: DRY RUN (no changes will be made)")

        # Ensure database exists
        db_created = self.ensure_database_exists()

        # Connect to database
        self.connect()

        # Initialize schema table
        if not dry_run:
            self.initialize_schema_table()

        # Get pending migrations
        pending = self.get_pending_migrations()

        if not pending:
            print("\n✨ No pending migrations. Database is up to date!")
            if not db_created:
                self.run_after_migrate_scripts(dry_run)
            self.close()
            return 0

        print(f"\n📋 Found {len(pending)} pending migration(s)")

        # Apply migrations
        applied_count = 0
        for migration in pending:
            success = self.apply_migration(migration, dry_run)
            if not success:
                print("\n❌ Migration failed. Stopping.")
                self.close()
                return 1
            applied_count += 1

        # Run afterMigrate scripts
        if applied_count > 0:
            self.run_after_migrate_scripts(dry_run)

        print(f"\n✅ Successfully applied {applied_count} migration(s)")
        self.close()
        return 0

    def seed(self, dry_run: bool = False) -> int:
        """Run seed data scripts."""
        print("🌱 Running seed data scripts...")
        print(f"   Database: {self.database}")

        if not self.seeds_dir or not self.seeds_dir.exists():
            print("   ❌ Seeds directory not found")
            return 1

        if dry_run:
            print("   Mode: DRY RUN (no changes will be made)")

        # Connect to database
        try:
            self.connect()
        except psycopg2.Error as e:
            print(f"   ❌ Cannot connect to database: {e}")
            return 1

        # Get seed files in alphabetical order
        seed_files = sorted(self.seeds_dir.glob("*.sql"))

        if not seed_files:
            print("   ⚠️  No seed files found")
            self.close()
            return 0

        print(f"\n📋 Found {len(seed_files)} seed file(s)")

        # Execute seed files
        for seed_file in seed_files:
            print(f"\n📄 Executing: {seed_file.name}")

            with open(seed_file) as f:
                sql_content = f.read()

            # Render template variables
            sql_content = self.render_sql_template(sql_content)

            if dry_run:
                print("   [DRY RUN] Would execute:")
                print("   " + "-" * 60)
                preview = sql_content[:500]
                print("   " + preview.replace("\n", "\n   "))
                if len(sql_content) > 500:
                    print("   ...")
                print("   " + "-" * 60)
                continue

            cursor = self.conn.cursor()
            try:
                start_time = datetime.now()
                cursor.execute(sql_content)
                self.conn.commit()
                end_time = datetime.now()
                execution_time = int((end_time - start_time).total_seconds() * 1000)
                print(f"   ✅ Seed executed successfully ({execution_time}ms)")
            except psycopg2.Error as e:
                self.conn.rollback()
                print(f"   ❌ Seed failed: {e}")
                cursor.close()
                self.close()
                return 1
            finally:
                cursor.close()

        print("\n✅ All seeds executed successfully")
        self.close()
        return 0

    def info(self) -> None:
        """Display migration status information."""
        print("📊 Migration Status")
        print(f"   Database: {self.database}")

        # Connect
        try:
            self.connect()
            self.initialize_schema_table()
        except psycopg2.Error as e:
            print(f"   ❌ Cannot connect to database: {e}")
            return

        # Get applied migrations
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        print(f"\n✅ Applied migrations: {len(applied)}")
        for filename, info in applied.items():
            status = "✅" if info["success"] else "❌"
            print(f"   {status} {filename}: {info['description']}")

        print(f"\n⏳ Pending migrations: {len(pending)}")
        for migration in pending:
            print(f"   ⏳ {migration.filename}: {migration.description}")

        if not pending:
            print("   Database is up to date!")

        self.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL migration tool with Flyway-like features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate.py migrate                  # Run pending migrations
  python migrate.py migrate --dry-run        # Preview migrations without applying
  python migrate.py seed                     # Load seed data
  python migrate.py seed --dry-run           # Preview seed data without loading
  python migrate.py info                     # Show migration status
  python migrate.py --help                   # Show this help message

Environment Variables:
  DB_HOST       Database host (default: localhost)
  DB_PORT       Database port (default: 5432)
  DB_NAME       Database name (required)
  DB_USER       Database user (required)
  DB_PASSWORD   Database password (required)
  
  Custom template variables can be added with any name and will be
  substituted in SQL files using ${VARIABLE_NAME} syntax.
        """,
    )

    parser.add_argument(
        "command", choices=["migrate", "seed", "info"], help="Command to execute"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migrations without applying them",
    )

    parser.add_argument(
        "--host", default=os.getenv("DB_HOST", "localhost"), help="Database host"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("DB_PORT", "5432")),
        help="Database port",
    )

    parser.add_argument(
        "--database", default=os.getenv("DB_NAME"), help="Database name"
    )

    parser.add_argument("--user", default=os.getenv("DB_USER"), help="Database user")

    parser.add_argument(
        "--password", default=os.getenv("DB_PASSWORD"), help="Database password"
    )

    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path(__file__).parent / "migrations",
        help="Migrations directory",
    )

    parser.add_argument(
        "--after-migrate-dir",
        type=Path,
        default=Path(__file__).parent / "afterMigrate",
        help="AfterMigrate scripts directory",
    )

    parser.add_argument(
        "--seeds-dir",
        type=Path,
        default=Path(__file__).parent / "seeds",
        help="Seeds directory",
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.database:
        print("❌ Error: Database name is required (use --database or DB_NAME env var)")
        sys.exit(1)

    if not args.user:
        print("❌ Error: Database user is required (use --user or DB_USER env var)")
        sys.exit(1)

    if not args.password:
        print(
            "❌ Error: Database password is required (use --password or DB_PASSWORD env var)"
        )
        sys.exit(1)

    if not args.migrations_dir.exists():
        print(f"❌ Error: Migrations directory not found: {args.migrations_dir}")
        sys.exit(1)

    # Load template variables from environment
    # All environment variables are available as template variables
    template_vars = dict(os.environ)

    # Create runner
    runner = MigrationRunner(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password,
        migrations_dir=args.migrations_dir,
        after_migrate_dir=args.after_migrate_dir
        if args.after_migrate_dir.exists()
        else None,
        seeds_dir=args.seeds_dir if args.seeds_dir.exists() else None,
        template_vars=template_vars,
    )

    # Execute command
    try:
        if args.command == "migrate":
            sys.exit(runner.migrate(dry_run=args.dry_run))
        elif args.command == "seed":
            sys.exit(runner.seed(dry_run=args.dry_run))
        elif args.command == "info":
            runner.info()
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
