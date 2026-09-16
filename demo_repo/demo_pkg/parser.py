"""Simple expression parser."""
from __future__ import annotations


class ParseError(Exception):
    pass


class Parser:
    """Parses simple arithmetic expressions."""

    def parse(self, tokens: list[str]) -> dict:
        """Parse a token list into an AST node.

        Bug: crashes with AttributeError when tokens is empty because
        it unconditionally accesses tokens[0] without checking length.
        """
        first = tokens[0]  # BUG: IndexError when tokens is empty
        if first.isdigit():
            return {"type": "number", "value": int(first), "rest": tokens[1:]}
        raise ParseError(f"Unexpected token: {first!r}")

    def validate(self, ast: dict) -> bool:
        return ast.get("type") in {"number", "binop"}
