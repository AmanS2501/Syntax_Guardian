# Technical Notes — Syntax Guardian

These are my working notes from building and iterating on the **Code Quality Intelligence Agent (aka “Syntax Guardian”)**.  Think of this more like a dev log than a polished spec.  It’s a mix of what worked, what didn’t, and things I’d tell my future self before diving back into the codebase.

---

## 1. Repo setup & tooling

* **Env management:** I settled on `uv` + a local venv instead of conda.  It’s just lighter and plays nicely with the CLI.  The `uv` CLI saved me from dependency hell more than once.
* **Folder layout:** I kept the `cqia/` package relatively flat.  Detectors live under `cqia/analysis/detectors/` while RAG bits are in `cqia/rag/`.  It’s not textbook-perfect, but it’s easy to navigate.
* **CLI:** Typer is doing all the heavy lifting.  I originally thought about plain argparse but Typer’s autocompletion and help text were worth it.
* **Tests:** Only partial coverage so far.  There’s a skeleton `tests/` folder with some smoke tests for the detectors.  Need more unit tests for the RAG pipeline.

## 2. What tripped me up

* **AST parsing for JS/TS:** Python’s `ast` is straightforward, but JS/TS is a rabbit hole.  I used a lightweight heuristic parser for now.  It catches obvious issues but isn’t bulletproof.
* **Duplication detection:** Initially tried a rolling hash approach.  It was accurate but painfully slow on larger repos.  Switched to token-shingling with Jaccard and that’s fast enough.
* **Security checks:** Balancing between false positives and coverage is tricky.  For example, flagging every `subprocess` call is noisy.  Ended up whitelisting some common safe patterns.
* **Dependency graph cycles:** NetworkX made this easy, but interpreting the results in a way that’s actually useful to devs (not just a graph dump) took some trial and error.

## 3. Things I’m happy with

* **Deterministic core analysis:** All the detectors and scoring are pure functions.  No LLM randomness unless you go into the chat/Q\&A mode.
* **Report artifacts:** The generated `report.md` is simple markdown but reads like a mini audit doc.  The JSON output is handy if we ever want to feed it into a dashboard.
* **Hotspot scoring:** Combining complexity and fan-in/out gave surprisingly meaningful results.  It immediately highlights the scary parts of a repo.

## 4. RAG/Q\&A side

* Went with function-level chunking + docstrings.  Keeps the vector DB small and retrieval precise.
* Using Groq for the LLM part.  Works fine but the plan is to keep the core analysis independent of any external API.
* Learned that giving the retriever some “filename boosting” helps the answers stay grounded in the right file.

## 5. Performance & scaling

* For medium repos (<5k files) everything runs comfortably under a few minutes on my laptop.
* The biggest bottleneck is duplication detection on very large files.  Might need to pre-filter huge files or parallelize that later.
* Embedding large repos for RAG is memory-heavy.  Could chunk in batches or swap to a persistent vector DB if this grows.

## 6. Future todos

* Proper CI pipeline: run detectors + generate `report.json` on every PR.
* Better JS/TS parser, ideally tree-sitter.
* Expand the test suite and measure coverage.
* Maybe a simple dashboard that charts severity trends over time.

## 7. Random lessons learned

* Good error messages save hours.  Added custom exceptions early and it paid off.
* Documenting detectors (even with a single line) means I actually remember why I wrote them.
* Don’t over-engineer early.  Some of the best decisions came from starting with the simplest possible version and only optimizing when I felt the pain.

---

These notes aren’t exhaustive, but they capture the messy reality of building Syntax Guardian: a mix of quick wins, rabbit holes, and those “aha” moments that you only get when you’re knee‑deep in the code.
