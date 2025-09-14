from __future__ import annotations
from dataclasses import dataclass
import ast
from pathlib import Path
from typing import Iterable
from cqia.parsing.ir import ModuleIR

@dataclass(frozen=True)
class SecFinding:
    id: str
    category: str
    message: str
    file: str
    start_line: int
    end_line: int
    hint: str

# Python security scanning via AST
class _PySec(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.findings: list[SecFinding] = []

    def visit_Call(self, node: ast.Call):
        # eval/exec
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            self.findings.append(SecFinding(
                id=f"{self.path.as_posix()}::{getattr(node, 'lineno', 1)}#pysec",
                category="security",
                message=f"Use of {node.func.id} is dangerous",
                file=self.path.as_posix(),
                start_line=getattr(node, "lineno", 1),
                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                hint="Avoid eval/exec; parse inputs or use safe alternatives.",
            ))
        # subprocess(..., shell=True)
        try:
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"Popen", "call", "run"}:
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            self.findings.append(SecFinding(
                                id=f"{self.path.as_posix()}::{getattr(node, 'lineno', 1)}#pysec",
                                category="security",
                                message="subprocess with shell=True can lead to command injection",
                                file=self.path.as_posix(),
                                start_line=getattr(node, "lineno", 1),
                                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                                hint="Pass shell=False and provide args list; sanitize inputs.",
                            ))
                            break
        except Exception:
            pass
        # yaml.load without SafeLoader
        try:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "load":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "yaml":
                    self.findings.append(SecFinding(
                        id=f"{self.path.as_posix()}::{getattr(node, 'lineno', 1)}#pysec",
                        category="security",
                        message="yaml.load without SafeLoader is unsafe",
                        file=self.path.as_posix(),
                        start_line=getattr(node, "lineno", 1),
                        end_line=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                        hint="Use yaml.safe_load or specify SafeLoader.",
                    ))
        except Exception:
            pass
        self.generic_visit(node)

def scan_python_security(mod: ModuleIR, text: str) -> list[SecFinding]:
    try:
        tree = ast.parse(text)
    except Exception:
        return []
    v = _PySec(mod.path)
    v.visit(tree)
    return v.findings

# JS/TS minimal heuristic via text search (Tree-sitter patterns can replace later)
def scan_js_security(mod: ModuleIR, text: str) -> list[SecFinding]:
    findings: list[SecFinding] = []
    lowered = text.lower()
    # eval/new Function
    if "eval(" in lowered:
        findings.append(SecFinding(
            id=f"{mod.path.as_posix()}::eval#jssec",
            category="security",
            message="Use of eval detected",
            file=mod.path.as_posix(),
            start_line=1,
            end_line=1,
            hint="Avoid eval; use JSON.parse or safer parsing.",
        ))
    if "new Function(" .lower() in lowered:
        findings.append(SecFinding(
            id=f"{mod.path.as_posix()}::newfunc#jssec",
            category="security",
            message="Use of new Function detected",
            file=mod.path.as_posix(),
            start_line=1,
            end_line=1,
            hint="Avoid dynamic code execution.",
        ))
    if "child_process" in lowered and ".exec(" in lowered:
        findings.append(SecFinding(
            id=f"{mod.path.as_posix()}::exec#jssec",
            category="security",
            message="child_process.exec detected; risk of command injection",
            file=mod.path.as_posix(),
            start_line=1,
            end_line=1,
            hint="Prefer execFile/spawn with args; sanitize inputs.",
        ))
    return findings
