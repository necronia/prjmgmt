from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres
    database_url: str = "postgresql://prjmgmt:prjmgmt@db:5432/prjmgmt"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Embedding — 로컬 ONNX 모델을 onnxruntime 로 직접 실행 (HF 다운로드 의존 없음).
    # 기본: all-MiniLM-L6-v2 (384-dim). 모델 파일은 /models 볼륨에 위치 (fetch_model.sh).
    # 품질↑이 필요하면 multilingual 모델 onnx 를 같은 구조로 받아 경로/차원만 교체.
    # NOTE: embed_dim 변경 시 db/init.sql 의 vector(N) 도 맞추고 DB 재생성 필요.
    embed_model_path: str = "/models/all-MiniLM-L6-v2"
    embed_dim: int = 384
    embed_max_tokens: int = 256
    embed_query_prefix: str = ""
    embed_passage_prefix: str = ""

    # Retrieval
    top_k: int = 8

    # CORS (dev)
    cors_origins: str = "http://localhost:5173"


settings = Settings()
