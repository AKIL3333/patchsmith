"""Tests for parser."""
import pytest
from demo_pkg.parser import Parser, ParseError


def test_parse_number():
    p = Parser()
    result = p.parse(["42"])
    assert result["type"] == "number"
    assert result["value"] == 42


def test_parse_empty_raises():
    """Parser should raise ParseError on empty input, not crash with IndexError."""
    p = Parser()
    with pytest.raises(ParseError):
        p.parse([])


def test_validate_number():
    p = Parser()
    assert p.validate({"type": "number", "value": 1})


def test_validate_unknown():
    p = Parser()
    assert not p.validate({"type": "garbage"})
