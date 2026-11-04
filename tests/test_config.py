from pathlib import Path

from app.config import ROOT_DIR, Settings, settings


def test_default_chunk_settings():
    assert settings.chunk_size > 0
    assert settings.chunk_overlap < settings.chunk_size
    assert settings.top_k > 0
    assert settings.pages_per_batch > 0
    assert settings.max_parallel > 0


def test_model_names_are_set():
    assert settings.nvidia_llm_model
    assert settings.embedding_model == "BAAI/bge-base-en-v1.5"


def test_resolve_joins_project_root():
    resolved = settings.resolve("data/app.db")
    assert resolved == ROOT_DIR / "data" / "app.db"
    assert resolved.is_absolute()


def test_resolve_keeps_absolute_path():
    absolute = Path("C:/temp/app.db")
    assert settings.resolve(str(absolute)) == absolute


def test_settings_can_be_created_from_env_file():
    loaded = Settings()
    assert loaded.sqlite_path.endswith("app.db")
    assert loaded.upload_dir.endswith("uploads")
