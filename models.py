from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, Index, Table
)
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from dotenv import load_dotenv
import os
import enum

# create base class
Base = declarative_base() 

# --------------------------
# Enums
# --------------------------

## 1.1 ProjectStatus
class ProjectStatus(enum.Enum):
    draft = "draft"                  # project created, requirements being defined
    ready_for_annotation = "ready_for_annotation"  # files uploaded, jobs not started
    in_progress = "in_progress"      # annotation jobs are running
    completed = "completed"          # all jobs done
    archived = "archived"            # project closed, read-only

## 1.2 FileStatus (file lifecycle)
class FileStatus(enum.Enum):
    pending = "pending"
    ready_for_annotation = "ready_for_annotation"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"

## 1.3 FileType
class FileType(enum.Enum):
    dataset = "dataset"
    requirement = "requirement"
    report = "annotation_results"
# Does our PM also needs to upload sliced file results? (NO currently)

## 1.4 UserRole
class UserRole(enum.Enum):
    org_admin = "org_admin"       # customer admin
    org_pm = "org_pm"             # customer project manager
    our_pm = "our_pm"             # our company PM that manages annotation jobs & assigns annotators
    annotator = "annotator"       # our company annotator
    qc = "qc"                     # our company QC for annotation results review

## 1.5 AnnotationJobStatus (job lifecycle)
class AnnotationJobStatus(enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"
    reviewed = "reviewed"

## 1.6 ReviewStatus
class ReviewStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

## 1.7 EntityType
class EntityType(enum.Enum):
    project = "project"
    file = "file"
    file_version = "file_version"
    annotation_job = "annotation_job"

## 1.8 EventType
class EventType(enum.Enum):
    uploaded = "uploaded"
    reuploaded = "reuploaded"
    annotation_started = "annotation_started"
    annotation_completed = "annotation_completed"
    reviewed = "reviewed"
    deleted = "deleted"
    status_changed = "status_changed"

## 1.9 AssignmentRole
class AssignmentRole(enum.Enum):
    annotator = "annotator"
    reviewer = "reviewer"
    qc = "qc"   # quality control / audit

# --------------------------
# Association Tables
# --------------------------

# 2.1 User <-> Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.role_id", ondelete="CASCADE"), primary_key=True)
)

# 2.2 Role <-> Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("role.role_id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permission.permission_id", ondelete="CASCADE"), primary_key=True)
)

# -----------------------------
# Core Tables
# -----------------------------
    
# Project Table
class Project(Base):
    __tablename__ = "project"
    __table_args__ = {"extend_existing": True}

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organization.org_id"), nullable=False)
    name = Column(String, nullable=False)

    # plain text instructions
    requirements_text = Column(Text, nullable=True)
    # optional uploaded doc (PDF, Word, PPT, etc.)
    requirements_file_id = Column(Integer, ForeignKey("file.file_id"), nullable=True)

    # project status enum
    status = Column(Enum(ProjectStatus, name="project_status_enum"), default=ProjectStatus.draft)

    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    files = relationship("File", back_populates="project")
    organization = relationship("Organization", back_populates="projects")
    requirement_files = relationship(
    "File",
    primaryjoin="and_(Project.project_id==File.project_id, File.file_type=='requirement')",
    viewonly=True) # only get files that are requirements

# --------------------------
# File Table
# --------------------------
class File(Base):
    __tablename__ = "file"
    __table_args__ = {"extend_existing": True}

    file_id = Column(Integer, primary_key=True, autoincrement=True)

    # belongs to a project
    project_id = Column(Integer, ForeignKey("project.project_id"), nullable=False)

    # descriptive file name (user-facing)
    name = Column(String, nullable=False)

    # what kind of file this is (dataset, requirement, annotation_results)
    file_type = Column(Enum(FileType, name="file_type_enum"), nullable=False, default=FileType.dataset)

    # workflow state
    status = Column(
        Enum(FileStatus, name="file_status_enum"),
        default=FileStatus.pending,
        nullable=False
    )

    # active version pointer
    active_version_id = Column(Integer, ForeignKey("file_version.version_id"), nullable=True)

    # audit timestamps
    date_created = Column(DateTime, default=func.now(), nullable=False)
    date_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # --------------------------
    # Relationships
    # --------------------------
    project = relationship("Project", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")
    annotation_jobs = relationship("AnnotationJob", back_populates="file")

# File Version Table
class FileVersion(Base):
    __tablename__ = "file_version"
    __table_args__ = (
        Index("idx_fileversion_file_id", "file_id"),
        {"extend_existing": True},
    )

    version_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    s3_key = Column(String, nullable=False)  # MinIO/S3 object key
    uploaded_by = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    file = relationship("File", back_populates="versions")

class User(Base):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}


    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    role = Column(Enum(UserRole, name="user_role_enum"), nullable=False)
    org_id = Column(Integer, ForeignKey("organization.org_id"), nullable=True)  
    # org_id is only relevant for client users (admins, PMs)

    # Keep only one real relationship: User & EventLog
    events = relationship("EventLog", back_populates="user")
    assignments = relationship("Assignment", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("Role", secondary=user_roles, back_populates="users")

# Annotation Job Table
class AnnotationJob(Base):
    __tablename__ = "annotation_job"
    __table_args__ = {"extend_existing": True}

    job_id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("user.user_id"), nullable=True)  # annotator
    reviewed_by = Column(Integer, ForeignKey("user.user_id"), nullable=True)  # reviewer

    # Workflow
    status = Column(
    Enum(AnnotationJobStatus, name="annotation_job_status_enum"),
    default=AnnotationJobStatus.not_started,
    nullable=False
    )
    
    # Review
    review_status = Column(
    Enum(ReviewStatus, name="review_status_enum"),
    default=ReviewStatus.pending,
    nullable=False
    )

    # Audit
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # ORM relationships
    file = relationship("File", back_populates="annotation_jobs")
    project = relationship("Project", back_populates="annotation_jobs")
    annotator = relationship("User", foreign_keys=[assigned_to])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    reviews = relationship("Review", back_populates="job", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="job", cascade="all, delete-orphan")

# Event Log Table
class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = {"extend_existing": True}

    event_id = Column(Integer, primary_key=True, autoincrement=True)

    entity_type = Column(Enum(EntityType, name="entity_type_enum"), nullable=False)
    entity_id = Column(Integer, nullable=False)      # e.g. file_id

    event_type = Column(Enum(EventType, name="event_type_enum"), nullable=False)

    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    event_time = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="events")

    event_metadata = Column(JSONB, nullable=True)  # use JSONB for flexible key/value storage

# --------------------------
# Review Table
# --------------------------
class Review(Base):
    __tablename__ = "review"
    __table_args__ = {"extend_existing": True}

    review_id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to the job being reviewed
    job_id = Column(Integer, ForeignKey("annotation_job.job_id"), nullable=False)

    # Reviewer (user with reviewer role)
    reviewer_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)

    # Review decision
    status = Column(
        Enum(ReviewStatus, name="review_status_enum"),
        default=ReviewStatus.pending,
        nullable=False
    )

    # Optional comments from reviewer
    feedback = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # --------------------------
    # Relationships
    # --------------------------
    job = relationship("AnnotationJob", back_populates="reviews")
    reviewer = relationship("User")

# --------------------------
# Assignment Table
# --------------------------
class Assignment(Base):
    __tablename__ = "assignment"
    __table_args__ = {"extend_existing": True}

    assignment_id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to the annotation job
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), nullable=False)

    # Who is assigned
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False)

    # Role in this job (annotator, reviewer, qc)
    role = Column(Enum(AssignmentRole, name="assignment_role_enum"), nullable=False)

    # Status of this assignment (separate from job status)
    status = Column(String, default="assigned")  
    # e.g. assigned, accepted, in_progress, completed

    # Audit fields
    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    job = relationship("AnnotationJob", back_populates="assignments")
    user = relationship("User", back_populates="assignments")

# --------------------------
# Role Table
# --------------------------
class Role(Base):
    __tablename__ = "role"
    __table_args__ = {"extend_existing": True}

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)   # e.g. "organization_admin", "pm", "annotator", "reviewer"

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

# --------------------------
# Permission Table
# --------------------------
class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = {"extend_existing": True}

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)   # e.g. "upload_file", "assign_job", "review_annotation"

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")   