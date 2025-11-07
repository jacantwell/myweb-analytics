#!/usr/bin/env python3
"""
Initialize Database Script

This script creates all database tables based on SQLAlchemy models.
Run this after setting up PostgreSQL (local or RDS).

Usage:
    python scripts/init_database.py [--drop]

Options:
    --drop    Drop all existing tables before creating new ones (CAUTION!)
"""
import sys
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from database.connection import init_db, test_connection
from rich.console import Console

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Initialize analytics database tables"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all existing tables before creating (CAUTION: deletes all data!)",
    )
    args = parser.parse_args()

    console.print("\n[bold blue]Analytics Database Initialization[/bold blue]\n")

    # Test connection first
    console.print("[yellow]Testing database connection...[/yellow]")
    if not test_connection():
        console.print("[bold red]❌ Connection failed. Please check your configuration.[/bold red]")
        sys.exit(1)

    console.print()

    # Warn if dropping tables
    if args.drop:
        console.print(
            "[bold red]⚠️  WARNING: This will DROP all existing tables and data![/bold red]"
        )
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            console.print("[yellow]Operation cancelled.[/yellow]")
            sys.exit(0)
        console.print()

    # Initialize database
    try:
        init_db(drop_existing=args.drop)
        console.print("\n[bold green]✅ Database initialization complete![/bold green]\n")
    except Exception as e:
        console.print(f"\n[bold red]❌ Database initialization failed: {e}[/bold red]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
