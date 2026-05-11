"""Fill ``formalizer.md`` / ``critic.md`` / ``repairer.md`` placeholders."""

from __future__ import annotations

import re
from pathlib import Path

from nagv.paths import PROMPTS_DIR

# Placeholder tokens used by the current prompt templates (see ``NagV/prompts/*.md``).
_FORMALIZER_NL_PLACEHOLDER = "[INSERT NL RULESET HERE]"
_CRITIC_NL_PLACEHOLDER = "[INSERT ORIGINAL NL TEXT HERE]"
_CRITIC_CODE_PLACEHOLDER = "[INSERT GENERATED PYTHON CODE HERE]"
_REPAIRER_CODE_PLACEHOLDER = "[INSERT CURRENT PYTHON CODE HERE]"
_REPAIRER_DIAG_PLACEHOLDER = "[INSERT LATEST DIAGNOSTIC / CRITIC FEEDBACK HERE]"


def load_prompt(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.is_file():
        raise FileNotFoundError(f"missing prompt {p}")
    return p.read_text(encoding="utf-8")


def inject_formalizer_base(template: str, nl_ruleset: str) -> str:
    """
    Insert NL after the ``INPUT RULESET`` heading.

    Supports, in order:

    - ``[INSERT NL RULESET HERE]`` (current prompts)
    - First empty ``[ ]`` pair after that heading (legacy)
    """
    idx = template.find("INPUT RULESET")
    if idx < 0:
        return template.rstrip() + "\n\n### INJECTED NL RULESET\n\n" + nl_ruleset.strip() + "\n"
    head, tail = template[:idx], template[idx:]
    nl_body = nl_ruleset.strip()
    if _FORMALIZER_NL_PLACEHOLDER in tail:
        new_tail = tail.replace(_FORMALIZER_NL_PLACEHOLDER, "[\n" + nl_body + "\n]", 1)
        return head + new_tail
    new_tail, n = re.subn(r"\[\s*\]", "[\n" + nl_body + "\n]", tail, count=1)
    if n == 0:
        return head + tail + "\n\n" + nl_body + "\n"
    return head + new_tail


def inject_formalizer_with_feedback(base: str, feedback: str) -> str:
    if not feedback.strip():
        return base
    return base.rstrip() + "\n\n### ITERATION FEEDBACK (address before generating)\n\n" + feedback.strip() + "\n"


def inject_repairer(template: str, nl_ruleset: str, current_python: str, diagnostic: str) -> str:
    """Fill ``repairer.md`` XML sections / INSERT placeholders (no ``INPUT RULESET`` in that file)."""
    t = template
    if _CRITIC_NL_PLACEHOLDER in t:
        t = t.replace(_CRITIC_NL_PLACEHOLDER, nl_ruleset.strip(), 1)
    elif _FORMALIZER_NL_PLACEHOLDER in t:
        t = t.replace(_FORMALIZER_NL_PLACEHOLDER, nl_ruleset.strip(), 1)
    else:
        t = inject_formalizer_base(t, nl_ruleset)

    if _REPAIRER_CODE_PLACEHOLDER in t:
        t = t.replace(_REPAIRER_CODE_PLACEHOLDER, current_python.strip(), 1)
    else:
        t = _replace_labeled_bracket_block(
            t,
            label=r"\*\*\[CURRENT PYTHON\]:\*\*",
            content=current_python.strip(),
        )

    if _REPAIRER_DIAG_PLACEHOLDER in t:
        t = t.replace(_REPAIRER_DIAG_PLACEHOLDER, diagnostic.strip(), 1)
    else:
        t = _replace_labeled_bracket_block(
            t,
            label=r"\*\*\[LATEST DIAGNOSTIC\]:\*\*",
            content=diagnostic.strip(),
        )
    return t


def inject_critic(template: str, nl_ruleset: str, python_code: str) -> str:
    """Fill critic NL + code placeholders (INSERT tokens or legacy ``**[...]:**`` brackets)."""
    nl_q = nl_ruleset.strip()
    code_q = python_code.strip()

    if _CRITIC_NL_PLACEHOLDER in template:
        t = template.replace(_CRITIC_NL_PLACEHOLDER, nl_q, 1)
    else:
        t = _replace_labeled_bracket_block(
            template,
            label=r"\*\*\[ORIGINAL NL RULESET\]:\*\*",
            content=nl_q,
        )

    if _CRITIC_CODE_PLACEHOLDER in t:
        t = t.replace(_CRITIC_CODE_PLACEHOLDER, code_q, 1)
    else:
        t = _replace_labeled_bracket_block(
            t,
            label=r"\*\*\[GENERATED NAGINI CODE\]:\*\*",
            content=code_q,
        )
    return t


def _replace_labeled_bracket_block(text: str, label: str, content: str) -> str:
    rx = re.compile(
        rf"({label}\s*\n\s*)(\[(?:[^\]]|\[[^\]]*\])*\])",
        re.DOTALL | re.IGNORECASE,
    )
    m = rx.search(text)
    if not m:
        return text + f"\n\n{content}\n"
    inner = "[\n" + content + "\n]"
    return text[: m.start()] + m.group(1) + inner + text[m.end() :]


def normalize_nagini_contracts_imports(source: str) -> str:
    """Rewrite legacy ``from nagini_contracts import ...`` to ``.contracts`` imports.

    The ``nagini-contracts`` wheel ships an empty ``nagini_contracts.__init__``; contract
    helpers live in ``nagini_contracts.contracts``. Nagini's translator follows imports and
    fails with "no attribute Requires" if only the package root is used.
    """

    def repl(m: re.Match[str]) -> str:
        indent, rest = m.group(1), m.group(2).strip()
        if rest.startswith("contracts"):
            return m.group(0)
        return f"{indent}from nagini_contracts.contracts import {rest}"

    pattern = re.compile(r"(?m)^(\s*)from\s+nagini_contracts\s+import\s+(.+)$")
    return pattern.sub(repl, source)


def extract_python_code(raw: str) -> str | None:
    """Extract ```python ... ``` or first ``` block; else full stripped text if looks like code.

    If the opening fence is present but the closing ``` is missing (common when the model
    hits an output limit), return the text after the opening fence so repair/syntax passes
    can recover.
    """
    raw = raw.strip()
    fence = re.search(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    open_only = re.search(r"```(?:python)?\s*\n(.*)", raw, re.DOTALL | re.IGNORECASE)
    if open_only:
        body = open_only.group(1).strip()
        if body and ("def " in body or body.startswith("from ") or body.startswith("import ")):
            return body
    if raw.startswith("from ") or raw.startswith("import ") or "@Requires" in raw:
        return raw
    return None


ABORT_PHRASE = "ABORT: Ruleset exceeds decidable scope."


def is_abort_response(text: str) -> bool:
    t = text.strip()
    if ABORT_PHRASE in t and "def " not in t:
        return True
    if t.startswith("ABORT:"):
        return True
    return False


def critic_passed(raw: str) -> bool:
    """True when the **last** ``[VERDICT: …]`` in the response is ``PASS``.

    The critic prompt asks for an ``<audit_trail>`` that often uses words like
    "boundary drift" or "no … drift"; a naive ``\"DRIFT\" in text`` check would
    reject legitimate ``[VERDICT: PASS]`` outputs.
    """
    t = raw.strip()
    matches = list(re.finditer(r"\[VERDICT:\s*([^\]]+)\]", t, re.IGNORECASE))
    if not matches:
        return False
    last = matches[-1].group(1).strip().upper()
    return last == "PASS"


def critic_detected_drift(raw: str) -> bool:
    return "DRIFT DETECTED" in raw.upper()
