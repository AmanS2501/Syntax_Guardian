"""
AST-based chunker for extracting functions, classes, methods, and docstrings from code files.
"""
from __future__ import annotations
import ast
from pathlib import Path
from typing import List, Optional, Union
from dataclasses import dataclass
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

@dataclass
class CodeChunk:
    content: str
    chunk_type: str  # 'function' | 'class' | 'method' | 'module_docstring' | 'generic'
    file_path: str
    start_line: int
    end_line: int
    name: str
    parent_name: Optional[str] = None
    language: str = "python"
    complexity_score: Optional[float] = None
    docstring: Optional[str] = None

class ASTFunctionChunker:
    def __init__(self, max_chunk_size: int = 2000, chunk_overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def extract_chunks(self, file_path: str, content: str, language: str = "python") -> List[CodeChunk]:
        if language.lower() == "python":
            return self._extract_python_chunks(file_path, content)
        if language.lower() in {"javascript", "typescript"}:
            return self._extract_js_chunks(file_path, content, language)
        return self._extract_generic_chunks(file_path, content, language)

    def _extract_python_chunks(self, file_path: str, content: str) -> List[CodeChunk]:
        chunks: List[CodeChunk] = []
        try:
            tree = ast.parse(content)
            lines = content.splitlines()

            # Module docstring
            module_docstring = ast.get_docstring(tree)
            if module_docstring:
                chunks.append(CodeChunk(
                    content=module_docstring,
                    chunk_type="module_docstring",
                    file_path=file_path,
                    start_line=1,
                    end_line=len(module_docstring.splitlines()),
                    name=f"{Path(file_path).stem}_module_doc",
                    language="python",
                    docstring=module_docstring
                ))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_chunk = self._extract_function_chunk(node, lines, file_path)
                    if fn_chunk:
                        chunks.append(fn_chunk)
                elif isinstance(node, ast.ClassDef):
                    cl_chunk = self._extract_class_chunk(node, lines, file_path)
                    if cl_chunk:
                        chunks.append(cl_chunk)
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            m_chunk = self._extract_function_chunk(item, lines, file_path, parent_class=node.name)
                            if m_chunk:
                                chunks.append(m_chunk)
        except SyntaxError:
            return self._extract_generic_chunks(file_path, content, "python")
        return chunks

    def _extract_function_chunk(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        lines: List[str],
        file_path: str,
        parent_class: Optional[str] = None
    ) -> Optional[CodeChunk]:
        try:
            start_line = int(getattr(node, "lineno", 1))
            end_line = int(getattr(node, "end_lineno", start_line + 10))
            end_line = min(end_line, len(lines))
            body = "\n".join(lines[start_line - 1:end_line])
            docstring = ast.get_docstring(node)
            complexity = self._complexity(node)
            ctype = "method" if parent_class else "function"
            name = f"{parent_class}.{node.name}" if parent_class else node.name
            return CodeChunk(
                content=body,
                chunk_type=ctype,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                name=name,
                parent_name=parent_class,
                language="python",
                complexity_score=complexity,
                docstring=docstring
            )
        except Exception:
            return None

    def _extract_class_chunk(self, node: ast.ClassDef, lines: List[str], file_path: str) -> Optional[CodeChunk]:
        try:
            start = int(getattr(node, "lineno", 1))
            # include the class signature and initial body (before first method)
            class_def_end = start
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    break
                class_def_end = int(getattr(item, "end_lineno", getattr(item, "lineno", class_def_end)))
            class_def_end = min(class_def_end, len(lines))
            text = "\n".join(lines[start - 1:class_def_end])
            docstring = ast.get_docstring(node)
            return CodeChunk(
                content=text,
                chunk_type="class",
                file_path=file_path,
                start_line=start,
                end_line=class_def_end,
                name=node.name,
                language="python",
                docstring=docstring
            )
        except Exception:
            return None

    def _extract_js_chunks(self, file_path: str, content: str, language: str) -> List[CodeChunk]:
        import re
        chunks: List[CodeChunk] = []
        lines = content.splitlines()
        patterns = [
            r'^\s*function\s+([\w$]+)\s*\(',
            r'^\s*const\s+([\w$]+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
            r'^\s*([\w$]+)\s*:\s*(?:async\s+)?function',
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+([\w$]+)',
        ]
        for i, line in enumerate(lines):
            for pat in patterns:
                m = re.match(pat, line)
                if m:
                    name = m.group(1)
                    start_line = i + 1
                    end_line = self._find_js_end(lines, i)
                    text = "\n".join(lines[i:end_line])
                    docstring = self._extract_jsdoc(lines, i)
                    chunks.append(CodeChunk(
                        content=text,
                        chunk_type="function",
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        name=name,
                        language=language,
                        docstring=docstring
                    ))
                    break
        if not chunks:
            chunks.extend(self._extract_generic_chunks(file_path, content, language))
        return chunks

    def _find_js_end(self, lines: List[str], start_idx: int) -> int:
        brace = 0
        in_fn = False
        for i in range(start_idx, len(lines)):
            s = lines[i]
            if not in_fn and "{" in s:
                in_fn = True
            if in_fn:
                brace += s.count("{") - s.count("}")
                if brace <= 0:
                    return i + 1
        return min(start_idx + 80, len(lines))

    def _extract_jsdoc(self, lines: List[str], func_start: int) -> Optional[str]:
        i = func_start - 1
        acc: List[str] = []
        while i >= 0:
            s = lines[i].strip()
            if s.endswith("*/"):
                acc.append(s)
                i -= 1
                while i >= 0 and not lines[i].strip().startswith("/**"):
                    acc.append(lines[i].strip())
                    i -= 1
                if i >= 0:
                    acc.append(lines[i].strip())
                acc.reverse()
                return "\n".join(acc)
            if s == "" or s.startswith("//"):
                i -= 1
            else:
                break
        return None

    def _extract_generic_chunks(self, file_path: str, content: str, language: str) -> List[CodeChunk]:
        out: List[CodeChunk] = []
        parts = self.text_splitter.split_text(content or "")
        for idx, part in enumerate(parts):
            out.append(CodeChunk(
                content=part,
                chunk_type="generic",
                file_path=file_path,
                start_line=1 + idx * 50,
                end_line=1 + (idx + 1) * 50,
                name=f"{Path(file_path).stem}_chunk_{idx}",
                language=language
            ))
        return out

    def _complexity(self, node: ast.AST) -> float:
        count = 1
        for ch in ast.walk(node):
            if isinstance(ch, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.IfExp)):
                count += 1
            elif isinstance(ch, ast.BoolOp):
                count += max(0, len(getattr(ch, "values", [])) - 1)
            elif isinstance(ch, ast.ExceptHandler):
                count += 1
        return float(count)

    def chunks_to_documents(self, chunks: List[CodeChunk]) -> List[Document]:
        docs: List[Document] = []
        for c in chunks:
            md = {
                "file_path": c.file_path,
                "chunk_type": c.chunk_type,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "name": c.name,
                "language": c.language,
                "file_name": Path(c.file_path).name,
                "file_stem": Path(c.file_path).stem,
            }
            if c.parent_name:
                md["parent_name"] = c.parent_name
            if c.complexity_score is not None:
                md["complexity_score"] = float(c.complexity_score)
            if c.docstring:
                md["docstring"] = c.docstring
            content = c.content
            if c.docstring and c.chunk_type != "module_docstring":
                content = f"# Docstring:\n{c.docstring}\n\n# Code:\n{c.content}"
            docs.append(Document(page_content=content, metadata=md))
        return docs
