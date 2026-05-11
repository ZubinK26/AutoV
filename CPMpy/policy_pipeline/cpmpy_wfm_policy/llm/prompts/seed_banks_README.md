# Seed bank (Phase 0 + Formalizer)

- **seed_signatures/** — validated `signature.py`-style references; first entry is `refund_example.py` from `domains/refund_example/`. Add more `.py` files as domains are validated.
- **seed_glossaries/** — YAML glossaries aligned to seed signatures; `refund_example.yaml` matches the refund bundle.
- **seed_examples.json** (repo root of prompts) — NL → CPMpy rule examples for the **Formalizer** (Phase 1), not Phase 0.

If this bank is empty, few-shot quality for the Signature Drafter and Glossary Drafter is reduced until you add curated seeds.
