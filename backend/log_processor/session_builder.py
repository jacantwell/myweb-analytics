"""
Session Detection and Building

Groups page views into sessions based on visitor ID and time gaps.
A new session starts after 30 minutes of inactivity.
"""
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class SessionBuilder:
    """
    Builds sessions from page view entries.

    A session is a group of page views from the same visitor within a time window.
    Default session timeout is 30 minutes.
    """

    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize session builder.

        Args:
            session_timeout_minutes: Minutes of inactivity before starting new session
        """
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.sessions_by_visitor: Dict[str, List[Dict]] = defaultdict(list)

    def add_page_view(self, entry: Dict[str, any]) -> Dict[str, any]:
        """
        Add a page view and assign it to a session.

        Args:
            entry: Enriched log entry

        Returns:
            Entry with added 'session_id' field
        """
        visitor_id = entry.get("visitor_id")
        timestamp = entry.get("timestamp")

        if not visitor_id or not timestamp:
            # Can't assign session without visitor ID or timestamp
            entry["session_id"] = None
            return entry

        # Get or create session for this visitor
        session_id = self._get_or_create_session(visitor_id, timestamp, entry)
        entry["session_id"] = session_id

        return entry

    def _get_or_create_session(
        self, visitor_id: str, timestamp: datetime, entry: Dict[str, any]
    ) -> str:
        """
        Find existing session or create new one based on timeout.

        Args:
            visitor_id: Visitor identifier
            timestamp: Timestamp of current page view
            entry: Full log entry (for session metadata)

        Returns:
            Session ID string
        """
        visitor_sessions = self.sessions_by_visitor[visitor_id]

        # Check if we have any sessions for this visitor
        if not visitor_sessions:
            # First session for this visitor
            session_id = self._generate_session_id(visitor_id, timestamp)
            visitor_sessions.append(
                {
                    "session_id": session_id,
                    "start_time": timestamp,
                    "last_activity": timestamp,
                    "page_views_count": 1,
                    "landing_page": entry.get("url_path"),
                    "exit_page": entry.get("url_path"),
                    "device_type": entry.get("device_type"),
                    "country_code": entry.get("country_code"),
                }
            )
            return session_id

        # Get the most recent session
        current_session = visitor_sessions[-1]

        # Check if current timestamp is within session timeout
        time_since_last_activity = timestamp - current_session["last_activity"]

        if time_since_last_activity <= self.session_timeout:
            # Continue existing session
            current_session["last_activity"] = timestamp
            current_session["page_views_count"] += 1
            current_session["exit_page"] = entry.get("url_path")
            return current_session["session_id"]
        else:
            # Timeout exceeded - start new session
            session_id = self._generate_session_id(visitor_id, timestamp)
            visitor_sessions.append(
                {
                    "session_id": session_id,
                    "start_time": timestamp,
                    "last_activity": timestamp,
                    "page_views_count": 1,
                    "landing_page": entry.get("url_path"),
                    "exit_page": entry.get("url_path"),
                    "device_type": entry.get("device_type"),
                    "country_code": entry.get("country_code"),
                }
            )
            return session_id

    def _generate_session_id(self, visitor_id: str, timestamp: datetime) -> str:
        """
        Generate a unique session ID.

        Args:
            visitor_id: Visitor identifier
            timestamp: Session start timestamp

        Returns:
            Unique session identifier
        """
        # Combine visitor ID and timestamp to create unique session ID
        session_key = f"{visitor_id}:{timestamp.isoformat()}"
        return hashlib.sha256(session_key.encode()).hexdigest()[:32]

    def get_sessions(self) -> List[Dict[str, any]]:
        """
        Get all completed sessions with calculated metrics.

        Returns:
            List of session dictionaries ready for database insertion
        """
        all_sessions = []

        for visitor_id, sessions in self.sessions_by_visitor.items():
            for session in sessions:
                # Calculate session duration
                duration = session["last_activity"] - session["start_time"]
                duration_seconds = int(duration.total_seconds())

                all_sessions.append(
                    {
                        "session_id": session["session_id"],
                        "visitor_id": visitor_id,
                        "start_time": session["start_time"],
                        "end_time": session["last_activity"],
                        "duration_seconds": duration_seconds,
                        "page_views_count": session["page_views_count"],
                        "landing_page": session["landing_page"],
                        "exit_page": session["exit_page"],
                        "device_type": session["device_type"],
                        "country_code": session["country_code"],
                    }
                )

        return all_sessions

    def get_visitors(self) -> List[Dict[str, any]]:
        """
        Get visitor statistics aggregated across all sessions.

        Returns:
            List of visitor dictionaries ready for database insertion
        """
        visitors = []

        for visitor_id, sessions in self.sessions_by_visitor.items():
            if not sessions:
                continue

            # Calculate visitor metrics
            first_session = sessions[0]
            last_session = sessions[-1]

            total_page_views = sum(s["page_views_count"] for s in sessions)
            total_visits = len(sessions)

            visitors.append(
                {
                    "visitor_id": visitor_id,
                    "first_seen": first_session["start_time"],
                    "last_seen": last_session["last_activity"],
                    "total_visits": total_visits,
                    "total_page_views": total_page_views,
                }
            )

        return visitors

    def reset(self):
        """Clear all session data"""
        self.sessions_by_visitor.clear()
