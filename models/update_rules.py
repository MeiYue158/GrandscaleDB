# models/update_rules.py
"""
Defines REAL_UPDATE_COLS and skip_updated_at() logic.

REAL_UPDATE_COLS controls which columns are considered “real” updates
for each table — i.e., only these changes trigger updated_at refresh.
Other changes (e.g. relationship-only changes) will keep updated_at unchanged.
"""

from sqlalchemy import event, inspect
from sqlalchemy.sql import func

# --------------------------------------------------
# Columns that count as “real” updates
# --------------------------------------------------

REAL_UPDATE_COLS = {
    # Project life-cycle
    "project": {
        "status", "name", "description",
        "client_pm_id", "our_pm_id", "is_active"
    },

    # Files inside a project
    "file": {
        "status", "name", "description",
        "active_version_id", "is_active"
    },

    # File versions (mostly immutable)
    "file_version": {
        "is_active", "generation_method",
        "llm_model", "llm_params"
    },

    # Table extracted from file
    "file_table": {
        "status", "description", "schema_json",
        "extracted_narrative", "is_active"
    },

    # Users
    "user": {
        "email", "org_id", "availability",
        "language_expertise", "skill_score",
        "skill_level", "qa_approval_rate", "is_active"
    },

    # Annotation jobs
    "annotation_job": {
        "status", "review_status", "priority",
        "language", "due_date", "is_active"
    },

    # Assignments
    "assignment": {
        "status", "role", "user_id"
    },

    # Reviews
    "review": {
        "status", "feedback", "is_active"
    },

    # Exports
    "export_log": {
        "status", "storage_path", "checksum"
    },

    # Organizations
    "organization": {
        "name", "description", "is_active"
    },

    # Event logs are append-only
    # "event_log": set(),
}


# --------------------------------------------------
# Skip updated_at if no “real” columns changed
# --------------------------------------------------

def skip_updated_at(mapper, connection, target):
    """
    Prevents auto-update of updated_at unless meaningful fields changed.
    """
    state = inspect(target)
    model_name = target.__tablename__
    real_cols = REAL_UPDATE_COLS.get(model_name, set())

    # If model has tracked columns, check if any changed
    if real_cols:
        if not any(state.attrs[c].history.has_changes() for c in real_cols):
            # No real change → keep old updated_at value
            if "updated_at" in state.attrs:
                target.updated_at = state.attrs["updated_at"].loaded_value


# --------------------------------------------------
# Register event listeners for all applicable models
# --------------------------------------------------

def register_update_hooks(models):
    """
    Attach skip_updated_at event listener to all provided models.
    Example usage (in __init__.py):

        from .update_rules import register_update_hooks
        register_update_hooks([Project, File, FileVersion, ...])
    """
    for model in models:
        event.listen(model, "before_update", skip_updated_at)
