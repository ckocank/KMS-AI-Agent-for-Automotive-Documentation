# Office KMS Design

## Objective

Build a grounded automotive knowledge-management service that ingests PowerPoint and Excel files without flattening away their structure. Answers must be supported by exact slide, shape, sheet, table, cell, and formula citations. FPT Cloud AI MaaS provides paid embedding, reranking, vision, and answer generation; native parsing and content-addressed caching minimize inference usage.

## Scope

- PowerPoint: slide text, groups, tables, charts, speaker notes, comments where exposed by OOXML, images, diagrams, and embedded workbook references.
- Excel: visible and hidden sheets, tables, cells, formulas, cached values, comments, merged ranges, named ranges, charts, conditional-formatting metadata, and macro presence without macro execution.
- Search: dense and sparse retrieval, reciprocal-rank fusion, reranking, parent-context expansion, security metadata, and grounded answer generation.
- Evidence: direct snippets and source locations with document checksum and version metadata.

## Architecture

1. A file router selects the native PowerPoint or Excel extractor.
2. Extractors emit normalized `DocumentElement` records with stable source locations.
3. Selective visual enrichment sends only unsupported images or diagrams to the configured vision provider.
4. The chunker preserves semantic boundaries and applies a token ceiling only to oversized elements.
5. Dense embeddings and deterministic sparse vectors are stored in Qdrant named vectors.
6. Queries run dense and sparse prefetches with reciprocal-rank fusion, then rerank the candidates.
7. The answer service supplies only retrieved evidence to the generation model and validates returned citation identifiers.
8. Offline providers and an in-memory store support deterministic development and tests without cloud cost.

## Citation Rules

- PowerPoint locations include section when available, slide number, shape name, table coordinates, chart name, or speaker-notes marker.
- Excel locations include sheet name, cell or range, table name when available, and the formula for formula evidence.
- Every citation includes document title, content checksum, element identifier, location, and verbatim evidence.
- The service returns `insufficient_evidence` when no evidence clears the configured relevance threshold.

## Cost Controls

- Native OOXML extraction is always attempted before vision inference.
- Images are identified by SHA-256 and enriched once.
- Unchanged document elements retain stable identifiers and embeddings.
- Embeddings are batched, retrieval is capped, reranking receives only top candidates, and generation receives an adaptive evidence set.
- The local provider is the default; FPT calls require explicit configuration and an API key.
- Each FPT response captures available token-usage metadata for future cost reporting.

## Security and Failure Behavior

- Uploaded paths are validated and file extensions are allowlisted.
- Macros are never executed.
- Password-protected or corrupt files fail with an explicit ingestion status.
- FPT credentials are read only from environment variables.
- Model failures fall back only when configured; grounded-answer rules remain active.
- Unsupported visual objects remain searchable through their native text and metadata and are marked for enrichment.

## Acceptance Criteria

- Ingest a `.pptx` and return slide/shape/note evidence.
- Ingest a `.xlsx` and return sheet/cell/formula evidence.
- Retrieve evidence using combined semantic and keyword signals.
- Return JSON containing answer, citations, textual evidence, confidence, and grounded status.
- Run all tests without FPT credentials or a Qdrant process.
- Run against Qdrant and FPT Cloud AI by changing environment settings only.

