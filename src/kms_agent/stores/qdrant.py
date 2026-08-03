from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID

from kms_agent.models import Chunk, SearchHit


class QdrantError(RuntimeError):
    pass


class QdrantStore:
    def __init__(self, url: str, collection: str, dimension: int, timeout: int = 30):
        self.url = url.rstrip("/")
        self.collection = collection
        self.dimension = dimension
        self.timeout = timeout
        self._ensure_collection()

    def upsert(self, chunks, dense, sparse):
        points = []
        for chunk, dense_vector, sparse_vector in zip(chunks, dense, sparse):
            points.append(
                {
                    "id": str(UUID(hex=chunk.id[:32])),
                    "vector": {
                        "dense": dense_vector,
                        "sparse": {
                            "indices": sorted(sparse_vector),
                            "values": [sparse_vector[index] for index in sorted(sparse_vector)],
                        },
                    },
                    "payload": chunk.to_payload(),
                }
            )
        self._request("PUT", f"/collections/{quote(self.collection)}/points?wait=true", {"points": points})

    def search(self, dense, sparse, limit):
        response = self._request(
            "POST",
            f"/collections/{quote(self.collection)}/points/query",
            {
                "prefetch": [
                    {"query": dense, "using": "dense", "limit": limit},
                    {
                        "query": {
                            "indices": sorted(sparse),
                            "values": [sparse[index] for index in sorted(sparse)],
                        },
                        "using": "sparse",
                        "limit": limit,
                    },
                ],
                "query": {"fusion": "rrf"},
                "limit": limit,
                "with_payload": True,
            },
        )
        result = response.get("result", {})
        points = result.get("points", result if isinstance(result, list) else [])
        return [
            SearchHit(chunk=Chunk.from_payload(point["payload"]), score=float(point.get("score", 0.0)))
            for point in points
        ]

    def delete_document(self, document_id):
        self._request(
            "POST",
            f"/collections/{quote(self.collection)}/points/delete?wait=true",
            {"filter": {"must": [{"key": "document_id", "match": {"value": document_id}}]}},
        )

    def list_documents(self):
        response = self._request(
            "POST",
            f"/collections/{quote(self.collection)}/points/scroll",
            {"limit": 10000, "with_payload": True, "with_vector": False},
        )
        points = response.get("result", {}).get("points", [])
        documents = {}
        for point in points:
            payload = point["payload"]
            item = documents.setdefault(
                payload["document_id"],
                {
                    "document_id": payload["document_id"],
                    "document_title": payload["document_title"],
                    "checksum": payload["document_checksum"],
                    "chunks": 0,
                },
            )
            item["chunks"] += 1
        return list(documents.values())

    def _ensure_collection(self):
        try:
            self._request("GET", f"/collections/{quote(self.collection)}")
        except QdrantError as exc:
            if "HTTP 404" not in str(exc):
                raise
            self._request(
                "PUT",
                f"/collections/{quote(self.collection)}",
                {
                    "vectors": {"dense": {"size": self.dimension, "distance": "Cosine"}},
                    "sparse_vectors": {"sparse": {"index": {"on_disk": False}}},
                },
            )

    def _request(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise QdrantError(f"Qdrant HTTP {exc.code}: {body[:500]}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise QdrantError(f"Qdrant request failed: {exc}") from exc

