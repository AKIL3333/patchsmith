"""Hybrid retriever: lexical + semantic + symbol, merged and re-ranked."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from patchsmith.repository.analyzer import RepositoryIndex


@dataclass
class CodeChunk:
    file: str
    start_line: int
    end_line: int
    content: str
    score: float = 0.0
    source: str = "lexical"  # lexical | semantic | symbol


@dataclass
class RetrievalContext:
    chunks: list[CodeChunk] = field(default_factory=list)

    def format(self, max_chunks: int = 10) -> str:
        parts = []
        for c in self.chunks[:max_chunks]:
            parts.append(f"### {c.file} (lines {c.start_line}-{c.end_line})\n{c.content}")
        return "\n\n".join(parts)


class HybridRetriever:
    def __init__(self, top_k: int = 20, chunk_size: int = 40, chunk_stride: int = 20):
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_stride = chunk_stride

    async def retrieve(self, query: str, repo_index: RepositoryIndex) -> RetrievalContext:
        from patchsmith.retrieval.lexical import LexicalRetriever
        from patchsmith.retrieval.symbol import SymbolRetriever
        from patchsmith.retrieval.reranker import Reranker

        lexical = LexicalRetriever(self.chunk_size, self.chunk_stride)
        symbol = SymbolRetriever()
        reranker = Reranker()

        lex_chunks, sym_chunks = await asyncio.gather(
            lexical.search(query, repo_index),
            symbol.search(query, repo_index),
        )

        # Merge, deduplicate by (file, start_line)
        seen: set[tuple[str, int]] = set()
        merged: list[CodeChunk] = []
        for c in sym_chunks + lex_chunks:
            key = (c.file, c.start_line)
            if key not in seen:
                seen.add(key)
                merged.append(c)

        ranked = await reranker.rank(query, merged)
        return RetrievalContext(chunks=ranked[: self.top_k])
