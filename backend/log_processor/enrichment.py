"""
Log Entry Enrichment

Enriches parsed log entries with additional data:
- User agent parsing (browser, OS, device type)
- Geographic location (GeoIP lookup)
- Referrer categorization
"""
from pathlib import Path
from typing import Dict, Optional

from user_agents import parse as parse_user_agent

try:
    import geoip2.database
    from geoip2.errors import AddressNotFoundError

    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False


class UserAgentEnricher:
    """Enriches log entries with parsed user agent data"""

    @staticmethod
    def enrich(entry: Dict[str, any]) -> Dict[str, any]:
        """
        Parse user agent and add browser, OS, and device type information.

        Args:
            entry: Log entry dictionary

        Returns:
            Entry with added user agent fields
        """
        user_agent_string = entry.get("user_agent")

        if not user_agent_string:
            entry["browser"] = None
            entry["browser_version"] = None
            entry["os"] = None
            entry["os_version"] = None
            entry["device_type"] = "unknown"
            return entry

        try:
            ua = parse_user_agent(user_agent_string)

            # Browser information
            entry["browser"] = ua.browser.family if ua.browser.family else None
            entry["browser_version"] = (
                ua.browser.version_string if ua.browser.version_string else None
            )

            # Operating system
            entry["os"] = ua.os.family if ua.os.family else None
            entry["os_version"] = ua.os.version_string if ua.os.version_string else None

            # Device type categorization
            if ua.is_bot:
                entry["device_type"] = "bot"
            elif ua.is_mobile:
                entry["device_type"] = "mobile"
            elif ua.is_tablet:
                entry["device_type"] = "tablet"
            elif ua.is_pc:
                entry["device_type"] = "desktop"
            else:
                entry["device_type"] = "unknown"

        except Exception as e:
            # If parsing fails, set defaults
            print(f"User agent parsing error: {e}")
            entry["browser"] = None
            entry["browser_version"] = None
            entry["os"] = None
            entry["os_version"] = None
            entry["device_type"] = "unknown"

        return entry


class GeoIPEnricher:
    """Enriches log entries with geographic location data using MaxMind GeoIP2"""

    def __init__(self, geoip_db_path: Optional[str] = None):
        """
        Initialize GeoIP enricher.

        Args:
            geoip_db_path: Path to MaxMind GeoLite2-City.mmdb file
        """
        self.reader = None

        if not GEOIP_AVAILABLE:
            print("Warning: geoip2 library not available. GeoIP enrichment disabled.")
            return

        if geoip_db_path and Path(geoip_db_path).exists():
            try:
                self.reader = geoip2.database.Reader(geoip_db_path)
                print(f"GeoIP database loaded: {geoip_db_path}")
            except Exception as e:
                print(f"Error loading GeoIP database: {e}")
        else:
            print(
                "GeoIP database not found. Geographic enrichment will be skipped."
                "\nTo enable GeoIP, download MaxMind GeoLite2-City database from:"
                "\nhttps://dev.maxmind.com/geoip/geolite2-free-geolocation-data"
            )

    def enrich(self, entry: Dict[str, any]) -> Dict[str, any]:
        """
        Add geographic location data based on IP address.

        Args:
            entry: Log entry dictionary with 'client_ip' field

        Returns:
            Entry with added geographic fields
        """
        # Set defaults
        entry["country_code"] = None
        entry["country_name"] = None
        entry["region"] = None
        entry["city"] = None

        if not self.reader:
            return entry

        client_ip = entry.get("client_ip")
        if not client_ip:
            return entry

        try:
            response = self.reader.city(client_ip)

            entry["country_code"] = (
                response.country.iso_code if response.country.iso_code else None
            )
            entry["country_name"] = response.country.name if response.country.name else None
            entry["region"] = (
                response.subdivisions.most_specific.name
                if response.subdivisions.most_specific.name
                else None
            )
            entry["city"] = response.city.name if response.city.name else None

        except AddressNotFoundError:
            # IP not found in database (private IP, etc.)
            pass
        except Exception as e:
            print(f"GeoIP lookup error for {client_ip}: {e}")

        return entry

    def __del__(self):
        """Close the GeoIP database reader"""
        if self.reader:
            self.reader.close()


class ReferrerEnricher:
    """Enriches log entries with categorized referrer information"""

    # Common search engines
    SEARCH_ENGINES = [
        "google",
        "bing",
        "yahoo",
        "duckduckgo",
        "baidu",
        "yandex",
        "ask",
    ]

    # Common social media platforms
    SOCIAL_MEDIA = [
        "facebook",
        "twitter",
        "linkedin",
        "reddit",
        "pinterest",
        "instagram",
        "tiktok",
        "youtube",
    ]

    @staticmethod
    def enrich(entry: Dict[str, any]) -> Dict[str, any]:
        """
        Categorize referrer source.

        Args:
            entry: Log entry dictionary

        Returns:
            Entry with added 'referrer_category' field
        """
        referrer_domain = entry.get("referrer_domain")

        if not referrer_domain:
            entry["referrer_category"] = "direct"
            return entry

        domain_lower = referrer_domain.lower()

        # Check if search engine
        if any(engine in domain_lower for engine in ReferrerEnricher.SEARCH_ENGINES):
            entry["referrer_category"] = "search"
        # Check if social media
        elif any(social in domain_lower for social in ReferrerEnricher.SOCIAL_MEDIA):
            entry["referrer_category"] = "social"
        # Check if internal referrer (same domain)
        elif entry.get("url_path") and domain_lower in entry.get("url_path", ""):
            entry["referrer_category"] = "internal"
        else:
            entry["referrer_category"] = "referral"

        return entry


def enrich_log_entry(
    entry: Dict[str, any], geoip_enricher: Optional[GeoIPEnricher] = None
) -> Dict[str, any]:
    """
    Apply all enrichment to a log entry.

    Args:
        entry: Parsed log entry
        geoip_enricher: Optional GeoIP enricher instance

    Returns:
        Fully enriched log entry
    """
    # User agent enrichment
    entry = UserAgentEnricher.enrich(entry)

    # GeoIP enrichment (if available)
    if geoip_enricher:
        entry = geoip_enricher.enrich(entry)
    else:
        # Set defaults if no GeoIP enricher
        entry["country_code"] = None
        entry["country_name"] = None
        entry["region"] = None
        entry["city"] = None

    # Referrer enrichment
    entry = ReferrerEnricher.enrich(entry)

    return entry
