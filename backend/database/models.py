"""
SQLAlchemy ORM Models for Analytics Dashboard

These models represent the database schema for storing and analyzing
CloudFront access log data.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


class PageView(Base):
    """
    Primary analytics table storing each HTTP request from CloudFront logs.

    This table captures detailed information about every page view including:
    - Request details (URL, method, status)
    - User agent information (browser, OS, device)
    - Geographic location
    - CloudFront edge performance metrics
    """
    __tablename__ = "page_views"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Timestamp and Identifiers
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    visitor_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Request Details
    url_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    query_string: Mapped[Optional[str]] = mapped_column(Text)
    http_method: Mapped[Optional[str]] = mapped_column(String(10))
    status_code: Mapped[Optional[int]] = mapped_column(Integer)

    # Referrer Information
    referrer_domain: Mapped[Optional[str]] = mapped_column(String(255))
    referrer_path: Mapped[Optional[str]] = mapped_column(String(1024))

    # User Agent Parsing
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    browser: Mapped[Optional[str]] = mapped_column(String(100))
    browser_version: Mapped[Optional[str]] = mapped_column(String(50))
    os: Mapped[Optional[str]] = mapped_column(String(100))
    os_version: Mapped[Optional[str]] = mapped_column(String(50))
    device_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)

    # Geographic Data
    country_code: Mapped[Optional[str]] = mapped_column(String(2), index=True)
    country_name: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))

    # CloudFront Specific Metrics
    edge_location: Mapped[Optional[str]] = mapped_column(String(50))
    edge_result_type: Mapped[Optional[str]] = mapped_column(String(50))
    bytes_sent: Mapped[Optional[int]] = mapped_column(BigInteger)
    time_taken_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_visitor_session", "visitor_id", "session_id"),
        Index("idx_timestamp_visitor", "timestamp", "visitor_id"),
        Index("idx_timestamp_url", "timestamp", "url_path"),
    )

    def __repr__(self) -> str:
        return f"<PageView(id={self.id}, url={self.url_path}, timestamp={self.timestamp})>"


class Session(Base):
    """
    Aggregated session data representing a single user visit.

    A session groups multiple page views by the same visitor within a time window
    (typically 30 minutes of inactivity defines session boundary).
    """
    __tablename__ = "sessions"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    visitor_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Session Timing
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Session Metrics
    page_views_count: Mapped[int] = mapped_column(Integer, default=0)
    landing_page: Mapped[Optional[str]] = mapped_column(String(1024))
    exit_page: Mapped[Optional[str]] = mapped_column(String(1024))

    # Session Attributes
    device_type: Mapped[Optional[str]] = mapped_column(String(50))
    country_code: Mapped[Optional[str]] = mapped_column(String(2))

    __table_args__ = (
        Index("idx_start_time_visitor", "start_time", "visitor_id"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.session_id}, visitor={self.visitor_id}, duration={self.duration_seconds}s)>"


class Visitor(Base):
    """
    Unique visitor tracking with lifetime statistics.

    Tracks individual visitors across multiple sessions to enable cohort analysis
    and user retention metrics.
    """
    __tablename__ = "visitors"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    visitor_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Visitor Timeline
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Lifetime Metrics
    total_visits: Mapped[int] = mapped_column(Integer, default=1)
    total_page_views: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_first_last_seen", "first_seen", "last_seen"),
    )

    def __repr__(self) -> str:
        return f"<Visitor(id={self.visitor_id}, visits={self.total_visits}, pages={self.total_page_views})>"


class DailyMetric(Base):
    """
    Pre-aggregated daily statistics for dashboard performance.

    This table stores computed daily metrics to avoid expensive real-time
    aggregations on large page_views table.
    """
    __tablename__ = "daily_metrics"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, unique=True, index=True)

    # Core Metrics
    total_page_views: Mapped[int] = mapped_column(Integer, default=0)
    unique_visitors: Mapped[int] = mapped_column(Integer, default=0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    avg_session_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Engagement Metrics
    bounce_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    # Top performing pages (stored as JSON)
    # Example: [{"url": "/page1", "views": 1000}, {"url": "/page2", "views": 500}]
    top_pages: Mapped[Optional[dict]] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return f"<DailyMetric(date={self.date}, views={self.total_page_views}, visitors={self.unique_visitors})>"


class URLMetadata(Base):
    """
    Optional table to store additional metadata about URLs.

    Useful for categorizing pages, storing page titles, and marking
    active/inactive pages.
    """
    __tablename__ = "url_metadata"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    url_path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)

    # Metadata
    page_title: Mapped[Optional[str]] = mapped_column(String(255))
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<URLMetadata(url={self.url_path}, title={self.page_title})>"
