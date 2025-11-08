"""
Database Connection Management

This module handles database connections for both local development and AWS RDS.
It automatically detects the environment and uses appropriate configuration.
"""
import json
import os
from typing import Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv

import boto3
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from database.models import Base


class DatabaseConfig:
    """Database configuration that works for both local and AWS environments"""

    def __init__(self):

        load_dotenv()  # Load environment variables from .env file

        self.env = os.getenv("ENVIRONMENT", "local")  # local, development, production
        self.use_aws = os.getenv("USE_AWS_RDS", "false").lower() == "true"

    def get_connection_url(self) -> str:
        """
        Get database connection URL based on environment.

        Returns appropriate connection string for:
        - Local development (Docker PostgreSQL)
        - AWS RDS (with credentials from Secrets Manager or environment variables)
        """
        print(f"Using AWS RDS: {self.use_aws}")

        if self.use_aws:
            return self._get_aws_connection_url()
        else:
            return self._get_local_connection_url()

    def _get_local_connection_url(self) -> str:
        """Get connection URL for local Docker PostgreSQL"""
        user = os.getenv("DB_USER", "analytics_admin")
        password = os.getenv("DB_PASSWORD", "local_dev_password")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "analytics")

        # URL encode password to handle special characters
        encoded_password = quote_plus(password)

        return f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"

    def _get_aws_connection_url(self) -> str:
        """
        Get connection URL for AWS RDS.

        Attempts to retrieve credentials in this order:
        1. AWS Secrets Manager (using secret ARN from environment)
        2. Environment variables (DB_USER, DB_PASSWORD, etc.)
        """
        secret_arn = os.getenv("DB_SECRET_ARN")

        if secret_arn:
            # Get credentials from Secrets Manager
            credentials = self._get_secret_from_aws(secret_arn)
            user = credentials["username"]
            password = credentials["password"]
        else:
            # Fallback to environment variables
            user = os.getenv("DB_USER")
            password = os.getenv("DB_PASSWORD")

            if not user or not password:
                raise ValueError(
                    "Database credentials not found. Set DB_SECRET_ARN or "
                    "DB_USER/DB_PASSWORD environment variables."
                )

        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME", "analytics")

        if not host:
            raise ValueError("DB_HOST environment variable is required for AWS RDS")

        # URL encode password to handle special characters
        encoded_password = quote_plus(password)

        return f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"

    @staticmethod
    def _get_secret_from_aws(secret_arn: str) -> dict:
        """
        Retrieve database credentials from AWS Secrets Manager.

        Args:
            secret_arn: ARN of the secret in Secrets Manager

        Returns:
            Dictionary containing 'username' and 'password'
        """
        region = os.getenv("AWS_REGION", "eu-west-1")
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region)

        try:
            response = client.get_secret_value(SecretId=secret_arn)
            secret_string = response["SecretString"]
            return json.loads(secret_string)
        except Exception as e:
            print(e)
            raise RuntimeError(f"Failed to retrieve secret from AWS: {e}")


# Global engine and session factory
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine(echo: bool = False, pool_size: int = 5) -> Engine:
    """
    Get or create SQLAlchemy engine.

    Args:
        echo: If True, log all SQL statements (useful for debugging)
        pool_size: Number of connections to maintain in the pool

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine

    if _engine is None:
        config = DatabaseConfig()
        connection_url = config.get_connection_url()

        # Configure connection pool based on environment
        if config.use_aws:
            # Use connection pooling for RDS
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": pool_size,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 3600,  # Recycle connections after 1 hour
                "pool_pre_ping": True,  # Verify connections before using
            }
        else:
            # For local development, simpler pooling is fine
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": pool_size,
                "max_overflow": 5,
                "pool_pre_ping": True,
            }

        _engine = create_engine(
            connection_url,
            echo=echo,
            poolclass=poolclass,
            **pool_kwargs,
        )

        # Add event listeners for better connection management
        @event.listens_for(_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Set connection parameters on new connections"""
            # Set timezone to UTC
            cursor = dbapi_conn.cursor()
            cursor.execute("SET timezone='UTC'")
            cursor.close()

    return _engine


def get_session() -> Session:
    """
    Get a new database session.

    Returns:
        SQLAlchemy Session instance

    Usage:
        with get_session() as session:
            # Use session
            session.add(obj)
            session.commit()
    """
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    return _SessionLocal()


def init_db(drop_existing: bool = False) -> None:
    """
    Initialize the database by creating all tables.

    Args:
        drop_existing: If True, drop all existing tables first (CAUTION!)

    Warning:
        Setting drop_existing=True will delete all data!
    """
    engine = get_engine()

    if drop_existing:
        print("⚠️  Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Existing tables dropped")

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


# Context manager for session management
class DatabaseSession:
    """
    Context manager for database sessions with automatic commit/rollback.

    Usage:
        with DatabaseSession() as session:
            session.add(obj)
            # Automatically commits on success, rolls back on exception
    """

    def __enter__(self) -> Session:
        self.session = get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
