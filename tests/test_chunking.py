import unittest

from tests.helpers import SRC  # noqa: F401
from kms_agent.chunking import Chunker
from kms_agent.models import DocumentElement, SourceLocation


class ChunkingTests(unittest.TestCase):
    def test_split_chunks_keep_original_location(self):
        element = DocumentElement.create(
            document_id="timing",
            document_title="Timing.xlsx",
            document_checksum="abc",
            location=SourceLocation(kind="xlsx", label="Sheet 'Timing' | A1:D20"),
            content_type="table",
            text="\n".join(f"row {index} response timeout value" for index in range(20)),
        )

        chunks = Chunker(max_words=20).chunk([element])

        self.assertGreater(len(chunks), 1)
        self.assertEqual({item.location.label for item in chunks}, {"Sheet 'Timing' | A1:D20"})


if __name__ == "__main__":
    unittest.main()

