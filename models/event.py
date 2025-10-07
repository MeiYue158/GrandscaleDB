# models/event.py
"""
Event and Audit Tracking Models:
- EventLog: records every change or action across entities (project, file, job, review, etc.)
"""

from sqlalchemy import (
    Column, Integer, DateTime, ForeignKey, Enum, JSON, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin
from .enums import EntityType, EventType


# --------------------------------------------------
# Event Log Table
# --------------------------------------------------
class EventLog(Base, TimestampMixin):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("ix_eventlog_entity", "entity_type", "entity_id"),  # speeds up “get events for this entity”
        {"extend_existing": True},
    )

    event_id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Generic pointers ---
    entity_type = Column(Enum(EntityType, name="entity_type_enum"), nullable=False)
    entity_id = Column(Integer, nullable=False)  # e.g. file_id, project_id, etc.
    event_type = Column(Enum(EventType, name="event_type_enum"), nullable=False)

    # --- Who triggered it ---
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", back_populates="events")

    # --- Optional contextual links (for direct joins) ---
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="SET NULL"), nullable=True)
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="SET NULL"), nullable=True)
    file_version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="SET NULL"), nullable=True)
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="SET NULL"), nullable=True)
    review_id = Column(Integer, ForeignKey("review.review_id", ondelete="CASCADE"), nullable=True)
    export_id = Column(Integer, ForeignKey("export_log.export_id", ondelete="SET NULL"), nullable=True)
    table_id = Column(Integer, ForeignKey("file_table.table_id", ondelete="SET NULL"), nullable=True)

    # --- Metadata and audit ---
    event_metadata = Column(JSONB, nullable=True)  # e.g. {"old_status": "pending", "new_status": "in_progress"}
    event_time = Column(DateTime, default=func.now(), nullable=False)

    # --- Relationships (linked to almost everything) ---
    project = relationship("Project", back_populates="events")
    file = relationship("File", back_populates="events")
    file_version = relationship("FileVersion", back_populates="events")
    job = relationship("AnnotationJob", back_populates="events")
    review = relationship("Review", back_populates="events")
    export = relationship("ExportLog", back_populates="events")
    table = relationship("FileTable", back_populates="events")
