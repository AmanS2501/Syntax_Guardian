from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from cqia.utils.deps import safe_dep_metrics as _safe_dep_metrics

from cqia.ingestion.walker import walk_repo
from cqia.presets import load_rules
from cqia.analysis.severity import override_weights
from cqia.analysis.runner import run_analysis
from cqia.reporting.markdown import (
    write_basic_report,
    append_top_issues,
    append_per_category_summary,
    append_issue_details,
    append_findings,
    append_dependencies,
    append_dependency_outline,
)
from cqia.reporting.exporters import export_dependency_graph, export_json_report

from cqia.rag.chunking.ast_chunker import ASTFunctionChunker
from cqia.rag.embeddings.vector_store import CodeEmbeddingManager
from cqia.rag.retrieval.smart_retriever import FileAwareRetriever

# Guardrails: route based on state.mode and inputs
def guardrails(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    mode = (state.get("mode") or "").lower()
    updates: Dict[str, Any] = {"steps": (state.get("steps") or []) + ["guardrails"]}

    if mode == "analyze":
        if Path(state.get("path", "")).exists():
            updates["next_action"] = "run_analyze"
        else:
            updates["next_action"] = "end"
            updates["messages"] = (state.get("messages") or []) + [
                AIMessage(content="Provided path not found; cannot analyze.")
            ]
    elif mode == "chat":
        if state.get("question"):
            updates["next_action"] = "run_chat"
        else:
            updates["next_action"] = "end"
            updates["messages"] = (state.get("messages") or []) + [
                AIMessage(content="No question provided for chat mode.")
            ]
    else:
        updates["next_action"] = "end"
        updates["messages"] = (state.get("messages") or []) + [
            AIMessage(content="Unsupported mode. Use 'analyze' or 'chat'.")
        ]
    return updates

# Analysis node: runs detectors and writes artifacts deterministically
def analyze_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    root = Path(state["path"])
    include = state.get("include") or ["**/*.py", "**/*.js", "**/*.ts"]
    exclude = state.get("exclude") or [
        ".git/**", "**/.git/**", "**/.venv/**", "**/venv/**", "**/env/**",
        "**/__pycache__/**", "**/node_modules/**", "**/dist/**", "**/build/**",
        "**/.next/**", "**/.turbo/**", "**/.idea/**", "**/.vscode/**",
        "**/.cache/**", "**/.pytest_cache/**",
    ]
    max_bytes = int(state.get("max_bytes") or 2_000_000)

    files = walk_repo(root, include, exclude, max_bytes, follow_symlinks=False)
    if not files:
        return {
            "next_action": "end",
            "messages": (state.get("messages") or []) + [AIMessage(content="No files matched include/exclude filters.")],
            "steps": (state.get("steps") or []) + ["analyze"],
        }

    rules = load_rules(Path("presets/rules.yaml"))
    override_weights(rules.get("weights"))

    out_dir = Path("reports"); out_dir.mkdir(parents=True, exist_ok=True)
    out_path = write_basic_report(files, out_dir)

    # Detectors
    results = run_analysis(
        root,
        include,
        exclude,
        rules=rules,
        max_bytes=max_bytes,
        warn_at=rules.get("complexity", {}).get("warn_at", 10),
        dup_k=rules.get("duplication", {}).get("k_shingle", 7),
        dup_threshold=rules.get("duplication", {}).get("similarity_threshold", 0.90),
    )
    append_top_issues(out_path, results.get("findings_scored", []))
    append_per_category_summary(out_path, results.get("findings_scored", []))
    append_issue_details(out_path, results.get("findings_scored", []))
    append_findings(out_path, results.get("findings_raw", {}))

    # Dependencies
    dep_graph = results.get("dep_graph") or results.get("dependencies", {}).get("graph")
    dep_metrics = _safe_dep_metrics(results)
    if dep_graph is not None:
        _ = export_dependency_graph(dep_graph, out_dir)
    append_dependencies(out_path, dep_metrics)
    append_dependency_outline(out_path, dep_metrics, results.get("hotspots", []))
    json_out = export_json_report(
        out_dir,
        files_scanned=len(files),
        by_language=results.get("by_language", {}),
        findings=results.get("findings_json", []),
        dep_metrics=dep_metrics,
    )

    return {
        "analysis_report_path": str(out_path),
        "analysis_json_path": str(json_out),
        "messages": (state.get("messages") or []) + [AIMessage(content=f"Wrote analysis to {out_path}")],
        "next_action": "end",
        "steps": (state.get("steps") or []) + ["analyze"],
    }

# Chat node: retrieve and answer deterministically (no model call here)
def chat_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    question = state.get("question") or ""
    k = int(state.get("k") or 5)
    boost = float(state.get("name_match_boost") or 0.3)

    manager = CodeEmbeddingManager()
    retriever = FileAwareRetriever(vector_store=manager.vector_store, k=k, name_match_boost=boost)
    docs = retriever.get_relevant_documents(question)

    # Deterministic, template-based answer (LLM hook can be added later)
    bullets: List[str] = []
    for d in docs:
        md = d.metadata or {}
        bullets.append(f"- {md.get('file_path','')} :: {md.get('name','')} [{md.get('chunk_type','')}] {md.get('start_line',1)}-{md.get('end_line',1)}")
    stitched = "Top matches:\n" + "\n".join(bullets) if bullets else "No matches."

    return {
        "retrieval_docs": [
            {"file_path": (d.metadata or {}).get("file_path",""),
             "name": (d.metadata or {}).get("name",""),
             "chunk_type": (d.metadata or {}).get("chunk_type",""),
             "start_line": int((d.metadata or {}).get("start_line",1)),
             "end_line": int((d.metadata or {}).get("end_line",1))}
            for d in docs
        ],
        "answer": stitched,
        "messages": (state.get("messages") or []) + [AIMessage(content=stitched)],
        "next_action": "end",
        "steps": (state.get("steps") or []) + ["chat"],
    }
