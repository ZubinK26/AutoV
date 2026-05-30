# External world fill — golden.sat

Given merged assignments (grounded + derived), predict whether the **full compiled policy** is satisfiable with those values (and closed-world defaults for any remaining grounded `not_found`).

Output JSON only:

```json
{
  "golden": { "sat": true }
}
```

- `true`: case should be compatible with the policy model.
- `false`: facts should contradict the policy.
- JSON only.
