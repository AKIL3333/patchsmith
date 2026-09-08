"""Source-weighted re-ranker."""
from __future__ import annotations
from patchsmith.retrieval.hybrid import CodeChunk

SOURCE_WEIGHTS = {"symbol": 1.5, "semantic": 1.2, "lexical": 1.0}


class Reranker:
    async def rank(self, query: str, chunks: list[CodeChunk]) -> list[CodeChunk]:
        for c in chunks:
            c.score = c.score * SOURCE_WEIGHTS.get(c.source, 1.0)
        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks
