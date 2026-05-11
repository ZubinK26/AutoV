"""Python syntax gate (``ast.parse``)."""

from __future__ import annotations

import ast


def syntax_errors(python_src: str) -> str | None:
    try:
        ast.parse(python_src)
    except SyntaxError as e:
        return f"{e.__class__.__name__}: {e.msg} (line {e.lineno})"
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"
    return None
