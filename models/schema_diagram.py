from sqlalchemy import create_engine
from sqlalchemy_schemadisplay import create_schema_graph

# import all your model modules so Base.metadata knows every table
from GrandscaleDB.models import annotation, event, organization, project, update_rules
from GrandscaleDB.models.base import Base

# create a dummy engine (in-memory SQLite is fine for just drawing the schema)
engine = create_engine("sqlite:///:memory:")

graph = create_schema_graph(
    engine,                     # <-- engine is REQUIRED in your version
    metadata=Base.metadata,
    show_datatypes=True,
    show_indexes=True,
    rankdir="LR",
    concentrate=False
)

graph.write_png("full_schema.png")
print("✅ ER diagram saved to full_schema.png")
