# LLM Prompts

Four prompts, one per LLM role defined in the project specification's section 9. Each prompt file contains the system prompt, user prompt template, and Cursor implementation notes for one role.

| File | Role | Required? | Temperature | Called when |
|---|---|---|---|---|
| `formalizer.md` | Formalizer | yes | 0.0 | Once per NL rule, in the FORMALIZE state |
| `back_translator.md` | Back-translator | yes | 0.0 | Once per rule during the FULL_VERIFY state's roundtrip equivalence check |
| `diagnoser.md` | Diagnoser | yes | 0.0 | When roundtrip equivalence fails for a rule |
| `test_case_generator.md` | Test-case Generator | optional | 0.3 | Per rule, only if `fixture_mode = "generated"` |

## Wiring

All four prompts assume a Pydantic-based output schema validator runs immediately after the LLM call and rejects malformed or schema-mismatched responses before they reach downstream pipeline components.

All four prompts should be bound to the LLM SDK's structured-output mode (Anthropic tool-use, OpenAI structured outputs) where available. The prompts describe the JSON output shape regardless, so they work without structured-output mode, but structured-output mode is more reliable.

## Logging

Every LLM call (input, output, latency, model, model version) is logged to `verification_log.jsonl`. This is the audit trail the project specification's success criteria depend on.

## Where seed examples live

The Formalizer's prompt references a seed few-shot example bank. Cursor produces this as `prompts/seed_examples.json` in slice 2 of the build order. The seed bank must include scalar examples, vector+comprehension examples, and at least one global-constraint example, per the project specification's section 9 conflict callout.

## Failure handling

Each prompt file describes its own failure modes and retry behavior in the Cursor notes section. The orchestrator implements retry-on-malformed-output (up to 3 retries per LLM call) before routing to the repair sub-state machine.
