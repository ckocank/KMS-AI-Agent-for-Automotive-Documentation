from __future__ import annotations

import argparse
import json

from kms_agent.api import main as serve
from kms_agent.service import KMSService


def build_parser():
    parser = argparse.ArgumentParser(description="Automotive Office KMS Agent")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Ingest one PowerPoint or Excel file")
    ingest.add_argument("path")

    query = commands.add_parser("query", help="Query documents already held by the configured store")
    query.add_argument("question")

    ask = commands.add_parser("ask", help="Ingest files and answer in one process")
    ask.add_argument("question")
    ask.add_argument("--file", action="append", required=True, dest="files")

    commands.add_parser("list", help="List indexed documents")

    server = commands.add_parser("serve", help="Start the JSON HTTP API")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8088)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        return serve(["--host", args.host, "--port", str(args.port)])
    service = KMSService()
    if args.command == "ingest":
        output = service.ingest(args.path).to_dict()
    elif args.command == "query":
        output = service.answer(args.question).to_dict()
    elif args.command == "ask":
        ingested = [service.ingest(path).to_dict() for path in args.files]
        output = {"ingested": ingested, "result": service.answer(args.question).to_dict()}
    else:
        output = {"documents": service.list_documents()}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

