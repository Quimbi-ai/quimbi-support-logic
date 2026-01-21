# Error Handling Strategy for Support Logic Backend

## Problem Statement

When tickets arrive with missing or malformed data (missing customer records, null fields, failed joins), the system should gracefully degrade rather than crash with 500 errors.

## Core Principles

1. **Never crash the list view** - Users should always see available tickets
2. **Degrade gracefully** - Show partial data rather than nothing
3. **Log intelligently** - Track data integrity issues for monitoring
4. **Fail soft** - Use default values for missing customer data
5. **Be explicit** - Show "Unknown" rather than hiding missing data

## Error Handling Patterns

### Pattern 1: Safe Customer Data Access (Null-Safe Getters)

**Problem**: `ticket.customer.lifetime_value` crashes when `ticket.customer` is `None`

**Solution**: Use helper functions with safe defaults

```python
def get_customer_ltv(ticket) -> float:
    """Safely get customer LTV, return 0 if missing."""
    return ticket.customer.lifetime_value if ticket.customer else 0.0

def get_customer_orders(ticket) -> int:
    """Safely get customer order count, return 0 if missing."""
    return ticket.customer.total_orders if ticket.customer else 0

def get_customer_churn(ticket) -> float:
    """Safely get customer churn risk, return 0.5 (unknown) if missing."""
    return ticket.customer.churn_risk_score if ticket.customer else 0.5
```

**Usage**:
```python
score = scoring_service.calculate_ticket_score(
    ticket={...},
    customer={
        "business_metrics": {
            "lifetime_value": get_customer_ltv(ticket),
            "total_orders": get_customer_orders(ticket),
        },
        "churn_risk": {
            "churn_risk_score": get_customer_churn(ticket),
        },
    }
)
```

### Pattern 2: Try-Except with Fallback Data

**Problem**: Entire endpoint crashes when one ticket has bad data

**Solution**: Wrap individual ticket processing in try-except, continue with degraded data

```python
tickets_with_scores = []
for ticket in tickets_db:
    try:
        # Try to process ticket normally
        score = scoring_service.calculate_ticket_score(...)
        tickets_with_scores.append({
            "ticket": ticket,
            "score": score,
            "has_customer_data": ticket.customer is not None
        })
    except Exception as e:
        # Log error but continue
        logger.warning(f"Error processing ticket {ticket.id}: {e}")

        # Add ticket with default score
        tickets_with_scores.append({
            "ticket": ticket,
            "score": 0.0,  # Default score
            "has_customer_data": False,
            "error": "Customer data unavailable"
        })
```

### Pattern 3: Database-Level Outer Joins

**Problem**: SQLAlchemy `joinedload(Ticket.customer)` can fail if FK relationship is broken

**Solution**: Use `outerjoin` instead of `joinedload` for optional relationships

```python
from sqlalchemy.orm import outerjoin

# Instead of:
query = select(Ticket).options(joinedload(Ticket.customer))

# Use:
query = select(Ticket).outerjoin(Ticket.customer)

# This ensures tickets without customers still load
```

### Pattern 4: Pydantic Models with Default Values

**Problem**: Missing fields cause validation errors

**Solution**: Define Pydantic models with sensible defaults

```python
from pydantic import BaseModel, Field
from typing import Optional

class CustomerMetrics(BaseModel):
    """Customer business metrics with safe defaults."""
    lifetime_value: float = Field(default=0.0)
    total_orders: int = Field(default=0)
    avg_order_value: float = Field(default=0.0)
    churn_risk_score: float = Field(default=0.5)  # Unknown

class TicketResponse(BaseModel):
    """Ticket response with optional customer data."""
    id: str
    subject: str
    status: str
    customer_metrics: Optional[CustomerMetrics] = None
    has_customer_data: bool = Field(default=False)
```

### Pattern 5: Middleware Error Recovery

**Problem**: Unhandled exceptions crash entire API

**Solution**: Global exception handler that returns degraded data

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return graceful error."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # For list endpoints, return empty list rather than error
    if "/api/tickets" in str(request.url):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "tickets": [],
                "error": "Unable to load tickets. Please try again.",
                "partial_failure": True
            }
        )

    # For detail endpoints, return minimal data
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error. Data may be incomplete.",
            "error_type": type(exc).__name__
        }
    )
```

### Pattern 6: Data Integrity Monitoring

**Problem**: Silent failures where bad data goes unnoticed

**Solution**: Log data integrity issues for monitoring

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DataIntegrityLogger:
    """Log data integrity issues for monitoring."""

    @staticmethod
    def log_missing_customer(ticket_id: str, customer_id: Optional[str]):
        """Log when ticket references non-existent customer."""
        logger.warning(
            "Data integrity issue: Missing customer",
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
            f"Data integrity issue: Null {field}",
            extra={
                "entity": entity,
                "entity_id": entity_id,
                "field": field,
                "issue_type": "null_required_field",
                "severity": "low"
            }
        )

    @staticmethod
    def log_failed_join(entity1: str, entity2: str, join_key: str):
        """Log when database join fails."""
        logger.error(
            f"Data integrity issue: Failed join",
            extra={
                "entity1": entity1,
                "entity2": entity2,
                "join_key": join_key,
                "issue_type": "failed_database_join",
                "severity": "high"
            }
        )

# Usage:
if not ticket.customer:
    DataIntegrityLogger.log_missing_customer(ticket.id, ticket.customer_id)
```

### Pattern 7: Frontend-Aware Error States

**Problem**: Frontend can't distinguish between loading, error, and empty states

**Solution**: Return structured metadata with responses

```python
class TicketListResponse(BaseModel):
    """Ticket list with metadata about data quality."""
    tickets: List[TicketSummary]
    total: int
    has_partial_failures: bool = Field(default=False)
    missing_customer_data_count: int = Field(default=0)
    errors: List[str] = Field(default_factory=list)

# Return:
return TicketListResponse(
    tickets=processed_tickets,
    total=len(tickets_db),
    has_partial_failures=any(t.get('error') for t in processed_tickets),
    missing_customer_data_count=sum(1 for t in processed_tickets if not t.get('has_customer_data')),
    errors=[t['error'] for t in processed_tickets if t.get('error')]
)
```

## Implementation Priority

### High Priority (Implement Now)
1. ✅ Safe customer data access in `list_tickets` (Pattern 1)
2. ⬜ Try-except wrapper for ticket processing (Pattern 2)
3. ⬜ Data integrity logging (Pattern 6)

### Medium Priority (Next Sprint)
4. ⬜ Pydantic models with defaults (Pattern 4)
5. ⬜ Global exception handler (Pattern 5)
6. ⬜ Frontend-aware error states (Pattern 7)

### Low Priority (Future)
7. ⬜ Database outer joins (Pattern 3) - only if needed

## Testing Strategy

### Unit Tests
```python
def test_safe_customer_access_with_null_customer():
    """Test that safe getters work when customer is None."""
    ticket = Ticket(id="test", customer=None)
    assert get_customer_ltv(ticket) == 0.0
    assert get_customer_orders(ticket) == 0
    assert get_customer_churn(ticket) == 0.5

def test_list_tickets_with_missing_customers():
    """Test that list endpoint handles missing customers gracefully."""
    # Create ticket with non-existent customer_id
    ticket = create_ticket(customer_id="999999999")

    response = client.get("/api/tickets?status=open")
    assert response.status_code == 200
    assert len(response.json()["tickets"]) > 0
    # Should not crash
```

### Integration Tests
```python
def test_end_to_end_with_malformed_data():
    """Test that system handles malformed data end-to-end."""
    # Create tickets with various data issues
    create_ticket(customer_id=None)  # No customer
    create_ticket(customer_id="invalid")  # Invalid customer
    create_ticket(subject=None)  # Missing subject

    response = client.get("/api/tickets?status=open")
    assert response.status_code == 200
    # Should return some tickets, even if degraded
```

## Monitoring & Alerts

### Log Aggregation
- Track frequency of `missing_customer_record` warnings
- Alert if > 10% of tickets have missing customer data
- Dashboard showing data integrity metrics

### Metrics to Track
- `tickets_missing_customers_count`
- `api_partial_failures_rate`
- `null_field_occurrences_by_field`
- `failed_join_count`

## Rollout Plan

1. **Phase 1**: Implement safe getters (Pattern 1) - DONE via fix
2. **Phase 2**: Add try-except wrappers (Pattern 2) - 30 min
3. **Phase 3**: Add data integrity logging (Pattern 6) - 1 hour
4. **Phase 4**: Add monitoring dashboard - 2 hours
5. **Phase 5**: Implement Pydantic defaults (Pattern 4) - 2 hours

## Success Criteria

- ✅ No 500 errors when loading ticket list
- ✅ Tickets with missing customer data still appear in list
- ⬜ Degraded data is clearly marked in UI
- ⬜ Data integrity issues are logged and monitored
- ⬜ Alert triggers when data quality degrades
