from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_llm_model: str = "deepseek-ai/deepseek-v4.1-flash"

    embedding_model: str = "BAAI/bge-base-en-v1.5"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 5
    min_score: float = 0.35
    pages_per_batch: int = 3
    max_parallel: int = 3

    sqlite_path: str = "data/app.db"
    upload_dir: str = "data/uploads"
    faiss_index_path: str = "data/faiss.index"
    faiss_meta_path: str = "data/faiss_meta.json"

    log_level: str = "INFO"

    def resolve(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return ROOT_DIR / path


settings = Settings()
