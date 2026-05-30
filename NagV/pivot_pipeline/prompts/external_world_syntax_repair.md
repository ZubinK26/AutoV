# External tester syntax repair

Fix the JSON for a lowered template test instance or fill payload.
Output **valid JSON only** matching the error feedback (Pydantic / schema).

Preserve variable values and provenance unless the error requires changing them.

**scenario:** `template_kind` `"scenario"`, no `query`, `golden.sat` boolean.  
**decision_query:** include `query` + `golden.decision` (`satisfied` | `unsatisfied`).

Do not add markdown fences.
