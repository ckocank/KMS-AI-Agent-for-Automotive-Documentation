from __future__ import annotations

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from kms_agent.providers.base import GenerationResult


class FPTCloudError(RuntimeError):
    pass


class FPTCloudProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        embedding_model: str,
        rerank_model: str,
        chat_model: str,
        vision_model: str = "",
        dimension: int = 1024,
        embedding_path: str = "/embeddings",
        rerank_path: str = "/rerank",
        chat_path: str = "/chat/completions",
        timeout: int = 90,
    ):
        if not api_key:
            raise ValueError("FPT_API_KEY is required when KMS_PROVIDER=fpt")
        if not chat_model:
            raise ValueError("FPT_CHAT_MODEL is required when KMS_PROVIDER=fpt")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.rerank_model = rerank_model
        self.chat_model = chat_model
        self.vision_model = vision_model or chat_model
        self.dimension = dimension
        self.embedding_path = embedding_path
        self.rerank_path = rerank_path
        self.chat_path = chat_path
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._post(self.embedding_path, {"model": self.embedding_model, "input": texts})
        data = sorted(response.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [item["embedding"] for item in data]
        if len(vectors) != len(texts):
            raise FPTCloudError("FPT embedding response did not contain one vector per input")
        if vectors:
            self.dimension = len(vectors[0])
        return vectors

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        response = self._post(
            self.rerank_path,
            {"model": self.rerank_model, "query": query, "documents": documents, "top_n": len(documents)},
        )
        results = response.get("results") or response.get("data") or []
        scores = [float("-inf")] * len(documents)
        for position, item in enumerate(results):
            index = int(item.get("index", position))
            scores[index] = float(item.get("relevance_score", item.get("score", 0.0)))
        if not results:
            raise FPTCloudError("FPT rerank response did not contain scores")
        return scores

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult:
        response = self._post(
            self.chat_path,
            {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "stream": False,
            },
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise FPTCloudError("FPT chat response did not contain message content") from exc
        return GenerationResult(content=content, usage=response.get("usage", {}))

    def describe_image(self, image: bytes, media_type: str, prompt: str) -> GenerationResult:
        encoded = base64.b64encode(image).decode("ascii")
        response = self._post(
            self.chat_path,
            {
                "model": self.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}},
                        ],
                    }
                ],
                "temperature": 0.0,
                "stream": False,
            },
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise FPTCloudError("FPT vision response did not contain message content") from exc
        return GenerationResult(content=content, usage=response.get("usage", {}))

    def _post(self, path: str, payload: dict) -> dict:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise FPTCloudError(f"FPT API returned HTTP {exc.code}: {body[:500]}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise FPTCloudError(f"FPT API request failed: {exc}") from exc

