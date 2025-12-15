import os
from pathlib import Path
from typing import Union, List
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Deepfake Detection API"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    GRADCAM_DIR: Path = BASE_DIR / "gradcam_uploads"
    RESULTS_FILE: Path = BASE_DIR / "results.json"
    MODEL_PATH: Path = BASE_DIR / "app" / "model" / "resnet50_detector_best.pth"
    
    # Security / CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Inbox / Mail
    INBOX_CACHE: Path = BASE_DIR / "app" / "inbox_cache.jsonl"
    TMP_DIR: Path = BASE_DIR / "tmp"
    MAIL_LOGS_PATH: Path = BASE_DIR / "mail_logs.txt"
    REDIS_URL: str = "redis://redis:6379/0" # Docker friendly default
    
    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create directories if they don't exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.GRADCAM_DIR.mkdir(parents=True, exist_ok=True)
settings.TMP_DIR.mkdir(parents=True, exist_ok=True)
