import unittest

from tests.helpers import SRC  # noqa: F401
from kms_agent.models import Chunk, SourceLocation
from kms_agent.providers.local import LocalProvider
from kms_agent.retrieval import RetrievalEngine
from kms_agent.stores.memory import MemoryStore


def make_chunk(chunk_id: str, text: str, requirement_id: str = "") -> Chunk:
    return Chunk(
        id=chunk_id,
        element_id=f"element-{chunk_id}",
        document_id="gateway",
        document_title="Gateway Requirements.xlsx",
        document_checksum="abc",
        location=SourceLocation(kind="xlsx", label="Sheet 'Timing' | A2:C2"),
        content_type="row",
        text=text,
        metadata={"requirement_id": requirement_id},
    )


class RetrievalTests(unittest.TestCase):
    def test_hybrid_search_prioritizes_exact_requirement(self):
        provider = LocalProvider(dimension=64)
        store = MemoryStore()
        engine = RetrievalEngine(provider, store, candidate_limit=10, evidence_limit=3)
        engine.index(
            [
                make_chunk("a", "General vehicle gateway architecture"),
                make_chunk("b", "GW-TIME-014 maximum response time is 100 ms", "GW-TIME-014"),
                make_chunk("c", "Brake ECU wake-up timing is 250 ms"),
            ]
        )

        hits = engine.search("What does GW-TIME-014 specify for response time?")

        self.assertEqual(hits[0].chunk.metadata["requirement_id"], "GW-TIME-014")
        self.assertGreater(hits[0].final_score, hits[-1].final_score)


if __name__ == "__main__":
    unittest.main()

