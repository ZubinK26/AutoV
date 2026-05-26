# Pivot pipeline architecture

Overview of the full pivot pipeline (including Pivot WFM), with a diagram and a plain-language workflow for readers who are not familiar with project-specific vocabulary.

## Viewing the diagram

The diagram below is written in [Mermaid](https://mermaid.js.org/). A plain text editor shows the source only; you need a **Markdown preview that supports Mermaid**, or view this file on **GitHub** (which renders Mermaid in `.md` files). You can also paste the fenced `mermaid` block into [mermaid.live](https://mermaid.live) to view or export PNG/SVG.

---

## Architecture diagram

```mermaid
flowchart TB
  subgraph prewfm["Optional pre–WFM — Scope rewriter"]
    REF["Reference doc / policy_intent_spec"]
    SR["scope-rewriter CLI"]
    LAT["latest.nl + latest.json sidecar"]
  end

  subgraph inputs["Inputs"]
    NL["Source NL rules file (--input)"]
  end

  subgraph phase0["Phase 0 — Pivot WFM"]
    WFM["Chunked workflow on the text"]
    WFMout["Normalized text + per-chunk artifacts + progress"]
  end

  subgraph extract["Extraction"]
    EXT["Turn lines into structured rule objects (JSON)"]
    REG["Registry pass: align names across rules (default on; use --skip-registry to disable)"]
    RULES["Frozen rule list for this run"]
  end

  subgraph formal["Formal model & solver"]
    COMP["Build meta-scheme + Z3 encoding from rules"]
    Z3["Automated consistency check (SAT solver)"]
    REPAIR_STRUCT["Structural repair when compilation fails (repairer rounds; see --repairer-max-rounds)"]
  end

  subgraph checks["Lightweight checks"]
    PRE["Heuristic: text vs model sanity"]
  end

  subgraph tester["Tester (--with-tester)"]
    TEST["Processed NL vs linearized IR (per-rule content)"]
  end

  subgraph critic["Semantic critic (--with-critic)"]
    SYN["English summary of the math model (synthetic_en.md)"]
    COMPARE["Compare normalized text to summary"]
    DRIFT["PASS or mismatch (DRIFT)"]
    SEM_REPAIR["Semantic repair (Repairer_Piv / interactive DRIFT path)"]
  end

  subgraph cross["Cross-critic (--with-cross-critic)"]
    LIN["Linearized view of rules for review"]
    XC["LLM: text vs linearized rules"]
    XREPAIR["Cross repair (--with-cross-repair)"]
  end

  subgraph postcross["Post–cross semantic pass"]
    CRIT2["Final semantic alignment after cross succeeds"]
  end

  subgraph irguard["Guards (can block if configured)"]
    VAR["Internal rule-shape checks"]
  end

  subgraph templates["Template suite (--with-template-generator or --template-suite)"]
    TGEN["Suite JSON: LLM fills instances under fixed kinds (--with-template-generator)"]
    TRUN["Execute instances in real Z3; compare to golden"]
    TREP["template_run_report.json"]
  end

  subgraph out["Outputs"]
    SUM["Run summary + outcome"]
    ART["Artifacts on disk (JSON, reports, traces)"]
  end

  REF --> SR --> LAT
  LAT -.->|often used as pivot --input| NL
  NL --> WFM --> WFMout --> EXT --> REG --> RULES
  RULES --> COMP
  COMP --> REPAIR_STRUCT
  REPAIR_STRUCT --> COMP
  COMP --> Z3 --> PRE

  PRE --> TEST
  TEST --> SYN
  PRE --> SYN
  SYN --> COMPARE --> DRIFT
  DRIFT --> SEM_REPAIR
  SEM_REPAIR --> COMPARE
  DRIFT --> LIN

  LIN --> XC --> XREPAIR
  XREPAIR --> XC
  XC --> CRIT2

  Z3 --- VAR
  PRE --- VAR
  DRIFT --- VAR
  XC --- VAR
  CRIT2 --- VAR

  CRIT2 -.-> TGEN
  PRE -.-> TGEN
  TGEN --> TRUN --> TREP
  VAR --> TGEN

  TREP --> SUM --> ART
  SUM --> ART
```

### How to read the diagram

- **Top to bottom** is the usual order of stages for a given run.
- **Default CLI** runs WFM → extract (with registry, unless `--skip-registry`) → compile → Z3 → precheck → outcome. Stages in boxes labeled with **`--with-...`** run only when that flag is set (or when a failure triggers repair loops).
- **Structural repair** runs when compilation fails and LLM repair is allowed (not when `--no-llm` or repair rounds are zero).
- **Guards** (internal rule-shape checks) can run at several points and may **stop the run** if you pass strict failure flags.
- **Optional scope rewriter** (`scope-rewriter` / `scope_rewriter_cli`) turns a **reference Markdown** (or policy-intent spec) into **`latest.nl`** + **`latest.json`** before Phase 0; pivot is then run with **`--input`** pointing at that NL file (or equivalent).
- **Temporal surrogates (no time axis):** Process order and prerequisites are **not** a separate solver dimension. Eight patterns **T1–T8** (scalar order, implication chains, phases, k-of-n, etc.) map to the **existing** eight core + optional vNext templates; see [`../../improved-scope.md`](../../improved-scope.md) Part G and [`prompts/temporal_surrogates_addendum.md`](prompts/temporal_surrogates_addendum.md).
- **Template suite** runs **late**, after the run has reached **precheck** and any optional **tester / critic / cross-critic / post–cross** stages you enabled—it exercises the **same** compiled model for that work-dir. Arrows from **both** `CRIT2` and `PRE` to `TGEN` indicate: if cross-critic never runs, the pipeline can still reach template generation when flags are set (no hard dependency on the post–cross critic-only path). **Template kinds and JSON shape are fixed by schema**; with `--with-template-generator`, an LLM **instantiates** concrete tests (worlds, queries, golden expectations) from policy context—not inventing the template format.

---

## Workflow (plain language)

**What you start with**  
Someone writes a policy as a list of plain-English rules in a file, or a longer document that an optional **scope rewriter** turns into encodable lines (`latest.nl`) plus a sidecar (`latest.json`). The pipeline’s job is to make that policy **precise enough for a computer to reason about** and to give you **evidence** that the computer’s version matches what the English says.

**Step 0 — Scope rewriter (optional)**  
When used, a **pre-WFM** step normalizes long-form text into **one rule per line** NL and records fidelity notes. Pivot WFM then runs on the resulting **`--input`** file.

**Step 1 — Clean and stabilize the English (Pivot WFM)**  
The system processes the **`--input`** file **in chunks** through a fixed writing workflow. It may rewrite unclear phrasing, split or merge chunks, and records what it did per chunk so you can **resume** if something fails mid-run. The main output is **normalized English**: the version of the policy the rest of the steps will treat as authoritative, plus supporting logs and handoff records.

**Step 2 — Extract structured rules**  
A step (often LLM-assisted) turns the normalized English into a **structured list of rules**—conditions, thresholds, allowed values, exceptions—in a machine-readable format. **By default**, an **identifier registry** pass **standardizes names** (variables, enums) so everything lines up; you can skip it with `--skip-registry` when you need to. If extraction hits a bad line, interactive mode can ask how to fix or skip.

**Step 3 — Build a formal model and ask the solver**  
Those structured rules are **compiled** into a mathematical model. A **solver** checks whether the policy-as-modeled can “make sense” together (for example, is not trivially impossible in the way the encoding expects). If compilation fails, the pipeline can run **structural repair** for a configured number of rounds (see `--repairer-max-rounds`) to fix the rule shape and retry before surfacing a hard failure.

**Step 4 — Quick sanity pass**  
A lightweight check compares the English and the model for obvious mismatches (for example numbers that appear in the model but not in the source text). This is **heuristic**: it can warn without meaning the model is wrong.

**Step 5 — Tester (`--with-tester`)**
When enabled, an LLM audit compares **processed NL** to a **linearized assessment view** for **per-rule content** alignment. `assessment_linearize.py` writes **`linearized_model_for_assessment.txt`** and **`linearized_model_for_cross_critic.txt`** (same body) from **pre-lowering** `rules_extracted.json`, so `K_OF_N` and multi-term `SUM_THRESHOLD` stay readable; compile still uses lowered core for Z3. **`expansion_assessment_digest.md`** is passed to the pivot critic when vNext templates are present. Runs **after precheck, before pivot critic**. See `dev_plans/dev_plan_k_of_n_and_assessment_views_v1.md`.

**Step 5b — Test-Repairer (optional, interactive)**
When `--with-test-repair` and `--interactive-tester` or `--interactive-policy` are set and the tester reports `issues`, the operator **triages each finding** (approve / ignore), then may type `REPAIR` to run **Test-Repairer** on **approved findings only**, or `PROCEED_INCOMPLETE` to continue. After repair: recompile → Z3 → synthetic → precheck → linearize → **re-run tester** (bounded rounds via `PIVOT_TESTER_REPAIR_MAX_ROUNDS`). Artifacts: `tester_repair_handoff.json`, `rules_after_test_repair.json`, `test_repairer_trace.jsonl`.

**Step 6 — Semantic critic (`--with-critic`)**  
When enabled, the system generates a **plain-English description of what the math model actually enforces** and compares it to the normalized policy text. If they disagree in a material way, you get a **mismatch (DRIFT)** verdict; you can run **semantic repair**, type through interactive prompts, or explicitly agree to continue with known gaps (`PROCEED_INCOMPLETE`-style handoff).

**Step 7 — Cross-critic (`--with-cross-critic`)**  
When enabled, another step compares the policy text to a **flattened, line-by-line rendering** of the formal rules—useful for catching drift in how conditions were encoded. **`--with-cross-repair`** allows an automated repair loop when the cross review reports issues (subject to interactive gates if you enable them).

**Step 8 — Post–cross semantic pass**  
If cross-critic ran and succeeded on your chosen path, the pipeline runs a **final semantic alignment** check so text and model still agree after any cross-stage edits.

**Throughout — internal shape checks**  
The pipeline runs **internal consistency checks** on how certain rule patterns are encoded (for example special “product” patterns). Depending on flags, failures here **block** the run.

**Step 9 — Template suite (`--with-template-generator` / `--template-suite`)**  
Near the end of a successful run, you can **ask the LLM to populate** a JSON suite—**using predefined template kinds** (scenario types, fields, and schema are fixed; the model only fills in allowed instances from your policy context)—or **supply** a suite file you wrote or checked in yourself. Each scenario is executed with the **real solver** and compared to expectations in the file; a **report** records pass, fail, and error counts. Template failures are typically **non-fatal** for the pipeline exit code (they inform you without always blocking the run).

**What you end up with**  
On disk you get **normalized text**, **structured rules**, **compiled model**, **solver output**, **reports from whichever alignment stages you enabled**, and a **single run summary** that says whether the run completed, was blocked, or finished with warnings. Together that package is what you would share or archive to show **what was formalized and how strongly it was validated**.
