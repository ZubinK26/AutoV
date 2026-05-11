"""NL numbered digest for assessor line evidence (same line order as chunk NL parsers)."""

from __future__ import annotations


def parse_nl_rule_lines(nl_text: str) -> list[str]:
    """One rule per non-empty line; full-line ``#`` comments and ``---`` skipped (matches chunk pipelines)."""
    out: list[str] = []
    for line in nl_text.splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if t == "---":
            continue
        out.append(line.strip())
    return out


def build_numbered_digest(nl_text: str) -> str:
    rules = parse_nl_rule_lines(nl_text)
    return "\n".join(f"{i + 1:03d}|{r}" for i, r in enumerate(rules))
