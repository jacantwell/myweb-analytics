"""
CloudFront Log Parser

Parses CloudFront access logs in standard tab-delimited format.
Supports both plain text and gzip-compressed (.gz) log files.

CloudFront log format reference:
https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html
"""
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, Optional, Union
from urllib.parse import unquote, urlparse


class CloudFrontLogParser:
    """Parser for CloudFront access logs"""

    # CloudFront standard log fields (version 1.0)
    FIELD_NAMES = [
        "date",
        "time",
        "x-edge-location",
        "sc-bytes",
        "c-ip",
        "cs-method",
        "cs-host",
        "cs-uri-stem",
        "sc-status",
        "cs-referer",
        "cs-user-agent",
        "cs-uri-query",
        "cs-cookie",
        "x-edge-result-type",
        "x-edge-request-id",
        "x-host-header",
        "cs-protocol",
        "cs-bytes",
        "time-taken",
        "x-forwarded-for",
        "ssl-protocol",
        "ssl-cipher",
        "x-edge-response-result-type",
        "cs-protocol-version",
        "fle-status",
        "fle-encrypted-fields",
        "c-port",
        "time-to-first-byte",
        "x-edge-detailed-result-type",
        "sc-content-type",
        "sc-content-len",
        "sc-range-start",
        "sc-range-end",
    ]

    def __init__(self):
        """Initialize the CloudFront log parser"""
        pass

    def parse_file(
        self, file_path: Union[str, Path]
    ) -> Generator[Dict[str, any], None, None]:
        """
        Parse a CloudFront log file (plain text or gzip-compressed).

        Args:
            file_path: Path to the log file

        Yields:
            Dictionary containing parsed log entry fields
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        # Determine if file is gzip-compressed
        is_gzipped = file_path.suffix == ".gz"

        open_func = gzip.open if is_gzipped else open
        mode = "rt" if is_gzipped else "r"

        with open_func(file_path, mode, encoding="utf-8") as f:
            for line in f:
                # Skip comments and version lines
                if line.startswith("#"):
                    continue

                # Skip empty lines
                line = line.strip()
                if not line:
                    continue

                # Parse the log entry
                entry = self._parse_line(line)
                if entry:
                    yield entry

    def parse_s3_object(
        self, s3_client, bucket: str, key: str
    ) -> Generator[Dict[str, any], None, None]:
        """
        Parse a CloudFront log file directly from S3.

        Args:
            s3_client: Boto3 S3 client
            bucket: S3 bucket name
            key: S3 object key

        Yields:
            Dictionary containing parsed log entry fields
        """
        response = s3_client.get_object(Bucket=bucket, Key=key)
        body = response["Body"]

        # Determine if file is gzip-compressed based on key
        is_gzipped = key.endswith(".gz")

        if is_gzipped:
            # Read and decompress the entire object
            compressed_data = body.read()
            decompressed_data = gzip.decompress(compressed_data)
            lines = decompressed_data.decode("utf-8").splitlines()
        else:
            # Read as text
            lines = body.read().decode("utf-8").splitlines()

        for line in lines:
            # Skip comments and version lines
            if line.startswith("#"):
                continue

            # Skip empty lines
            line = line.strip()
            if not line:
                continue

            # Parse the log entry
            entry = self._parse_line(line)
            if entry:
                yield entry

    def _parse_line(self, line: str) -> Optional[Dict[str, any]]:
        """
        Parse a single line from a CloudFront log.

        Args:
            line: Tab-delimited log line

        Returns:
            Dictionary with parsed fields, or None if parsing fails
        """
        try:
            # Split by tabs
            fields = line.split("\t")

            # Create dictionary from field names and values
            entry = {}
            for i, field_name in enumerate(self.FIELD_NAMES):
                if i < len(fields):
                    value = fields[i]
                    # CloudFront uses '-' for empty/null values
                    entry[field_name] = None if value == "-" else value
                else:
                    entry[field_name] = None

            # Parse and normalize the entry
            return self._normalize_entry(entry)

        except Exception as e:
            # Log parsing error but don't stop processing
            print(f"Error parsing line: {e}")
            return None

    def _normalize_entry(self, entry: Dict[str, any]) -> Dict[str, any]:
        """
        Normalize and transform parsed log entry.

        Args:
            entry: Raw parsed entry

        Returns:
            Normalized entry with proper data types and enriched fields
        """
        normalized = {}

        # Combine date and time into timestamp
        if entry.get("date") and entry.get("time"):
            timestamp_str = f"{entry['date']} {entry['time']}"
            normalized["timestamp"] = datetime.strptime(
                timestamp_str, "%Y-%m-%d %H:%M:%S"
            )
        else:
            normalized["timestamp"] = None

        # Request details
        normalized["url_path"] = (
            unquote(entry["cs-uri-stem"]) if entry.get("cs-uri-stem") else None
        )
        normalized["query_string"] = (
            unquote(entry["cs-uri-query"]) if entry.get("cs-uri-query") else None
        )
        normalized["http_method"] = entry.get("cs-method")
        normalized["status_code"] = (
            int(entry["sc-status"]) if entry.get("sc-status") else None
        )

        # Client IP (used for visitor ID hashing)
        normalized["client_ip"] = entry.get("c-ip")

        # Referrer parsing
        referrer = entry.get("cs-referer")
        if referrer and referrer != "-":
            try:
                referrer = unquote(referrer)
                parsed_referrer = urlparse(referrer)
                normalized["referrer_domain"] = parsed_referrer.netloc
                normalized["referrer_path"] = parsed_referrer.path
            except:
                normalized["referrer_domain"] = None
                normalized["referrer_path"] = None
        else:
            normalized["referrer_domain"] = None
            normalized["referrer_path"] = None

        # User agent
        normalized["user_agent"] = (
            unquote(entry["cs-user-agent"]) if entry.get("cs-user-agent") else None
        )

        # CloudFront specific metrics
        normalized["edge_location"] = entry.get("x-edge-location")
        normalized["edge_result_type"] = entry.get("x-edge-result-type")
        normalized["bytes_sent"] = (
            int(entry["sc-bytes"]) if entry.get("sc-bytes") else None
        )

        # Time taken (convert to milliseconds)
        if entry.get("time-taken"):
            try:
                # CloudFront logs time in seconds with decimals
                time_taken_seconds = float(entry["time-taken"])
                normalized["time_taken_ms"] = int(time_taken_seconds * 1000)
            except:
                normalized["time_taken_ms"] = None
        else:
            normalized["time_taken_ms"] = None

        # Create a visitor ID from hashed IP
        if normalized["client_ip"]:
            normalized["visitor_id"] = self._hash_ip(normalized["client_ip"])
        else:
            normalized["visitor_id"] = None

        return normalized

    @staticmethod
    def _hash_ip(ip_address: str) -> str:
        """
        Create a privacy-preserving hash of the IP address.

        Uses SHA256 with a salt for one-way hashing to protect user privacy
        while maintaining consistent visitor identification.

        Args:
            ip_address: IP address to hash

        Returns:
            Hex digest of hashed IP
        """
        # Use a consistent salt (in production, load from environment)
        salt = "analytics-visitor-id-salt"
        hash_input = f"{salt}{ip_address}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()[:32]
