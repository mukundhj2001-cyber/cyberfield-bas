"""Back-compat shim — quote_from_email now runs via multi-intent ops_workflow."""

from app.agent.ops_workflow import (  # noqa: F401
    OpsWorkflowError as QuoteWorkflowError,
    approve_plan,
    approve_quote,
    reject_quote,
    run_ops_plan,
    run_quote_from_email,
)
