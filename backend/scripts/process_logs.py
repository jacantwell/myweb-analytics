#!/usr/bin/env python3
"""
CloudFront Log Processing Pipeline

Main script that orchestrates the complete log processing workflow:
1. Parse CloudFront access logs (local files or S3)
2. Enrich log entries with user agent and GeoIP data
3. Build sessions from page views
4. Load data into PostgreSQL database

Usage:
    # Process local log files
    python process_logs.py --local sample_logs/*.log.gz

    # Process logs from S3
    python process_logs.py --s3 --bucket my-logs --prefix cloudfront-logs/

    # Process with GeoIP enrichment
    python process_logs.py --local sample_logs/*.log.gz --geoip /path/to/GeoLite2-City.mmdb
"""
import argparse
import sys
from glob import glob
from pathlib import Path
from typing import List

import boto3
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.connection import get_db_session
from backend.log_processor import (
    CloudFrontLogParser,
    LogLoader,
    SessionBuilder,
    enrich_log_entry,
)
from backend.log_processor.enrichment import GeoIPEnricher

console = Console()


def process_local_files(
    file_patterns: List[str],
    geoip_db_path: str = None,
    session_timeout: int = 30,
    batch_size: int = 1000,
):
    """
    Process CloudFront log files from local filesystem.

    Args:
        file_patterns: List of file path patterns (supports globs)
        geoip_db_path: Optional path to GeoIP database
        session_timeout: Session timeout in minutes
        batch_size: Database insert batch size
    """
    console.print("\n[bold cyan]CloudFront Log Processing Pipeline[/bold cyan]\n")

    # Initialize components
    parser = CloudFrontLogParser()
    geoip_enricher = GeoIPEnricher(geoip_db_path) if geoip_db_path else None
    session_builder = SessionBuilder(session_timeout_minutes=session_timeout)

    # Collect all matching files
    all_files = []
    for pattern in file_patterns:
        matching_files = glob(pattern)
        all_files.extend(matching_files)

    if not all_files:
        console.print("[red]Error: No log files found matching the patterns[/red]")
        return

    console.print(f"Found {len(all_files)} log file(s) to process:")
    for f in all_files:
        console.print(f"  • {Path(f).name}")
    console.print()

    # Process all log files
    all_page_views = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing log files...", total=len(all_files))

        for log_file in all_files:
            progress.update(task, description=f"Processing {Path(log_file).name}...")

            try:
                # Parse log file
                for entry in parser.parse_file(log_file):
                    # Enrich entry
                    entry = enrich_log_entry(entry, geoip_enricher)

                    # Assign session
                    entry = session_builder.add_page_view(entry)

                    # Collect for database insertion
                    all_page_views.append(entry)

            except Exception as e:
                console.print(f"[red]Error processing {log_file}: {e}[/red]")

            progress.advance(task)

    console.print(
        f"\n[green]✓ Parsed {len(all_page_views)} log entries[/green]"
    )

    # Get sessions and visitors
    sessions = session_builder.get_sessions()
    visitors = session_builder.get_visitors()

    console.print(f"[green]✓ Built {len(sessions)} sessions from {len(visitors)} visitors[/green]\n")

    # Load into database
    with get_db_session() as db_session:
        loader = LogLoader(db_session, batch_size=batch_size)
        results = loader.load_all(all_page_views, sessions, visitors)

    console.print("[bold green]✓ Pipeline complete![/bold green]\n")
    return results


def process_s3_logs(
    bucket: str,
    prefix: str = "",
    geoip_db_path: str = None,
    session_timeout: int = 30,
    batch_size: int = 1000,
    max_files: int = None,
):
    """
    Process CloudFront log files from S3.

    Args:
        bucket: S3 bucket name
        prefix: S3 key prefix for log files
        geoip_db_path: Optional path to GeoIP database
        session_timeout: Session timeout in minutes
        batch_size: Database insert batch size
        max_files: Maximum number of files to process (for testing)
    """
    console.print("\n[bold cyan]CloudFront Log Processing Pipeline (S3)[/bold cyan]\n")

    # Initialize AWS S3 client
    s3_client = boto3.client("s3")

    # Initialize processing components
    parser = CloudFrontLogParser()
    geoip_enricher = GeoIPEnricher(geoip_db_path) if geoip_db_path else None
    session_builder = SessionBuilder(session_timeout_minutes=session_timeout)

    # List log files in S3
    console.print(f"Listing files in s3://{bucket}/{prefix}...")
    paginator = s3_client.get_paginator("list_objects_v2")
    log_files = []

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                # Only process .gz files or .log files
                if key.endswith(".gz") or key.endswith(".log"):
                    log_files.append(key)

    if max_files:
        log_files = log_files[:max_files]

    if not log_files:
        console.print("[red]Error: No log files found in S3[/red]")
        return

    console.print(f"Found {len(log_files)} log file(s) to process\n")

    # Process all log files
    all_page_views = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing S3 logs...", total=len(log_files))

        for log_key in log_files:
            progress.update(task, description=f"Processing {Path(log_key).name}...")

            try:
                # Parse S3 object
                for entry in parser.parse_s3_object(s3_client, bucket, log_key):
                    # Enrich entry
                    entry = enrich_log_entry(entry, geoip_enricher)

                    # Assign session
                    entry = session_builder.add_page_view(entry)

                    # Collect for database insertion
                    all_page_views.append(entry)

            except Exception as e:
                console.print(f"[red]Error processing {log_key}: {e}[/red]")

            progress.advance(task)

    console.print(
        f"\n[green]✓ Parsed {len(all_page_views)} log entries[/green]"
    )

    # Get sessions and visitors
    sessions = session_builder.get_sessions()
    visitors = session_builder.get_visitors()

    console.print(
        f"[green]✓ Built {len(sessions)} sessions from {len(visitors)} visitors[/green]\n"
    )

    # Load into database
    with get_db_session() as db_session:
        loader = LogLoader(db_session, batch_size=batch_size)
        results = loader.load_all(all_page_views, sessions, visitors)

    console.print("[bold green]✓ Pipeline complete![/bold green]\n")
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Process CloudFront access logs into analytics database"
    )

    # Source selection
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--local",
        nargs="+",
        metavar="FILE",
        help="Process local log files (supports glob patterns)",
    )
    source_group.add_argument(
        "--s3",
        action="store_true",
        help="Process logs from S3",
    )

    # S3 options
    parser.add_argument(
        "--bucket",
        help="S3 bucket name (required with --s3)",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="S3 key prefix for log files (default: root)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum number of S3 files to process (for testing)",
    )

    # Processing options
    parser.add_argument(
        "--geoip",
        metavar="DB_PATH",
        help="Path to MaxMind GeoLite2-City.mmdb database",
    )
    parser.add_argument(
        "--session-timeout",
        type=int,
        default=30,
        help="Session timeout in minutes (default: 30)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Database insert batch size (default: 1000)",
    )

    args = parser.parse_args()

    # Validate S3 arguments
    if args.s3 and not args.bucket:
        parser.error("--bucket is required when using --s3")

    try:
        if args.local:
            process_local_files(
                file_patterns=args.local,
                geoip_db_path=args.geoip,
                session_timeout=args.session_timeout,
                batch_size=args.batch_size,
            )
        elif args.s3:
            process_s3_logs(
                bucket=args.bucket,
                prefix=args.prefix,
                geoip_db_path=args.geoip,
                session_timeout=args.session_timeout,
                batch_size=args.batch_size,
                max_files=args.max_files,
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Processing interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
