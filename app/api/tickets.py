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
    TicketUpdateSchema,
    MessageCreateSchema,
)
from app.services.scoring_service import ScoringService
from app.services.quimbi_id_service import get_complete_customer_profile
from app.services.pii_extractor import extract_pii_from_message
from app.utils.safe_accessors import (
    get_safe_customer_metrics,
    get_safe_ticket_data,
    has_customer_data
)
import uuid
import logging

logger = logging.getLogger(__name__)


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

    # Filter out system notification tickets (subscription cancellations, etc.)
    # These are automated messages from systems like Recharge, not actual customer support tickets
    filters.append(~Ticket.subject.like('%Cancelled Subscription%'))

    if filters:
        query = query.where(and_(*filters))

    # Execute query
    result = await db.execute(query)
    tickets_db = result.scalars().unique().all()

    # Recalculate smart scores with topic alerts
    tickets_with_scores = []
    for ticket in tickets_db:
        try:
            # Calculate score using safe accessors
            score = scoring_service.calculate_ticket_score(
                ticket=get_safe_ticket_data(ticket),
                customer=get_safe_customer_metrics(ticket, log_missing=False),
                topic_alerts=alert_list
            )
        except Exception as e:
            # Log error but continue with default score
            logger.error(f"Error calculating score for ticket {ticket.id}: {e}")
            score = 0.0

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
    """Get single ticket with full details, enriched with QuimbiID customer profile."""
    query = (
        select(Ticket)
        .options(joinedload(Ticket.customer), joinedload(Ticket.messages))
        .where(Ticket.id == ticket_id)
    )

    result = await db.execute(query)
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Convert to schema
    ticket_data = TicketDetailSchema.from_orm(ticket)

    # Enrich with QuimbiID customer profile
    customer_profile = None

    if ticket.customer_id:
        customer_profile = await get_complete_customer_profile(db, customer_id=ticket.customer_id)

    # Fallback: Try PII hash lookup from message content (Google Groups emails)
    if not customer_profile and ticket.messages:
        logger.info(f"No customer_id match for ticket {ticket_id}, trying PII extraction from messages")
        # Get first message content
        first_message = ticket.messages[0] if ticket.messages else None
        if first_message and first_message.content:
            pii = extract_pii_from_message(first_message.content, first_message.from_email)
            if pii.get('email') or pii.get('name'):
                logger.info(f"Extracted PII: email={pii.get('email')}, name={pii.get('name')}")
                customer_profile = await get_complete_customer_profile(
                    db,
                    email=pii.get('email'),
                    name=pii.get('name')
                )
                if customer_profile:
                    logger.info(f"Found customer via PII hash: {customer_profile.get('quimbi_id')}")

    if customer_profile:
            # Transform to frontend-expected structure
            intelligence = customer_profile.get("intelligence") or {}

            # Get last purchase with full details
            recent_orders = customer_profile.get("recent_orders", [])
            last_purchase = None
            if recent_orders and len(recent_orders) > 0:
                last_order = recent_orders[0]  # Most recent order
                last_purchase = {
                    "order_number": last_order.get("order_number"),
                    "order_date": last_order.get("order_date"),  # Fixed: use order_date not created_at
                    "total": str(last_order.get("total")) if last_order.get("total") is not None else None,  # Fixed: use total not total_price, convert to string
                    "status": last_order.get("financial_status"),
                    "fulfillment_status": last_order.get("fulfillment_status"),
                    "products": last_order.get("products", []),
                    "tracking_numbers": last_order.get("tracking_numbers", []),
                    "tracking_urls": last_order.get("tracking_urls", []),
                    "shipping_carrier": last_order.get("shipping_carrier"),
                    "days_ago": intelligence.get("days_since_last_purchase") if intelligence else None
                }

            # Build frontend-compatible structure
            frontend_profile = {
                "customer_id": ticket.customer_id,
                "quimbi_id": customer_profile.get("quimbi_id"),
                "business_metrics": {
                    "lifetime_value": intelligence.get("lifetime_value", 0.0) if intelligence else 0.0,
                    "total_orders": intelligence.get("total_orders", 0) if intelligence else 0,
                    "avg_order_value": intelligence.get("avg_order_value", 0.0) if intelligence else 0.0,
                    "days_since_last_purchase": intelligence.get("days_since_last_purchase") if intelligence else None,
                    "customer_tenure_days": intelligence.get("customer_tenure_days", 0) if intelligence else 0
                },
                "churn_risk": {
                    "churn_risk_score": intelligence.get("churn_risk_score", 0.0) if intelligence else 0.0
                },
                "archetype": {
                    "id": intelligence.get("archetype_id") if intelligence and intelligence.get("archetype_id") != "unknown" else ", ".join(intelligence.get("behaviors", []) if intelligence else []) or "unknown",
                    "level": intelligence.get("archetype_level") if intelligence else None,
                    "behaviors": intelligence.get("behaviors", []) if intelligence else []
                } if intelligence and (intelligence.get("archetype_id") or intelligence.get("behaviors")) else None,
                "behaviors": intelligence.get("behaviors", []) if intelligence else [],
                "dominant_segments": intelligence.get("dominant_segments", {}) if intelligence else {},
                "identifiers": customer_profile.get("identifiers", []),
                "recent_orders": recent_orders,
                "last_purchase": last_purchase  # NEW: Dedicated last purchase section
            }

            # Add customer profile to the response
            ticket_dict = ticket_data.dict()
            ticket_dict["customer_profile"] = frontend_profile
            return ticket_dict

    return ticket_data


@router.post("/tickets")
async def create_ticket(
    ticket_data: TicketCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Create a new ticket."""
    # Get or create customer
    customer_query = select(Customer).where(Customer.id == ticket_data.customer_id)
    result = await db.execute(customer_query)
    customer = result.scalar_one_or_none()

    if not customer:
        # Auto-create customer if doesn't exist
        customer = Customer(
            id=ticket_data.customer_id,
            email=ticket_data.author_email or f"{ticket_data.customer_id}@customer.quimbi.com",
            name=ticket_data.author_name or "Customer",
            lifetime_value=0.0,
            total_orders=0,
            churn_risk_score=0.0
        )
        db.add(customer)
        await db.flush()  # Flush to make customer available for ticket foreign key

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
        from_name=ticket_data.author_name or customer.name,
        from_email=ticket_data.author_email or customer.email
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


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    update_data: TicketUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    """Update ticket status or priority."""
    # Get ticket
    query = select(Ticket).where(Ticket.id == ticket_id)
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Update fields
    if update_data.status is not None:
        ticket.status = update_data.status
    if update_data.priority is not None:
        ticket.priority = update_data.priority

    await db.commit()
    await db.refresh(ticket)

    return {"status": "updated", "ticket_id": ticket.id}


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
