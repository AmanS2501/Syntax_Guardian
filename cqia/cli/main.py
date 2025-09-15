from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import subprocess
import statistics
import sys
import typer

from rich.console import Console
from rich.table import Table

# Core graph and QA
from cqia.agent.graph.flow import build_cqia_graph
from langchain_core.messages import HumanMessage

# Dependency metrics helper
from cqia.utils.deps import safe_dep_metrics as _safe_dep_metrics

# Analysis pipeline
from cqia.core.config import AnalyzeConfig
from cqia.ingestion.walker import walk_repo
from cqia.analysis.runner import run_analysis
from cqia.presets import load_rules, save_rules
from cqia.analysis.severity import override_weights

# Reporting
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

# RAG pieces
from cqia.qa.chain import build_chatgroq_llm, answer_with_citations
from cqia.qa.artifacts import load_scope_findings
from cqia.rag.chunking.ast_chunker import ASTFunctionChunker
from cqia.rag.embeddings.vector_store import CodeEmbeddingManager
from cqia.rag.retrieval.smart_retriever import FileAwareRetriever


app = typer.Typer(add_completion=False, help="Code Quality Intelligence Agent (CQIA)")
console = Console()


def _clone_or_use(path_or_git: str, workdir: Path) -> Path:
    p = Path(path_or_git)
    if p.exists():
        return p
    # Sanitize trailing dot in repo name (Windows)
    repo_name = Path(path_or_git).stem.rstrip(".") or "repo"
    repo_dir = workdir / repo_name
    if repo_dir.exists():
        return repo_dir
    subprocess.check_call(["git", "clone", "--depth", "1", path_or_git, str(repo_dir)])
    return repo_dir


def _detector_rationale_for_path(root: Path, include: list[str], exclude: list[str], max_bytes: int) -> str:
    """
    Run a lightweight analysis to extract brief rationale strings to aid QA.
    Uses correct keys from ScoredFinding: file/start_line/end_line/title/category/severity.
    """
    try:
        rules = load_rules(Path("presets/rules.yaml"))
        override_weights(rules.get("weights"))
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
        snippets: list[str] = []
        for f in (results.get("findings_scored") or [])[:5]:
            cat = f.get("category", "issue")
            sev = f.get("severity", "P3")
            loc = f"{f.get('file','')}:{int(f.get('start_line',1))}-{int(f.get('end_line',1))}"
            title = f.get("title", "Finding")
            snippets.append(f"{cat} ({sev}) at {loc}: {title}")
        return "\n".join(snippets[:3]) if snippets else "No notable findings."
    except Exception:
        return "No notable findings."


@app.command("serve-api")
def serve_api(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the FastAPI web service."""
    import uvicorn
    uvicorn.run("cqia.web.service:app", host=host, port=port, reload=False)


@app.command("serve-ui")
def serve_ui() -> None:
    """Run the Streamlit UI."""
    subprocess.run([sys.executable, "-m", "streamlit", "run", "cqia/web/ui_app.py"], check=True)


@app.command("pr-comment")
def pr_comment(
    owner: str = typer.Argument(...),
    repo: str = typer.Argument(...),
    number: int = typer.Argument(..., help="PR number"),
    body: str = typer.Option(..., "--body", "-b", help="Comment body (Markdown allowed)"),
) -> None:
    """Post a general PR comment (issues API)."""
    from cqia.integrations.github_pr import GitHubPRClient
    client = GitHubPRClient()
    res = client.comment_issue(owner, repo, number, body)
    console.print(f"[green]Posted comment:[/] {res.get('html_url','')}")


@app.command("chat")
def chat_repo(
    analyze_path: str = typer.Argument(..., help="Repository or folder path to scope Q&A"),
    question: str = typer.Option(..., "--question", "-q", help="User question about the codebase"),
    k: int = typer.Option(5, help="Top-K retrieval results"),
    name_boost: float = typer.Option(0.3, help="Boost for function/file name matches"),
    model_name: str = typer.Option("openai/gpt-oss-120b", help="Groq model name"),
    temperature: float = typer.Option(0.0, help="LLM temperature"),
    include: list[str] = typer.Option(["**/*.py", "**/*.js", "**/*.ts"], help="Include globs"),
    exclude: list[str] = typer.Option(
        [".git/**", "**/node_modules/**", "**/__pycache__/**", "**/.venv/**", "**/venv/**"],
        help="Exclude globs"
    ),
    max_bytes: int = typer.Option(5_000_000, help="Per-file size cap (for rationale analysis)"),
    persist_dir: str = typer.Option(".cqia_vectordb", help="Chroma persistence directory"),
) -> None:
    """Scoped Q&A over a repository path with inline file:line citations."""
    scope = Path(analyze_path)
    if not scope.exists():
        typer.secho(f"Path not found: {scope}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    # Retrieval
    manager = CodeEmbeddingManager(persist_directory=persist_dir)
    retriever = FileAwareRetriever(vector_store=manager.vector_store, k=k, name_match_boost=name_boost)
    raw_docs = retriever.invoke(question)

    # Scope filter
    scoped_docs = []
    scope_str = str(scope.resolve()).replace("\\", "/")
    for d in raw_docs:
        fp = (d.metadata or {}).get("file_path", "")
        if not fp:
            continue
        fpn = str(Path(fp).resolve()).replace("\\", "/")
        if fpn.startswith(scope_str):
            scoped_docs.append(d)

    if not scoped_docs:
        console.print("[yellow]No scoped matches found in the provided path. Consider re-indexing that path or relaxing the query.[/]")
        return

    # Reduce k further if too many matches
    scoped_docs = scoped_docs[:3]

    # Detector rationale (already lightweight)
    rationale = _detector_rationale_for_path(scope, include, exclude, max_bytes)

    # Findings context: limit size
    findings_context = load_scope_findings(scope, max_chars=8_000)

    # Trim retrieved docs to avoid 413
    max_chars_per_doc = 1500
    def trim_text(t: str, n: int) -> str:
        return t[:n] if t and len(t) > n else (t or "")

    trimmed_docs = []
    for d in scoped_docs:
        d_copy = d.copy()
        d_copy.page_content = trim_text(d.page_content, max_chars_per_doc)
        trimmed_docs.append(d_copy)

    # Build compact context preview
    def render_snippet(doc):
        md = doc.metadata or {}
        loc = f"{md.get('file_path','')}:{int(md.get('start_line',1))}-{int(md.get('end_line',1))}"
        name = md.get("name", md.get("chunk_type", ""))
        header = f"# {loc} :: {name}\n"
        return header + (doc.page_content or "")

    context_pieces = [render_snippet(d) for d in trimmed_docs]
    context_text = "\n\n---\n\n".join(context_pieces)

    # Approximate prompt size guard: further shrink if needed
    approx_input_chars = len(context_text) + len(findings_context) + len(question) + len(rationale)
    if approx_input_chars > 12000:
        # tighten per-doc budget
        tighter_docs = []
        for d in trimmed_docs:
            d2 = d.copy()
            d2.page_content = trim_text(d.page_content, 800)
            tighter_docs.append(d2)
        trimmed_docs = tighter_docs
        context_pieces = [render_snippet(d) for d in trimmed_docs]
        context_text = "\n\n---\n\n".join(context_pieces)

    # LLM call with trimmed context
    llm = build_chatgroq_llm(model_name=model_name, temperature=temperature)
    answer = answer_with_citations(
        llm,
        question,
        trimmed_docs,           # pass trimmed docs
        detector_rationale=rationale,
        findings_context=findings_context,
    )


    table = Table(title="Retrieved Matches (Scoped)")
    table.add_column("File", overflow="fold")
    table.add_column("Name", overflow="fold")
    table.add_column("Type")
    table.add_column("Lines", justify="right")
    for d in scoped_docs:
        md = d.metadata or {}
        table.add_row(
            str(md.get("file_path", "")),
            str(md.get("name", "")),
            str(md.get("chunk_type", "")),
            f"{int(md.get('start_line', 1))}-{int(md.get('end_line', 1))}",
        )
    console.print(table)

    console.rule("[bold]Answer")
    console.print(answer)


@app.command("graph-analyze")
def graph_analyze(
    path: str = typer.Argument(..., help="Path to analyze"),
    include: list[str] = typer.Option(["**/*.py", "**/*.js", "**/*.ts"], help="Include globs"),
    exclude: list[str] = typer.Option(
        [".git/**", "**/node_modules/**", "**/__pycache__/**", "**/.venv/**", "**/venv/**"], help="Exclude globs"
    ),
    max_bytes: int = typer.Option(2_000_000, help="Per-file size cap"),
) -> None:
    graph = build_cqia_graph()
    state = {
        "mode": "analyze",
        "path": path,
        "include": include,
        "exclude": exclude,
        "max_bytes": max_bytes,
        "messages": [HumanMessage(content=f"Analyze {path}")],
    }
    result = graph.invoke(state)
    console.print(f"[green]Graph steps:[/] {result.get('steps')}")
    console.print(f"[green]Report:[/] {result.get('analysis_report_path')}")
    console.print(f"[green]JSON:[/] {result.get('analysis_json_path')}")


@app.command("graph-chat")
def graph_chat(
    question: str = typer.Argument(..., help="Question about the codebase"),
    k: int = typer.Option(5, help="Top-K results"),
    name_boost: float = typer.Option(0.3, help="Boost for name/path match"),
) -> None:
    graph = build_cqia_graph()
    state = {
        "mode": "chat",
        "question": question,
        "k": k,
        "name_match_boost": name_boost,
        "messages": [HumanMessage(content=question)],
    }
    result = graph.invoke(state)
    console.print(f"[green]Graph steps:[/] {result.get('steps')}")
    console.print(f"[blue]{result.get('answer','')}")


@app.command("analyze")
def analyze(
    path: str = typer.Argument(..., help="Path to file or folder to analyze"),
    include: list[str] = typer.Option(["**/*.py", "**/*.js", "**/*.ts"], help="Glob patterns to include"),
    exclude: list[str] = typer.Option(
        [
            ".git/**", "**/.git/**",
            "**/.venv/**", "**/venv/**", "**/env/**",
            "**/__pycache__/**",
            "**/node_modules/**",
            "**/dist/**", "**/build/**", "**/.next/**", "**/.turbo/**",
            "**/.idea/**", "**/.vscode/**",
            "**/.cache/**", "**/.pytest_cache/**",
        ],
        help="Glob patterns to exclude",
    ),
    max_bytes: int = typer.Option(2_000_000, help="Per-file size cap in bytes"),
    output_dir: str = typer.Option("reports", help="Output directory for reports"),
    rules_file: str = typer.Option("presets/rules.yaml", help="Rules/thresholds file"),
    no_findings: bool = typer.Option(False, help="Skip detectors and only write the basic summary"),
) -> None:
    root = Path(path)
    if not root.exists():
        typer.secho(f"Path not found: {root}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    rules = load_rules(Path(rules_file))
    override_weights(rules.get("weights"))

    cfg = AnalyzeConfig(
        path=root,
        include=include,
        exclude=exclude,
        max_bytes=max_bytes,
        output_dir=Path(output_dir),
        rules_path=Path(rules_file),
    )

    console.rule("[bold]Scanning repository")
    files = walk_repo(cfg.path, cfg.include, cfg.exclude, cfg.max_bytes, follow_symlinks=False)
    if not files:
        typer.secho("No files matched include/exclude filters.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    table = Table(title="Scanned Files")
    table.add_column("Path", overflow="fold")
    table.add_column("Lang", justify="center")
    table.add_column("Lines", justify="right")
    table.add_column("Bytes", justify="right")
    for f in files[:50]:
        table.add_row(str(f.path), f.language, str(f.lines), str(f.bytes))
    console.print(table)
    if len(files) > 50:
        console.print(f"... and {len(files) - 50} more")

    out_path = write_basic_report(files, cfg.resolve_output_dir())
    typer.secho(f"Wrote summary: {out_path}", fg=typer.colors.GREEN)

    if no_findings:
        return

    console.rule("[bold]Running detectors")
    try:
        results = run_analysis(
            cfg.path,
            cfg.include,
            cfg.exclude,
            rules=rules,
            max_bytes=cfg.max_bytes,
            warn_at=rules.get("complexity", {}).get("warn_at", 10),
            dup_k=rules.get("duplication", {}).get("k_shingle", 7),
            dup_threshold=rules.get("duplication", {}).get("similarity_threshold", 0.90),
        )

        # Pass-through without reshaping: expected keys are title/file/start_line/end_line/why/fix/score/severity/category
        append_top_issues(out_path, results.get("findings_scored", []))
        append_per_category_summary(out_path, results.get("findings_scored", []))
        append_issue_details(out_path, results.get("findings_scored", []))
        append_findings(out_path, results.get("findings_raw", {}))

        typer.secho(f"Appended findings, category summaries, and details: {out_path}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Detector pipeline failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    console.rule("[bold]Analyzing dependencies")
    try:
        dep_graph = results.get("dep_graph") or results.get("dependencies", {}).get("graph")
        dep_metrics = _safe_dep_metrics(results)

        dep_out = export_dependency_graph(dep_graph, cfg.resolve_output_dir()) if dep_graph is not None else None
        append_dependencies(out_path, dep_metrics)
        append_dependency_outline(out_path, dep_metrics, results.get("hotspots", []))

        json_out = export_json_report(
            cfg.resolve_output_dir(),
            files_scanned=len(files),
            by_language=results.get("by_language", {}),
            findings=results.get("findings_json", []),
            dep_metrics=dep_metrics,
        )
        if dep_out:
            typer.secho(f"Wrote artifacts: {dep_out}, {json_out}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"Wrote artifacts: {json_out}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Dependency/report export failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command("index")
def index_repository(
    path: str = typer.Argument(..., help="Path to repository to index for RAG"),
    include: list[str] = typer.Option(["**/*.py", "**/*.js", "**/*.ts"], help="Include globs"),
    exclude: list[str] = typer.Option(
        [".git/**", "**/node_modules/**", "**/__pycache__/**", "**/.venv/**", "**/venv/**"],
        help="Exclude globs",
    ),
    reset: bool = typer.Option(False, help="Reset the vector index before indexing"),
    persist_dir: str = typer.Option(".cqia_vectordb", help="Chroma persistence directory"),
    embedding_model: str = typer.Option("sentence-transformers/all-MiniLM-L6-v2", help="Embedding model"),
) -> None:
    """Index repository into Chroma with function-level and docstring chunks."""
    root = Path(path)
    if not root.exists():
        typer.secho(f"Path not found: {root}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    console.rule("[bold]Preparing files for indexing")
    files = walk_repo(root, include, exclude, max_bytes=2_000_000, follow_symlinks=False)
    if not files:
        typer.secho("No files matched include/exclude filters.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    chunker = ASTFunctionChunker()
    manager = CodeEmbeddingManager(persist_directory=persist_dir, embedding_model=embedding_model)
    if reset:
        ok = manager.vector_store.reset_collection()
        if ok:
            console.print("[yellow]Reset vector collection[/]")

    def _chunk_file(file_path: str, text: str, language: str):
        chunks = chunker.extract_chunks(file_path, text, language)
        return chunker.chunks_to_documents(chunks)

    console.rule("[bold]Indexing repository into Chroma")
    res = manager.index_repository(files, _chunk_file)
    stats = manager.get_stats()

    console.print(f"[green]Indexed files: {res['successful_files']}/{res['total_files']}[/]")
    console.print(f"[green]Total chunks stored: {res['total_chunks']}[/]")
    if res["failed_files"]:
        console.print(f"[yellow]Failed files: {res['failed_files']}[/]")
    console.print(f"[blue]Collection stats: {stats}[/]")


@app.command("query")
def query_index(
    query: str = typer.Argument(..., help="Natural language or code search query"),
    k: int = typer.Option(5, help="Top-K results"),
    persist_dir: str = typer.Option(".cqia_vectordb", help="Chroma persistence directory"),
    name_boost: float = typer.Option(0.3, help="Boost factor for path/function name matches"),
) -> None:
    """Query the indexed codebase with a smart retriever that boosts path/name matches."""
    manager = CodeEmbeddingManager(persist_directory=persist_dir)
    retriever = FileAwareRetriever(vector_store=manager.vector_store, k=k, name_match_boost=name_boost)
    docs = retriever.invoke(query)

    table = Table(title="RAG Results")
    table.add_column("File", overflow="fold")
    table.add_column("Name", overflow="fold")
    table.add_column("Type")
    table.add_column("Lines", justify="right")
    for d in docs:
        md = d.metadata or {}
        table.add_row(
            str(md.get("file_path", "")),
            str(md.get("name", "")),
            str(md.get("chunk_type", "")),
            f"{int(md.get('start_line', 1))}-{int(md.get('end_line', 1))}",
        )
    console.print(table)


@app.command("tune")
def tune(
    py_repo: str = typer.Option("https://github.com/pallets/flask", help="Python repo (path or Git URL)"),
    js_repo: str = typer.Option("https://github.com/stacklok/demo-repo-js", help="JS repo (path or Git URL)"),
    tmp_dir: str = typer.Option(".cqia-tune", help="Working directory for clones"),
    rules_file: str = typer.Option("presets/rules.yaml", help="Rules file to write tuned values"),
    max_bytes: int = typer.Option(2_000_000, help="Per-file size cap in bytes"),
    skip_py: bool = typer.Option(False, help="Skip tuning on Python repo"),
    skip_js: bool = typer.Option(False, help="Skip tuning on JS repo"),
) -> None:
    work = Path(tmp_dir)
    work.mkdir(parents=True, exist_ok=True)
    rules = load_rules(Path(rules_file))

    py_res: dict = {}
    js_res: dict = {}

    if not skip_py and py_repo:
        console.rule("[bold]Tuning on Python repo")
        py_path = _clone_or_use(py_repo, work)
        override_weights(rules.get("weights"))
        py_res = run_analysis(
            py_path,
            ["**/*.py", "**/*.js", "**/*.ts"],
            [".git/**", "**/.git/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**", "**/node_modules/**"],
            rules=rules,
            max_bytes=max_bytes,
            warn_at=rules.get("complexity", {}).get("warn_at"),
            p1_cutoff=rules.get("complexity", {}).get("p1_cutoff"),
            p0_cutoff=rules.get("complexity", {}).get("p0_cutoff"),
        )

    if not skip_js and js_repo:
        console.rule("[bold]Tuning on JS repo")
        js_path = _clone_or_use(js_repo, work)
        js_res = run_analysis(
            js_path,
            ["**/*.py", "**/*.js", "**/*.ts"],
            [".git/**", "**/.git/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**", "**/node_modules/**"],
            rules=rules,
            max_bytes=max_bytes,
            warn_at=rules.get("complexity", {}).get("warn_at", 10),
            dup_k=rules.get("duplication", {}).get("k_shingle", 7),
            dup_threshold=rules.get("duplication", {}).get("similarity_threshold", 0.90),
        )

    def _collect_complexity(res: dict) -> list[float]:
        vals: list[float] = []
        for f in (res.get("findings_raw", {}) or {}).get("complexity", []):
            try:
                vals.append(float(getattr(f, "value", 0.0) or 0.0))
            except Exception:
                pass
        return vals

    comp_vals = _collect_complexity(py_res or {}) + _collect_complexity(js_res or {})
    if comp_vals:
        comp_vals.sort()
        n = len(comp_vals)
        p80 = comp_vals[int(0.8 * n) - 1] if n >= 5 else max(comp_vals)
        p90 = comp_vals[int(0.9 * n) - 1] if n >= 10 else max(comp_vals)
        rules.setdefault("complexity", {})
        rules["complexity"]["warn_at"] = max(8, int(round(statistics.median(comp_vals)))) if n >= 5 else 10
        rules["complexity"]["p1_cutoff"] = max(12, int(round(p80)))
        rules["complexity"]["p0_cutoff"] = max(rules["complexity"]["p1_cutoff"] + 2, int(round(p90)))
    else:
        console.print("No complexity data found; keeping defaults")

    dup_total = len((py_res.get("findings_raw", {}) or {}).get("duplication", [])) + len(
        (js_res.get("findings_raw", {}) or {}).get("duplication", [])
    )
    thr = float(rules.get("duplication", {}).get("similarity_threshold", 0.90))
    if dup_total > 50:
        thr = min(0.97, thr + 0.02)
    elif dup_total < 5:
        thr = max(0.85, thr - 0.03)
    rules.setdefault("duplication", {})
    rules["duplication"]["similarity_threshold"] = round(thr, 2)

    py_dm = _safe_dep_metrics(py_res or {})
    js_dm = _safe_dep_metrics(js_res or {})
    py_fi = list((py_dm.get("fan_in") or {}).values())
    js_fi = list((js_dm.get("fan_in") or {}).values())
    fi_vals = py_fi + js_fi
    if fi_vals:
        top = sorted(fi_vals, reverse=True)[:5]
        if sum(top) / max(1, sum(fi_vals)) > 0.25:
            w = float(rules.setdefault("weights", {}).get("performance", 0.6))
            rules["weights"]["performance"] = min(1.0, round(w + 0.05, 2))

    outp = save_rules(rules, Path(rules_file))
    console.print(f"[green]Wrote tuned rules to {outp}[/]")

    tbl = Table(title="Tuned thresholds and weights")
    tbl.add_column("Key")
    tbl.add_column("Value")
    for k in ["warn_at", "p1_cutoff", "p0_cutoff"]:
        if "complexity" in rules and k in rules["complexity"]:
            tbl.add_row(f"complexity.{k}", str(rules["complexity"][k]))
    if "duplication" in rules and "similarity_threshold" in rules["duplication"]:
        tbl.add_row("duplication.similarity_threshold", str(rules["duplication"]["similarity_threshold"]))
    for cat, w in (rules.get("weights") or {}).items():
        tbl.add_row(f"weights.{cat}", str(w))
    console.print(tbl)
    console.print("[blue]Tuning complete. Future analyze runs will use these settings.[/]")


if __name__ == "__main__":
    app()
