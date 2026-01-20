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
from app.services.quimbi_id_service import get_complete_customer_profile
from app.services.pii_extractor import extract_pii_from_message
import logging
import anthropic
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def generate_personalized_response_with_claude(
    customer_profile: dict,
    ticket: Ticket,
    conversation: list,
    tone: str = "appreciative"
) -> str:
    """
    Generate a personalized response using Claude directly with full customer context
    """
    intelligence = customer_profile.get("intelligence") or {}
    behaviors = intelligence.get("behaviors", []) if intelligence else []
    recent_orders = customer_profile.get("recent_orders", [])[:3] if customer_profile else []

    # Build customer context
    behavior_str = ", ".join(behaviors) if behaviors else "new customer"
    ltv = intelligence.get("lifetime_value", 0) if intelligence else 0
    total_orders = intelligence.get("total_orders", 0) if intelligence else 0

    # Build order context
    order_context = ""
    if recent_orders:
        order_context = "\n\nRecent Orders:\n"
        for order in recent_orders:
            order_context += f"- Order #{order['order_number']} ({order['order_date'][:10]}): ${order['total']:.2f} - {order['financial_status']}\n"

    # Build conversation history
    convo_text = ""
    for msg in conversation:
        role = "Customer" if msg["from"] == "customer" else "Agent"
        convo_text += f"{role}: {msg['content']}\n\n"

    # Create prompt
    # Check if customer mentions orders but has none in database
    order_mismatch = total_orders == 0 and any(word in convo_text.lower() for word in ['ordered', 'order', 'bought', 'purchased', 'purchase'])

    # Channel-specific character limits and format instructions
    channel = ticket.channel or "email"
    channel_instructions = {
        "sms": {
            "max_chars": 300,
            "format": "CRITICAL: SMS response - MAX 300 characters. Be ultra-concise. Skip greeting if needed. Get straight to the point.",
            "max_tokens": 150
        },
        "chat": {
            "max_chars": 400,
            "format": "CRITICAL: Live Chat response - MAX 400 characters. Be concise and friendly. Brief greeting OK.",
            "max_tokens": 200
        },
        "email": {
            "max_chars": None,
            "format": "Email response - Can be 2-3 paragraphs.",
            "max_tokens": 800
        }
    }

    channel_config = channel_instructions.get(channel, channel_instructions["email"])
    char_limit_instruction = f"\n\n**{channel_config['format']}**" if channel in ["sms", "chat"] else ""

    prompt = f"""You are a customer support agent for Linda's Electric Quilters, an e-commerce quilting supply company.

Generate a helpful, personalized {channel} response to this customer support ticket.{char_limit_instruction}

CUSTOMER PROFILE:
- Name: {ticket.customer.name if ticket.customer else "Customer"}
- Behavioral Profile: {behavior_str}
- Order History: {total_orders} orders, ${ltv:.2f} lifetime value
{order_context}

CONVERSATION HISTORY:
{convo_text}

INSTRUCTIONS:
1. Use an {tone} tone - this customer is {behavior_str.lower()}
2. Reference their specific order if mentioned (look it up above)
3. Acknowledge their loyalty if they're a repeat customer
4. Offer a practical solution (exchange, refund, replacement)
5. Be warm and professional - avoid corporate language
6. Do NOT mention their LTV or dollar amounts
7. Keep response concise (2-3 paragraphs max for email, much shorter for SMS/chat)
{"8. IMPORTANT: Customer mentions an order but we have no order history - politely ask for their order number or confirmation email to help locate it" if order_mismatch else ""}

Generate the {channel} response now:"""

    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=channel_config['max_tokens'],
            messages=[{"role": "user", "content": prompt}]
        )

        draft_text = message.content[0].text

        # Enforce hard character limit for SMS/Chat (safety net)
        if channel_config['max_chars'] and len(draft_text) > channel_config['max_chars']:
            draft_text = draft_text[:channel_config['max_chars']-3] + "..."
            logger.warning(f"Truncated {channel} response from {len(message.content[0].text)} to {channel_config['max_chars']} chars")

        return draft_text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "Thank you for contacting us. We're looking into your issue and will respond shortly."


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
        # Get customer profile from QuimbiID service
        logger.info(f"Fetching QuimbiID customer profile for {ticket.customer_id}")
        customer_profile = await get_complete_customer_profile(db, customer_id=ticket.customer_id) if ticket.customer_id else None

        # Fallback: Try PII hash lookup from message content (Google Groups emails)
        if not customer_profile and ticket.messages:
            logger.info(f"No customer_id match for ticket {ticket_id}, trying PII extraction from messages")
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

        if not customer_profile:
            logger.warning(f"No customer profile found for ticket {ticket_id}")
            customer_profile = {}

        intelligence = customer_profile.get("intelligence") or {}
        behaviors = intelligence.get("behaviors", []) if intelligence else []

        # Get customer intelligence from Quimbi AI brain (fallback for archetype analysis)
        logger.info(f"Fetching customer intelligence from AI brain for {ticket.customer_id}")
        try:
            customer_intel = await quimbi_client.analyze_customer(
                customer_id=ticket.customer_id
            )
        except Exception as e:
            logger.warning(f"Could not fetch AI brain intelligence: {e}, using QuimbiID data only")
            customer_intel = {
                "business_metrics": {
                    "lifetime_value": intelligence.get("lifetime_value", 0),
                    "total_orders": intelligence.get("total_orders", 0),
                    "avg_order_value": intelligence.get("avg_order_value", 0)
                },
                "churn_risk": {
                    "score": intelligence.get("churn_risk_score", 0)
                },
                "behaviors": behaviors,
                "archetype_id": intelligence.get("archetype_id", "unknown")
            }

        # Build conversation history
        conversation = []
        for msg in ticket.messages:
            conversation.append({
                "from": "agent" if msg.from_agent else "customer",
                "content": msg.content
            })

        # Determine tone based on customer behaviors
        requested_tone = "empathetic"
        if "Loyal Customer" in behaviors or "Highly Engaged" in behaviors:
            requested_tone = "appreciative"  # Show appreciation for loyal customers
        elif "Premium Buyer" in behaviors:
            requested_tone = "professional"  # Professional for premium customers

        # Generate draft with Claude directly using full customer context
        logger.info(f"Generating AI draft for ticket {ticket_id} with tone: {requested_tone}")
        requested_channel = ticket.channel or "email"

        draft_message = await generate_personalized_response_with_claude(
            customer_profile=customer_profile,
            ticket=ticket,
            conversation=conversation,
            tone=requested_tone
        )

        draft = {"message": draft_message, "personalizations": {}}

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
            "behaviors": behaviors,  # Add behavioral traits for frontend display
            "churn_risk": customer_intel.get("churn_risk", {}).get("score", 0.5),
            "churn_risk_level": customer_intel.get("churn_risk", {}).get("risk_level", "unknown"),
            "lifetime_value": customer_intel.get("business_metrics", {}).get("lifetime_value", intelligence.get("lifetime_value", 0) if intelligence else 0)
        }

    except QuimbiAPIError as e:
        logger.error(f"Quimbi API error for ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI service temporarily unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error generating AI draft for ticket {ticket_id}: {e}", exc_info=True)
        # Return a fallback response instead of crashing
        return {
            "ticket_id": ticket_id,
            "draft": "Thank you for contacting us. We're looking into your issue and will respond shortly.",
            "tone": "empathetic",
            "channel": ticket.channel or "email",
            "personalization_applied": [],
            "customer_dna": {},
            "behaviors": [],
            "churn_risk": 0.5,
            "churn_risk_level": "unknown",
            "lifetime_value": 0
        }


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
