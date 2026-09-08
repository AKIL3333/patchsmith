"""AST-based repository indexer."""
from __future__ import annotations
import ast
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SKIP_DIRS = {"__pycache__", ".git", ".tox", "node_modules", ".venv", "venv", "build", "dist", ".eggs"}
SKIP_EXTS = {".pyc", ".pyo", ".so", ".egg"}


@dataclass
class ClassInfo:
    name: str
    line: int
    methods: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    line: int
    calls: list[str] = field(default_factory=list)


@dataclass
class FileInfo:
    path: str
    raw_lines: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    def content(self) -> str:
        return "\n".join(self.raw_lines)


@dataclass
class RepositoryIndex:
    root: str
    files: dict[str, FileInfo] = field(default_factory=dict)
    symbols: dict[str, list[str]] = field(default_factory=dict)  # name -> [file, ...]

    def summary(self) -> str:
        n_classes = sum(len(f.classes) for f in self.files.values())
        n_fns = sum(len(f.functions) for f in self.files.values())
        return (
            f"Repository: {self.root}\n"
            f"  Files  : {len(self.files)}\n"
            f"  Classes: {n_classes}\n"
            f"  Functions: {n_fns}\n"
            f"  Symbols: {len(self.symbols)}"
        )


def _parse_file(path: Path, rel: str) -> FileInfo:
    raw = path.read_text(errors="replace").splitlines()
    fi = FileInfo(path=rel, raw_lines=raw)
    try:
        tree = ast.parse("\n".join(raw), filename=str(path))
    except SyntaxError:
        return fi

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
            fi.classes.append(ClassInfo(name=node.name, line=node.lineno, methods=methods))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.append(child.func.attr)
            fi.functions.append(FunctionInfo(name=node.name, line=node.lineno, calls=calls))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                fi.imports.extend(a.name for a in node.names)
            else:
                fi.imports.append(node.module or "")
    return fi


class RepositoryAnalyzer:
    async def analyze(self, repo_path: str) -> RepositoryIndex:
        root = Path(repo_path).resolve()
        index = RepositoryIndex(root=str(root))

        py_files = []
        for p in root.rglob("*.py"):
            if any(s in p.parts for s in SKIP_DIRS):
                continue
            if p.suffix in SKIP_EXTS:
                continue
            py_files.append(p)

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, _parse_file, p, str(p.relative_to(root)))
            for p in py_files
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for fi in results:
            if isinstance(fi, Exception):
                logger.warning("Parse error: %s", fi)
                continue
            index.files[fi.path] = fi
            for cls in fi.classes:
                index.symbols.setdefault(cls.name, []).append(fi.path)
                for m in cls.methods:
                    index.symbols.setdefault(m, []).append(fi.path)
            for fn in fi.functions:
                index.symbols.setdefault(fn.name, []).append(fi.path)

        logger.info("Indexed %d files, %d symbols", len(index.files), len(index.symbols))
        return index
