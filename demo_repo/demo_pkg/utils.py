"""Utility functions."""
from __future__ import annotations


def tokenize(expr: str) -> list[str]:
    """Split expression into tokens."""
    return expr.split()
