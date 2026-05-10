The requested token consumption must be strictly less than or equal to 100,000.

The agent's semantic confidence score must be strictly greater than 0.85.

The allocated compute cores multiplied by the requested runtime hours must be less than or equal to 120.

The proposed financial budget multiplied by the task risk multiplier must not exceed 500.

The requested memory allocation must not exceed the agent's pre-authorized memory limit.

The maximum concurrent API calls requested must be strictly less than 50.

The model engine version must be one of the following: "GPT-4", "CLAUDE-3", "GEMINI-3".

The target deployment environment must be one of the following: "DEV", "STAGING", "SANDBOX".

The proposed outbound network port must not be one of the following: 22, 23, 3389.

If the action type is "WRITE", the agent role must be "AUTONOMOUS_EDITOR".

If the target dataset contains PII, the human_in_loop flag must be true.

If the request origin subnet is "EXTERNAL", a cryptographic secondary token must be provided.

If the target geographic region is "EU", the compliance enforcement flag must be true.

If the target system is "FINANCIAL_LEDGER", the required approval level must be "DIRECTOR".

If the action type is "DESTRUCTIVE", the request is immediately denied regardless of other conditions.

If the global quarantine flag is true, the request is immediately denied regardless of other conditions.

If an emergency override token is provided, the budget math limit (Rule 4) and token consumption limit (Rule 1) are bypassed.

If the agent role is "READ_ONLY", the human_in_loop requirement for PII data (Rule 11) is waived.

If the target environment is "SANDBOX", the outbound network port restrictions (Rule 9) are bypassed.

If the request involves system configuration changes, it is denied unless the human_in_loop flag is true.