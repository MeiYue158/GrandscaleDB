from sqlalchemy_schemadisplay import create_schema_graph
from models import Base # notice here looks for a model, NOT package like models.py
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# load env file so DATABASE_URL is available
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

graph = create_schema_graph(
    engine=engine,              # 👈 required in your version
    metadata=Base.metadata,
    show_datatypes=True,
    show_indexes=True,
    rankdir='LR',
    concentrate=False
)

graph.write_png('er_diagram.png')

