from sqlalchemy_schemadisplay import create_schema_graph
from sqlalchemy import create_engine
from models import Base  # 👈 import your schema file

# Create a dummy in-memory engine (no real DB connection needed)
engine = create_engine("sqlite:///:memory:")

# Generate the graph
graph = create_schema_graph(
    metadata=Base.metadata,
    engine=engine,
    show_datatypes=True,
    show_indexes=True,
    rankdir="TB",             # top-to-bottom
    concentrate=False,
    #graph_attr={"splines": "ortho", "nodesep": "0.8", "ranksep": "1.0"}
)

# Export as PNG
graph.write_png("schema.png")
graph.write_svg("schema.svg")
graph.write_pdf("schema.pdf")
print("✅ Schema diagram saved as schema.png")

