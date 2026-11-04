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
    nvidia_llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b"

    # Use nvidia (NIM), openai, or gemini
    llm_provider: str = "nvidia"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-flash-latest"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_llm_model: str = "gpt-4o-mini"

    embedding_model: str = "BAAI/bge-base-en-v1.5"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 5
    min_score: float = 0.35
    pages_per_batch: int = 3
    max_parallel: int = 3

    sqlite_path: str = "Data/app.db"
    upload_dir: str = "Data/uploads"
    faiss_index_path: str = "Data/faiss.index"
    faiss_meta_path: str = "Data/faiss_meta.json"

    log_level: str = "INFO"

    def resolve(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return ROOT_DIR / path


settings = Settings()
