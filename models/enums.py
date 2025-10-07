# models/enums.py
"""
Centralized enumeration definitions for all models.
These enums represent lifecycle states, workflow roles, priorities, etc.
Each is defined once here and imported wherever needed.
"""

import enum


# -------------------------------
# 1. Project lifecycle
# -------------------------------
class ProjectStatus(enum.Enum):
    draft = "draft"                     # project created, requirements being defined
    ready_for_annotation = "ready_for_annotation"  # files uploaded, jobs not started
    in_progress = "in_progress"         # annotation jobs are running
    completed = "completed"             # all jobs done
    archived = "archived"               # project closed, read-only


# -------------------------------
# 2. File lifecycle and type
# -------------------------------
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


# -------------------------------
# 3. Annotation job workflow
# -------------------------------
class AnnotationJobStatus(enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"
    reviewed = "reviewed"


class ReviewStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# -------------------------------
# 4. Event logging
# -------------------------------
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


# -------------------------------
# 5. Assignment and roles
# -------------------------------
class AssignmentRole(enum.Enum):
    annotator = "annotator"
    reviewer = "reviewer"
    qc = "qc"   # quality control / audit


# -------------------------------
# 6. Job language and priority
# -------------------------------
class Language(enum.Enum):
    en = "en"   # English
    zh = "zh"   # Chinese
    fr = "fr"   # French
    de = "de"   # German
    es = "es"   # Spanish
    ar = "ar"   # Arabic


class JobPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
