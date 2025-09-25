from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum,
    Index, Table, UniqueConstraint, JSON, Float
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

# Base registry for all models
Base = declarative_base()

# ============================================================
# Enums
# ============================================================

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

class AnnotationJobStatus(enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"
    reviewed = "reviewed"

class ReviewStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

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

class AssignmentRole(enum.Enum):
    annotator = "annotator"
    reviewer = "reviewer"
    qc = "qc"

class Language(enum.Enum):
    en = "en"
    zh = "zh"
    fr = "fr"
    de = "de"
    es = "es"
    ar = "ar"

class JobPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

# ============================================================
# Association Tables
# ============================================================

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.role_id", ondelete="CASCADE"), primary_key=True)
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("role.role_id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permission.permission_id", ondelete="CASCADE"), primary_key=True)
)

job_previous_annotators = Table(
    "job_previous_annotators",
    Base.metadata,
    Column("job_id", Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=func.now())
)

# ============================================================
# Core Tables
# ============================================================

class Project(Base):
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

    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    client_pm_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    our_pm_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)

    files = relationship("File", back_populates="project")
    requirement_files = relationship(
        "File",
        primaryjoin="and_(Project.project_id==File.project_id, File.file_type=='requirement')",
        viewonly=True
    )
    jobs = relationship("AnnotationJob", back_populates="project")
    events = relationship("EventLog", back_populates="project")
    organization = relationship("Organization", back_populates="projects")
    client_pm = relationship("User", foreign_keys=[client_pm_id], back_populates="client_projects")
    our_pm = relationship("User", foreign_keys=[our_pm_id], back_populates="managed_projects")
    exports = relationship("ExportLog", back_populates="project")


class File(Base):
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

    status = Column(Enum(FileStatus, name="file_status_enum"), default=FileStatus.pending, nullable=False)
    file_type = Column(Enum(FileType, name="file_type_enum"), default=FileType.dataset, nullable=False)

    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)

    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)
    active_version_id = Column(Integer, ForeignKey("file_version.version_id"), nullable=True)

    uploader = relationship("User", back_populates="uploaded_files")
    project = relationship("Project", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")
    annotation_jobs = relationship("AnnotationJob", back_populates="file")
    events = relationship("EventLog", back_populates="file")
    active_version = relationship("FileVersion", foreign_keys=[active_version_id], uselist=False)


class FileVersion(Base):
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

    generation_method = Column(
        Enum("upload", "ocr", "llm", name="generation_method_enum"),
        default="upload",
        nullable=False
    )
    llm_model = Column(String, nullable=True)
    llm_params = Column(JSON, nullable=True)

    file = relationship("File", back_populates="versions")
    source_version = relationship("FileVersion", remote_side=[version_id])
    events = relationship("EventLog", back_populates="file_version")
    exports = relationship("ExportLog", secondary="exported_file", back_populates="file_versions")
    exported_files = relationship("ExportedFile", back_populates="file_version", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)

    org_id = Column(Integer, ForeignKey("organization.org_id", ondelete="SET NULL"), nullable=True)

    availability = Column(JSON, nullable=True)
    language_expertise = Column(JSON, nullable=True)
    skill_score = Column(Float, nullable=True)
    skill_level = Column(String, nullable=True)
    qa_approval_rate = Column(Float, nullable=True)
    completed_task_count = Column(Integer, default=0)

    uploaded_files = relationship("File", back_populates="uploader")
    events = relationship("EventLog", back_populates="user")
    assignments = relationship("Assignment", back_populates="user", cascade="all, delete-orphan")

    is_active = Column(Boolean, default=True, nullable=False)
    roles = relationship("Role", secondary=user_roles, back_populates="users")

    client_projects = relationship("Project", back_populates="client_pm")
    managed_projects = relationship("Project", back_populates="our_pm")

    previous_jobs = relationship(
        "AnnotationJob",
        secondary="job_previous_annotators",
        back_populates="previous_annotators"
    )

    reviews = relationship("Review", back_populates="reviewer")


class AnnotationJob(Base):
    __tablename__ = "annotation_job"
    __table_args__ = {"extend_existing": True}

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)

    language = Column(Enum(Language, name="annotation_job_language_enum"), nullable=True)
    priority = Column(Enum(JobPriority, name="job_priority_enum"), default=JobPriority.medium, nullable=False)

    status = Column(Enum(AnnotationJobStatus, name="annotation_job_status_enum"),
                    default=AnnotationJobStatus.not_started, nullable=False)
    review_status = Column(Enum(ReviewStatus, name="review_status_enum"),
                           default=ReviewStatus.pending, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    file = relationship("File", back_populates="annotation_jobs")
    project = relationship("Project", back_populates="jobs")

    reviews = relationship("Review", back_populates="job", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="job", cascade="all, delete-orphan")

    previous_annotators = relationship(
        "User",
        secondary="job_previous_annotators",
        back_populates="previous_jobs"
    )


class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("ix_eventlog_entity", "entity_type", "entity_id"),
        {"extend_existing": True},
    )

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(Enum(EntityType, name="entity_type_enum"), nullable=False)
    entity_id = Column(Integer, nullable=False)
    event_type = Column(Enum(EventType, name="event_type_enum"), nullable=False)

    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", back_populates="events")

    event_metadata = Column(JSONB, nullable=True)
    event_time = Column(DateTime, default=func.now(), nullable=False)

    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="SET NULL"), nullable=True)
    file_version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="SET NULL"), nullable=True)
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="SET NULL"), nullable=True)
    export_id = Column(Integer, ForeignKey("export_log.export_id", ondelete="SET NULL"), nullable=True)
    review_id = Column(Integer, ForeignKey("review.review_id", ondelete="CASCADE"), nullable=True)

    project = relationship("Project", back_populates="events")
    file = relationship("File", back_populates="events")
    file_version = relationship("FileVersion", back_populates="events")
    job = relationship("AnnotationJob", back_populates="events")
    export = relationship("ExportLog", back_populates="events")
    review = relationship("Review", back_populates="events")


class Review(Base):
    __tablename__ = "review"
    __table_args__ = (
        Index("ix_review_job_id", "job_id"),
        Index("ix_review_status", "status"),
        {"extend_existing": True},
    )

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)

    status = Column(Enum(ReviewStatus, name="review_status_enum"), default=ReviewStatus.pending, nullable=False)
    feedback = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    job = relationship("AnnotationJob", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
    events = relationship("EventLog", back_populates="review")


class Assignment(Base):
    __tablename__ = "assignment"
    __table_args__ = (
        Index("ix_assignment_job_id", "job_id"),
        Index("ix_assignment_user_id", "user_id"),
        Index("ix_assignment_role", "role"),
        {"extend_existing": True},
    )

    assignment_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)

    role = Column(Enum(AssignmentRole, name="assignment_role_enum"), nullable=False)
    status = Column(
        Enum("assigned", "accepted", "in_progress", "submitted", "completed",
             name="assignment_status_enum"),
        default="assigned",
        nullable=False
    )

    is_active = Column(Boolean, default=True, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    job = relationship("AnnotationJob", back_populates="assignments")
    user = relationship("User", back_populates="assignments")

    reviews = relationship("Review", secondary="annotation_job", viewonly=True)


class Role(Base):
    __tablename__ = "role"
    __table_args__ = {"extend_existing": True}

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = {"extend_existing": True}

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = (
        Index("ix_org_name", "name"),
        {"extend_existing": True},
    )

    org_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("User", back_populates="organization", passive_deletes=True)
    projects = relationship("Project", back_populates="organization", passive_deletes=True)

    files = relationship(
        "File",
        secondary="project",
        viewonly=True,
        primaryjoin="Organization.org_id==Project.org_id",
        secondaryjoin="Project.project_id==File.project_id",
    )

    events = relationship(
        "EventLog",
        primaryjoin="Organization.org_id==Project.org_id",
        secondary="project",
        viewonly=True,
    )


class ExportedFile(Base):
    __tablename__ = "exported_file"
    __table_args__ = {"extend_existing": True}

    export_id = Column(Integer, ForeignKey("export_log.export_id", ondelete="CASCADE"), primary_key=True)
    file_version_id = Column(Integer, ForeignKey("file_version.version_id", ondelete="CASCADE"), primary_key=True)
    included_at = Column(DateTime, default=func.now())

    export = relationship("ExportLog", back_populates="exported_files")
    file_version = relationship("FileVersion", back_populates="exported_files")


class ExportLog(Base):
    __tablename__ = "export_log"

    export_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("user.user_id"), nullable=False)

    storage_path = Column(String, nullable=False)
    checksum = Column(String, nullable=True)

    status = Column(Enum("pending", "completed", "failed", name="export_status_enum"), default="pending")

    date_requested = Column(DateTime, default=func.now(), nullable=False)
    date_completed = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="exports")
    requested_user = relationship("User", foreign_keys=[requested_by])
    file_versions = relationship("FileVersion", secondary="exported_file", back_populates="exports")
    exported_files = relationship("ExportedFile", back_populates="export", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="export")
