
from __future__ import annotations
import json
from pathlib import Path
import requests
import streamlit as st

st.set_page_config(page_title="CQIA Web", layout="wide")

st.title("Code Quality Intelligence (CQIA) – Web UI")

# Controls
mode = st.radio("Run mode", ["Local (no API)", "Call FastAPI"], horizontal=True)

github_url = st.text_input("GitHub URL to analyze", placeholder="https://github.com/org/repo")
branch = st.text_input("Branch (optional)", value="")

col_a, col_b = st.columns(2)
with col_a:
    include = st.text_area("Include globs", value="**/*.py\n**/*.ts\n**/*.js", height=100)
with col_b:
    exclude = st.text_area("Exclude globs", value=".git/**\n**/node_modules/**\n**/__pycache__/**\n**/.venv/**\n**/venv/**", height=100)

col_c, col_d = st.columns(2)
with col_c:
    max_bytes = st.number_input("Per-file byte cap", value=2_000_000, step=100_000, min_value=100_000)
with col_d:
    clone_mode = st.selectbox("Clone mode", ["clean", "unique"], index=0)

api_base = st.text_input("API base (FastAPI mode)", value="http://127.0.0.1:8000")

run = st.button("Analyze", type="primary")

def _render_report(report_md_path: str):
    p = Path(report_md_path)
    st.subheader("report.md")
    if not p.exists():
        st.warning("report.md not found at: " + report_md_path)
        return
    try:
        md_text = p.read_text(encoding="utf-8", errors="ignore")
        st.markdown(md_text)
    except Exception as e:
        st.error(f"Failed to read report.md: {e}")

def _render_json(json_path: str):
    p = Path(json_path)
    st.subheader("report.json (summary)")
    if not p.exists():
        st.warning("report.json not found at: " + json_path)
        return
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(raw)
        st.json(data)
    except Exception:
        st.code(raw, language="json")

if run and github_url.strip():
    inc = [g.strip() for g in include.splitlines() if g.strip()]
    exc = [g.strip() for g in exclude.splitlines() if g.strip()]

    if mode == "Call FastAPI":
        payload = {
            "github_url": github_url.strip(),
            "branch": branch.strip() or None,
            "include": inc,
            "exclude": exc,
            "max_bytes": int(max_bytes),
            "clone_mode": clone_mode,
        }
        with st.spinner("Calling CQIA Web Service..."):
            try:
                r = requests.post(f"{api_base.rstrip('/')}/api/analyze", json=payload, timeout=600)
            except Exception as e:
                st.error(f"Request failed: {e}")
                st.stop()

        if r.status_code != 200:
            # Try to show server-side detail cleanly
            try:
                data = r.json()
                st.error(f"API error {r.status_code}: {data.get('detail', data)}")
            except Exception:
                st.error(f"API error {r.status_code}: {r.text}")
            st.stop()

        res = r.json()
        st.success(f"Analyzed repo at: {res.get('repo_path','')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Files scanned", res.get("files_scanned", 0))
        with col2:
            st.metric("Top issues", res.get("top_issues", 0))
        with col3:
            st.write("By language:", res.get("by_language", {}))

        if res.get("report_md"):
            _render_report(res["report_md"])
        if res.get("report_json"):
            _render_json(res["report_json"])

    else:
        # Local run: clone + analyze without HTTP
        from cqia.web.clone import shallow_clone
        from cqia.presets import load_rules
        from cqia.analysis.severity import override_weights
        from cqia.analysis.runner import run_analysis
        from cqia.reporting.markdown import (
            write_basic_report, append_top_issues, append_per_category_summary,
            append_issue_details, append_findings, append_dependencies, append_dependency_outline,
        )
        from cqia.reporting.exporters import export_dependency_graph, export_json_report
        from cqia.ingestion.walker import walk_repo

        work = Path(".cqia-web-work")
        with st.spinner("Cloning repository..."):
            try:
                repo_root = shallow_clone(github_url.strip(), work, branch.strip() or None, clone_mode)
            except Exception as e:
                st.error(f"Clone failed: {e}")
                st.stop()

        with st.spinner("Walking repository..."):
            metas = walk_repo(Path(repo_root), inc, exc, int(max_bytes), follow_symlinks=False)
        st.write("Files discovered:", len(metas))
        if not metas:
            st.warning("No files matched include/exclude filters.")
            st.stop()

        rules = load_rules(Path("presets/rules.yaml"))
        override_weights(rules.get("weights"))

        out_dir = Path(repo_root) / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = write_basic_report(metas, out_dir)

        with st.spinner("Running analysis..."):
            results = run_analysis(
                Path(repo_root),
                inc,
                exc,
                rules=rules,
                max_bytes=int(max_bytes),
                warn_at=rules.get("complexity", {}).get("warn_at", 10),
                dup_k=rules.get("duplication", {}).get("k_shingle", 7),
                dup_threshold=rules.get("duplication", {}).get("similarity_threshold", 0.90),
            )

        append_top_issues(out_path, results.get("findings_scored", []))
        append_per_category_summary(out_path, results.get("findings_scored", []))
        append_issue_details(out_path, results.get("findings_scored", []))
        append_findings(out_path, results.get("findings_raw", {}))

        dep_graph = results.get("dep_graph") or results.get("dependencies", {}).get("graph")
        dep_metrics = results.get("dep_metrics") or results.get("dependencies", {}).get("metrics", {})
        if dep_graph is not None:
            export_dependency_graph(dep_graph, out_dir)
        append_dependencies(out_path, dep_metrics)
        append_dependency_outline(out_path, dep_metrics, results.get("hotspots", []))

        json_out = export_json_report(
            out_dir,
            files_scanned=len(metas),
            by_language=results.get("by_language", {}),
            findings=results.get("findings_json", []),
            dep_metrics=dep_metrics,
        )

        st.success(f"Analysis done. Reports in: {out_dir}")
        _render_report(str(out_path))
        _render_json(str(json_out))
