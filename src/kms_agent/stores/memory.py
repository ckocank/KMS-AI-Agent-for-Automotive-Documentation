from __future__ import annotations

from collections import defaultdict

from kms_agent.models import Chunk, SearchHit
from kms_agent.stores.base import SparseVector


class MemoryStore:
    def __init__(self):
        self._points: dict[str, tuple[Chunk, list[float], SparseVector]] = {}

    def upsert(self, chunks, dense, sparse):
        for chunk, dense_vector, sparse_vector in zip(chunks, dense, sparse):
            self._points[chunk.id] = (chunk, dense_vector, sparse_vector)

    def search(self, dense, sparse, limit):
        dense_scores = {}
        sparse_scores = {}
        for chunk_id, (_, dense_vector, sparse_vector) in self._points.items():
            dense_scores[chunk_id] = sum(a * b for a, b in zip(dense, dense_vector))
            sparse_scores[chunk_id] = sum(value * sparse_vector.get(index, 0.0) for index, value in sparse.items())
        dense_rank = self._ranks(dense_scores)
        sparse_rank = self._ranks(sparse_scores)
        fused = {}
        for chunk_id in self._points:
            score = 0.65 / (60 + dense_rank[chunk_id]) + 0.35 / (60 + sparse_rank[chunk_id])
            fused[chunk_id] = score * 61
        ordered = sorted(fused, key=fused.get, reverse=True)[:limit]
        return [SearchHit(chunk=self._points[item][0], score=fused[item]) for item in ordered]

    def delete_document(self, document_id):
        self._points = {
            key: value for key, value in self._points.items() if value[0].document_id != document_id
        }

    def list_documents(self):
        documents = {}
        counts = defaultdict(int)
        for chunk, _, _ in self._points.values():
            counts[chunk.document_id] += 1
            documents[chunk.document_id] = {
                "document_id": chunk.document_id,
                "document_title": chunk.document_title,
                "checksum": chunk.document_checksum,
            }
        return [{**documents[key], "chunks": counts[key]} for key in sorted(documents)]

    @staticmethod
    def _ranks(scores):
        ordered = sorted(scores, key=scores.get, reverse=True)
        return {item: index for index, item in enumerate(ordered, start=1)}

