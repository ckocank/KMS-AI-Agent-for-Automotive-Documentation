import json
import base64
import io
import threading
import unittest
from urllib.request import Request, urlopen

from openpyxl import Workbook

from tests.helpers import SRC  # noqa: F401
from kms_agent.api import create_server
from kms_agent.config import Settings
from kms_agent.service import KMSService


class ApiTests(unittest.TestCase):
    def test_health_and_empty_query_routes(self):
        service = KMSService(settings=Settings(embedding_dimension=64))
        server = create_server(service, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            with urlopen(f"http://{host}:{port}/health") as response:
                health = json.loads(response.read())
            request = Request(
                f"http://{host}:{port}/v1/query",
                data=json.dumps({"question": "What is the timeout?"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request) as response:
                answer = json.loads(response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(health["status"], "ok")
        self.assertEqual(answer["status"], "insufficient_evidence")

    def test_base64_upload_preserves_original_filename(self):
        stream = io.BytesIO()
        book = Workbook()
        book.active["A1"] = "GW-TIME-014"
        book.save(stream)
        service = KMSService(settings=Settings(embedding_dimension=64))
        server = create_server(service, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/v1/documents/ingest",
            data=json.dumps(
                {
                    "filename": "Gateway Requirements.xlsx",
                    "content_base64": base64.b64encode(stream.getvalue()).decode(),
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request) as response:
                result = json.loads(response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(result["document_title"], "Gateway Requirements.xlsx")


if __name__ == "__main__":
    unittest.main()
