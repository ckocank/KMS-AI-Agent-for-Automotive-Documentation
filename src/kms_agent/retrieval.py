from __future__ import annotations

from hashlib import sha256
import math

from kms_agent.models import Chunk, SearchHit
from kms_agent.providers.local import tokenize


def sparse_vector(text: str) -> dict[int, float]:
    vector: dict[int, float] = {}
    for token in tokenize(text):
        index = int.from_bytes(sha256(token.encode("utf-8")).digest()[:4], "big") % 1_000_003
        vector[index] = vector.get(index, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in vector.values()))
    return {index: value / norm for index, value in vector.items()} if norm else {}


class RetrievalEngine:
    def __init__(self, provider, store, candidate_limit: int = 50, evidence_limit: int = 5):
        self.provider = provider
        self.store = store
        self.candidate_limit = candidate_limit
        self.evidence_limit = evidence_limit

    def index(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        dense = self.provider.embed([chunk.embedding_text for chunk in chunks])
        sparse = [sparse_vector(chunk.embedding_text) for chunk in chunks]
        self.store.upsert(chunks, dense, sparse)

    def search(self, query: str, limit: int | None = None) -> list[SearchHit]:
        dense = self.provider.embed([query])[0]
        candidates = self.store.search(dense, sparse_vector(query), self.candidate_limit)
        if not candidates:
            return []
        rerank_scores = self.provider.rerank(query, [hit.chunk.embedding_text for hit in candidates])
        for hit, score in zip(candidates, rerank_scores):
            hit.rerank_score = self._normalize(score)
        candidates.sort(key=lambda item: (item.final_score, item.score), reverse=True)
        return candidates[: (limit or self.evidence_limit)]

    @staticmethod
    def _normalize(score: float) -> float:
        if 0.0 <= score <= 1.0:
            return score
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, score))))

