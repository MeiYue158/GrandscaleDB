from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, Index, Table, UniqueConstraint, JSON, Float, event, inspect
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .mixins import TimestampMixin
from .base import Base
import enum

# ---------- Enums ----------
class ProjectStatus(enum.Enum):
    draft = "draft"
    ready_for_annotation = "ready_for_annotation"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"

class FileStatus(enum.Enum):
    pending = "pending"
    ready_for_annotation = "ready_for_annotation"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"

class FileType(enum.Enum):
    dataset = "dataset"
    requirement = "requirement"
    report = "annotation_results"
    llm_output = "llm_output"

# ---------- Core Tables ----------
# Project Table
class Project(Base, TimestampMixin):
    __tablename__ = "project"
    __table_args__ = (
    UniqueConstraint("org_id", "name", name="uq_org_project_name"), # no two projects can share same name in one comp
    Index("ix_project_status", "status"), # speeds up dashboards like “show me all in-progress projects”.
    Index("ix_project_is_active", "is_active"), # speeds up “only show active projects”.
    Index("ix_project_client_pm_id", "client_pm_id"), # useful if query “all projects started by this PM”.
    Index("ix_project_org_id", "org_id"), # useful if query “all projects for this org”.
    {"extend_existing": True} # delete
    )

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organization.org_id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True) # longer desp than name

    # plain text instructions
    requirements_text = Column(Text, nullable=True)
    # optional uploaded doc (PDF, Word, PPT, etc.)
    # requirements_file_id = Column(Integer, ForeignKey("file.file_id"), nullable=True)

    # project status enum
    status = Column(Enum(ProjectStatus, name="project_status_enum"), default=ProjectStatus.draft)
    
    is_active = Column(Boolean, default=True, nullable=False)

    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True) # when customer delete the project

    # --- PM links ---
    client_pm_id = Column(Integer, ForeignKey("user.user_id"), nullable=False) # client PM
    our_pm_id = Column(Integer, ForeignKey("user.user_id"), nullable=True) # our PM

    # --- Relationships ---
    files = relationship("File", back_populates="project")             # all files
    # convenience: only requirement files
    requirement_files = relationship(
        "File",
        primaryjoin="and_(Project.project_id==File.project_id, File.file_type=='requirement')",
        viewonly=True
    ) # only get files that accords with reqs
    jobs = relationship("AnnotationJob", back_populates="project")     # all jobs
    events = relationship("EventLog", back_populates="project")        # all events
    organization = relationship("Organization", back_populates="projects")
    client_pm = relationship("User", foreign_keys=[client_pm_id], back_populates="client_projects")
    our_pm = relationship("User", foreign_keys=[our_pm_id], back_populates="managed_projects")
    exports = relationship("ExportLog", back_populates="project")

class File(Base, TimestampMixin):
    __tablename__ = "file"
    __table_args__ = (
    UniqueConstraint("project_id", "name", name="uq_project_file_name"),
    Index("ix_file_project_id", "project_id"), # speeds up “all files in project.”
    Index("ix_file_status", "status"), # speeds up “all files ready for annotation.”
    Index("ix_file_type", "file_type"), # speeds up filtering datasets vs. requirements.
    {"extend_existing": True},
)


    file_id = Column(Integer, primary_key=True, autoincrement=True)
    # descriptive file name (user-facing)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("user.user_id"), nullable=False)


    # workflow state
    status = Column(
        Enum(FileStatus, name="file_status_enum"),
        default=FileStatus.pending,
        nullable=False
    )
    # what kind of file this is (dataset, requirement, annotation_results, llm_nl)
    file_type = Column(Enum(FileType, name="file_type_enum"), nullable=False, default=FileType.dataset)

    # audit timestamps
    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # validate uploads by storage
    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True) # technical format

    
    # --- PM links ---
    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)
    # active version pointer
    active_version_id = Column(Integer, ForeignKey("file_version.version_id"), nullable=True)


    # --- Relationships ---
    uploader = relationship("User", back_populates="uploaded_files")
    project = relationship("Project", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")
    annotation_jobs = relationship("AnnotationJob", back_populates="file") 
    events = relationship("EventLog", back_populates="file")
    active_version = relationship("FileVersion", foreign_keys=[active_version_id], uselist=False)

class FileVersion(Base, TimestampMixin):
    __tablename__ = "file_version"
    __table_args__ = (
        Index("ix_fileversion_file_id", "file_id"),
        {"extend_existing": True},
    )

    version_id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Parent link ---
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)  # 1, 2, 3…

    # --- Storage info ---
    storage_path = Column(String, nullable=False)   # MinIO/S3 key or path
    checksum = Column(String, nullable=True)        # for integrity validation
    size_bytes = Column(Integer, nullable=True)     # optional: store size at version-level
    mime_type = Column(String, nullable=True)       # optional: file format at version-level

    # --- Upload & provenance ---
    uploaded_by = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # --- Lifecycle flags ---
    is_active = Column(Boolean, default=True, nullable=False)

    source_file_version_id = Column(Integer, ForeignKey("file_version.version_id"), nullable=True)
    generation_method = Column(
        Enum("upload", "ocr", "llm", name="generation_method_enum"),
        default="upload",
        nullable=False
    )
    llm_model = Column(String, nullable=True)       # e.g., "gpt-4", "llama-3"
    llm_params = Column(JSON, nullable=True)        # parameters if generated by LLM


    # --- Relationships ---
    file = relationship("File", back_populates="versions")
    source_version = relationship("FileVersion", remote_side=[version_id])  # self-ref
    events = relationship("EventLog", back_populates="file_version")        # version-level logs
    exports = relationship(
    "ExportLog",
    secondary="exported_file",
    back_populates="file_versions"
    )


    # export_id = Column(Integer, ForeignKey("export_log.export_id"), nullable=True)
    exported_files = relationship(
        "ExportedFile",
        back_populates="file_version",
        cascade="all, delete-orphan"
    )

