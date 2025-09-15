from __future__ import annotations
from pathlib import Path
from typing import List
try:
    from tree_sitter import Language, Parser
except Exception:
    Language = None  # type: ignore
    Parser = None    # type: ignore

from cqia.parsing.ir import FunctionIR, ModuleIR, Span

def _fallback_module(path: Path, text: str, lang_hint: str) -> ModuleIR:
    # No parsed functions; still return a ModuleIR so other detectors can run on file text.
    return ModuleIR(path=Path(path), lang=lang_hint, functions=[])

def parse_js_ts(path: Path, text: str, lang_hint: str) -> ModuleIR:
    if Parser is None or Language is None:
        return _fallback_module(path, text, lang_hint)
    try:
        parser = Parser()
        # Expect caller to have set Language instances globally; if not available, fallback.
        try:
            from cqia.vendor.ts_languages import JAVASCRIPT, TYPESCRIPT  # optional
        except Exception:
            return _fallback_module(path, text, lang_hint)
        parser.set_language(JAVASCRIPT if lang_hint == "javascript" else TYPESCRIPT)
        src = text.encode("utf-8", errors="ignore")
        tree = parser.parse(src)
        root = tree.root_node
        functions: List[FunctionIR] = []
        stack = [root]
        while stack:
            node = stack.pop()
            for i in range(len(node.children) - 1, -1, -1):
                stack.append(node.children[i])
            if node.type in ("function_declaration",):
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue
                name = src[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="ignore").strip()
                if not name:
                    continue
                s_line = int(node.start_point) + 1
                e_line = int(node.end_point) + 1
                body_src = src[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
                functions.append(
                    FunctionIR(
                        id=f"{path.as_posix()}::{name}:{s_line}",
                        name=name,
                        lang=lang_hint,
                        span=Span(path=Path(path), start_line=s_line, end_line=e_line),
                        doc=None,
                        text=body_src,
                        metrics={"complexity_branch_count": 0.0},
                    )
                )
        return ModuleIR(path=Path(path), lang=lang_hint, functions=functions)
    except Exception:
        return _fallback_module(path, text, lang_hint)
