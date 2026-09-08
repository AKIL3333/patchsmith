# demo-repo

A minimal broken Python package used to demonstrate PatchSmith end-to-end repair.

**The bug:** `Parser.parse()` crashes with `IndexError` on empty input
instead of raising `ParseError`.

Run tests to see the failure:
```bash
pytest tests/ -v
```
