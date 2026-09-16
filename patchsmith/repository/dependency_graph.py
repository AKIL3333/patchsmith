"""Call graph and import graph construction."""
from __future__ import annotations
from collections import defaultdict
from patchsmith.repository.analyzer import RepositoryIndex


class DependencyGraph:
    def __init__(self, index: RepositoryIndex):
        self.calls: dict[str, list[str]] = defaultdict(list)
        self.imports: dict[str, list[str]] = defaultdict(list)
        self._build(index)

    def _build(self, index: RepositoryIndex) -> None:
        for path, fi in index.files.items():
            for imp in fi.imports:
                self.imports[path].append(imp)
            for fn in fi.functions:
                for callee in fn.calls:
                    self.calls[fn.name].append(callee)

    def callers_of(self, fn: str) -> list[str]:
        return [caller for caller, callees in self.calls.items() if fn in callees]

    def callees_of(self, fn: str) -> list[str]:
        return self.calls.get(fn, [])
