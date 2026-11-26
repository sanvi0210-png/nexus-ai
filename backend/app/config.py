from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    qdrant_path: str = "./data/qdrant"
    collection_name: str = "nexus_documents"
    max_upload_mb: int = 25
    # Minimum cosine score for the best hit; below this NEXUS abstains.
    # Tune this on your own evaluation set (guide section 10F).
    min_score: float = 0.25
    allowed_origins: str = "http://localhost:3000"
    # "local" = sentence-transformers on this machine, "gemini" = Google embedding API (tiny memory footprint)
    embedding_provider: str = "local"
    data_dir: str = "data"
    # Public-demo guards (the Space Dockerfile sets tighter values)
    max_pages: int = 300
    max_docs_per_workspace: int = 50
    daily_llm_budget: int = 100000
    # semantic | hybrid | hybrid_rerank
    retrieval_mode: str = "hybrid"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
