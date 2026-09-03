import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Central configuration, populated from environment variables (.env)."""

    # --- Flask core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_EXP_MINUTES = int(os.environ.get("JWT_EXP_MINUTES", 60))

    # --- Database ---
    database_url = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'neuraforge.db')}"
    )
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- AI Provider ---
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # --- RAG ---
    CHROMA_PERSIST_DIR = os.path.join(basedir, os.environ.get("CHROMA_PERSIST_DIR", "app/chroma_db"))
    UPLOAD_FOLDER = os.path.join(basedir, os.environ.get("UPLOAD_FOLDER", "app/uploads"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 15)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf"}
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150
    RETRIEVAL_K = 4