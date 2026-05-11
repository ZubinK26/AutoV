Toy scheduling domain for Phase 0 cold-start testing (success criterion 5).

- Roster window: small integer counts suitable for Hypothesis (see `TEST_SHAPE_BOUNDS` when formalized).
- "Shift slot" means a discrete (nurse-day) or (slot id) pairing; keep bounds small (for example up to 8 nurses and 7 days) for testing.
- Hours are integer or half-hour increments; use a single integer cap per week for simplicity.
