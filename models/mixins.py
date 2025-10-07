# models/mixins.py
"""
Reusable mixins for SQLAlchemy models.

Currently includes:
- TimestampMixin: adds created_at / updated_at fields with auto-update.
- SoftDeleteMixin (optional): provides is_active / deleted_at pattern.
"""

from sqlalchemy import Column, DateTime, Boolean
from sqlalchemy.sql import func


class TimestampMixin:
    """
    Adds automatic created_at and updated_at columns to a model.

    - created_at is set when the record is inserted.
    - updated_at automatically updates whenever the record changes.
    """

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """
    Adds soft-deletion support.

    - is_active controls whether the record is logically “deleted”.
    - deleted_at stores timestamp of deletion.
    """

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
