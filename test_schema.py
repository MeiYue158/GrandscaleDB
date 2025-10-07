# test_schema.py
from sqlalchemy import create_engine
from sqlalchemy_schemadisplay import create_schema_graph
from models import Base

# We only need a PostgreSQL dialect so JSONB/ENUM render correctly.
# No network connection will be made unless you call .connect().
engine = create_engine("postgresql+psycopg2://")

graph = create_schema_graph(
    metadata=Base.metadata,
    engine=engine,
    show_datatypes=True,
    show_indexes=True,
    rankdir="TB",
    concentrate=False,
)

graph.write_png("schema.png")
graph.write_svg("schema.svg")
graph.write_pdf("schema.pdf")
print("✅ Schema diagram saved as schema.png / .svg / .pdf")

