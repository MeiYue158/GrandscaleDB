from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Index
)
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, ForeignKey,
    Index, Table            # ✅ Table is needed
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ JSONB is used in EventLog

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .mixins import TimestampMixin
from .base import Base
import enum

class EntityType(enum.Enum):
    project = "project"
    file = "file"
    file_version = "file_version"
    annotation_job = "annotation_job"

class EventType(enum.Enum):
    uploaded = "uploaded"
    reuploaded = "reuploaded"
    annotation_started = "annotation_started"
    annotation_completed = "annotation_completed"
    reviewed = "reviewed"
    deleted = "deleted"
    status_changed = "status_changed"

class ExportedFile(Base):
    __tablename__ = "exported_file"
    __table_args__ = {"extend_existing": True}

    export_id = Column(Integer, ForeignKey("export_log.export_id", ondelete="CASCADE"), primary_key=True)
    file_version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="CASCADE"), primary_key=True)
    included_at = Column(DateTime, default=func.now())

    # Relationships
    export = relationship("ExportLog", back_populates="exported_files")
    file_version = relationship("FileVersion", back_populates="exported_files")

# This table records which annotators have worked on this job before 
# (for feedback loops / reassignment tracking)
job_previous_annotators = Table(
    "job_previous_annotators",
    Base.metadata,
    Column("job_id", Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=func.now()),
    extend_existing=True  
)

class ExportLog(Base, TimestampMixin):
    __tablename__ = "export_log"

    export_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("user.user_id"), nullable=False)

    # Where the final package (ZIP, PDF, TAR, etc.) lives in S3/MinIO
    storage_path = Column(String, nullable=False)

    # Optional metadata
    checksum = Column(String, nullable=True)
    #included_file_ids = Column(JSON, nullable=True)  # list of files packaged
    #included_versions = Column(JSON, nullable=True)  # if version-level tracking matters

    status = Column(Enum("pending", "completed", "failed", name="export_status_enum"), default="pending")

    date_requested = Column(DateTime, default=func.now(), nullable=False)
    date_completed = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="exports")
    requested_user = relationship("User", foreign_keys=[requested_by])
    file_versions = relationship(
    "FileVersion",
    secondary="exported_file",    # uses the join table
    back_populates="exports"
    )
    exported_files = relationship(
        "ExportedFile",
        back_populates="export",
        cascade="all, delete-orphan"
    ) # Keep cascade — join table cleanup make sense here.

class EventLog(Base, TimestampMixin):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("ix_eventlog_entity", "entity_type", "entity_id"),  # speeds up "get events for this entity"
        {"extend_existing": True},
    )

    event_id = Column(Integer, primary_key=True, autoincrement=True)

    # Generic entity pointer
    entity_type = Column(Enum(EntityType, name="entity_type_enum"), nullable=False)
    entity_id = Column(Integer, nullable=False)  # e.g. file_id, project_id, etc.

    # Event classification
    event_type = Column(Enum(EventType, name="event_type_enum"), nullable=False)

    # Who triggered the event
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", back_populates="events")

    # Flexible metadata
    event_metadata = Column(JSONB, nullable=True)  # {"old_status": "pending", "new_status": "in_progress"}

    # Audit
    event_time = Column(DateTime, default=func.now(), nullable=False)

    # Optional direct links for efficient joins
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="SET NULL"), nullable=True)
    file_version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="SET NULL"), nullable=True)
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="SET NULL"), nullable=True)
    export_id = Column(Integer, ForeignKey("export_log.export_id", ondelete="SET NULL"), nullable=True)
    review_id = Column(
    Integer,
    ForeignKey("review.review_id", ondelete="CASCADE"),
    nullable=True
    )

    # Relationships
    project = relationship("Project", back_populates="events")
    file = relationship("File", back_populates="events")
    file_version = relationship("FileVersion", back_populates="events")
    job = relationship("AnnotationJob", back_populates="events")
    export = relationship("ExportLog", back_populates="events")
    review = relationship("Review", back_populates="events")
