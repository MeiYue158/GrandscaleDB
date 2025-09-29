from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, Index, Table, UniqueConstraint, JSON, Float, event, inspect
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .mixins import TimestampMixin
from .base import Base     # or wherever you define declarative_base()

# ---------- Enums ----------
# (Role/Permission are simple tables, no special enums here)

# ---------- Association Tables ----------
user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("user.user_id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.role_id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True 
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("role.role_id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permission.permission_id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True 

)

# ---------- Core Tables ----------
class Organization(Base, TimestampMixin):
    __tablename__ = "organization"
    __table_args__ = (Index("ix_org_name", "name"), {"extend_existing": True})
    org_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime)

    users = relationship("User", back_populates="organization", passive_deletes=True)
    projects = relationship("Project", back_populates="organization", passive_deletes=True)

class User(Base, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    # --- Core fields ---
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    #role = Column(Enum(UserRole, name="user_role_enum"), nullable=False)

    org_id = Column(
        Integer,
        ForeignKey("organization.org_id", ondelete="SET NULL"),
        nullable=True
    ) # better: keep user even if org deleted

    # --- Availability & Skills ---
    availability = Column(JSON, nullable=True)             # weekly availability
    language_expertise = Column(JSON, nullable=True)       # {"en": 4.5, "zh": 3.0}
    skill_score = Column(Float, nullable=True)             # overall skill score
    skill_level = Column(String, nullable=True)           
    qa_approval_rate = Column(Float, nullable=True)        # average QA pass rate
    completed_task_count = Column(Integer, default=0)      # total tasks completed

    # --- Relationships ---
    uploaded_files = relationship("File", back_populates="uploader")
    events = relationship("EventLog", back_populates="user")
    assignments = relationship("Assignment", back_populates="user", cascade="all, delete-orphan")

    is_active = Column(Boolean, default=True, nullable=False)
    #roles = relationship("Role", secondary=user_roles, back_populates="users")

    # PM links
    client_projects = relationship("Project", back_populates="client_pm")
    # make sure our PM has access to projects and further assign annotators
    managed_projects = relationship("Project", back_populates="our_pm")

    # Historical job links
    # Records which annotators have worked on this job before
    # (for feedback loops / reassignment tracking)
    previous_jobs = relationship(
        "AnnotationJob",
        secondary="job_previous_annotators",
        back_populates="previous_annotators"
    )

    reviews = relationship("Review", back_populates="reviewer")

class Role(Base, TimestampMixin):
    __tablename__ = "role"
    __table_args__ = {"extend_existing": True}

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)   # e.g. "annotator", "qc", "pm"
    description = Column(Text, nullable=True)            # human-readable explanation

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class Permission(Base, TimestampMixin):
    __tablename__ = "permission"
    __table_args__ = {"extend_existing": True}

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)   # e.g. "upload_file", "assign_job", "review_annotation"
    description = Column(Text, nullable=True)            # what this permission means in plain English

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
