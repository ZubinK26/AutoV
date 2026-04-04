"""Select stratified FOLIO rows for WFM test examples (English, in-scope biased)."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "datasets" / "folio"


def load_all():
    rows = []
    for fn in ("folio-validation.jsonl", "folio-train.jsonl"):
        with open(ROOT / fn, encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
    return rows


def row_key_full(r):
    return (tuple(p.strip() for p in r["premises"]), r["conclusion"].strip())


def premise_key(r):
    return tuple(p.strip() for p in r["premises"])


def bad_out_of_scope_heuristic(r):
    t = (" ".join(r["premises"]) + " " + r["conclusion"]).lower()
    if "many " in t or "most " in t or "few " in t:
        return True
    if any(x in t for x in ("eventually", "never been", "at some point in time")):
        return True
    return False


def n_prem(r):
    return len(r["premises"])


def clean_premise(p):
    s = p.strip().rstrip()
    if s.startswith("[BG]"):
        s = s[4:].lstrip()
    return s


def normalize_nl(text: str) -> str:
    """Minor normalizations for known FOLIO typos / awkward phrasing (test harness only)."""
    reps = (
        ("lives in well paid.", "lives in a tax haven."),
        ("lives in well paid,", "lives in a tax haven,"),
        ("get a glu.", "get the flu."),
        ("get a glu,", "get the flu,"),
        (
            "If person x is taller than person y, and person y is taller than person z, than x is taller than z",
            "If person x is taller than person y, and person y is taller than person z, then x is taller than z",
        ),
        ("taller than z Peter", "taller than z. Peter"),
    )
    for a, b in reps:
        text = text.replace(a, b)
    return text


def fmt_user_block(r):
    ps = [normalize_nl(clean_premise(p)) for p in r["premises"]]
    body = normalize_nl(" ".join(ps))
    concl = normalize_nl(r["conclusion"].strip())
    return f"{body} In conclusion: {concl}"


def one_per_premise_set(rows):
    """First row per unique premise set (preserves dataset order)."""
    seen = set()
    out = []
    for r in rows:
        pk = premise_key(r)
        if pk in seen:
            continue
        if bad_out_of_scope_heuristic(r):
            continue
        seen.add(pk)
        out.append(r)
    return out


def diff_label(r):
    n = n_prem(r)
    if n <= 2:
        return "easy"
    if n >= 7:
        return "hard"
    return "medium"


def pick_stratified(pool, picked_keys, ne, nm, nh):
    """Pick n easy, medium, hard from pool by premise_key not in picked_keys."""
    easy = [r for r in pool if diff_label(r) == "easy"]
    med = [r for r in pool if diff_label(r) == "medium"]
    hard = [r for r in pool if diff_label(r) == "hard"]
    result = []

    def take(rcat, n_need):
        nonlocal result
        got = 0
        for r in rcat:
            if got >= n_need:
                break
            pk = premise_key(r)
            if pk in picked_keys:
                continue
            picked_keys.add(pk)
            result.append((diff_label(r), r))
            got += 1

    take(easy, ne)
    take(med, nm)
    take(hard, nh)
    return result


def main():
    rows = load_all()
    stories = one_per_premise_set(rows)

    picked_keys = set()

    folio = pick_stratified(stories, picked_keys, 3, 4, 3)

    for r in stories:
        if len(folio) >= 10:
            break
        pk = premise_key(r)
        if pk in picked_keys:
            continue
        picked_keys.add(pk)
        folio.append((diff_label(r), r))

    pfolio = pick_stratified(stories, picked_keys, 2, 5, 3)

    for r in stories:
        if len(pfolio) >= 10:
            break
        pk = premise_key(r)
        if pk in picked_keys:
            continue
        picked_keys.add(pk)
        pfolio.append((diff_label(r), r))

    out_path = pathlib.Path(__file__).resolve().parents[1] / "wfm_folio_pffolio_examples_en.md"
    lines = [
        "# WFM manual test — English examples from FOLIO (and P-FOLIO base text)",
        "",
        "Sources: **FOLIO** v0.0 from [Yale-LILY/FOLIO](https://github.com/Yale-LILY/FOLIO) (CC-BY-SA-4.0).",
        "",
        "**P-FOLIO note:** The Hugging Face dataset [`yale-nlp/P-FOLIO`](https://huggingface.co/datasets/yale-nlp/P-FOLIO) is **gated** (accept license + login). P-FOLIO builds **human proof chains** on top of the same underlying FOLIO natural-language problems. Until you download `P-FOLIO.csv` into `test_sets/datasets/p-folio/`, the **P-FOLIO section below** uses **additional distinct FOLIO premise bundles** (no duplicate with the first ten), each as one English block—the same NL P-FOLIO annotators used as source material. This is suitable for **Agent 1 / WFM** smoke tests; it does **not** include P-FOLIO step-by-step proofs.",
        "",
        "Rough difficulty tags: **easy** / **medium** / **hard** (premise count and structural complexity). `[BG]` background markers from FOLIO are stripped below. A few known FOLIO NL typos are lightly normalized (e.g. tax haven / flu wording) for cleaner manual testing.",
        "",
        "---",
        "",
        "## FOLIO (10 examples)",
        "",
    ]
    for idx, (tag, r) in enumerate(folio, 1):
        lines.append(f"### F-{idx} ({tag})")
        lines.append("")
        lines.append(fmt_user_block(r))
        lines.append("")

    lines.extend(["---", "", "## P-FOLIO base text (10 examples; replace with official CSV rows when available)", ""])
    for idx, (tag, r) in enumerate(pfolio, 1):
        lines.append(f"### PF-{idx} ({tag})")
        lines.append("")
        lines.append(fmt_user_block(r))
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", out_path)
    print("FOLIO:", [(t, len(r["premises"])) for t, r in folio])
    print("PF-base:", [(t, len(r["premises"])) for t, r in pfolio])


if __name__ == "__main__":
    main()
