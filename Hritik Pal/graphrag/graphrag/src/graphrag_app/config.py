"""
Configuration file for GraphRAG system
All credentials are loaded from .env file
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Local SQLite configuration
GRAPH_DB_PATH = os.getenv("GRAPH_DB_PATH", "graphrag_local.db")

# Ollama local model configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "qwen3:0.6b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

# Graph configuration
GRAPH_CONFIG = {
    "entity_types": ["Person", "Organization", "Location", "Date", "Event", "Concept"],
    "relationship_types": ["RELATED_TO", "LOCATED_IN", "WORKS_FOR", "CREATED", "MENTIONS", "CONNECTED_TO"]
}
