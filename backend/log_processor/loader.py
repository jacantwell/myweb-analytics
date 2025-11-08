"""
Database Loader

Loads processed log entries, sessions, and visitor data into PostgreSQL
using SQLAlchemy ORM with batch operations for performance.
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from backend.database.models import PageView, Session as SessionModel, Visitor

console = Console()


class LogLoader:
    """Handles loading log data into the database efficiently"""

    def __init__(self, db_session: Session, batch_size: int = 1000):
        """
        Initialize the log loader.

        Args:
            db_session: SQLAlchemy database session
            batch_size: Number of records to insert per batch
        """
        self.db_session = db_session
        self.batch_size = batch_size

    def load_page_views(self, page_views: List[Dict[str, any]]) -> int:
        """
        Load page views into the database in batches.

        Args:
            page_views: List of page view dictionaries

        Returns:
            Number of records inserted
        """
        if not page_views:
            console.print("[yellow]No page views to load[/yellow]")
            return 0

        console.print(f"[cyan]Loading {len(page_views)} page views...[/cyan]")

        inserted_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Inserting page views", total=len(page_views))

            # Process in batches
            for i in range(0, len(page_views), self.batch_size):
                batch = page_views[i : i + self.batch_size]

                # Prepare records for insertion
                records = []
                for pv in batch:
                    # Remove fields that aren't in the PageView model
                    record = {
                        "timestamp": pv.get("timestamp"),
                        "visitor_id": pv.get("visitor_id"),
                        "session_id": pv.get("session_id"),
                        "url_path": pv.get("url_path"),
                        "query_string": pv.get("query_string"),
                        "http_method": pv.get("http_method"),
                        "status_code": pv.get("status_code"),
                        "referrer_domain": pv.get("referrer_domain"),
                        "referrer_path": pv.get("referrer_path"),
                        "user_agent": pv.get("user_agent"),
                        "browser": pv.get("browser"),
                        "browser_version": pv.get("browser_version"),
                        "os": pv.get("os"),
                        "os_version": pv.get("os_version"),
                        "device_type": pv.get("device_type"),
                        "country_code": pv.get("country_code"),
                        "country_name": pv.get("country_name"),
                        "region": pv.get("region"),
                        "city": pv.get("city"),
                        "edge_location": pv.get("edge_location"),
                        "edge_result_type": pv.get("edge_result_type"),
                        "bytes_sent": pv.get("bytes_sent"),
                        "time_taken_ms": pv.get("time_taken_ms"),
                    }
                    records.append(record)

                try:
                    # Bulk insert using SQLAlchemy core
                    self.db_session.bulk_insert_mappings(PageView, records)
                    self.db_session.commit()
                    inserted_count += len(records)
                    progress.update(task, advance=len(records))
                except Exception as e:
                    console.print(f"[red]Error inserting batch: {e}[/red]")
                    self.db_session.rollback()
                    # Try inserting one by one to identify problematic records
                    for record in records:
                        try:
                            self.db_session.bulk_insert_mappings(PageView, [record])
                            self.db_session.commit()
                            inserted_count += 1
                            progress.update(task, advance=1)
                        except Exception as e2:
                            console.print(
                                f"[red]Failed to insert record: {e2}[/red]"
                            )
                            self.db_session.rollback()

        console.print(f"[green]✓ Inserted {inserted_count} page views[/green]")
        return inserted_count

    def load_sessions(self, sessions: List[Dict[str, any]]) -> int:
        """
        Load sessions into the database with upsert logic.

        Args:
            sessions: List of session dictionaries

        Returns:
            Number of records inserted/updated
        """
        if not sessions:
            console.print("[yellow]No sessions to load[/yellow]")
            return 0

        console.print(f"[cyan]Loading {len(sessions)} sessions...[/cyan]")

        inserted_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Inserting sessions", total=len(sessions))

            # Process in batches
            for i in range(0, len(sessions), self.batch_size):
                batch = sessions[i : i + self.batch_size]

                try:
                    # Use PostgreSQL INSERT ... ON CONFLICT for upsert
                    stmt = insert(SessionModel).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["session_id"],
                        set_={
                            "end_time": stmt.excluded.end_time,
                            "duration_seconds": stmt.excluded.duration_seconds,
                            "page_views_count": stmt.excluded.page_views_count,
                            "exit_page": stmt.excluded.exit_page,
                        },
                    )
                    self.db_session.execute(stmt)
                    self.db_session.commit()
                    inserted_count += len(batch)
                    progress.update(task, advance=len(batch))
                except Exception as e:
                    console.print(f"[red]Error inserting session batch: {e}[/red]")
                    self.db_session.rollback()

        console.print(f"[green]✓ Inserted/updated {inserted_count} sessions[/green]")
        return inserted_count

    def load_visitors(self, visitors: List[Dict[str, any]]) -> int:
        """
        Load visitors into the database with upsert logic.

        Args:
            visitors: List of visitor dictionaries

        Returns:
            Number of records inserted/updated
        """
        if not visitors:
            console.print("[yellow]No visitors to load[/yellow]")
            return 0

        console.print(f"[cyan]Loading {len(visitors)} visitors...[/cyan]")

        inserted_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Inserting visitors", total=len(visitors))

            # Process in batches
            for i in range(0, len(visitors), self.batch_size):
                batch = visitors[i : i + self.batch_size]

                try:
                    # Use PostgreSQL INSERT ... ON CONFLICT for upsert
                    stmt = insert(Visitor).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["visitor_id"],
                        set_={
                            "last_seen": stmt.excluded.last_seen,
                            "total_visits": stmt.excluded.total_visits,
                            "total_page_views": stmt.excluded.total_page_views,
                        },
                    )
                    self.db_session.execute(stmt)
                    self.db_session.commit()
                    inserted_count += len(batch)
                    progress.update(task, advance=len(batch))
                except Exception as e:
                    console.print(f"[red]Error inserting visitor batch: {e}[/red]")
                    self.db_session.rollback()

        console.print(f"[green]✓ Inserted/updated {inserted_count} visitors[/green]")
        return inserted_count

    def load_all(
        self,
        page_views: List[Dict[str, any]],
        sessions: List[Dict[str, any]],
        visitors: List[Dict[str, any]],
    ) -> Dict[str, int]:
        """
        Load all data (page views, sessions, visitors) into the database.

        Args:
            page_views: List of page view dictionaries
            sessions: List of session dictionaries
            visitors: List of visitor dictionaries

        Returns:
            Dictionary with counts of inserted records by type
        """
        console.print("\n[bold cyan]Starting database load...[/bold cyan]\n")

        results = {
            "page_views": self.load_page_views(page_views),
            "sessions": self.load_sessions(sessions),
            "visitors": self.load_visitors(visitors),
        }

        console.print(
            f"\n[bold green]✓ Load complete![/bold green]"
            f"\n  Page Views: {results['page_views']}"
            f"\n  Sessions: {results['sessions']}"
            f"\n  Visitors: {results['visitors']}\n"
        )

        return results
