"""
Tickets API Endpoint - PostgreSQL version

Implements Smart Inbox Ordering with Topic Alerts support.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from typing import Optional, List
from app.models import (
    get_db,
    Ticket,
    Customer,
    Message,
    TicketListSchema,
    TicketDetailSchema,
    TicketCreateSchema,
    MessageCreateSchema,
)
from app.services.scoring_service import ScoringService
import uuid


router = APIRouter()
scoring_service = ScoringService()


@router.get("/tickets")
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    status: str = Query("open", description="Filter by ticket status"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    limit: int = Query(50, ge=1, le=100, description="Max tickets to return"),
    page: int = Query(1, ge=1, description="Page number"),
    topic_alerts: Optional[str] = Query(
        None,
        description="Comma-separated topics to boost (e.g., 'chargeback,wrong address')"
    )
):
    """
    Get tickets list in smart order.

    Topic Alerts:
    - Agents can specify keywords to watch for
    - Matching tickets get +5.0 score boost
    - Example: "chargeback,fraud,wrong address"
    """
    # Parse topic alerts
    alert_list = None
    if topic_alerts:
        alert_list = [alert.strip() for alert in topic_alerts.split(",") if alert.strip()]

    # Build query
    query = select(Ticket).options(joinedload(Ticket.customer))

    # Apply filters
    filters = [Ticket.status == status] if status else []
    if channel:
        filters.append(Ticket.channel == channel)

    if filters:
        query = query.where(and_(*filters))

    # Execute query
    result = await db.execute(query)
    tickets_db = result.scalars().unique().all()

    # Recalculate smart scores with topic alerts
    tickets_with_scores = []
    for ticket in tickets_db:
        # Calculate score
        score = scoring_service.calculate_ticket_score(
            ticket={
                "created_at": ticket.created_at,
                "priority": ticket.priority,
                "customer_sentiment": ticket.customer_sentiment,
                "estimated_difficulty": ticket.estimated_difficulty,
                "subject": ticket.subject,
            },
            customer={
                "business_metrics": {
                    "lifetime_value": ticket.customer.lifetime_value,
                    "total_orders": ticket.customer.total_orders,
                },
                "churn_risk": {
                    "churn_risk_score": ticket.customer.churn_risk_score,
                },
            },
            topic_alerts=alert_list
        )

        # Check if matches topic alert
        matches_alert = False
        if alert_list:
            matches_alert = scoring_service._get_topic_alert_component(
                {"subject": ticket.subject},
                alert_list
            ) > 0

        tickets_with_scores.append({
            "ticket": ticket,
            "smart_score": score,
            "matches_topic_alert": matches_alert
        })

    # Sort by smart score
    tickets_with_scores.sort(key=lambda x: x["smart_score"], reverse=True)

    # Pagination
    start = (page - 1) * limit
    end = start + limit
    tickets_page = tickets_with_scores[start:end]

    # Count matches
    matches_count = sum(1 for t in tickets_with_scores if t["matches_topic_alert"])

    # Convert to response schema
    tickets_response = [
        TicketListSchema(
            id=t["ticket"].id,
            customer_id=t["ticket"].customer_id,
            subject=t["ticket"].subject,
            status=t["ticket"].status,
            priority=t["ticket"].priority,
            channel=t["ticket"].channel,
            created_at=t["ticket"].created_at,
            updated_at=t["ticket"].updated_at,
            customer_sentiment=t["ticket"].customer_sentiment,
            smart_score=t["smart_score"],
            estimated_difficulty=t["ticket"].estimated_difficulty,
            matches_topic_alert=t["matches_topic_alert"]
        )
        for t in tickets_page
    ]

    return {
        "tickets": tickets_response,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": len(tickets_with_scores),
            "has_next": end < len(tickets_with_scores),
            "has_prev": page > 1
        },
        "topic_alerts_active": alert_list if alert_list else [],
        "matches": matches_count if alert_list else 0
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get single ticket with full details."""
    query = (
        select(Ticket)
        .options(joinedload(Ticket.customer), joinedload(Ticket.messages))
        .where(Ticket.id == ticket_id)
    )

    result = await db.execute(query)
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketDetailSchema.from_orm(ticket)


@router.post("/tickets")
async def create_ticket(
    ticket_data: TicketCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Create a new ticket."""
    # Verify customer exists
    customer_query = select(Customer).where(Customer.id == ticket_data.customer_id)
    result = await db.execute(customer_query)
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Create ticket
    ticket_id = str(uuid.uuid4())
    ticket = Ticket(
        id=ticket_id,
        customer_id=ticket_data.customer_id,
        subject=ticket_data.subject,
        priority=ticket_data.priority,
        channel=ticket_data.channel,
        status="open",
        customer_sentiment=0.5,
        estimated_difficulty=0.5,
        smart_score=0.0
    )

    # Create initial message
    message = Message(
        id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        content=ticket_data.initial_message,
        from_agent=False,
        from_name=customer.name,
        from_email=customer.email
    )

    db.add(ticket)
    db.add(message)
    await db.commit()
    await db.refresh(ticket)

    return {"id": ticket_id, "status": "created"}


@router.post("/tickets/{ticket_id}/messages")
async def send_message(
    ticket_id: str,
    message_data: MessageCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Send response to ticket."""
    # Verify ticket exists
    ticket_query = select(Ticket).where(Ticket.id == ticket_id)
    result = await db.execute(ticket_query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Create message
    message = Message(
        id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        content=message_data.content,
        from_agent=message_data.from_agent,
        from_name=message_data.from_name,
        from_email=message_data.from_email
    )

    db.add(message)
    await db.commit()

    return {"status": "sent", "message_id": message.id}


@router.get("/tickets/{ticket_id}/score-breakdown")
async def get_score_breakdown(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint: See why ticket has its score."""
    query = select(Ticket).options(joinedload(Ticket.customer)).where(Ticket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    breakdown = scoring_service.get_scoring_breakdown(
        ticket={
            "created_at": ticket.created_at,
            "priority": ticket.priority,
            "customer_sentiment": ticket.customer_sentiment,
            "estimated_difficulty": ticket.estimated_difficulty,
            "subject": ticket.subject,
        },
        customer={
            "business_metrics": {
                "lifetime_value": ticket.customer.lifetime_value,
                "total_orders": ticket.customer.total_orders,
            },
            "churn_risk": {
                "churn_risk_score": ticket.customer.churn_risk_score,
            },
        },
        topic_alerts=None
    )

    return breakdown
