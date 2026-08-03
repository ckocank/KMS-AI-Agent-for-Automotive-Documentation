from __future__ import annotations

from hashlib import sha256
import json
import math
import re

from kms_agent.providers.base import GenerationResult


TOKEN_PATTERN = re.compile(r"[\w]+(?:[-./][\w]+)*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(text)]


class LocalProvider:
    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in tokenize(text):
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        query_tokens = set(tokenize(query))
        query_vector = self._embed_one(query)
        scores = []
        for document in documents:
            document_tokens = set(tokenize(document))
            exact = len(query_tokens & document_tokens) / max(1, len(query_tokens))
            semantic = sum(a * b for a, b in zip(query_vector, self._embed_one(document)))
            scores.append(max(0.0, min(1.0, 0.75 * exact + 0.25 * max(0.0, semantic))))
        return scores

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        question_line = next((line for line in user_prompt.splitlines() if line.startswith("QUESTION:")), "")
        query_tokens = set(tokenize(question_line.partition(":")[2]))
        candidates = []
        for line in user_prompt.splitlines():
            match = re.match(r"EVIDENCE (E\d+):\s*(.*)", line)
            if not match:
                continue
            evidence_id, raw = match.groups()
            parts = raw.split(" | ", 2)
            body = parts[2] if len(parts) == 3 else raw
            for sentence in re.split(r"(?<=[.!?])\s+", body):
                sentence = sentence.strip()
                if sentence:
                    overlap = len(query_tokens & set(tokenize(sentence)))
                    candidates.append((overlap, evidence_id, sentence))
        candidates.sort(key=lambda item: item[0], reverse=True)
        best = candidates[0] if candidates else None
        content = json.dumps(
            {
                "answer": f"According to the documentation, {best[2]}" if best else "No supporting evidence was found.",
                "citation_ids": [best[1]] if best else [],
            }
        )
        return GenerationResult(content=content, usage={"provider": "local"})

    def describe_image(self, image: bytes, media_type: str, prompt: str) -> GenerationResult:
        checksum = sha256(image).hexdigest()[:12]
        return GenerationResult(
            content=f"Unenriched visual asset {checksum} ({media_type}).",
            usage={"provider": "local", "billable": False},
        )
