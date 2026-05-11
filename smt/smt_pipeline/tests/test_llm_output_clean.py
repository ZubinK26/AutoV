from smt_pipeline.llm_output_clean import strip_markdown_fenced_smt


def test_strip_fence_plain() -> None:
    inner = "(set-logic ALL)\n(assert true)\n"
    assert strip_markdown_fenced_smt(f"```\n{inner}```") == inner.strip()
    assert strip_markdown_fenced_smt(f"```smt2\n{inner}```") == inner.strip()


def test_strip_fence_no_fence() -> None:
    s = "(assert true)"
    assert strip_markdown_fenced_smt(s) == s
