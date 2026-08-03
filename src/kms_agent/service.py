from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import re

from kms_agent.chunking import Chunker
from kms_agent.config import Settings
from kms_agent.extractors import ExcelExtractor, PowerPointExtractor
from kms_agent.models import Answer, Citation, DocumentElement, IngestionResult
from kms_agent.providers import FPTCloudProvider, LocalProvider
from kms_agent.retrieval import RetrievalEngine
from kms_agent.stores import MemoryStore, QdrantStore


SYSTEM_PROMPT = """You are an automotive documentation KMS agent.
Answer strictly from the supplied evidence. Do not add facts from prior knowledge.
Return one JSON object with keys: answer (string) and citation_ids (array of evidence IDs).
If the evidence does not answer the question, return an empty citation_ids array and say that the documentation is insufficient."""


class KMSService:
    def __init__(self, settings: Settings | None = None, provider=None, store=None):
        self.settings = settings or Settings.from_env()
        self.provider = provider or self._build_provider()
        self.store = store or self._build_store()
        self.retrieval = RetrievalEngine(
            self.provider,
            self.store,
            candidate_limit=self.settings.retrieval_candidates,
            evidence_limit=self.settings.evidence_limit,
        )
        self.chunker = Chunker(self.settings.chunk_max_words)

    def ingest(self, path: str | Path) -> IngestionResult:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Document not found: {source}")
        suffix = source.suffix.lower()
        checksum = sha256(source.read_bytes()).hexdigest()
        existing = next(
            (
                item
                for item in self.store.list_documents()
                if item.get("checksum") == checksum and item.get("document_title") == source.name
            ),
            None,
        )
        if existing:
            return IngestionResult(
                document_id=existing["document_id"],
                document_title=existing["document_title"],
                checksum=checksum,
                elements=0,
                chunks=int(existing.get("chunks", 0)),
                unchanged=True,
            )
        if suffix in {".pptx", ".pptm"}:
            elements = PowerPointExtractor().extract(source)
        elif suffix in {".xlsx", ".xlsm"}:
            elements = ExcelExtractor().extract(source)
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Expected .pptx, .pptm, .xlsx, or .xlsm")

        enriched = self._enrich_visuals(elements)
        chunks = self.chunker.chunk(elements)
        if chunks:
            self.store.delete_document(chunks[0].document_id)
        self.retrieval.index(chunks)
        return IngestionResult(
            document_id=chunks[0].document_id if chunks else "",
            document_title=source.name,
            checksum=chunks[0].document_checksum if chunks else "",
            elements=len(elements),
            chunks=len(chunks),
            enriched_visuals=enriched,
        )

    def answer(self, question: str) -> Answer:
        if not question.strip():
            raise ValueError("Question must not be empty")
        hits = self.retrieval.search(question)
        if not hits or hits[0].final_score < self.settings.minimum_score:
            return Answer(
                answer="The provided documentation does not contain sufficient evidence to answer this question.",
                citations=[],
                confidence=0.0,
                status="insufficient_evidence",
            )

        evidence_map = {f"E{index}": hit for index, hit in enumerate(hits, start=1)}
        evidence_text = "\n".join(
            f"EVIDENCE {evidence_id}: {hit.chunk.document_title} | {hit.chunk.location.label} | {hit.chunk.text}"
            for evidence_id, hit in evidence_map.items()
        )
        prompt = f"QUESTION: {question.strip()}\n\n{evidence_text}"
        generated = self.provider.generate(SYSTEM_PROMPT, prompt)
        parsed = self._parse_generation(generated.content)
        citation_ids = [item for item in parsed.get("citation_ids", []) if item in evidence_map]
        if not citation_ids:
            return Answer(
                answer="The provided documentation does not contain sufficient evidence to answer this question.",
                citations=[],
                confidence=round(hits[0].final_score * 0.5, 3),
                status="insufficient_evidence",
                usage=generated.usage,
            )

        citations = [self._citation(evidence_id, evidence_map[evidence_id]) for evidence_id in citation_ids]
        confidence = self._confidence(hits, len(citations))
        return Answer(
            answer=str(parsed.get("answer") or citations[0].evidence),
            citations=citations,
            confidence=confidence,
            status="grounded",
            usage=generated.usage,
        )

    def list_documents(self) -> list[dict]:
        return self.store.list_documents()

    def delete_document(self, document_id: str) -> None:
        self.store.delete_document(document_id)

    def _build_provider(self):
        if self.settings.provider == "local":
            return LocalProvider(self.settings.embedding_dimension)
        if self.settings.provider == "fpt":
            return FPTCloudProvider(
                api_key=self.settings.fpt_api_key,
                base_url=self.settings.fpt_base_url,
                embedding_model=self.settings.embedding_model,
                rerank_model=self.settings.rerank_model,
                chat_model=self.settings.chat_model,
                vision_model=self.settings.vision_model,
                dimension=self.settings.embedding_dimension,
                embedding_path=self.settings.fpt_embedding_path,
                rerank_path=self.settings.fpt_rerank_path,
                chat_path=self.settings.fpt_chat_path,
                timeout=self.settings.request_timeout_seconds,
            )
        raise ValueError(f"Unsupported provider: {self.settings.provider}")

    def _build_store(self):
        if self.settings.store == "memory":
            return MemoryStore()
        if self.settings.store == "qdrant":
            return QdrantStore(
                self.settings.qdrant_url,
                self.settings.qdrant_collection,
                self.settings.embedding_dimension,
                self.settings.request_timeout_seconds,
            )
        raise ValueError(f"Unsupported store: {self.settings.store}")

    def _enrich_visuals(self, elements: list[DocumentElement]) -> int:
        if self.settings.provider != "fpt" or not self.settings.vision_model:
            for element in elements:
                if element.content_type == "image":
                    element.metadata["visual_enrichment"] = "skipped"
                    element.binary = None
            return 0
        enriched = 0
        for element in elements:
            if element.content_type != "image" or not element.binary:
                continue
            extension = element.metadata.get("image_extension", "png")
            media_type = "image/jpeg" if extension.lower() in {"jpg", "jpeg"} else f"image/{extension}"
            result = self.provider.describe_image(
                element.binary,
                media_type,
                "Describe this automotive engineering visual precisely. Include labels, interfaces, flows, values, and requirements visible in the image.",
            )
            element.text = f"{element.text}\nVisual description: {result.content}".strip()
            element.metadata["visual_enrichment"] = "fpt"
            element.metadata["vision_usage"] = result.usage
            element.binary = None
            enriched += 1
        return enriched

    @staticmethod
    def _parse_generation(content: str) -> dict:
        cleaned = content.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fenced:
            cleaned = fenced.group(1)
        else:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                cleaned = cleaned[start : end + 1]
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"answer": cleaned, "citation_ids": []}
        if "citation_ids" not in parsed and isinstance(parsed.get("citations"), list):
            parsed["citation_ids"] = [
                item.get("evidence_id") for item in parsed["citations"] if isinstance(item, dict)
            ]
        return parsed

    @staticmethod
    def _citation(evidence_id, hit):
        return Citation(
            evidence_id=evidence_id,
            document=hit.chunk.document_title,
            document_checksum=hit.chunk.document_checksum,
            location=hit.chunk.location.label,
            evidence=hit.chunk.text,
        )

    @staticmethod
    def _confidence(hits, citation_count):
        top = hits[0].final_score
        support = sum(hit.final_score for hit in hits[:3]) / min(3, len(hits))
        completeness = min(1.0, citation_count / 2)
        return round(max(0.0, min(1.0, 0.7 * top + 0.2 * support + 0.1 * completeness)), 3)
