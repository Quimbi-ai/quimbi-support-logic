"""
Safe Data Accessors - Graceful Error Handling Utilities

Provides null-safe accessor functions for potentially missing data.
Prevents AttributeError crashes when database joins fail or records are missing.

Philosophy: Degrade gracefully rather than crash. Show "Unknown" rather than error.
"""
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class DataIntegrityLogger:
    """Log data integrity issues for monitoring and alerting."""

    @staticmethod
    def log_missing_customer(ticket_id: str, customer_id: Optional[str]):
        """Log when ticket references non-existent customer."""
        logger.warning(
            f"Data integrity issue: Ticket {ticket_id} has no customer record (customer_id={customer_id})",
            extra={
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "issue_type": "missing_customer_record",
                "severity": "medium"
            }
        )

    @staticmethod
    def log_null_field(entity: str, entity_id: str, field: str):
        """Log when required field is null."""
        logger.warning(
            f"Data integrity issue: {entity} {entity_id} has null {field}",
            extra={
                "entity": entity,
                "entity_id": entity_id,
                "field": field,
                "issue_type": "null_required_field",
                "severity": "low"
            }
        )


# Safe Customer Data Accessors

def get_customer_ltv(ticket: Any, log_missing: bool = True) -> float:
    """
    Safely get customer lifetime value.

    Args:
        ticket: Ticket object (may have null customer)
        log_missing: Whether to log when customer is missing

    Returns:
        LTV value or 0.0 if customer is missing
    """
    if not ticket.customer:
        if log_missing:
            DataIntegrityLogger.log_missing_customer(ticket.id, ticket.customer_id)
        return 0.0
    return ticket.customer.lifetime_value if ticket.customer.lifetime_value is not None else 0.0


def get_customer_orders(ticket: Any, log_missing: bool = True) -> int:
    """
    Safely get customer total orders.

    Args:
        ticket: Ticket object (may have null customer)
        log_missing: Whether to log when customer is missing

    Returns:
        Order count or 0 if customer is missing
    """
    if not ticket.customer:
        if log_missing:
            DataIntegrityLogger.log_missing_customer(ticket.id, ticket.customer_id)
        return 0
    return ticket.customer.total_orders if ticket.customer.total_orders is not None else 0


def get_customer_churn(ticket: Any, log_missing: bool = True) -> float:
    """
    Safely get customer churn risk score.

    Args:
        ticket: Ticket object (may have null customer)
        log_missing: Whether to log when customer is missing

    Returns:
        Churn risk score or 0.5 (unknown) if customer is missing
    """
    if not ticket.customer:
        if log_missing:
            DataIntegrityLogger.log_missing_customer(ticket.id, ticket.customer_id)
        return 0.5  # Unknown churn risk
    return ticket.customer.churn_risk_score if ticket.customer.churn_risk_score is not None else 0.5


def has_customer_data(ticket: Any) -> bool:
    """
    Check if ticket has associated customer data.

    Args:
        ticket: Ticket object

    Returns:
        True if customer data exists, False otherwise
    """
    return ticket.customer is not None


def get_safe_customer_metrics(ticket: Any, log_missing: bool = False) -> dict:
    """
    Get customer metrics with safe defaults for all fields.

    Args:
        ticket: Ticket object (may have null customer)
        log_missing: Whether to log when customer is missing (default False to avoid spam)

    Returns:
        Dict with business_metrics and churn_risk, using defaults if customer missing
    """
    return {
        "business_metrics": {
            "lifetime_value": get_customer_ltv(ticket, log_missing=log_missing),
            "total_orders": get_customer_orders(ticket, log_missing=log_missing),
        },
        "churn_risk": {
            "churn_risk_score": get_customer_churn(ticket, log_missing=log_missing),
        },
    }


# Safe Ticket Data Accessors

def get_safe_ticket_data(ticket: Any) -> dict:
    """
    Get ticket data with safe defaults for potentially null fields.

    Args:
        ticket: Ticket object

    Returns:
        Dict with ticket fields using safe defaults
    """
    return {
        "created_at": ticket.created_at,
        "priority": ticket.priority if ticket.priority else "normal",
        "customer_sentiment": ticket.customer_sentiment if ticket.customer_sentiment is not None else 0.0,
        "estimated_difficulty": ticket.estimated_difficulty if ticket.estimated_difficulty is not None else 0.0,
        "subject": ticket.subject if ticket.subject else "No subject",
    }


# Error Recovery Wrapper

def with_fallback(func, fallback_value=None, log_error: bool = True):
    """
    Decorator to wrap a function with try-except and fallback value.

    Args:
        func: Function to wrap
        fallback_value: Value to return if function raises exception
        log_error: Whether to log the error

    Returns:
        Wrapped function that returns fallback_value on error
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return fallback_value
    return wrapper
