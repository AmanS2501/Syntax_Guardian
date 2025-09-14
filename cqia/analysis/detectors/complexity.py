from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from cqia.parsing.ir import FunctionIR

@dataclass(frozen=True)
class ComplexityFinding:
    id: str
    category: str
    message: str
    file: str
    start_line: int
    end_line: int
    value: float
    threshold: float

def detect_complexity(functions: Iterable[FunctionIR], warn_at: int = 10) -> list[ComplexityFinding]:
    findings: list[ComplexityFinding] = []
    for fn in functions:
        decisions = int(fn.metrics.get("complexity_branch_count", 0))
        complexity = 1 + decisions  # decision-points + 1
        if complexity >= warn_at:
            findings.append(ComplexityFinding(
                id=f"{fn.id}#complexity",
                category="complexity",
                message=f"High cyclomatic complexity: {complexity} (≥ {warn_at})",
                file=fn.span.path.as_posix(),
                start_line=fn.span.start_line,
                end_line=fn.span.end_line,
                value=complexity,
                threshold=float(warn_at),
            ))
    return findings
