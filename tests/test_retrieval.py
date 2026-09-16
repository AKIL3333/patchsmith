"""Tests for retrieval components."""
import pytest
from patchsmith.retrieval.lexical import LexicalRetriever
from patchsmith.retrieval.symbol import SymbolRetriever
from patchsmith.retrieval.reranker import Reranker
from patchsmith.retrieval.hybrid import CodeChunk
from patchsmith.repository.analyzer import RepositoryIndex, FileInfo


def make_index():
    index = RepositoryIndex(root="/tmp/test_repo")
    fi = FileInfo(path="parser.py", raw_lines=[
        "class Parser:",
        "    def parse(self, node):",
        "        if node is None:",
        "            raise ValueError('empty node')",
        "        return node.children",
        "",
        "class Token:",
        "    pass",
    ])
    index.files["parser.py"] = fi
    index.symbols["Parser"] = ["parser.py"]
    index.symbols["parse"] = ["parser.py"]
    return index


@pytest.mark.asyncio
async def test_lexical_finds_keyword():
    chunks = await LexicalRetriever().search("parser crashes empty node", make_index())
    assert len(chunks) > 0
    assert any("parser.py" in c.file for c in chunks)


@pytest.mark.asyncio
async def test_symbol_finds_class():
    chunks = await SymbolRetriever().search("Parser crashes", make_index())
    assert len(chunks) > 0
    assert chunks[0].source == "symbol"


@pytest.mark.asyncio
async def test_reranker_symbol_beats_lexical():
    chunks = [
        CodeChunk(file="a.py", start_line=1, end_line=10,
                  content="x", score=1.0, source="lexical"),
        CodeChunk(file="b.py", start_line=1, end_line=10,
                  content="y", score=1.0, source="symbol"),
    ]
    ranked = await Reranker().rank("query", chunks)
    assert ranked[0].source == "symbol"
