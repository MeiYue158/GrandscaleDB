# models/organization.py
"""
Organization and User models:
- Organization: represents a client company or internal org.
- User: represents annotators, PMs, reviewers, and other human users.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON, Index, func
)
from sqlalchemy.orm import relationship
from .base import Base
from .mixins import TimestampMixin


# --------------------------------------------------
# Organization Table
# --------------------------------------------------
class Organization(Base, TimestampMixin):
    __tablename__ = "organization"
    __table_args__ = (
        Index("ix_org_name", "name"),
        {"extend_existing": True},
    )

    org_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)     # e.g. "Acme Corp"
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # --- Relationships ---
    users = relationship("User", back_populates="organization", passive_deletes=True)
    projects = relationship("Project", back_populates="organization", passive_deletes=True)

    # Convenience: all files uploaded under this org (via projects)
    files = relationship(
        "File",
        secondary="project",  # indirect join via Project.project_id
        viewonly=True,
        primaryjoin="Organization.org_id==Project.org_id",
        secondaryjoin="Project.project_id==File.project_id",
    )

    # Optional event linkage
    events = relationship(
        "EventLog",
        secondary="project",
        primaryjoin="Organization.org_id == Project.org_id",
        secondaryjoin="Project.project_id == EventLog.project_id",
        viewonly=True,
    )


# --------------------------------------------------
# User Table
# --------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organization.org_id", ondelete="SET NULL"), nullable=True)

    # Optional attributes
    availability = Column(JSON, nullable=True)             # {"mon": 4, "tue": 6, ...}
    language_expertise = Column(JSON, nullable=True)       # {"en": 4.5, "zh": 3.0}
    skill_score = Column(Float, nullable=True)
    skill_level = Column(String, nullable=True)
    qa_approval_rate = Column(Float, nullable=True)
    completed_task_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True, nullable=False)

    # --- Relationships ---
    organization = relationship("Organization", back_populates="users")
    uploaded_files = relationship("File", back_populates="uploader")
    assignments = relationship("Assignment", back_populates="user", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="user", cascade="all, delete-orphan")

    client_projects = relationship("Project", back_populates="client_pm", foreign_keys="[Project.client_pm_id]")
    managed_projects = relationship("Project", back_populates="our_pm", foreign_keys="[Project.our_pm_id]")

    previous_jobs = relationship(
        "AnnotationJob",
        secondary="job_previous_annotators",
        back_populates="previous_annotators"
    )

    reviews = relationship("Review", back_populates="reviewer", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
