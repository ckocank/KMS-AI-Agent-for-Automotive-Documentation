from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class SourceLocation:
    kind: str
    label: str
    coordinates: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentElement:
    id: str
    document_id: str
    document_title: str
    document_checksum: str
    location: SourceLocation
    content_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    binary: bytes | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        document_title: str,
        document_checksum: str,
        location: SourceLocation,
        content_type: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        binary: bytes | None = None,
    ) -> "DocumentElement":
        identity = "|".join(
            [document_checksum, location.kind, location.label, content_type, sha256(text.encode("utf-8")).hexdigest()]
        )
        return cls(
            id=sha256(identity.encode("utf-8")).hexdigest(),
            document_id=document_id,
            document_title=document_title,
            document_checksum=document_checksum,
            location=location,
            content_type=content_type,
            text=text,
            metadata=dict(metadata or {}),
            binary=binary,
        )


@dataclass
class Chunk:
    id: str
    element_id: str
    document_id: str
    document_title: str
    document_checksum: str
    location: SourceLocation
    content_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def embedding_text(self) -> str:
        return f"{self.document_title}\n{self.location.label}\n{self.text}"

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["location"] = asdict(self.location)
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Chunk":
        data = dict(payload)
        data["location"] = SourceLocation(**data["location"])
        return cls(**data)


@dataclass
class SearchHit:
    chunk: Chunk
    score: float
    rerank_score: float | None = None

    @property
    def final_score(self) -> float:
        return self.rerank_score if self.rerank_score is not None else self.score


@dataclass
class Citation:
    evidence_id: str
    document: str
    document_checksum: str
    location: str
    evidence: str


@dataclass
class Answer:
    answer: str
    citations: list[Citation]
    confidence: float
    status: str
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionResult:
    document_id: str
    document_title: str
    checksum: str
    elements: int
    chunks: int
    enriched_visuals: int = 0
    unchanged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
