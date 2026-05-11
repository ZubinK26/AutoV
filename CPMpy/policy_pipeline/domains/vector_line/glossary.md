# vector_line

- `LINE_LEN`: number of boolean flags in the line (`DOMAIN_DIMENSIONS`).
- `line_flags`: 1D vector of Booleans indexed `0 .. LINE_LEN-1`.
- Rule: every flag must hold (`cp.all` over the line).
