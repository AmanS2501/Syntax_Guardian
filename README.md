Project: Code Quality Intelligence Agent (CQIA)

Overview

CQIA analyzes code repositories, detects quality issues across multiple categories, and produces an actionable report (Markdown + JSON) with severity scoring, dependency metrics, and targeted fix suggestions.

Features:

Multi-language repo scanning (Python, JS/TS) with include/exclude globs and size caps.

Findings across security, complexity, duplication, performance, documentation, testing.

Report generation: report.md + report.json; severity scoring with overall score and per-category scores.

Repo-scoped Q&A via ChatGroq (Llama 3.x): retrieval from Chroma index, file:line citations, detector rationale, and findings context (report.md/JSON) in the prompt.

Lightweight web UI (Streamlit) and FastAPI endpoint to accept a GitHub URL, shallow clone, analyze, and render the report.

Optional GitHub PR comment stub to post summarized findings to a PR.

Quick start

Prereqs: Python 3.10+, git, uv or pip, Node (optional for repo targets).

Environment:

GROQ_API_KEY=sk_... (ChatGroq)

Optional: GITHUB_TOKEN=ghp_... (for PR comments)

Install:

uv venv && uv pip install -e .

CLI usage:

Index repo: uv run cqia index <path>

Analyze: uv run cqia analyze <path>

Q&A (scoped): uv run cqia chat <path> --question "How is X implemented?"

Serve API: uv run cqia serve-api

Serve UI: uv run cqia serve-ui

Web mode:

Start API: uv run cqia serve-api

Start UI: uv run cqia serve-ui (select “Call FastAPI” and paste GitHub URL)

Repository structure (key folders)

cqia/cli: typer CLI entry points (index, analyze, chat, serve-api, serve-ui, pr-comment).

cqia/ingestion: repository walker and glob filtering.

cqia/rag: chunking, embeddings, vector store (Chroma), smart retriever.

cqia/analysis: detectors, severity, severity_score, and reporting harness.

cqia/reporting: markdown builders and exporters to JSON and dependency graphs.

cqia/qa: prompting and ChatGroq chain for cited answers.

cqia/web: FastAPI service, clone utilities, Streamlit UI.

Severity scoring

Overall Code Quality Score in 0–100 using a smooth-decay mapping of weighted findings (P0–P3 or category-level weights), plus per-category scores. Appears in report.md and report.json.

Citations and Q&A

Retrieval grounded answers with inline citations [file:line-start–line-end], using metadata from chunking and a prompt that incorporates findings context. Requires GROQ_API_KEY.

License and credits

Built with LangChain, Chroma, FastAPI, Streamlit, and Groq’s ChatGroq integration.