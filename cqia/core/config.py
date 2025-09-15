from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class AnalyzeConfig:
    path: Path
    include: List[str]
    exclude: List[str]
    max_bytes: int
    output_dir: Path
    rules_path: Path | None = None  # NEW

    def resolve_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir