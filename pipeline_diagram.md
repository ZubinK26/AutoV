# NL→Z3 pipeline — ASCII diagram & build status

Companion to **`pipeline_spec.md`**. The numbered steps and full architecture are defined there; this file is only the **diagram** and **legend**.

---

## Legend

| Marker | Meaning |
|--------|---------|
| `[ ok ]` | **In repo today:** prompts and/or `test_sets/scripts/` harness runs (Gemini/Claude); not necessarily full product UI. |
| `[ ~ ]` | **Partial:** behavior exists only in test tooling or merge helpers; product orchestration TBD. |
| `[ .. ]` | **Not implemented:** spec only. |
| `[ -- ]` | **Deferred:** separate post-pipeline component (see **`pipeline_spec.md`** — Consistency checking). |

---

## Diagram

```
                          +---------------------------+
                          | 1. User input (NL rule)   |
                          | safety: max_input_codepts |
                          +-------------+-------------+
                                        |
                                        v
                  +---------------------------------------------+
                  | 2. WELL-FORMEDNESS MODULE (WFM)            |
                  |  Limits / exhaustion / LIMIT_EXCEEDED --> |
                  |      return to user (no downstream work)   |
                  |  +--------+   +--------+   +--------+      |
                  |  |Agent 1 |-->|Agent 2 |-->|Agent 3 |      |
                  |  +--------+   +--------+   +--------+      |
                  |  [ ok ] prompts + runners (Gemini / Claude |
                  |       test_sets/scripts/run_wfm_folio_*)   |
                  |                      |                       |
                  |                      v                       |
                  |            +----------------------+          |
                  |            | Confirmation package |          |
                  |            | (per Agent_WFM.md)   |          |
                  |            +----------+-----------+          |
                  |  [ ~ ] full product UI not in repo;        |
                  |        console flow + payloads OK          |
                  |                       |                      |
                  |             accept all| disagree / patch     |
                  |                  |    |                      |
                  |                  |    v                      |
                  |                  | +-----------+            |
                  |                  | | Agent 4   | [ ok ]     |
                  |                  | | (opt.)  | CLI +        |
                  |                  | +-----+---+ interactive  |
                  |                  |       |    + merge       |
                  |                  |       v    preview in    |
                  |                  |  merge / re-run A1..A3   |
                  |                  |  [ ok ] loopback script  |
                  |                  |       |                  |
                  +------------------+-------+------------------+
                                                      |
                              confirmed NL ready for registry
                                                      |
                                                      v
                          +---------------------------+
                          | 3. Registry agent         |  [ .. ]
                          |  search | extract |       |
                          |  resolve | populate       |  Phase 1: auto only     |
                          +-------------+-------------+
                                        |
                                        v
                          +---------------------------+
                          | 4. Formalizer (LLM)       |  [ .. ]
                          +-------------+-------------+
                                        |
                                        v
                          +---------------------------+
                          | 5. Z3 syntax / type check |  [ .. ]
                          +-------------+-------------+
                                        |
                                        v
                          +---------------------------+
                          | 6. Identifier critic      |  [ .. ]
                          +-------------+-------------+
                                        |
                         errors         | ok
                            +-----------+----------+
                            v                      v
                    +---------------+      +-------------+
                    | 7. Repair loop|      | 8. Rule      |
                    |  (formalizer) |      |  accepted    |
                    +-------+-------+      +------+-------+
                            |                     |
                            +--------+------------+
                                     |
                                     v
                          +---------------------------+
                          | rules store + registry    |  [ .. ]
                          | refs persisted            |
                          +-------------+-------------+
                                     |
                                     v
                          +---------------------------+
                          | Consistency / contradiction|  [ -- ]
                          | (future; graph-friendly    |
                          |  registry design above)   |
                          +---------------------------+
```
