from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal

Lang = Literal["python", "javascript", "typescript", "unknown"]

@dataclass(frozen=True)
class Span:
    path: Path
    start_line: int
    end_line: int

@dataclass
class FunctionIR:
    id: str
    name: str
    lang: Lang
    span: Span
    doc: Optional[str]
    text: str  # source text for duplication/embedding
    metrics: dict[str, float] = field(default_factory=dict)

@dataclass
class ModuleIR:
    path: Path
    lang: Lang
    functions: list[FunctionIR]
