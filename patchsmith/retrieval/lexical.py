"""BM25-style keyword retrieval over code chunks."""
from __future__ import annotations
import math
import re
from collections import Counter
from patchsmith.repository.analyzer import RepositoryIndex
from patchsmith.retrieval.hybrid import CodeChunk


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


def _bm25_score(query_terms: list[str], doc_terms: list[str],
                avg_dl: float, k1: float = 1.5, b: float = 0.75) -> float:
    tf = Counter(doc_terms)
    dl = len(doc_terms)
    score = 0.0
    for term in query_terms:
        if term not in tf:
            continue
        f = tf[term]
        score += (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / max(avg_dl, 1)))
    return score


class LexicalRetriever:
    def __init__(self, chunk_size: int = 40, chunk_stride: int = 20):
        self.chunk_size = chunk_size
        self.chunk_stride = chunk_stride

    async def search(self, query: str, index: RepositoryIndex) -> list[CodeChunk]:
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        chunks: list[tuple[float, CodeChunk]] = []
        total_lines = sum(len(fi.raw_lines) for fi in index.files.values())
        n_files = max(len(index.files), 1)
        avg_dl = total_lines / n_files

        for path, fi in index.files.items():
            lines = fi.raw_lines
            for start in range(0, max(len(lines), 1), self.chunk_stride):
                end = min(start + self.chunk_size, len(lines))
                chunk_lines = lines[start:end]
                doc_terms = _tokenize(" ".join(chunk_lines))
                score = _bm25_score(query_terms, doc_terms, avg_dl)
                if score > 0:
                    chunks.append((score, CodeChunk(
                        file=path,
                        start_line=start + 1,
                        end_line=end,
                        content="\n".join(chunk_lines),
                        score=score,
                        source="lexical",
                    )))
                if end >= len(lines):
                    break

        chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in chunks[:50]]
