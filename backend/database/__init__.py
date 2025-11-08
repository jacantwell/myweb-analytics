"""
Database package for Analytics Dashboard

This package contains:
- SQLAlchemy models for all database tables
- Database connection and session management
- Query utilities and data access layer
"""
from .models import (
    Base,
    PageView,
    Session,
    Visitor,
    DailyMetric,
    URLMetadata,
)
from .connection import (
    get_engine,
    get_session,
    get_db_session,
    init_db,
)

__all__ = [
    "Base",
    "PageView",
    "Session",
    "Visitor",
    "DailyMetric",
    "URLMetadata",
    "get_engine",
    "get_session",
    "get_db_session",
    "init_db",
]
