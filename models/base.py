# models/base.py
"""
Defines SQLAlchemy Base, engine, and session factory.
This is the shared foundation for all ORM models.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# ------------------------------------------------------
# Load environment variables
# ------------------------------------------------------
load_dotenv()

# Database URL (PostgreSQL recommended)
DATABASE_URL = os.getenv("DATABASE_URL")

# Example:
# DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/mydb"

# ------------------------------------------------------
# Base class for all models
# ------------------------------------------------------
Base = declarative_base()

# ------------------------------------------------------
# Engine & Session Setup
# ------------------------------------------------------
# Lazy engine creation — will raise error if DATABASE_URL not set
engine = None
SessionLocal = None


def init_engine(echo: bool = False, future: bool = True):
    """
    Initialize SQLAlchemy engine and session factory.
    Safe to call multiple times — idempotent.
    """
    global engine, SessionLocal
    if engine is None:
        if not DATABASE_URL:
            raise ValueError("❌ DATABASE_URL not set in environment (.env)")
        engine = create_engine(DATABASE_URL, echo=echo, future=future)
        SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
        print(f"✅ Connected to database: {DATABASE_URL.split('@')[-1]}")
    return engine


def get_session():
    """
    Returns a new SQLAlchemy session.
    Usage:
        with get_session() as db:
            db.query(Project).all()
    """
    global SessionLocal
    if SessionLocal is None:
        init_engine()
    return SessionLocal()


def create_all_tables():
    """
    Create all tables in the database based on model metadata.
    Safe to call once after all models are imported.
    """
    global engine
    if engine is None:
        init_engine()
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully.")


def drop_all_tables(confirm: bool = False):
    """
    Drop all tables — use carefully.
    """
    global engine
    if engine is None:
        init_engine()
    if confirm:
        Base.metadata.drop_all(bind=engine)
        print("⚠️ All tables dropped.")
