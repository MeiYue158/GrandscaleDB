# models/annotation.py
"""
Annotation-related models:
- AnnotationJob: core annotation task for each file/table.
- Assignment: links users to jobs with specific roles.
- Review: stores reviewer feedback and approval status.
- Role / Permission: defines RBAC (role-based access control).
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Enum, Index, func
)
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import TimestampMixin
from .enums import (
    AnnotationJobStatus,
    ReviewStatus,
    AssignmentRole,
    Language,
    JobPriority
)

# --------------------------------------------------
# Annotation Job Table
# --------------------------------------------------
class AnnotationJob(Base, TimestampMixin):
    __tablename__ = "annotation_job"
    __table_args__ = {"extend_existing": True}

    job_id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign keys ---
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    table_id = Column(Integer, ForeignKey("file_table.table_id", ondelete="CASCADE"), nullable=False)

    # --- Job attributes ---
    language = Column(Enum(Language, name="annotation_job_language_enum"), nullable=True)
    priority = Column(Enum(JobPriority, name="job_priority_enum"), default=JobPriority.medium, nullable=False)
    status = Column(Enum(AnnotationJobStatus, name="annotation_job_status_enum"),
                    default=AnnotationJobStatus.not_started, nullable=False)
    review_status = Column(Enum(ReviewStatus, name="review_status_enum"),
                           default=ReviewStatus.pending, nullable=False)

    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # --- Relationships ---
    project = relationship("Project", back_populates="jobs")
    table = relationship("FileTable", back_populates="jobs")
    assignments = relationship("Assignment", back_populates="job", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="job", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="job", cascade="all, delete-orphan")

    previous_annotators = relationship(
        "User",
        secondary="job_previous_annotators",
        back_populates="previous_jobs"
    )


# --------------------------------------------------
# Assignment Table
# --------------------------------------------------
class Assignment(Base, TimestampMixin):
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

    # --- Relationships ---
    job = relationship("AnnotationJob", back_populates="assignments")
    user = relationship("User", back_populates="assignments")


# --------------------------------------------------
# Review Table
# --------------------------------------------------
class Review(Base, TimestampMixin):
    __tablename__ = "review"
    __table_args__ = (
        Index("ix_review_job_id", "job_id"),
        Index("ix_review_status", "status"),
        {"extend_existing": True},
    )

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)

    status = Column(Enum(ReviewStatus, name="review_table_status_enum"),
                    default=ReviewStatus.pending, nullable=False)
    feedback = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # --- Relationships ---
    job = relationship("AnnotationJob", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
    events = relationship("EventLog", back_populates="review", cascade="all, delete-orphan")


# --------------------------------------------------
# Role Table
# --------------------------------------------------
class Role(Base, TimestampMixin):
    __tablename__ = "role"
    __table_args__ = {"extend_existing": True}

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)   # e.g. "annotator", "qc", "pm"
    description = Column(Text, nullable=True)

    # --- Relationships ---
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")


# --------------------------------------------------
# Permission Table
# --------------------------------------------------
class Permission(Base, TimestampMixin):
    __tablename__ = "permission"
    __table_args__ = {"extend_existing": True}

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)   # e.g. "upload_file", "assign_job", "review_annotation"
    description = Column(Text, nullable=True)

    # --- Relationships ---
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")
