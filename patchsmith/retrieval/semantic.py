"""Embedding-based semantic retrieval (optional; requires sentence-transformers)."""
from __future__ import annotations
import logging
from patchsmith.retrieval.hybrid import CodeChunk
from patchsmith.repository.analyzer import RepositoryIndex

logger = logging.getLogger(__name__)


class SemanticRetriever:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self._model = SentenceTransformer(model_name)
            self._np = np
            self._available = True
        except ImportError:
            logger.warning("sentence-transformers not installed; semantic retrieval disabled")
            self._available = False

    async def search(self, query: str, index: RepositoryIndex,
                     chunk_size: int = 40) -> list[CodeChunk]:
        if not self._available:
            return []

        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, index, chunk_size)

    def _search_sync(self, query: str, index: RepositoryIndex, chunk_size: int) -> list[CodeChunk]:
        np = self._np
        chunks: list[CodeChunk] = []
        texts: list[str] = []

        for path, fi in index.files.items():
            lines = fi.raw_lines
            for start in range(0, max(len(lines), 1), chunk_size // 2):
                end = min(start + chunk_size, len(lines))
                content = "\n".join(lines[start:end])
                chunks.append(CodeChunk(file=path, start_line=start+1, end_line=end,
                                        content=content, source="semantic"))
                texts.append(content)
                if end >= len(lines):
                    break

        if not texts:
            return []

        q_emb = self._model.encode([query])
        c_embs = self._model.encode(texts)
        scores = (c_embs @ q_emb.T).flatten()

        for i, c in enumerate(chunks):
            c.score = float(scores[i])

        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks[:30]
