from sqlalchemy import event, inspect
from .project import Project, File, FileVersion
from .organization import User, Organization
from .annotation import AnnotationJob, Assignment, Review
from .event import ExportLog

REAL_UPDATE_COLS = {
    "project": {"status","name","description","client_pm_id","our_pm_id","is_active"},
    "file": {"status","name","description","active_version_id","is_active"},
    "file_version": {"is_active","generation_method","llm_model","llm_params"},
    "user": {"email","org_id","availability","language_expertise",
             "skill_score","skill_level","qa_approval_rate","is_active"},
    "annotation_job": {"status","review_status","priority","language","due_date","is_active"},
    "assignment": {"status","role","user_id"},
    "review": {"status","feedback","is_active"},
    "export_log": {"status","storage_path","checksum"},
    "organization": {"name","description","is_active"},
}

def skip_updated_at(mapper, connection, target):
    state = inspect(target)
    cols = REAL_UPDATE_COLS.get(target.__tablename__, set())
    if cols and not any(state.attrs[c].history.has_changes() for c in cols):
        target.updated_at = state.attrs["updated_at"].loaded_value

for model in [Project, File, FileVersion, User, AnnotationJob,
              Assignment, Review, ExportLog, Organization]:
    event.listen(model, "before_update", skip_updated_at)
