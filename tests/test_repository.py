"""Tests for repository analyzer."""
import tempfile
from pathlib import Path
import pytest
from patchsmith.repository.analyzer import RepositoryAnalyzer


@pytest.mark.asyncio
async def test_analyzer_indexes_python_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "example.py").write_text(
            "class Foo:\n"
            "    def bar(self, x):\n"
            "        return x + 1\n"
        )
        index = await RepositoryAnalyzer().analyze(tmpdir)

    assert "example.py" in index.files
    fi = index.files["example.py"]
    assert any(c.name == "Foo" for c in fi.classes)
    assert any(f.name == "bar" for f in fi.functions)
    assert "Foo" in index.symbols


@pytest.mark.asyncio
async def test_analyzer_skips_pycache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = Path(tmpdir) / "__pycache__"
        cache.mkdir()
        (cache / "cached.py").write_text("x = 1")
        (Path(tmpdir) / "real.py").write_text("y = 2")
        index = await RepositoryAnalyzer().analyze(tmpdir)

    assert "real.py" in index.files
    assert not any("__pycache__" in f for f in index.files)


@pytest.mark.asyncio
async def test_summary_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "a.py").write_text("def foo(): pass\n")
        index = await RepositoryAnalyzer().analyze(tmpdir)

    s = index.summary()
    assert "Files" in s
    assert "Functions" in s
