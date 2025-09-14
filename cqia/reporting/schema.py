from __future__ import annotations
from typing import List, Dict, Literal, Optional, Tuple
from pydantic import BaseModel, Field

# Severities used across the report
Severity = Literal["P0", "P1", "P2", "P3"]

class LocationJSON(BaseModel):
    file: str = Field(..., description="Relative path from repo root")
    start_line: int = Field(..., ge=1, description="1-based start line")
    end_line: int = Field(..., ge=1, description="1-based end line (inclusive)")

class FindingJSON(BaseModel):
    id: str = Field(..., description="Stable identifier for this finding")
    category: str = Field(..., description="Category: security|complexity|duplication|...")
    severity: Severity = Field(..., description="P0..P3")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized 0..1 score used for ranking")
    title: str = Field(..., description="One-line summary")
    file: str = Field(..., description="Relative path of primary location")
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    hint: Optional[str] = Field(None, description="Fix suggestion or remediation steps")
    extra: Optional[Dict] = Field(None, description="Category-specific metadata (e.g., other_file, similarity, complexity)")

class DepMetricsJSON(BaseModel):
    fan_in: Dict[str, int] = Field(..., description="In-degree per node (module/file)")
    fan_out: Dict[str, int] = Field(..., description="Out-degree per node (module/file)")
    cycles: List[List[str]] = Field(..., description="Detected simple cycles (truncated)")
    top_fan_in: List[List[str | int]] = Field(..., description="Top nodes by fan-in [[node, value], ...]")
    top_fan_out: List[List[str | int]] = Field(..., description="Top nodes by fan-out [[node, value], ...]")

class ScanSummaryJSON(BaseModel):
    files_scanned: int = Field(..., ge=0)
    by_language: Dict[str, int] = Field(..., description="Counts per language")

class ReportJSON(BaseModel):
    summary: ScanSummaryJSON
    findings: List[FindingJSON]
    dependencies: DepMetricsJSON
