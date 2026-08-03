from __future__ import annotations

import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from urllib.parse import unquote, urlparse

from kms_agent.service import KMSService


MAX_REQUEST_BYTES = 64 * 1024 * 1024


def create_server(service: KMSService, host: str = "127.0.0.1", port: int = 8088) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, {"status": "ok", "provider": service.settings.provider, "store": service.settings.store})
            elif path == "/v1/documents":
                self._send(200, {"documents": service.list_documents()})
            else:
                self._send(404, {"error": "Route not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                payload = self._json_body()
                if path == "/v1/query":
                    self._send(200, service.answer(str(payload.get("question", ""))).to_dict())
                elif path == "/v1/documents/ingest":
                    result = self._ingest_payload(payload)
                    self._send(201, result.to_dict())
                else:
                    self._send(404, {"error": "Route not found"})
            except (ValueError, FileNotFoundError) as exc:
                self._send(400, {"error": str(exc)})
            except Exception as exc:
                self._send(500, {"error": str(exc)})

        def do_DELETE(self):
            path = urlparse(self.path).path
            prefix = "/v1/documents/"
            if not path.startswith(prefix) or len(path) == len(prefix):
                self._send(404, {"error": "Route not found"})
                return
            service.delete_document(unquote(path[len(prefix) :]))
            self._send(200, {"status": "deleted"})

        def _ingest_payload(self, payload):
            if payload.get("path"):
                return service.ingest(payload["path"])
            filename = Path(str(payload.get("filename", ""))).name
            encoded = payload.get("content_base64")
            if not filename or not encoded:
                raise ValueError("Provide either path, or filename with content_base64")
            content = base64.b64decode(encoded, validate=True)
            with tempfile.TemporaryDirectory() as folder:
                temporary = Path(folder) / filename
                temporary.write_bytes(content)
                return service.ingest(temporary)

        def _json_body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            if length > MAX_REQUEST_BYTES:
                raise ValueError("Request body exceeds 64 MB")
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Request body must be valid JSON") from exc

        def _send(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return ThreadingHTTPServer((host, port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Automotive Office KMS HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args(argv)
    service = KMSService()
    server = create_server(service, args.host, args.port)
    print(f"KMS API listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
