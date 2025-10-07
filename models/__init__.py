# models/__init__.py
"""
Model package initializer.

This file imports all ORM models and sets up event listeners (e.g. skip_updated_at).
After this, you can safely import models from anywhere using:
    from models import Base, Project, File, AnnotationJob, etc.
"""

# ----------------------------
# Core imports
# ----------------------------
from .base import Base
from .mixins import TimestampMixin
from .enums import (
    ProjectStatus,
    FileStatus,
    FileType,
    AnnotationJobStatus,
    ReviewStatus,
    EntityType,
    EventType,
    AssignmentRole,
    Language,
    JobPriority,
)

# ----------------------------
# Project / File / Export models
# ----------------------------
from .project import (
    Project,
    File,
    FileVersion,
    FileTable,
    ExportLog,
    ExportedFile,
)

# ----------------------------
# Annotation / Workflow models
# ----------------------------
from .annotation import (
    AnnotationJob,
    Assignment,
    Review,
    Role,
    Permission,
)

# ----------------------------
# Organization / User models
# ----------------------------
from .organization import (
    Organization,
    User,
)

# ----------------------------
# Event model
# ----------------------------
from .event import EventLog

# ----------------------------
# Update rules (REAL_UPDATE_COLS + listener)
# ----------------------------
from .update_rules import register_update_hooks

# Register hooks for models whose updated_at should only change
# when "real" business columns change
register_update_hooks([
    Project,
    File,
    FileVersion,
    FileTable,
    User,
    AnnotationJob,
    Assignment,
    Review,
    ExportLog,
    Organization,
])

# ----------------------------
# What gets exported when doing:
#     from models import *
# ----------------------------
__all__ = [
    # Base + mixins
    "Base",
    "TimestampMixin",
    # Enums
    "ProjectStatus", "FileStatus", "FileType",
    "AnnotationJobStatus", "ReviewStatus",
    "EntityType", "EventType", "AssignmentRole",
    "Language", "JobPriority",
    # Core models
    "Project", "File", "FileVersion", "FileTable",
    "ExportLog", "ExportedFile",
    "AnnotationJob", "Assignment", "Review",
    "Organization", "User", "Role", "Permission",
    "EventLog",
]

# A quick self check I designed purposefully(only runs if executed directly)
if __name__ == "__main__":
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///test.db", echo=True)
    Base.metadata.create_all(engine)
    print("✅ All models created successfully in test.db")
