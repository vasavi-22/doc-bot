import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone

# Add backend directory to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import Config

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Create the Index object
index = pc.Index(Config.PINECONE_INDEX_NAME)

# delete all vectors in the default namespace
index.delete(delete_all=True)

print("All vectors deleted successfully.")