# LLM Prompts

Eight prompts across two phases of the pipeline. Each prompt file contains the system prompt, user prompt template, and Cursor implementation notes for one role.

## Phase 0 — Signature and glossary drafting

| File | Role | Required? | Temperature | Called when |
|---|---|---|---|---|
| `signature_drafter.md` | Signature Drafter | yes | 0.0 | Once per domain, first stage of Phase 0a |
| `signature_critic.md` | Signature Critic | yes | 0.0 | Once per domain, after Drafter passes structural check |
| `signature_refiner.md` | Signature Refiner | yes | 0.0 | Once per domain, after Critic |
| `glossary_drafter.md` | Glossary Drafter | yes | 0.0 | Once per domain, after Phase 0a is human-approved |

## Phase 1 — Formalization and verification

| File | Role | Required? | Temperature | Called when |
|---|---|---|---|---|
| `formalizer.md` | Formalizer | yes | 0.0 | Once per NL rule, in the FORMALIZE state |
| `back_translator.md` | Back-translator | yes | 0.0 | Once per rule during FULL_VERIFY's roundtrip equivalence check |
| `diagnoser.md` | Diagnoser | yes | 0.0 | When roundtrip equivalence fails for a rule |
| `test_case_generator.md` | Test-case Generator | optional | 0.3 | Per rule, only if `fixture_mode = "generated"` |

## Wiring

All eight prompts assume a Pydantic-based output schema validator runs immediately after each LLM call and rejects malformed or schema-mismatched responses before they reach downstream pipeline components.

All eight should be bound to the LLM SDK's structured-output mode (Anthropic tool-use, OpenAI structured outputs) where available. The prompts describe the JSON output shape regardless, so they work without structured-output mode, but structured-output mode is more reliable.

## Logging

Every LLM call (input, output, latency, model, model version) is logged. Phase 0a calls go to `signature_draft_log.jsonl` with stage tags (`drafter`, `critic`, `refiner`). Phase 0b calls go to `glossary_draft_log.jsonl`. Phase 1 calls go to `verification_log.jsonl`.

## Seed example banks

Three of the prompts reference seed example banks that Cursor must populate:

- `prompts/seed_signatures/` — reference signatures from prior validated domains, used as few-shot examples by the Signature Drafter.
- `prompts/seed_glossaries/` — reference glossaries from prior validated domains, used as few-shot examples by the Glossary Drafter.
- `prompts/seed_examples.json` — formalized rule examples (NL → CPMpy expression pairs), used as few-shot examples by the Formalizer.

The example domain artifact is the source for all three seed banks initially. As more domains are validated, contributing back to the seed banks improves drafting consistency for future domains.

## Failure handling

Each prompt file describes its own failure modes and retry behavior in the Cursor notes section. The orchestrator implements retry-on-malformed-output (up to 3 retries per LLM call) before routing to the repair sub-state machine or escalating to human review.

## Phase ordering

The pipeline is strictly sequential across the eight roles for any single rule:

1. Signature Drafter → Signature Critic → Signature Refiner (loop in Phase 0a, with structural self-checks and human review).
2. Glossary Drafter (Phase 0b, after Phase 0a is approved).
3. Formalizer (per rule, Phase 1).
4. Back-translator (per rule, end of Phase 1).
5. Diagnoser (per rule, only on roundtrip failure).
6. Test-case Generator (optional, per rule, before per-rule cheap checks).

Phases 0a and 0b run once per domain. Phases for steps 3-6 run per rule across the policy.
