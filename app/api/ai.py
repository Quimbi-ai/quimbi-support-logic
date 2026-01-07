"""
AI Endpoints - Proxy to Quimbi Intelligence API

Provides AI-powered features by calling Quimbi Backend:
1. Draft response generation (POST /api/generation/message)
2. Next best actions recommendations (POST /api/generation/actions)
3. Customer intelligence (POST /api/intelligence/analyze)

Philosophy: Intelligence Replaces Interface
- No template selection - AI generates appropriate response
- No manual research - Context gathered automatically from Quimbi
- No action planning - AI recommends next steps
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models import get_db, Ticket, Customer
from app.services.quimbi_client import quimbi_client, QuimbiAPIError
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tickets/{ticket_id}/draft-response")
async def get_draft_response(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI draft response for ticket.

    Flow:
    1. Fetch ticket + messages from local DB
    2. Fetch customer from local DB
    3. Call Quimbi: POST /api/intelligence/analyze (get customer DNA)
    4. Call Quimbi: POST /api/generation/message (generate draft)
    5. Return enriched draft to frontend

    Returns:
        {
            "ticket_id": "...",
            "draft_content": "Generated message...",
            "tone": "empathetic",
            "channel": "email",
            "personalization_applied": [...],
            "customer_dna": {...},
            "churn_risk": 0.18
        }
    """
    # Get ticket with messages and customer
    query = (
        select(Ticket)
        .options(joinedload(Ticket.messages), joinedload(Ticket.customer))
        .where(Ticket.id == ticket_id)
    )
    result = await db.execute(query)
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    try:
        # Get customer intelligence from Quimbi
        logger.info(f"Fetching customer intelligence for {ticket.customer_id}")
        customer_intel = await quimbi_client.analyze_customer(
            customer_id=ticket.customer_id
        )

        # Build conversation history
        conversation = []
        for msg in ticket.messages:
            conversation.append({
                "from": "agent" if msg.from_agent else "customer",
                "content": msg.content
            })

        # Generate draft with Quimbi
        logger.info(f"Generating AI draft for ticket {ticket_id}")
        requested_channel = ticket.channel or "email"
        requested_tone = "empathetic"

        draft = await quimbi_client.generate_message(
            customer_profile=customer_intel,
            goal="resolve_support_issue",
            conversation=conversation,
            channel=requested_channel,
            tone=requested_tone,
            length="medium"
        )

        # Extract personalization details from the response
        personalizations = draft.get("personalizations", {})
        personalization_list = []
        if personalizations.get("used_customer_name"):
            personalization_list.append("Used customer name")
        if personalizations.get("vip_treatment"):
            personalization_list.append("Applied VIP treatment based on high LTV")
        if personalizations.get("adapted_to_churn_risk"):
            personalization_list.append(f"Adapted for churn risk ({customer_intel.get('churn_risk', {}).get('risk_level', 'unknown')})")

        return {
            "ticket_id": ticket_id,
            "draft": draft["message"],
            "tone": requested_tone,
            "channel": requested_channel,
            "personalization_applied": personalization_list,
            "customer_dna": customer_intel.get("dominant_segments", {}),
            "churn_risk": customer_intel.get("churn_risk", {}).get("score", 0.5),
            "churn_risk_level": customer_intel.get("churn_risk", {}).get("risk_level", "unknown"),
            "lifetime_value": customer_intel.get("lifetime_value", {}).get("current", 0)
        }

    except QuimbiAPIError as e:
        logger.error(f"Quimbi API error for ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI service temporarily unavailable: {str(e)}"
        )


@router.get("/tickets/{ticket_id}/recommendation")
async def get_recommendation(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-recommended next best actions for ticket.

    Flow:
    1. Fetch ticket from local DB
    2. Get customer intelligence from Quimbi
    3. Call Quimbi: POST /api/generation/actions
    4. Return recommendations with context

    Returns:
        {
            "ticket_id": "...",
            "actions": [
                {
                    "action": "Send immediate replacement with expedited shipping",
                    "priority": 1,
                    "reasoning": "High-value customer with elevated churn risk",
                    "estimated_impact": {
                        "retention_probability": 0.85,
                        "revenue_at_risk": 780.00
                    }
                }
            ],
            "warnings": [...],
            "talking_points": [...],
            "customer_dna": {...},
            "churn_risk": 0.65,
            "revenue_at_risk": 780.00
        }
    """
    # Get ticket with customer
    query = (
        select(Ticket)
        .options(joinedload(Ticket.customer))
        .where(Ticket.id == ticket_id)
    )
    result = await db.execute(query)
    ticket = result.unique().scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    try:
        # Get customer intelligence from Quimbi
        logger.info(f"Fetching customer intelligence for {ticket.customer_id}")
        customer_intel = await quimbi_client.analyze_customer(
            customer_id=ticket.customer_id
        )

        # Get AI recommendations
        logger.info(f"Getting AI recommendations for ticket {ticket_id}")
        recommendations = await quimbi_client.recommend_actions(
            customer_profile=customer_intel,
            scenario="support_ticket",
            context={
                "ticket": {
                    "subject": ticket.subject,
                    "priority": ticket.priority,
                    "channel": ticket.channel,
                    "status": ticket.status
                }
            }
        )

        # Calculate revenue at risk
        churn_risk = customer_intel.get("churn_risk", {}).get("score", 0.5)
        lifetime_value = customer_intel.get("lifetime_value", {}).get("current", 0)
        revenue_at_risk = churn_risk * lifetime_value

        return {
            "ticket_id": ticket_id,
            "actions": recommendations["actions"],
            "warnings": recommendations["warnings"],
            "talking_points": recommendations["talking_points"],
            "customer_dna": customer_intel.get("dominant_segments", {}),
            "archetype_id": customer_intel.get("archetype_id", "unknown"),
            "churn_risk": churn_risk,
            "churn_risk_level": customer_intel.get("churn_risk", {}).get("risk_level", "unknown"),
            "lifetime_value": lifetime_value,
            "revenue_at_risk": round(revenue_at_risk, 2)
        }

    except QuimbiAPIError as e:
        logger.error(f"Quimbi API error for ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI service temporarily unavailable: {str(e)}"
        )


@router.post("/tickets/{ticket_id}/regenerate-draft")
@router.post("/tickets/{ticket_id}/draft-response/regenerate")  # Alias for frontend compatibility
async def regenerate_draft(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Force regenerate draft (bypasses cache).

    Useful when:
    - Agent doesn't like first draft
    - Context has changed (order shipped, customer updated)
    - Want different tone/approach

    Same as /draft-response but forces cache bypass.
    """
    # Invalidate cached customer intelligence
    from app.services.cache import redis_client

    # Get ticket to find customer
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Clear customer intelligence cache
    cache_key = f"customer_intel:{ticket.customer_id}"
    await redis_client.delete(cache_key)

    logger.info(f"Cache cleared for customer {ticket.customer_id}, regenerating draft")

    # Call draft-response with cache bypassed
    return await get_draft_response(ticket_id, db)


@router.get("/customers/{customer_id}/intelligence")
async def get_customer_intelligence(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer intelligence (DNA, churn, LTV).

    Used for: Customer profile views, agent context panels

    Returns:
        {
            "customer_id": "...",
            "archetype": {...},
            "behavioral_metrics": {...},
            "predictions": {...},
            "communication_guidance": [...]
        }
    """
    # Verify customer exists in our DB
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        # Get intelligence from Quimbi
        logger.info(f"Fetching customer intelligence for {customer_id}")
        intel = await quimbi_client.analyze_customer(customer_id)

        return {
            "customer_id": customer_id,
            "archetype": intel["archetype"],
            "behavioral_metrics": intel["behavioral_metrics"],
            "predictions": intel["predictions"],
            "communication_guidance": intel["communication_guidance"]
        }

    except QuimbiAPIError as e:
        logger.error(f"Quimbi API error for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Intelligence service temporarily unavailable: {str(e)}"
        )
