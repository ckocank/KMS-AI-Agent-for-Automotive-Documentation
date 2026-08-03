# Office KMS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable KMS service that natively ingests PowerPoint and Excel, performs hybrid retrieval, and returns grounded answers through configurable FPT Cloud AI inference.

**Architecture:** Native OOXML extractors emit a common evidence model. Provider and store protocols isolate FPT MaaS and Qdrant from offline test implementations, while a service layer coordinates ingestion, hybrid retrieval, reranking, and citation validation.

**Tech Stack:** Python 3.11+, python-pptx, openpyxl, standard-library HTTP/CLI, Qdrant REST, FPT Cloud AI MaaS REST, unittest, Docker Compose.

---

### Task 1: Domain Model and Configuration

**Files:**
- Create: `src/kms_agent/models.py`
- Create: `src/kms_agent/config.py`
- Test: `tests/test_models.py`

- [ ] Define immutable source locations, document elements, chunks, search hits, citations, and answers as dataclasses.
- [ ] Load model IDs, endpoint paths, dimensions, retrieval limits, and backend choices from environment variables.
- [ ] Verify identifiers are stable for identical document checksum and source location.

```python
def test_element_id_is_stable():
    one = make_element(document_checksum="abc", location="Slide 2 | Shape Title")
    two = make_element(document_checksum="abc", location="Slide 2 | Shape Title")
    assert one.id == two.id
```

Run: `python -m unittest tests.test_models -v`
Expected: all model tests pass.

### Task 2: Native PowerPoint Extraction

**Files:**
- Create: `src/kms_agent/extractors/pptx.py`
- Test: `tests/test_pptx_extractor.py`

- [ ] Extract slide text, grouped shapes, tables, charts, images, and speaker notes with exact locations.
- [ ] Hash image bytes and expose them for selective vision enrichment.
- [ ] Parse unsupported OOXML text as a conservative fallback without duplicating known text.

```python
def test_pptx_locations_include_slide_and_shape(sample_pptx):
    elements = PowerPointExtractor().extract(sample_pptx)
    assert any("Slide 1" in item.location.label and "Title" in item.location.label for item in elements)
```

Run: `python -m unittest tests.test_pptx_extractor -v`
Expected: PowerPoint extraction tests pass.

### Task 3: Native Excel Extraction

**Files:**
- Create: `src/kms_agent/extractors/xlsx.py`
- Test: `tests/test_xlsx_extractor.py`

- [ ] Load formula and cached-value workbook views without executing macros.
- [ ] Emit row/table blocks with repeated headers, units, cell ranges, comments, formulas, merged ranges, and sheet visibility.
- [ ] Emit workbook metadata for defined names, charts, validation rules, and macro presence.

```python
def test_excel_formula_evidence_keeps_cell_and_formula(sample_xlsx):
    elements = ExcelExtractor().extract(sample_xlsx)
    hit = next(item for item in elements if "=B2/C2" in item.text)
    assert "D2" in hit.location.label
```

Run: `python -m unittest tests.test_xlsx_extractor -v`
Expected: Excel extraction tests pass.

### Task 4: Structure-Aware Chunking

**Files:**
- Create: `src/kms_agent/chunking.py`
- Test: `tests/test_chunking.py`

- [ ] Preserve each semantic element when it is below the configured ceiling.
- [ ] Split oversized text at paragraph/row boundaries and retain the original citation location on every child.
- [ ] Prefix chunks with concise document and location context before embedding.

```python
def test_chunk_children_keep_source_location():
    chunks = Chunker(max_words=20).chunk(long_element())
    assert len(chunks) > 1
    assert {chunk.location.label for chunk in chunks} == {"Sheet 'Timing' | A1:D20"}
```

Run: `python -m unittest tests.test_chunking -v`
Expected: chunking tests pass.

### Task 5: Inference Providers

**Files:**
- Create: `src/kms_agent/providers/base.py`
- Create: `src/kms_agent/providers/local.py`
- Create: `src/kms_agent/providers/fpt.py`
- Test: `tests/test_providers.py`

- [ ] Define embedding, reranking, vision, and generation protocols.
- [ ] Implement deterministic local embeddings and extractive answers for zero-cost tests.
- [ ] Implement bearer-authenticated FPT calls for `/embeddings`, `/rerank`, and `/chat/completions`, with configurable paths and model IDs.
- [ ] Parse FPT usage metadata and validate malformed responses.

```python
def test_local_embedding_is_normalized():
    vector = LocalProvider(dimension=64).embed(["brake timeout"])[0]
    assert abs(sum(value * value for value in vector) - 1.0) < 1e-6
```

Run: `python -m unittest tests.test_providers -v`
Expected: provider tests pass without network access.

### Task 6: Hybrid Stores and Retrieval

**Files:**
- Create: `src/kms_agent/stores/base.py`
- Create: `src/kms_agent/stores/memory.py`
- Create: `src/kms_agent/stores/qdrant.py`
- Create: `src/kms_agent/retrieval.py`
- Test: `tests/test_retrieval.py`

- [ ] Generate sparse term vectors and persist dense/sparse named vectors.
- [ ] Implement Qdrant collection creation, upsert, deletion by document, and RRF query through REST.
- [ ] Implement equivalent in-memory fusion for deterministic tests.
- [ ] Rerank fused candidates and retain an adaptive evidence set.

```python
def test_hybrid_search_finds_exact_requirement(memory_service):
    hits = memory_service.search("GW-TIME-014 response time", limit=3)
    assert hits[0].chunk.metadata["requirement_id"] == "GW-TIME-014"
```

Run: `python -m unittest tests.test_retrieval -v`
Expected: hybrid retrieval tests pass.

### Task 7: Grounded Service, CLI, and HTTP API

**Files:**
- Create: `src/kms_agent/service.py`
- Create: `src/kms_agent/cli.py`
- Create: `src/kms_agent/api.py`
- Test: `tests/test_service.py`

- [ ] Coordinate file routing, enrichment, chunking, embedding, and storage.
- [ ] Construct a bounded evidence prompt and reject model citations not present in retrieved evidence.
- [ ] Compute confidence from retrieval, reranking, agreement, and citation completeness.
- [ ] Expose health, ingestion, document-list, and query operations through CLI and JSON HTTP routes.

```python
def test_answer_contains_traceable_excel_evidence(memory_service, sample_xlsx):
    memory_service.ingest(sample_xlsx)
    answer = memory_service.answer("What is the maximum response time?")
    assert answer.citations
    assert "Sheet" in answer.citations[0].location
```

Run: `python -m unittest tests.test_service -v`
Expected: grounded service tests pass.

### Task 8: Packaging and End-to-End Verification

**Files:**
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `docker-compose.yml`
- Create: `README.md`
- Create: `tests/test_end_to_end.py`

- [ ] Document local mode and FPT/Qdrant mode with exact commands.
- [ ] Add a Qdrant Compose service with persistent storage and a health check.
- [ ] Generate fixture workbooks/presentations in test setup and run the complete ingestion-to-answer flow.
- [ ] Start the HTTP service and verify `/health`, `/v1/documents/ingest`, and `/v1/query`.

```python
def test_offline_end_to_end(service, sample_pptx, sample_xlsx):
    service.ingest(sample_pptx)
    service.ingest(sample_xlsx)
    result = service.answer("Which requirement specifies the gateway timeout?")
    assert result.status in {"grounded", "insufficient_evidence"}
    assert all(citation.evidence for citation in result.citations)
```

Run: `python -m unittest discover -s tests -v`
Expected: all tests pass with no external services or paid inference.

