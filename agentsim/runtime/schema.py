"""SQLite DDL for the agent simulation (see agentsim/01_simulation_environment.md)."""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customer (
    customer_id TEXT PRIMARY KEY,
    kyc_status TEXT NOT NULL,
    account_tier TEXT NOT NULL,
    vulnerable_flag INTEGER NOT NULL,
    pep_flag INTEGER NOT NULL,
    sanctions_flag INTEGER NOT NULL,
    joint_account INTEGER NOT NULL,
    account_open_date TEXT NOT NULL,
    dispute_count_last_12m INTEGER NOT NULL DEFAULT 0,
    prior_goodwill_credits_last_12m_amount TEXT NOT NULL DEFAULT '0'
);

CREATE TABLE IF NOT EXISTS account (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    balance_pence INTEGER NOT NULL,
    available_balance_pence INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'GBP',
    account_status TEXT NOT NULL,
    restriction_reasons_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS card (
    card_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES account(account_id),
    card_status TEXT NOT NULL,
    card_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transaction_row (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES account(account_id),
    card_id TEXT REFERENCES card(card_id),
    merchant_name TEXT NOT NULL,
    merchant_category TEXT NOT NULL,
    amount_pence INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'GBP',
    transaction_date TEXT NOT NULL,
    posted_date TEXT NOT NULL,
    status TEXT NOT NULL,
    is_section75_eligible INTEGER NOT NULL,
    chargeback_window_days INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dispute (
    dispute_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transaction_row(transaction_id),
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    dispute_type TEXT NOT NULL,
    dispute_status TEXT NOT NULL,
    opened_date TEXT NOT NULL,
    evidence_documents_json TEXT NOT NULL DEFAULT '[]',
    outcome_amount_pence INTEGER,
    customer_statement TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS refund (
    refund_id TEXT PRIMARY KEY,
    transaction_id TEXT REFERENCES transaction_row(transaction_id),
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    refund_type TEXT NOT NULL,
    amount_pence INTEGER NOT NULL,
    requires_approval INTEGER NOT NULL,
    approval_status TEXT NOT NULL,
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS restriction (
    restriction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES account(account_id),
    restriction_type TEXT NOT NULL,
    applied_date TEXT NOT NULL,
    lift_eligible_after TEXT,
    requires_human_to_lift INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fraud_report (
    fraud_report_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    transaction_ids_json TEXT NOT NULL,
    fraud_type TEXT NOT NULL,
    report_status TEXT NOT NULL,
    reported_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interaction (
    interaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    channel TEXT NOT NULL,
    started_at TEXT NOT NULL,
    actions_taken_json TEXT NOT NULL DEFAULT '[]',
    escalated_to_human INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS consumer_duty_assessment (
    assessment_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    interaction_id TEXT NOT NULL REFERENCES interaction(interaction_id),
    vulnerability_indicators_json TEXT NOT NULL DEFAULT '[]',
    fair_value_check_passed INTEGER NOT NULL,
    clear_communication_check_passed INTEGER NOT NULL,
    assessment_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    decision TEXT NOT NULL,
    unsat_core_json TEXT,
    explanation TEXT,
    policy_version TEXT NOT NULL,
    rules_consulted_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS documentation_request (
    documentation_request_id TEXT PRIMARY KEY,
    interaction_id TEXT NOT NULL REFERENCES interaction(interaction_id),
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    document_type TEXT NOT NULL,
    deadline TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbound_message (
    outbound_message_id TEXT PRIMARY KEY,
    interaction_id TEXT NOT NULL REFERENCES interaction(interaction_id),
    customer_id TEXT NOT NULL REFERENCES customer(customer_id),
    message_text TEXT NOT NULL,
    message_category TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
