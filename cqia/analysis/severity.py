from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Mapping

Severity = Literal["P0", "P1", "P2", "P3"]

@dataclass(frozen=True)
class ScoredFinding:
    id: str
    category: str
    severity: Severity
    score: float
    title: str
    file: str
    start_line: int
    end_line: int
    why: str
    fix: str
    extra: dict | None = None

DEFAULT_WEIGHTS: Mapping[str, float] = {
    "security": 1.0,
    "complexity": 0.6,
    "duplication": 0.5,
    "performance": 0.6,
    "documentation": 0.3,
    "testing": 0.7,
}

CONTEXT_CAP: Mapping[str, float] = {
    "security": 1.0,
    "complexity": 0.3,
    "duplication": 0.3,
    "performance": 0.4,
    "documentation": 0.2,
    "testing": 0.4,
}

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def _to_severity(x: float) -> Severity:
    if x >= 0.80:
        return "P0"
    if x >= 0.60:
        return "P1"
    if x >= 0.40:
        return "P2"
    return "P3"

def combine_with_context(base: float, category: str, context: float | None = None) -> float:
    if context is None:
        return _clamp01(base)
    cap = CONTEXT_CAP.get(category, 0.2)
    c = _clamp01(context)
    return _clamp01(base + cap * c - base * cap * c)

def score_security(weight: float) -> float:
    return _clamp01(weight)

def score_complexity(cc: float, weight: float, warn_at: float = 10.0) -> float:
    norm = max(0.0, (cc - warn_at) / (warn_at * 2.0))
    return _clamp01(norm * weight)

def score_duplication(sim: float, weight: float) -> float:
    return _clamp01(sim * weight)

def score_performance_base(weight: float) -> float:
    return _clamp01(weight)

def score_testing_base(weight: float) -> float:
    return _clamp01(weight)

def score_documentation_base(weight: float) -> float:
    return _clamp01(weight)

def pick_severity(category: str, raw: float) -> Severity:
    return _to_severity(raw)

def explain(category: str) -> str:
    if category == "security":
        return "Security-sensitive API usage increases the risk of injection or RCE; fix immediately."
    if category == "complexity":
        return "High cyclomatic complexity makes code harder to test and maintain and hides defects."
    if category == "duplication":
        return "Duplicated logic leads to divergence and bugs, increasing maintenance effort."
    if category == "performance":
        return "Loop performs expensive operations; this can dominate runtime and reduce throughput."
    if category == "documentation":
        return "Missing docstrings reduce readability, API clarity, and onboarding speed."
    if category == "testing":
        return "Missing tests risk regressions and make safe refactoring harder."
    return "Quality issue."

def fix_text(category: str, extra: dict | None) -> str:
    if category == "security":
        return "- Replace eval/exec; validate inputs; use safe loaders; for subprocess set shell=False and pass args list.\n"
    if category == "complexity":
        return "- Extract helpers; guard-return early; simplify boolean expressions with named predicates.\n"
    if category == "duplication":
        other = (extra or {}).get("other_file")
        tail = f" (see also {other})" if other else ""
        return f"- Extract common code into a shared function or module{tail}; add tests for the shared path.\n"
    if category == "performance":
        kind = (extra or {}).get("kind", "")
        if kind == "string_concat_in_loop":
            return "- Append to a list in the loop and join once: parts.append(x); s=''.join(parts).\n"
        if kind in {"io_in_loop", "requests_in_loop"}:
            return "- Hoist I/O out of the loop, batch requests, or use concurrency/async with pooling and timeouts.\n"
        return "- Reduce per-iteration work; batch or cache repeated operations.\n"
    if category == "documentation":
        return "- Add module/class/function docstrings (PEP 257) with parameters, returns, and brief examples.\n"
    if category == "testing":
        expected = (extra or {}).get("expected_test", "tests/test_<name>.py")
        return f"- Create {expected} and add at least one unit test; use pytest fixtures and descriptive names.\n"
    return "- Apply standard refactorings and add tests.\n"

def override_weights(new_weights: dict | None):
    global DEFAULT_WEIGHTS
    if not new_weights:
        return
    # copy to a mutable dict and update
    w = dict(DEFAULT_WEIGHTS)
    for k, v in new_weights.items():
        if isinstance(v, (int, float)):
            w[k] = float(v)
    # rebind DEFAULT_WEIGHTS to updated mapping
    DEFAULT_WEIGHTS = w  # type: ignore[assignment]
