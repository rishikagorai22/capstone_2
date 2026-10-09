import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Use whichever model name worked in your smoke test:
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

DOCS_PATH = ROOT / "data" / "documents"
CHROMA_PATH = ROOT / "data" / "chroma"
DB_PATH = ROOT / "data" / "database.sqlite"
LOG_PATH = ROOT / "tokenomics_log.jsonl"

COLLECTION_NAME = "enterprise-docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 150      # words per chunk
CHUNK_OVERLAP = 30
TOP_K = 4             # chunks sent to the LLM (fewer = fewer tokens)

# Paid-equivalent price estimate, USD per 1M tokens. The free tier really bills $0.
# Check Google's Gemini pricing page for your model and update these if you want exact numbers.
PRICE_IN_PER_1M = 1.50
PRICE_OUT_PER_1M = 7.50
