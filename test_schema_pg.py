from sqlalchemy_schemadisplay import create_schema_graph
from sqlalchemy import create_engine
from models import Base

# Use your real engine only if you want reflection
# For schema-only visualization, keep it in-memory
engine = create_engine("sqlite:///:memory:")

# Build the schema
Base.metadata.create_all(engine)

# Generate the ERD
graph = create_schema_graph(
    metadata=Base.metadata,
    show_datatypes=True,
    show_indexes=True,
    rankdir="LR",   # optional: Left-to-Right layout (clearer for wide schemas)
    concentrate=False,
    graph_attr={
        "splines": "ortho",
        "nodesep": "0.8",
        "ranksep": "1.0",
        "fontsize": "10",
    },
)

# Export diagrams
graph.write_png("schema.png")
graph.write_svg("schema.svg")
print("✅ ER diagram generated successfully (schema.png / schema.svg)")
