import unittest

from tests.helpers import SRC  # noqa: F401
from kms_agent.models import DocumentElement, SourceLocation


class ModelTests(unittest.TestCase):
    def test_element_id_is_stable_for_same_source(self):
        location = SourceLocation(kind="pptx", label="Slide 2 | Shape Title")
        first = DocumentElement.create(
            document_id="design",
            document_title="Design.pptx",
            document_checksum="abc",
            location=location,
            content_type="text",
            text="Gateway timeout",
        )
        second = DocumentElement.create(
            document_id="design",
            document_title="Design.pptx",
            document_checksum="abc",
            location=location,
            content_type="text",
            text="Gateway timeout",
        )
        self.assertEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()

