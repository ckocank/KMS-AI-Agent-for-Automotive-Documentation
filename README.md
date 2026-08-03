# Automotive Office KMS Agent

A grounded knowledge-management service for automotive PowerPoint and Excel documentation. It preserves native Office structure, performs dense and sparse hybrid search, reranks evidence, and returns answers with exact source snippets and locations.

## What It Indexes

PowerPoint ingestion extracts slide text, grouped shapes, tables, chart series, speaker notes, and embedded images. Image bytes are sent to vision inference only when FPT mode and a vision model are explicitly enabled.

Excel ingestion extracts visible and hidden sheets, rows, formulas, cached formula results, comments, merged ranges, named tables, named ranges, validation metadata, conditional formatting metadata, and macro presence. Macros are never executed.

Example evidence locations:

- `Gateway Design.pptx, Slide 9 | Speaker Notes`
- `ASIL Traceability.xlsx, Sheet 'Safety Goals' | C12:H16`
- `Coverage.xlsx, Sheet 'Summary' | G31`, including the formula and cached value

## Architecture

```text
PPTX/XLSX -> Native OOXML extraction -> Selective FPT vision enrichment
          -> Structure-aware chunks -> FPT embeddings + sparse vectors
          -> Qdrant dense/sparse RRF -> FPT reranker -> Grounded generation
          -> Answer + exact citations + evidence + computed confidence
```

Local mode uses deterministic embeddings, reranking, and extractive generation with an in-memory store. It is intended for development and automated verification and makes no paid API calls.

## Run Locally

Python 3.11 or later is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
office-kms serve --host 127.0.0.1 --port 8088
```

Without installing the package, set `PYTHONPATH` and run the module directly:

```powershell
$env:PYTHONPATH="$PWD\src"
python -m kms_agent.api --host 127.0.0.1 --port 8088
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8088/health
```

Ingest a file already available to the service:

```powershell
$body = @{ path = "C:\docs\Gateway Requirements.xlsx" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8088/v1/documents/ingest -ContentType application/json -Body $body
```

Ask a grounded question:

```powershell
$body = @{ question = "What does GW-TIME-014 specify?" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8088/v1/query -ContentType application/json -Body $body
```

For a one-process CLI demonstration:

```powershell
office-kms ask "What is the gateway timeout?" --file ".\Gateway Design.pptx" --file ".\Gateway Requirements.xlsx"
```

## Enable Qdrant and FPT Cloud AI

1. Start Qdrant:

```powershell
docker compose up -d qdrant
```

2. Copy the relevant settings from `.env.example` into your environment or secret manager.
3. Set `KMS_PROVIDER=fpt`, `KMS_STORE=qdrant`, and `FPT_API_KEY`.
4. Set model IDs exactly as displayed for your project in the FPT AI Marketplace. Confirm the embedding dimension before creating the Qdrant collection.
5. Start the API.

The default FPT base URL is `https://mkp-api.fptcloud.com`. Endpoint paths are configurable because model APIs and project configurations can differ.

Official references:

- [FPT AI Inference quickstart](https://ai-docs.fptcloud.com/ai-marketplace/ai-inference/quickstart)
- [FPT MaaS serverless pricing](https://ai.fptcloud.com/pricing/maas?tab=serverless)
- [FPT multimodal API example](https://ai-docs.fptcloud.com/api-reference/ai-marketplace/api-reference/api-integration-multimodal-model-text-md)

## Cost Controls

- Office text, formulas, and chart data are parsed locally.
- Vision calls are skipped unless a visual model is configured.
- Stable content hashes prevent duplicate points for unchanged source elements.
- Retrieval is capped before reranking, and only the final evidence set reaches generation.
- The local profile validates ingestion and retrieval without inference cost.
- FPT token usage returned by generation and vision endpoints is included in service metadata.
- Serverless MaaS avoids continuously allocated GPU infrastructure and follows the provider's pay-per-use billing model.

## API

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Provider/store readiness summary |
| `GET` | `/v1/documents` | List indexed documents |
| `POST` | `/v1/documents/ingest` | Ingest by server path or base64 file content |
| `POST` | `/v1/query` | Return grounded answer JSON |
| `DELETE` | `/v1/documents/{id}` | Remove one document version |

An ingestion body may contain `path`, or `filename` plus `content_base64`. In production, prefer content upload or a controlled document connector over unrestricted server paths.

## Test

```powershell
$env:PYTHONPATH="$PWD\src"
python -m unittest discover -s tests -v
```

The test suite creates real `.pptx` and `.xlsx` fixtures and validates extraction, chunking, hybrid retrieval, citations, confidence status, and the HTTP API without external services.

