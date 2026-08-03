from dataclasses import dataclass
import os


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    provider: str = "local"
    store: str = "memory"
    fpt_api_key: str = ""
    fpt_base_url: str = "https://mkp-api.fptcloud.com"
    fpt_embedding_path: str = "/embeddings"
    fpt_rerank_path: str = "/rerank"
    fpt_chat_path: str = "/chat/completions"
    embedding_model: str = "multilingual-e5-large"
    rerank_model: str = "bge-reranker-v2-m3"
    chat_model: str = ""
    vision_model: str = ""
    embedding_dimension: int = 256
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "automotive_office_kms"
    chunk_max_words: int = 380
    retrieval_candidates: int = 50
    evidence_limit: int = 5
    minimum_score: float = 0.12
    request_timeout_seconds: int = 90

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=os.getenv("KMS_PROVIDER", "local").lower(),
            store=os.getenv("KMS_STORE", "memory").lower(),
            fpt_api_key=os.getenv("FPT_API_KEY", ""),
            fpt_base_url=os.getenv("FPT_BASE_URL", "https://mkp-api.fptcloud.com").rstrip("/"),
            fpt_embedding_path=os.getenv("FPT_EMBEDDING_PATH", "/embeddings"),
            fpt_rerank_path=os.getenv("FPT_RERANK_PATH", "/rerank"),
            fpt_chat_path=os.getenv("FPT_CHAT_PATH", "/chat/completions"),
            embedding_model=os.getenv("FPT_EMBEDDING_MODEL", "multilingual-e5-large"),
            rerank_model=os.getenv("FPT_RERANK_MODEL", "bge-reranker-v2-m3"),
            chat_model=os.getenv("FPT_CHAT_MODEL", ""),
            vision_model=os.getenv("FPT_VISION_MODEL", ""),
            embedding_dimension=_int("KMS_EMBEDDING_DIMENSION", 256),
            qdrant_url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "automotive_office_kms"),
            chunk_max_words=_int("KMS_CHUNK_MAX_WORDS", 380),
            retrieval_candidates=_int("KMS_RETRIEVAL_CANDIDATES", 50),
            evidence_limit=_int("KMS_EVIDENCE_LIMIT", 5),
            minimum_score=_float("KMS_MINIMUM_SCORE", 0.12),
            request_timeout_seconds=_int("KMS_REQUEST_TIMEOUT_SECONDS", 90),
        )

