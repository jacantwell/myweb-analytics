#!/usr/bin/env python3
"""
Generate Sample CloudFront Access Logs

Creates realistic CloudFront access log files for testing the analytics pipeline.
Generates diverse user behaviors including:
- Multiple visitors with different session patterns
- Various devices, browsers, and operating systems
- Geographic distribution
- Referrer sources (direct, search, social, referral)
- Different page paths and status codes
"""
import gzip
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from faker import Faker

fake = Faker()


class CloudFrontLogGenerator:
    """Generates realistic CloudFront access log entries"""

    # Common user agents
    USER_AGENTS = [
        # Desktop Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Desktop Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Desktop Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Mobile Chrome
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        # Mobile Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Tablet
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Bots
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    ]

    # Common page paths
    PAGE_PATHS = [
        "/",
        "/about",
        "/contact",
        "/blog",
        "/blog/getting-started",
        "/blog/advanced-tips",
        "/products",
        "/products/widget-1",
        "/products/widget-2",
        "/pricing",
        "/documentation",
        "/api/docs",
        "/login",
        "/signup",
        "/dashboard",
    ]

    # Referrers
    REFERRERS = [
        "-",  # Direct traffic
        "https://www.google.com/search?q=example",
        "https://www.bing.com/search?q=example",
        "https://www.facebook.com/",
        "https://twitter.com/",
        "https://www.reddit.com/r/programming",
        "https://news.ycombinator.com/",
        "https://www.linkedin.com/",
    ]

    # CloudFront edge locations
    EDGE_LOCATIONS = [
        "IAD89-C1",
        "LAX50-C1",
        "DFW55-C1",
        "SEA19-C1",
        "LHR61-C1",
        "FRA56-C1",
        "NRT57-C1",
        "SYD62-C1",
    ]

    # Result types
    RESULT_TYPES = ["Hit", "Miss", "RefreshHit", "Error"]

    def __init__(self):
        """Initialize the log generator"""
        pass

    def generate_log_entry(
        self,
        timestamp: datetime,
        ip_address: str,
        user_agent: str,
        referrer: str = "-",
    ) -> str:
        """
        Generate a single CloudFront log entry.

        Args:
            timestamp: Timestamp for the log entry
            ip_address: Client IP address
            user_agent: User agent string
            referrer: Referrer URL

        Returns:
            Tab-delimited log entry string
        """
        date = timestamp.strftime("%Y-%m-%d")
        time = timestamp.strftime("%H:%M:%S")
        edge_location = random.choice(self.EDGE_LOCATIONS)
        sc_bytes = random.randint(500, 50000)
        cs_method = "GET"
        cs_host = "example.cloudfront.net"
        cs_uri_stem = random.choice(self.PAGE_PATHS)

        # Status code (mostly 200s, some 404s, rare 500s)
        status_rand = random.random()
        if status_rand < 0.90:
            sc_status = "200"
        elif status_rand < 0.97:
            sc_status = "404"
        else:
            sc_status = "500"

        cs_uri_query = "-"
        cs_cookie = "-"
        x_edge_result_type = random.choice(self.RESULT_TYPES)
        x_edge_request_id = fake.uuid4()
        x_host_header = "www.example.com"
        cs_protocol = "https"
        cs_bytes = random.randint(100, 1000)
        time_taken = round(random.uniform(0.01, 2.0), 3)
        x_forwarded_for = "-"
        ssl_protocol = "TLSv1.3"
        ssl_cipher = "ECDHE-RSA-AES128-GCM-SHA256"
        x_edge_response_result_type = x_edge_result_type
        cs_protocol_version = "HTTP/2.0"
        fle_status = "-"
        fle_encrypted_fields = "-"
        c_port = random.choice(["443", "80"])
        time_to_first_byte = round(random.uniform(0.001, 0.5), 3)
        x_edge_detailed_result_type = x_edge_result_type
        sc_content_type = "text/html"
        sc_content_len = sc_bytes
        sc_range_start = "-"
        sc_range_end = "-"

        # Build tab-delimited entry
        fields = [
            date,
            time,
            edge_location,
            str(sc_bytes),
            ip_address,
            cs_method,
            cs_host,
            cs_uri_stem,
            str(sc_status),
            referrer,
            user_agent,
            cs_uri_query,
            cs_cookie,
            x_edge_result_type,
            x_edge_request_id,
            x_host_header,
            cs_protocol,
            str(cs_bytes),
            str(time_taken),
            x_forwarded_for,
            ssl_protocol,
            ssl_cipher,
            x_edge_response_result_type,
            cs_protocol_version,
            fle_status,
            fle_encrypted_fields,
            c_port,
            str(time_to_first_byte),
            x_edge_detailed_result_type,
            sc_content_type,
            str(sc_content_len),
            sc_range_start,
            sc_range_end,
        ]

        return "\t".join(fields)

    def generate_visitor_session(
        self, start_time: datetime, pages_count: int = None
    ) -> List[str]:
        """
        Generate a realistic visitor session (multiple page views).

        Args:
            start_time: Session start timestamp
            pages_count: Number of pages in session (random if None)

        Returns:
            List of log entry strings
        """
        if pages_count is None:
            # Most sessions have 1-5 pages, some have more
            pages_count = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                weights=[30, 25, 20, 10, 7, 4, 2, 1, 0.5, 0.5],
            )[0]

        # Generate consistent visitor attributes
        ip_address = fake.ipv4()
        user_agent = random.choice(self.USER_AGENTS)
        referrer = random.choice(self.REFERRERS)

        entries = []
        current_time = start_time

        for i in range(pages_count):
            # First page uses external referrer, subsequent pages use internal
            if i == 0:
                page_referrer = referrer
            else:
                # Internal referrer (previous page)
                page_referrer = f"https://www.example.com{random.choice(self.PAGE_PATHS)}"

            # Generate log entry
            entry = self.generate_log_entry(
                current_time, ip_address, user_agent, page_referrer
            )
            entries.append(entry)

            # Time between pages (5-60 seconds typically)
            time_gap = random.randint(5, 60)
            current_time += timedelta(seconds=time_gap)

        return entries

    def generate_log_file(
        self,
        output_path: Path,
        start_date: datetime,
        duration_hours: int = 24,
        visitors_per_hour: int = 50,
        compress: bool = True,
    ):
        """
        Generate a complete CloudFront log file.

        Args:
            output_path: Path for output file
            start_date: Start timestamp for logs
            duration_hours: Number of hours to generate logs for
            visitors_per_hour: Average number of visitors per hour
            compress: Whether to gzip compress the output
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # CloudFront log header
        header_lines = [
            "#Version: 1.0",
            f"#Fields: date time x-edge-location sc-bytes c-ip cs-method cs(Host) cs-uri-stem sc-status cs(Referer) cs(User-Agent) cs-uri-query cs(Cookie) x-edge-result-type x-edge-request-id x-host-header cs-protocol cs-bytes time-taken x-forwarded-for ssl-protocol ssl-cipher x-edge-response-result-type cs-protocol-version fle-status fle-encrypted-fields c-port time-to-first-byte x-edge-detailed-result-type sc-content-type sc-content-len sc-range-start sc-range-end",
        ]

        all_entries = []

        # Generate sessions across the time period
        print(f"Generating {duration_hours} hours of logs...")
        for hour in range(duration_hours):
            hour_start = start_date + timedelta(hours=hour)

            # Generate visitors for this hour
            num_visitors = random.randint(
                int(visitors_per_hour * 0.7), int(visitors_per_hour * 1.3)
            )

            for _ in range(num_visitors):
                # Random start time within the hour
                minute_offset = random.randint(0, 59)
                second_offset = random.randint(0, 59)
                session_start = hour_start + timedelta(
                    minutes=minute_offset, seconds=second_offset
                )

                # Generate session
                session_entries = self.generate_visitor_session(session_start)
                all_entries.extend(session_entries)

        # Sort entries by timestamp
        print("Sorting entries by timestamp...")
        all_entries.sort()

        # Write to file
        print(f"Writing to {output_path}...")
        if compress:
            with gzip.open(output_path, "wt", encoding="utf-8") as f:
                f.write("\n".join(header_lines) + "\n")
                f.write("\n".join(all_entries) + "\n")
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(header_lines) + "\n")
                f.write("\n".join(all_entries) + "\n")

        # Count unique IPs
        unique_ips = len(set(e.split('\t')[4] for e in all_entries))
        print(
            f"✓ Generated {len(all_entries)} log entries ({unique_ips} unique IPs)"
        )


def main():
    """Generate sample log files"""
    generator = CloudFrontLogGenerator()

    # Create sample_logs directory
    sample_logs_dir = Path(__file__).parent.parent / "sample_logs"
    sample_logs_dir.mkdir(exist_ok=True)

    # Generate 7 days of logs
    print("\nGenerating 7 days of sample CloudFront logs...\n")
    start_date = datetime.now() - timedelta(days=7)

    for day in range(7):
        day_start = start_date + timedelta(days=day)
        filename = f"cloudfront-logs-{day_start.strftime('%Y-%m-%d')}.log.gz"
        output_path = sample_logs_dir / filename

        print(f"\nDay {day + 1}/7: {day_start.strftime('%Y-%m-%d')}")
        generator.generate_log_file(
            output_path=output_path,
            start_date=day_start,
            duration_hours=24,
            visitors_per_hour=100,  # 100 visitors/hour = ~2,400/day
            compress=True,
        )

    print(f"\n✓ All sample logs generated in: {sample_logs_dir}\n")


if __name__ == "__main__":
    main()
