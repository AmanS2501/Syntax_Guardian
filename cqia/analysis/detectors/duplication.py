from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple, List
import re
from cqia.parsing.ir import FunctionIR
import time

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|==|!=|<=|>=|&&|\|\||[{}()\[\];,.\+\-\*/%<>]")

def normalize(text: str) -> List[str]:
    tokens = _TOKEN_RE.findall(text or "")
    out: List[str] = []
    for t in tokens:
        t = str(t)
        if t.isidentifier():
            out.append("ID")
        elif t.isdigit():
            out.append("NUM")
        else:
            out.append(t)
    return out

def shingles(tokens: List[str], k: int = 7) -> set[Tuple[str, ...]]:
    if len(tokens) < k:
        return set()
    return {tuple(tokens[i:i+k]) for i in range(len(tokens) - k + 1)}

def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni else 0.0

@dataclass(frozen=True)
class DupFinding:
    id: str
    category: str
    message: str
    files: tuple[str, str]
    lines: tuple[tuple[int, int], tuple[int, int]]
    similarity: float

def detect_duplication(
    functions: Iterable[FunctionIR],
    k: int = 7,
    threshold: float = 0.90,
    max_funcs: int = 400,
    max_len: int = 2000,
    time_budget_s: float = 8.0,
) -> list[DupFinding]:
    start = time.time()
    fn_list = []
    for fn in functions:
        if len(fn.text or "") <= max_len:
            fn_list.append(fn)
        if len(fn_list) >= max_funcs:
            break

    sigs: list[set] = [shingles(normalize(fn.text or ""), k=k) for fn in fn_list]

    out: list[DupFinding] = []
    for i in range(len(fn_list)):
        if time.time() - start > time_budget_s:
            break
        si = sigs[i]
        if not si:
            continue
        for j in range(i+1, len(fn_list)):
            if fn_list[i].lang != fn_list[j].lang:
                continue
            sj = sigs[j]
            if not sj:
                continue
            sim = jaccard(si, sj)
            if sim >= threshold and str(fn_list[i].span.path) != str(fn_list[j].span.path):
                i_s, i_e = int(fn_list[i].span.start_line), int(fn_list[i].span.end_line)
                j_s, j_e = int(fn_list[j].span.start_line), int(fn_list[j].span.end_line)
                lines_norm = ((i_s if i_s > 0 else 1, i_e if i_e >= i_s else i_s),
                              (j_s if j_s > 0 else 1, j_e if j_e >= j_s else j_s))
                out.append(DupFinding(
                    id=f"{str(fn_list[i].id)}~{str(fn_list[j].id)}#dup",
                    category="duplication",
                    message=f"Near-duplicate functions (Jaccard {sim:.2f})",
                    files=(str(fn_list[i].span.path), str(fn_list[j].span.path)),
                    lines=lines_norm,
                    similarity=float(sim),
                ))
    return out
