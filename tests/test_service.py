import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from tests.helpers import SRC  # noqa: F401
from kms_agent.config import Settings
from kms_agent.providers.local import LocalProvider
from kms_agent.service import KMSService


def create_requirements_book(path: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "Timing"
    sheet.append(["Requirement ID", "Description", "Limit"])
    sheet.append(["GW-TIME-014", "Maximum gateway response time", "100 ms"])
    book.save(path)


class ServiceTests(unittest.TestCase):
    def test_excel_answer_contains_traceable_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Gateway Requirements.xlsx"
            create_requirements_book(path)
            service = KMSService(settings=Settings(embedding_dimension=64, minimum_score=0.05))
            result = service.ingest(path)
            answer = service.answer("What does GW-TIME-014 specify?")

        self.assertGreater(result.chunks, 0)
        self.assertEqual(answer.status, "grounded")
        self.assertTrue(answer.citations)
        self.assertIn("Sheet 'Timing'", answer.citations[0].location)
        self.assertIn("GW-TIME-014", answer.citations[0].evidence)

    def test_no_documents_returns_insufficient_evidence(self):
        service = KMSService(settings=Settings(embedding_dimension=64))

        answer = service.answer("What is the gateway timeout?")

        self.assertEqual(answer.status, "insufficient_evidence")
        self.assertEqual(answer.citations, [])

    def test_rejects_unsupported_file_type(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "notes.txt"
            path.write_text("not an Office document", encoding="utf-8")
            service = KMSService(settings=Settings(embedding_dimension=64))

            with self.assertRaisesRegex(ValueError, "Unsupported file type"):
                service.ingest(path)

    def test_identical_document_is_not_embedded_twice(self):
        class CountingProvider(LocalProvider):
            def __init__(self):
                super().__init__(dimension=64)
                self.embedded_batches = 0

            def embed(self, texts):
                self.embedded_batches += 1
                return super().embed(texts)

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Gateway Requirements.xlsx"
            create_requirements_book(path)
            provider = CountingProvider()
            service = KMSService(settings=Settings(embedding_dimension=64), provider=provider)
            first = service.ingest(path)
            second = service.ingest(path)

        self.assertEqual(provider.embedded_batches, 1)
        self.assertFalse(first.unchanged)
        self.assertTrue(second.unchanged)


if __name__ == "__main__":
    unittest.main()
