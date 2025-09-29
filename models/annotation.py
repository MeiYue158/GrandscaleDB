from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey, Index, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .mixins import TimestampMixin
from .base import Base
import enum

# ---------- Enums ----------
class AnnotationJobStatus(enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"
    reviewed = "reviewed"

class ReviewStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

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

# ---------- Association ----------
job_previous_annotators = Table(
    "job_previous_annotators", Base.metadata,
    Column("job_id", Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=func.now())
)

# ---------- Core Tables ----------
class AnnotationJob(Base, TimestampMixin):
    __tablename__ = "annotation_job"
    __table_args__ = {"extend_existing": True}

    job_id = Column(Integer, primary_key=True, autoincrement=True)

    file_id = Column(Integer, ForeignKey("file.file_id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)

    # New attributes
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

    # created_at = Column(DateTime, default=func.now(), nullable=False)
    # updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    file = relationship("File", back_populates="annotation_jobs")
    project = relationship("Project", back_populates="annotation_jobs")

    reviews = relationship("Review", back_populates="job", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="job", cascade="all, delete-orphan")
    # cascade — reviews/assignments are job-level leaves.

    # Historical annotators (M2M self join via Assignment/User)
    previous_annotators = relationship(
        "User",
        secondary="job_previous_annotators",
        back_populates="previous_jobs"
    )

# --------------------------
# Assignment Table
# --------------------------
class Assignment(Base, TimestampMixin):
    __tablename__ = "assignment"
    __table_args__ = (
        Index("ix_assignment_job_id", "job_id"),
        Index("ix_assignment_user_id", "user_id"),
        Index("ix_assignment_role", "role"),
        {"extend_existing": True},
    )

    assignment_id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to the annotation job (one job = one file version to be annotated)
    job_id = Column(
        Integer,
        ForeignKey("annotation_job.job_id", ondelete="CASCADE"),
        nullable=False
    )

    # Who is assigned
    user_id = Column(
        Integer,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # Role in this job (annotator, reviewer, qc)
    role = Column(Enum(AssignmentRole, name="assignment_role_enum"), nullable=False)

    # Status of this assignment (separate from job status)
    status = Column(
        Enum("assigned", "accepted", "in_progress", "submitted", "completed",
             name="assignment_status_enum"),
        default="assigned",
        nullable=False
    )

    # Whether this assignment is currently active (soft delete for history)
    is_active = Column(Boolean, default=True, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Audit fields
    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    job = relationship("AnnotationJob", back_populates="assignments")
    user = relationship("User", back_populates="assignments")

    # Track reviews connected to this assignment (indirectly through job)
    reviews = relationship(
        "Review",
        secondary="annotation_job",  # review links via job_id
        viewonly=True
    )


class Review(Base, TimestampMixin):
    __tablename__ = "review"
    __table_args__ = (
    Index("ix_review_job_id", "job_id"),
    Index("ix_review_status", "status"),
    {"extend_existing": True},
)


    review_id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to the job being reviewed
    job_id = Column(Integer, ForeignKey("annotation_job.job_id", ondelete="CASCADE"), nullable=False)

    # Reviewer (user with reviewer role)
    reviewer_id = Column(Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True)

    # Review decision
    status = Column(
        Enum(ReviewStatus, name="review_status_enum"),
        default=ReviewStatus.pending,
        nullable=False
    )

    # Optional comments from reviewer
    feedback = Column(Text, nullable=True)


    # Audit timestamps
    # created_at = Column(DateTime, default=func.now(), nullable=False)
    # updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Soft delete fields (prevents permanent data loss)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


    # Relationships
    job = relationship("AnnotationJob", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
    events = relationship("EventLog", back_populates="review")



