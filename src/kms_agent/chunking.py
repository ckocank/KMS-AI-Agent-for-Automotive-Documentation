from __future__ import annotations

from hashlib import sha256

from kms_agent.models import Chunk, DocumentElement


class Chunker:
    def __init__(self, max_words: int = 380):
        if max_words < 10:
            raise ValueError("max_words must be at least 10")
        self.max_words = max_words

    def chunk(self, elements: list[DocumentElement]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for element in elements:
            for index, text in enumerate(self._split(element.text)):
                identity = f"{element.id}|{index}|{sha256(text.encode('utf-8')).hexdigest()}"
                chunks.append(
                    Chunk(
                        id=sha256(identity.encode("utf-8")).hexdigest(),
                        element_id=element.id,
                        document_id=element.document_id,
                        document_title=element.document_title,
                        document_checksum=element.document_checksum,
                        location=element.location,
                        content_type=element.content_type,
                        text=text,
                        metadata={**element.metadata, "chunk_index": index},
                    )
                )
        return chunks

    def _split(self, text: str) -> list[str]:
        words = text.split()
        if len(words) <= self.max_words:
            return [text.strip()] if text.strip() else []
        chunks: list[str] = []
        current: list[str] = []
        for line in (line.strip() for line in text.splitlines() if line.strip()):
            line_words = line.split()
            if len(current) + len(line_words) <= self.max_words:
                current.append(line)
                continue
            if current:
                chunks.append("\n".join(current))
                current = []
            while len(line_words) > self.max_words:
                chunks.append(" ".join(line_words[: self.max_words]))
                line_words = line_words[self.max_words :]
            if line_words:
                current.append(" ".join(line_words))
        if current:
            chunks.append("\n".join(current))
        return chunks

