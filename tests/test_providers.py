import math
import json
import unittest

from tests.helpers import SRC  # noqa: F401
from kms_agent.providers.local import LocalProvider


class LocalProviderTests(unittest.TestCase):
    def test_embedding_is_normalized_and_deterministic(self):
        provider = LocalProvider(dimension=64)
        first, second = provider.embed(["brake timeout", "brake timeout"])
        self.assertEqual(first, second)
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in first)), 1.0, places=6)

    def test_reranker_prefers_exact_automotive_terms(self):
        provider = LocalProvider(dimension=64)
        scores = provider.rerank(
            "GW-TIME-014 timeout",
            ["Generic gateway overview", "GW-TIME-014 maximum timeout is 100 ms"],
        )
        self.assertGreater(scores[1], scores[0])

    def test_local_generation_selects_most_relevant_evidence_sentence(self):
        provider = LocalProvider(dimension=64)
        result = provider.generate(
            "Ground answers in evidence.",
            "QUESTION: What component performs hybrid search?\n\n"
            "EVIDENCE E1: Design.pptx | Slide 6 | Docling parses files. Qdrant performs semantic and hybrid search.",
        )

        answer = json.loads(result.content)["answer"]
        self.assertIn("Qdrant performs semantic and hybrid search", answer)
        self.assertNotIn("Docling parses files", answer)


if __name__ == "__main__":
    unittest.main()
