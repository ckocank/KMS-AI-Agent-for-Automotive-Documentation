from __future__ import annotations

from typing import Protocol

from kms_agent.models import Chunk, SearchHit


SparseVector = dict[int, float]


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk], dense: list[list[float]], sparse: list[SparseVector]) -> None: ...

    def search(self, dense: list[float], sparse: SparseVector, limit: int) -> list[SearchHit]: ...

    def delete_document(self, document_id: str) -> None: ...

    def list_documents(self) -> list[dict]: ...

