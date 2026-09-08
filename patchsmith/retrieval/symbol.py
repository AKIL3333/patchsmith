"""Symbol-name lookup retriever."""
from __future__ import annotations
import re
from patchsmith.repository.analyzer import RepositoryIndex
from patchsmith.retrieval.hybrid import CodeChunk

CAMEL_RE = re.compile(r"[A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z]|$)")


def _extract_identifiers(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text)
    expanded: list[str] = []
    for tok in raw:
        expanded.append(tok)
        parts = CAMEL_RE.findall(tok)
        if len(parts) > 1:
            expanded.extend(p.lower() for p in parts)
    return list(set(expanded))


class SymbolRetriever:
    async def search(self, query: str, index: RepositoryIndex) -> list[CodeChunk]:
        identifiers = _extract_identifiers(query)
        chunks: list[CodeChunk] = []
        seen: set[tuple[str, str]] = set()

        for ident in identifiers:
            for path in index.symbols.get(ident, []):
                key = (ident, path)
                if key in seen:
                    continue
                seen.add(key)
                fi = index.files.get(path)
                if not fi:
                    continue
                # Find the line where the symbol is defined
                for i, line in enumerate(fi.raw_lines):
                    if ident in line:
                        start = max(0, i - 2)
                        end = min(len(fi.raw_lines), i + 20)
                        chunks.append(CodeChunk(
                            file=path,
                            start_line=start + 1,
                            end_line=end,
                            content="\n".join(fi.raw_lines[start:end]),
                            score=2.0,
                            source="symbol",
                        ))
                        break

        return chunks
