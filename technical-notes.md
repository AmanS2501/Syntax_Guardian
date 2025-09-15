Environment and keys

GROQ_API_KEY for ChatGroq models (e.g., llama-3.3-70b-versatile); set in shell before CLI or in system env for services.

GITHUB_TOKEN for PR comments (optional).

Dependencies

Core: langchain, chromadb, langchain-groq, fastapi, uvicorn, streamlit, requests, git (system).

Notes:

Use retriever.invoke instead of deprecated get_relevant_documents.

Streamlit rendering uses st.markdown and st.json; expect large report.md to load directly.

CLI commands

Index: Builds a Chroma collection from code chunks (function/method/docstring).

Analyze: Runs detectors and outputs reports; includes severity scoring block after per-category section.

Chat: Scopes retrieval by file_path prefix to the analyze_path and generates a cited answer with findings context.

serve-api: Starts FastAPI; /api/analyze accepts JSON with github_url, branch, include/exclude, max_bytes, clone_mode (“clean”/“unique”) and returns report paths and stats.

serve-ui: Opens Streamlit UI to run locally or call API.

pr-comment: Posts a simple Markdown comment to a PR.

Web service details

Cloning: Shallow clone with --depth 1; “clean” mode force-removes an existing target (Windows-safe rmtree with read-only fix); “unique” creates a timestamped folder.

Analysis: Reuses CLI routines; writes to repo_root/reports/report.md and report.json.

Errors: Returns 400 with detail upon clone or analysis failure; Streamlit displays detail.

Severity scoring specifics

P-levels: P0 critical, P1 high, P2 medium, P3 low; repo-level load uses P_WEIGHTS = {P0:10, P1:5, P2:2, P3:0.5}.

Overall score: 100/(1+load) → fewer and less severe findings approach 100.

Per-category scores computed with the same mapping.

Q&A design

Prompt includes:

Retrieved chunks formatted with file:line spans.

Findings context from report.md and report.json to provide extra grounding.

Instruction to cite [path:start-end] for each claim.

ChatGroq model defaults to llama-3.3-70b-versatile, temperature configurable.

Deployment notes

Local: uv run cqia serve-api, uv run cqia serve-ui.

Containers: add Dockerfiles if deploying; ensure git available and network egress to GitHub; mount writeable volume for .cqia-web-work and reports.

Environment configuration: prefer system env for long-running services; for Windows terminals use set VAR=... (cmd) or $env:VAR="..." (PowerShell).

Hardening and extensions

Auth: Private repo clones require configured git credentials or token-based URLs.

Scaling: Offload heavy analysis to a worker queue and stream progress to the UI; back the vector DB with persistent volume.

Advanced: Add AST parsers for precise structure; integrate rankers; add trend tracking by persisting report.json time series.

Testing strategy

Unit: Detectors, chunkers, scoring combinators, prompt formatting.

Integration: Index → Analyze → Report roundtrip on sample repos.

E2E: FastAPI + UI flow using a known public repo.

