#!/usr/bin/env python3
"""
Test Database Connection

Simple script to verify database connection is working.

Usage:
    python scripts/test_connection.py
"""
import sys
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import test_connection, DatabaseConfig
from rich.console import Console
from rich.table import Table

console = Console()


def main():
    console.print("\n[bold blue]Database Connection Test[/bold blue]\n")

    # Show current configuration
    config = DatabaseConfig()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Environment", config.env)
    table.add_row("Using AWS RDS", "Yes" if config.use_aws else "No")

    console.print(table)
    console.print()

    # Test connection
    console.print("[yellow]Testing connection...[/yellow]\n")
    success = test_connection()

    if success:
        console.print("\n[bold green]✅ Connection successful![/bold green]\n")
        return 0
    else:
        console.print("\n[bold red]❌ Connection failed![/bold red]")
        console.print("\n[yellow]Troubleshooting tips:[/yellow]")
        console.print("  1. Check your .env file configuration")
        console.print("  2. Ensure PostgreSQL is running (if local)")
        console.print("  3. Verify network access to RDS (if using AWS)")
        console.print("  4. Check database credentials\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
