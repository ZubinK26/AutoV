TRANSACTION_STATUS:
  type: enum
  description: Maps symbolic transaction statuses to integer codes used when the rules refer to whether a transaction is posted or pending.
  value_meanings:
    0: Transaction has status POSTED in the sense used by the refund rules.
    1: Transaction has status PENDING in the sense used by the refund rules.
  example_nl_phrases:
    - A refund call requires that transaction_status is zero (posted); value one means pending and is not sufficient for a refund.
    - A refund call requires that transaction_status is zero (posted); value one means pending and is not sufficient for a refund.

KYC_STATUS:
  type: enum
  description: Maps symbolic KYC outcomes to integer codes used when the rules refer to the affected customer's KYC status.
  value_meanings:
    0: Customer KYC is in the VERIFIED state.
    1: Customer KYC is in the FAILED state as described in the refund rules.
  example_nl_phrases:
    - A refund call is not permitted if the affected customer's KYC status is FAILED.
    - A refund call is not permitted if the affected customer's KYC status is FAILED.

REFUND_TYPE:
  type: enum
  description: Distinguishes merchant refund versus goodwill credit paths referenced when the rules constrain proposed amounts.
  value_meanings:
    0: Merchant refund path for the tool call.
    1: Goodwill credit path for the tool call.
  example_nl_phrases:
    - A merchant refund call with an amount greater than the referenced transaction's amount is not permitted.
    - A goodwill credit call with an amount greater than ten thousand pence is not permitted.

customer_exists:
  type: scalar_field
  description: Boolean flag indicating whether the affected customer exists in the database.
  example_nl_phrases:
    - A refund call requires that the affected customer exists in the database.
    - A refund call requires that the affected customer exists in the database.

account_exists:
  type: scalar_field
  description: Boolean flag indicating whether the affected account exists in the database.
  example_nl_phrases:
    - A refund call requires that the affected account exists in the database.
    - A refund call requires that the affected account exists in the database.

transaction_exists:
  type: scalar_field
  description: Boolean flag indicating whether the referenced transaction exists in the database.
  example_nl_phrases:
    - A refund call requires that the referenced transaction exists in the database.
    - A refund call requires that the referenced transaction exists in the database.

transaction_status:
  type: scalar_field
  description: Integer-coded status of the referenced transaction; zero (posted) is required before allowing a refund call.
  value_meanings:
    0: Transaction has status POSTED.
    1: Transaction has status PENDING.
  example_nl_phrases:
    - A refund call requires that transaction_status is zero (posted); value one means pending and is not sufficient for a refund.
    - A refund call requires that transaction_status is zero (posted); value one means pending and is not sufficient for a refund.

customer_kyc_status:
  type: scalar_field
  description: Integer-coded KYC state of the affected customer; the rules tie FAILED status to blocking refund calls.
  value_meanings:
    0: Customer KYC is in the VERIFIED state.
    1: Customer KYC is in the FAILED state.
  example_nl_phrases:
    - A refund call is not permitted if the affected customer's KYC status is FAILED.
    - A refund call is not permitted if the affected customer's KYC status is FAILED.

account_sanctions_block_flag:
  type: scalar_field
  description: Boolean flag indicating whether the affected account has its sanctions block flag set to true.
  example_nl_phrases:
    - A refund call is not permitted if the affected account has its sanctions block flag set to true.
    - A refund call is not permitted if the affected account has its sanctions block flag set to true.

transaction_amount_pence:
  type: scalar_field
  description: Amount of the referenced transaction in pence; merchant refund amount must not exceed this value per the rules.
  example_nl_phrases:
    - A merchant refund call with an amount greater than the referenced transaction's amount is not permitted.
    - A merchant refund call with an amount greater than the referenced transaction's amount is not permitted.

customer_recent_goodwill_credit_total:
  type: scalar_field
  description: Running total of recent goodwill credits for the customer in pence; used with proposed amount against the fifty thousand pence cap.
  example_nl_phrases:
    - A goodwill credit call is not permitted if the sum of the affected customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence.
    - A goodwill credit call is not permitted if the sum of the affected customer's recent goodwill credit total and the proposed amount exceeds fifty thousand pence.

customer_vulnerable_flag:
  type: scalar_field
  description: Boolean flag indicating whether the affected customer's vulnerable flag is set to true; combined with amount caps in the rules.
  example_nl_phrases:
    - A refund call is not permitted if the affected customer's vulnerable flag is set to true and the proposed refund amount exceeds twenty thousand pence.
    - A refund call is not permitted if the affected customer's vulnerable flag is set to true and the proposed refund amount exceeds twenty thousand pence.

apply_refund_call_amount_pence:
  type: tool_parameter
  description: The proposed refund amount from the current gated refund tool call, in pence, used across merchant and goodwill rules.
  example_nl_phrases:
    - A merchant refund call with an amount greater than the referenced transaction's amount is not permitted.
    - A goodwill credit call with an amount greater than ten thousand pence is not permitted.

apply_refund_call_refund_type:
  type: tool_parameter
  description: Integer-coded refund type for the current tool call; distinguishes merchant refund versus goodwill credit paths in the rules.
  value_meanings:
    0: Merchant refund path for the tool call.
    1: Goodwill credit path for the tool call.
  example_nl_phrases:
    - A merchant refund call with an amount greater than the referenced transaction's amount is not permitted.
    - A goodwill credit call with an amount greater than ten thousand pence is not permitted.
