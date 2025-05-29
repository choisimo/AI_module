from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # UPLOAD_DIR should resolve to app/backend/uploads/
    # Assuming this config.py is in app/backend/app/core/
    # Path(__file__) -> app/backend/app/core/config.py
    # .resolve() -> absolute path
    # .parent -> app/backend/app/core/
    # .parent -> app/backend/app/
    # .parent -> app/backend/
    # Then append 'uploads/'
    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"
    
    ALLOWED_FILE_EXTENSIONS: list[str] = [
        ".txt", ".md", ".py", ".js", ".html", ".css", ".csv", ".json", ".xml", ".yaml", ".yml",
        ".log", ".ini", ".cfg", ".conf", ".sh", ".bat", ".rst", ".tex", ".rtf" # Added more common text-based
    ]
    ALLOWED_MIME_TYPES: list[str] = [
        "text/plain", 
        "text/markdown", 
        "text/x-python", "application/x-python-code", # Some systems use application/x-python-code
        "application/javascript", "text/javascript", # text/javascript is common
        "text/html", 
        "text/css", 
        "text/csv", 
        "application/json", 
        "application/xml", "text/xml", # text/xml is also common
        "application/x-yaml", "text/yaml", "text/x-yaml", # Various YAML MIME types
        "application/rtf", "text/rtf"
        # Consider specific types for .log, .ini, .cfg, .conf, .sh, .bat, .rst, .tex if needed,
        # though they often fall under text/plain or no specific MIME type is universally set.
    ]

    # Example of how other settings might be added:
    # API_V1_STR: str = "/api/v1"
    # PROJECT_NAME: str = "My FastAPI App"

    class Config:
        # For loading from .env file if you have one (optional)
        # env_file = ".env"
        # env_file_encoding = "utf-8"
        pass

settings = Settings()

# Ensure the directory is created when settings are loaded (optional, can also be done in API)
# settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# For this task, API will handle directory creation.

# To verify the path (for development/debugging):
# print(f"UPLOAD_DIR configured to: {settings.UPLOAD_DIR.resolve()}")
