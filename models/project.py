# models/project.py
"""
Project-related models:
- Project: top-level container for client projects.
- File: uploaded data or requirement files.
- FileVersion: versioned files (uploads, OCR, LLM outputs).
- FileTable: tables extracted from files (LLM parsed tables).
- ExportLog / ExportedFile: export tracking.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Enum, JSON, Index, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin
from .enums import (
    ProjectStatus,
    FileStatus,
    FileType,
)
# Note: we don’t import AnnotationJob here to avoid circular import.
# It will import this file through __init__.py automatically.


# --------------------------------------------------
# Project Table
# --------------------------------------------------
class Project(Base, TimestampMixin):
    __tablename__ = "project"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_org_project_name"),
        Index("ix_project_status", "status"),
        Index("ix_project_is_active", "is_active"),
        Index("ix_project_client_pm_id", "client_pm_id"),
        Index("ix_project_org_id", "org_id"),
        {"extend_existing": True},
    )

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organization.org_id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    requirements_text = Column(Text, nullable=True)

    status = Column(Enum(ProjectStatus, name="project_status_enum"), default=ProjectStatus.draft)
    is_active = Column(Boolean, default=True, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # PM links
    client_pm_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    our_pm_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)

    # --- Relationships ---
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("AnnotationJob", back_populates="project")  # defined in annotation.py
    events = relationship("EventLog", back_populates="project")      # defined in event.py
    organization = relationship("Organization", back_populates="projects")
    client_pm = relationship("User", foreign_keys=[client_pm_id], back_populates="client_projects")
    our_pm = relationship("User", foreign_keys=[our_pm_id], back_populates="managed_projects")
    exports = relationship("ExportLog", back_populates="project", cascade="all, delete-orphan")


# --------------------------------------------------
# File Table
# --------------------------------------------------
class File(Base, TimestampMixin):
    __tablename__ = "file"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_file_name"),
        Index("ix_file_project_id", "project_id"),
        Index("ix_file_status", "status"),
        Index("ix_file_type", "file_type"),
        {"extend_existing": True},
    )

    file_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)
    active_version_id = Column(Integer, ForeignKey("file_version.version_id"), nullable=True)

    status = Column(Enum(FileStatus, name="file_status_enum"), default=FileStatus.pending, nullable=False)
    file_type = Column(Enum(FileType, name="file_type_enum"), nullable=False, default=FileType.dataset)

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)

    # --- Relationships ---
    uploader = relationship("User", back_populates="uploaded_files")
    project = relationship("Project", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="file")
    active_version = relationship("FileVersion", foreign_keys=[active_version_id], uselist=False)
    tables = relationship("FileTable", back_populates="file", cascade="all, delete-orphan")


# --------------------------------------------------
# File Version Table
# --------------------------------------------------
class FileVersion(Base, TimestampMixin):
    __tablename__ = "file_version"
    __table_args__ = (
        Index("ix_fileversion_file_id", "file_id"),
        {"extend_existing": True},
    )

    version_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)

    storage_path = Column(String, nullable=False)
    checksum = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)

    uploaded_by = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    source_file_version_id = Column(Integer, ForeignKey("file_version.version_id"), nullable=True)
    generation_method = Column(Enum("upload", "ocr", "llm", name="generation_method_enum"), default="upload", nullable=False)
    llm_model = Column(String, nullable=True)
    llm_params = Column(JSON, nullable=True)

    # --- Relationships ---
    file = relationship("File", back_populates="versions")
    source_version = relationship("FileVersion", remote_side=[version_id])
    events = relationship("EventLog", back_populates="file_version")
    exports = relationship("ExportLog", secondary="exported_file", back_populates="file_versions")
    exported_files = relationship("ExportedFile", back_populates="file_version", cascade="all, delete-orphan")
    tables = relationship("FileTable", back_populates="version", cascade="all, delete-orphan")


# --------------------------------------------------
# File Table (LLM-extracted)
# --------------------------------------------------
class FileTable(Base, TimestampMixin):
    __tablename__ = "file_table"
    __table_args__ = (
        Index("ix_table_file_id", "file_id"),
        Index("ix_table_status", "status"),
        {"extend_existing": True},
    )

    table_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="SET NULL"), nullable=True)

    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    schema_json = Column(JSONB, nullable=True)
    extracted_narrative = Column(Text, nullable=True)

    status = Column(Enum(FileStatus, name="filetable_status_enum"), default=FileStatus.pending, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # --- Relationships ---
    file = relationship("File", back_populates="tables")
    version = relationship("FileVersion", back_populates="tables", foreign_keys=[version_id])
    jobs = relationship("AnnotationJob", back_populates="table", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="table", cascade="all, delete-orphan")


# --------------------------------------------------
# Export Tracking
# --------------------------------------------------
class ExportLog(Base, TimestampMixin):
    __tablename__ = "export_log"
    __table_args__ = {"extend_existing": True}

    export_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("user.user_id"), nullable=False)

    storage_path = Column(String, nullable=False)
    checksum = Column(String, nullable=True)
    status = Column(Enum("pending", "completed", "failed", name="export_status_enum"), default="pending")

    date_requested = Column(DateTime, default=func.now(), nullable=False)
    date_completed = Column(DateTime, nullable=True)

    # --- Relationships ---
    project = relationship("Project", back_populates="exports")
    requested_user = relationship("User", foreign_keys=[requested_by])
    file_versions = relationship("FileVersion", secondary="exported_file", back_populates="exports")
    exported_files = relationship("ExportedFile", back_populates="export", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="export", cascade="all, delete-orphan")


class ExportedFile(Base):
    __tablename__ = "exported_file"
    __table_args__ = {"extend_existing": True}

    export_id = Column(Integer, ForeignKey("export_log.export_id", ondelete="CASCADE"), primary_key=True)
    file_version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="CASCADE"), primary_key=True)
    included_at = Column(DateTime, default=func.now())

    # --- Relationships ---
    export = relationship("ExportLog", back_populates="exported_files")
    file_version = relationship("FileVersion", back_populates="exported_files")

