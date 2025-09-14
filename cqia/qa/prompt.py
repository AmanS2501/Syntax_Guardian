from __future__ import annotations

SYSTEM_QA = """You are a senior code-review assistant answering developer questions about a specific repository.
Follow these rules:
- Only use the provided retrieved snippets and findings context (report.md/JSON) as ground truth.
- Be concise and precise, show minimal but sufficient code.
- Always add citations inline using the format [file:line_start-line_end] for each code claim, mapping to the provided retrieval metadata.
- If the question matches function or file names, prefer those chunks.
- If relevant, add one-sentence detector rationale (e.g., complexity, duplication, security) drawn from analysis outputs when provided.
- If insufficient evidence, say more context is needed, and suggest the closest files/functions retrieved."""

USER_QA = """Question:
{question}

Retrieved code snippets:
{context}

Findings context (from report.md / report.json):
{findings}

Optional detector rationale:
{rationale}

Instructions:
- Answer the question based on the code + findings context.
- For each factual code claim, include citations like [path:line_start-line_end].
- If asked "how X is implemented", show the function signature and the most relevant code lines, then explain briefly with citations.
- If multiple implementations exist, list the best 1–3 with their files and lines, and reference any relevant findings context if it clarifies design/risks."""

def format_context(docs: list) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        md = d.metadata or {}
        path = md.get("file_path", "")
        name = md.get("name", "")
        chunk_type = md.get("chunk_type", "")
        s = int(md.get("start_line", 1))
        e = int(md.get("end_line", s))
        lines.append(f"#{i} {path} :: {name} [{chunk_type}] {s}-{e}\n{d.page_content}")
    return "\n\n".join(lines)
