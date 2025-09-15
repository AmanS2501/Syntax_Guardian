System view

Components:

Ingestion: Walks repo, matches files by include/exclude, normalizes paths, extracts metadata (language, line spans, file stems).

Chunking/Embeddings: Produces function/method/docstring chunks and embeddings into Chroma with file:line metadata.

Detectors: Rules and heuristics for categories; results normalized into ScoredFinding with id, category, severity, score, file, line range, why, and fix.

Severity scoring: Aggregates findings into severity counts and weighted load; outputs Overall Quality Score and per-category scores.

Reporting: Markdown sections (summary, top issues, per-category, severity scoring, details, dependencies) and JSON payload with scoring fields and dependency metrics.

Q&A: Retriever filters results to the requested scope path, finds k relevant chunks, formats them with file:line metadata, appends report.md/JSON slices, and prompts ChatGroq to produce cited answers.

Web/API: FastAPI exposes POST /api/analyze → clone, analyze, return report paths and basic stats; Streamlit triggers API or runs locally and renders report outputs.

PR integration: Minimal client to post a summary comment to a PR (issues or review comments endpoint).

Key decisions

Chroma + sentence/func-level chunking for speed and simple deployment.

Citations rely on exact file:line metadata to ensure traceability.

Smooth-decay scoring (100/(1+load)) chosen to penalize critical counts more than many low severities while remaining explainable.

Windows-first path normalization and robust directory deletion for clean re-clones in web mode.

Assumptions

Source language combos remain Python/JS/TS; adding others requires loader and chunker extension.

Deterministic detectors; LLM is not used to “hallucinate” findings; LLM is used for Q&A synthesis only.
