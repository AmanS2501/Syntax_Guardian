# Syntax Guardian — Architecture

> High-level architecture and design notes for the Code Quality Intelligence Agent ("Syntax Guardian").

---

## 1. Purpose & goals

* Provide an automated, developer-friendly code-quality analysis agent that:

  * Scans repositories (Python + JS/TS), detects security, complexity, duplication, performance, testing and documentation issues.
  * Produces deterministic, prioritized reports (report.md + report.json).
  * Supports repo-scoped Q\&A using RAG with file\:line citations.
  * Runs locally via CLI and optionally as a web service (FastAPI + Streamlit UI).

## 2. High-level components

```
  +-----------+      +-------------+      +-------------+      +-----------+
  |  Ingest   | ---> |  Parsers &  | ---> | Detectors & | ---> | Reporting |
  | (git / FS)|      |  Chunkers   |      |  Analysis   |      |  (MD/JSON)|
  +-----------+      +-------------+      +-------------+      +-----------+
                             |                    |
                             v                    v
                         +--------+           +-------------+
                         | RAG    | <-------- | Severity &  |
                         | Index  |           | Hotspoting  |
                         +--------+           +-------------+
                              |
                              v
                          +-------+
                          | Q&A   |
                          | Chat  |
                          +-------+
```

## 3. Detailed component descriptions

### 3.1 Ingestion

* Responsibilities: clone or use a local path, enumerate files, apply include/exclude globs, enforce per-file size caps.
* Key modules: `cqia.web.clone.shallow_clone` (web path), `cqia.ingestion.walker.walk_repo`.
* Behaviour: supports shallow clone for GitHub URLs and local paths; protects against large files via `max_bytes` filter.

### 3.2 Parsers & IR

* Parse source files into a light AST / IR that captures modules and function-level spans.
* Language-specific parsers: `cqia.parsing.python_parser.parse_python` and `cqia.parsing.ts_parser.parse_js_ts`.
* Output: `ModuleIR` and `FunctionIR` structures fed to detectors.

### 3.3 Detectors (quality checks)

* Implemented detectors (examples):

  * **Complexity** (`cqia.analysis.detectors.complexity`) — cyclomatic-style checks on `FunctionIR`.
  * **Duplication** (`cqia.analysis.detectors.duplication`) — token-shingling + Jaccard for near-duplicate functions.
  * **Security** (`cqia.analysis.detectors.security`) — Python AST checks (eval/exec, yaml.load, subprocess shell=True) and JS heuristics (eval, child\_process.exec).
  * **Performance** (`cqia.analysis.detectors.performance`) — AST visitor finds IO/requests/string concat in loops.
  * **Docs & Testing** (`cqia.analysis.detectors.testing_docs`) — missing docstrings and test-gap heuristics (pytest file patterns).
* Node: detectors operate at function/module granularity so findings can reference exact `file:start-end` spans.

### 3.4 Analysis Orchestration

* Orchestrator: `cqia.analysis.runner.analyze_repository` and `run_analysis` compose parsers, detectors, dependency extraction and hotspoting.
* Dependency graph: edges assembled into a NetworkX DiGraph (`cqia.analysis.dependency_graph`); metrics (fan-in/out, cycles) are computed and serialized.
* Hotspot scoring combines complexity sums and fan-in to surface files with high maintenance risk.

### 3.5 Severity & Scoring

* Severity system: numeric scores -> P0/P1/P2/P3 mapping (`cqia.analysis.severity`).
* Weights configurable via `presets/rules.yaml`; override via `override_weights`.
* Scoring functions available per-category (security, complexity, duplication, performance, testing, documentation).

### 3.6 Reporting

* Two primary artifacts: `report.md` (human readable) and `report.json` (machine readable).
* Report writer: `cqia.reporting.markdown` handles table-of-contents, summary, per-category sections, and writes `reports/report.md`.
* Exporters: `cqia.reporting.exporters` produces `report.json` and dependency graph exports.

### 3.7 RAG / Retrieval & Q\&A

* Chunking: `cqia.rag.chunking.ast_chunker.ASTFunctionChunker` produces function/docstring chunks.
* Embeddings & vector store: `cqia.rag.embeddings.vector_store.CodeEmbeddingManager` (Chroma or pluggable store).
* Retriever: `cqia.rag.retrieval.smart_retriever.FileAwareRetriever` supports repo scoping and name-boosting.
* Q\&A chain: `cqia.qa.chain.build_chatgroq_llm` + `answer_with_citations` glue LLM answers with retrieved chunks and findings context.
* Deterministic chat path exists (graph chat node) which returns top matches without an LLM; full LLM path uses Groq/ChatGroq.

### 3.8 CLI, Graph & Web layers

* CLI: typed via Typer (`cqia.cli.main`), commands include `index`, `analyze`, `chat`, `graph-analyze`, `serve-api`, `serve-ui`.
* Agent graph: a small LangGraph state machine (`cqia.agent.graph.flow` + `nodes`) orchestrates guardrails → analyze/chat nodes for reproducible runs.
* Web API: FastAPI service (`cqia.web.service`) exposing an `/api/analyze` endpoint.
* UI: Streamlit app (`cqia.web.ui_app`) which calls the API (or runs local analysis) for interactive usage.

## 4. Data flow (sequence)

1. User invokes CLI / UI or calls API with a repo path or GitHub URL.
2. Repo is cloned or local path is used; `walk_repo` enumerates files (include/exclude globs applied).
3. Parsers create IR objects (`ModuleIR`, `FunctionIR`).
4. Detectors run over IRs and raw file text producing findings (with file spans).
5. `run_analysis` aggregates results, runs dependency analysis, produces hotspots and scores.
6. `report.md` and `report.json` are written; optional exported dependency JSON / graph images are produced.
7. (Optional) AST chunker + embeddings index function/docstring chunks for RAG.
8. Q\&A queries use FileAwareRetriever to retrieve scoped chunks and `answer_with_citations` to synthesize an answer including findings.

## 5. Key design trade-offs & decisions

* **Rule-driven detectors vs heavy AST/Tree-sitter**: current detectors use AST for Python and light heuristics for JS/TS. This keeps implementation simpler and reduces dependency surface, while still allowing precise location-aware findings. (future: swap to tree-sitter for JS/TS).
* **Shallow clone & size caps**: prevents runaway analyses on large repos and keeps UX fast for reviewers.
* **Deterministic analysis + optional LLM**: core report generation is deterministic so reports are reproducible. LLM only used for conversational answers (and is optional via config).
* **Scoring tuned via presets**: `presets/rules.yaml` centralizes thresholds/weights for reproducible severity computation.

## 6. File ↔ component mapping (important modules)

* Ingestion / clone / walker: `cqia.web.clone`, `cqia.ingestion.walker`.
* Parsers / IR: `cqia.parsing.python_parser`, `cqia.parsing.ts_parser`, `cqia.parsing.ir`.
* Detectors: `cqia.analysis.detectors.*` (complexity, duplication, security, performance, testing\_docs).
* Runner / Orchestration: `cqia.analysis.runner`, `cqia.agent.graph.flow`, `cqia.agent.graph.nodes`.
* Severity & scoring: `cqia.analysis.severity` and `presets/rules.yaml`.
* Reporting & exporters: `cqia.reporting.markdown`, `cqia.reporting.exporters`.
* RAG & embeddings: `cqia.rag.chunking.ast_chunker`, `cqia.rag.embeddings.vector_store`, `cqia.rag.retrieval.smart_retriever`.
* CLI & web UI: `cqia.cli.main`, `cqia.web.service`, `cqia.web.ui_app`.

## 7. Operational concerns & deployment

* **Local**: packaged with `pip install -e .` and invoked via `uv run cqia <command>` (Typer CLI).
* **API**: FastAPI served via Uvicorn; run `uv run cqia serve-api` for local hosting.
* **UI**: Streamlit app connects to API or performs local runs; run `uv run cqia serve-ui`.
* **Secrets**: LLM API keys (Groq) are environment variables (e.g., `GROQ_API_KEY`). Avoid committing keys.

## 8. Scalability & next steps

* **Indexing large repos**: introduce chunk batching, persistent vector DB sharding and RAG hybrid retrieval (coarse + fine).
* **AST/Treesitter for JS/TS**: replace heuristics with accurate AST-based detectors for JS/TS.
* **CI integration**: add a GitHub App / PR webhook to post findings on PRs and annotate lines.
* **Trend dashboard**: persist `report.json` series and visualize scores over time per category.

## 9. How to run (quick reference)

```bash
# install
python -m venv .venv && source .venv/bin/activate
pip install -e .

# analyze a local path
uv run cqia analyze /path/to/repo

# chat / Q&A
export GROQ_API_KEY=sk_...
uv run cqia chat /path/to/repo --question "How is url_for implemented?"

# serve web UI
uv run cqia serve-api
uv run cqia serve-ui
# UI: http://localhost:8501  API: http://127.0.0.1:8000
```

## 10. Notes & references

* This architecture doc was created from the project writeup and source tree present in the attachments (`SYNTAX GAURDIAN` overview + source snippets).

---
