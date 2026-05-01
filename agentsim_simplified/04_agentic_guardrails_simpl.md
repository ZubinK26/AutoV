# Agentic guardrails (simplified)
#
# Canonical NL for agentsim_simplified. Feed to: python -m wfm_orchestration.nl_chunk_smt_policy_pipeline --nl-file agentsim_simplified/04_agentic_guardrails_simpl.md
# Non-comment lines below are one rule/declaration per line for the chunk parser.

A customer is identified by a unique customer identifier and has a KYC status that is either VERIFIED or FAILED.
A customer has a vulnerable flag that is either true or false.
A customer has a field named recent goodwill credit total which is a non-negative amount in pence maintained by the runtime.
An account is identified by a unique account identifier and belongs to exactly one customer.
An account has a flag named has sanctions block which is either true or false.
A transaction is identified by a unique transaction identifier and belongs to exactly one account.
A transaction has an amount in pence which is a positive integer.
A transaction has a status that is either POSTED or PENDING.
A refund call has a refund type that is one of MERCHANT_REFUND or GOODWILL_CREDIT.
A refund call has an amount in pence which is a positive integer.
A tool call is one of the defined write tool calls and carries typed parameters.

A call to apply a refund of any type requires that the affected customer exists in the database.
A call to apply a refund of any type requires that the affected account exists in the database.
A call to apply a refund of any type requires that the referenced transaction exists in the database.
A call to apply a refund of any type requires that the referenced transaction has status POSTED.
A call to apply a refund of any type is not permitted if the affected customer's KYC status is FAILED.
A call to apply a refund of any type is not permitted if the affected account has its has sanctions block flag set to true.
A call to apply a refund of type MERCHANT_REFUND with an amount greater than the referenced transaction's amount is not permitted.
A call to apply a refund of type GOODWILL_CREDIT with an amount greater than ten thousand pence is not permitted.
A call to apply a refund of type GOODWILL_CREDIT is not permitted if the sum of the customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence.
A call to apply a refund of any type is not permitted if the affected customer's vulnerable flag is set to true and the proposed amount exceeds twenty thousand pence.
