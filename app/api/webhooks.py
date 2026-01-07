"""
Webhook Endpoints for External Integrations

Handles incoming webhooks from:
- Gorgias (support tickets)
- Shopify (orders, customers)
"""
import logging
import hmac
import hashlib
import asyncio
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.integrations.ticket_fulfillment_enricher import (
    enrich_ticket_with_fulfillments,
    extract_order_number_from_ticket,
    format_fulfillment_summary_for_ai,
    format_fulfillment_for_internal_note
)
from app.services.quimbi_client import quimbi_client
from app.services.gorgias_client import gorgias_client
from app.models.database import get_db, WebhookEvent
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Configuration
MAX_WEBHOOK_PAYLOAD_SIZE = 1024 * 1024  # 1MB
WEBHOOK_TIMEOUT = 25.0  # 25 seconds


@router.post("/gorgias/ticket")
@limiter.limit("30/minute")  # Max 30 webhooks per minute per IP
async def handle_gorgias_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_gorgias_signature: Optional[str] = Header(None, alias="X-Gorgias-Signature")
):
    """
    Handle Gorgias ticket webhooks.

    Triggered on:
    - Ticket created
    - Message created

    Workflow:
    1. Validate webhook signature
    2. Check for duplicate webhooks
    3. Extract order number from ticket
    4. Fetch fulfillment data from Shopify
    5. Detect split shipments
    6. Call QuimbiBrain for AI draft generation
    7. Return enriched context
    """
    try:
        # Wrap entire handler with timeout
        return await asyncio.wait_for(
            _process_gorgias_webhook(request, db, x_gorgias_signature),
            timeout=WEBHOOK_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.error("Webhook processing timeout")
        raise HTTPException(status_code=504, detail="Webhook processing timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Gorgias webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _process_gorgias_webhook(
    request: Request,
    db: AsyncSession,
    x_gorgias_signature: Optional[str]
) -> Dict[str, Any]:
    """Internal webhook processing logic."""

    # 1. Validate payload size
    body = await request.body()
    if len(body) > MAX_WEBHOOK_PAYLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Webhook payload too large (max {MAX_WEBHOOK_PAYLOAD_SIZE} bytes)"
        )

    # 2. Verify webhook signature
    if settings.gorgias_webhook_secret and settings.gorgias_webhook_secret != "demo-webhook-secret":
        if not x_gorgias_signature:
            raise HTTPException(status_code=401, detail="Missing webhook signature")

        # Compute expected signature
        expected_signature = hmac.new(
            settings.gorgias_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(x_gorgias_signature, expected_signature):
            logger.warning(f"Invalid webhook signature received")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 3. Parse webhook data
    try:
        webhook_data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")

    # 4. Calculate payload hash for deduplication
    payload_hash = hashlib.sha256(body).hexdigest()

    # 5. Validate this is a Gorgias ticket webhook
    # Gorgias webhooks have specific structure with ticket fields
    if "message" in webhook_data and "body_html" in webhook_data.get("message", {}):
        # Check if this is actually a Recharge or other system webhook
        body_html = webhook_data.get("message", {}).get("body_html", "")
        if "Store Daily Actions" in body_html or "Recharge Admin" in body_html:
            logger.warning(f"Received non-Gorgias webhook (likely Recharge subscription data). Ignoring.")
            return {
                "status": "ignored",
                "reason": "Not a Gorgias support ticket webhook",
                "webhook_type": "recharge_or_other"
            }

    # 6. Extract ticket ID (handle both ticket.created and message.created formats)
    ticket_id = None
    if "ticket" in webhook_data:
        # message.created format: {"ticket": {...}, "message": {...}}
        ticket_id = webhook_data.get("ticket", {}).get("id")
    else:
        # ticket.created format: {"id": ..., "customer": {...}}
        ticket_id = webhook_data.get("id")

    # Validate required Gorgias fields
    if not ticket_id:
        raise HTTPException(status_code=400, detail="Invalid Gorgias webhook: missing ticket ID")

    # Check for Gorgias-specific fields
    has_gorgias_structure = (
        "customer" in webhook_data or
        ("ticket" in webhook_data and "customer" in webhook_data.get("ticket", {}))
    )

    if not has_gorgias_structure:
        logger.warning(f"Webhook missing Gorgias structure. Payload keys: {list(webhook_data.keys())}")
        return {
            "status": "ignored",
            "reason": "Missing Gorgias ticket structure",
            "received_keys": list(webhook_data.keys())
        }

    # 7. Check for duplicate webhook processing
    webhook_id = f"gorgias_ticket_{ticket_id}_{payload_hash[:16]}"

    # Check if already processed
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.webhook_id == webhook_id)
    )
    existing_event = result.scalar_one_or_none()

    if existing_event:
        logger.info(f"Webhook already processed: {webhook_id} at {existing_event.processed_at}")
        return {
            "status": "already_processed",
            "webhook_id": webhook_id,
            "ticket_id": ticket_id,
            "originally_processed_at": existing_event.processed_at.isoformat()
        }

    logger.info(f"Received Gorgias webhook: ticket #{ticket_id}")

    # 8. Normalize webhook format (Gorgias sends different formats)
    if "ticket" in webhook_data and "message" in webhook_data:
        # Format: message.created event
        ticket_data = webhook_data["ticket"]
        new_message = webhook_data["message"]
    else:
        # Format: ticket.created event
        ticket_data = webhook_data

    # Extract order number from ticket
    order_number = extract_order_number_from_ticket(ticket_data)

    # Enrich with fulfillment data if order number found
    fulfillment_data = None
    if order_number:
        logger.info(f"Order number found: #{order_number}, fetching fulfillment data...")
        try:
            fulfillment_data = await enrich_ticket_with_fulfillments(
                ticket_data=ticket_data,
                order_number=order_number
            )

            if fulfillment_data and fulfillment_data.get("fulfillments"):
                logger.info(
                    f"✅ Fulfillment enriched: {fulfillment_data.get('fulfillment_count')} shipment(s), "
                    f"Split: {fulfillment_data.get('has_split_shipment')}"
                )
        except Exception as e:
            logger.warning(f"Failed to enrich fulfillment data: {e}")
            fulfillment_data = None

    # Format fulfillment context for AI
    fulfillment_context = None
    split_shipment_note = None

    if fulfillment_data and fulfillment_data.get("fulfillments"):
        fulfillment_context = format_fulfillment_summary_for_ai(fulfillment_data)

        # Generate internal note for split shipments
        if fulfillment_data.get("has_split_shipment"):
            split_shipment_note = format_fulfillment_for_internal_note(fulfillment_data)

    # Call QuimbiBrain for AI draft generation
    # Pass fulfillment context so AI can use it
    ai_draft = None
    if quimbi_client.client:
        try:
            # Extract customer message
            messages = ticket_data.get("messages", [])
            customer_message = ""
            if messages:
                for msg in reversed(messages):
                    if not msg.get("from_agent", False):
                        customer_message = msg.get("body_text", "")
                        break

            # Get customer info
            customer_data = ticket_data.get("customer", {})
            customer_id = customer_data.get("external_id") or customer_data.get("id")

            # Get customer intelligence from QuimbiBrain
            customer_profile = await quimbi_client.analyze_customer(customer_id)

            # Build conversation history
            conversation = []
            if customer_message:
                conversation.append({
                    "from": "customer",
                    "content": customer_message
                })

            # Add fulfillment context to customer profile if available
            if fulfillment_context:
                customer_profile["fulfillment_context"] = fulfillment_context
                customer_profile["has_split_shipment"] = fulfillment_data.get("has_split_shipment") if fulfillment_data else False

            # Call QuimbiBrain for draft generation
            logger.info(f"Calling QuimbiBrain for AI draft generation...")
            ai_response = await quimbi_client.generate_message(
                customer_profile=customer_profile,
                goal="resolve_support_issue",
                conversation=conversation,
                channel="email",
                tone="empathetic",
                length="medium"
            )
            ai_draft = ai_response.get("message") if ai_response else None

        except Exception as e:
            logger.warning(f"Failed to generate AI draft: {e}")
            ai_draft = None

    # POST internal notes to Gorgias for EVERY ticket (NO draft replies)
    note_posted = False

    try:
        # Build internal note with AI draft and context
        internal_note_parts = []

        # Always include AI-generated draft
        if ai_draft:
            internal_note_parts.append(f"🤖 AI-Generated Draft Response:\n\n{ai_draft}")

        # Add split shipment info if detected
        if split_shipment_note:
            internal_note_parts.append(f"\n\n📦 Split Shipment Alert:\n\n{split_shipment_note}")

        # Add fulfillment context if available
        if fulfillment_data and fulfillment_context:
            internal_note_parts.append(f"\n\n📋 Fulfillment Context:\n\n{fulfillment_context}")

        # Post internal note for EVERY ticket (if we have any content)
        if internal_note_parts:
            internal_note = "\n".join(internal_note_parts)
            logger.info(f"Posting internal note to Gorgias ticket {ticket_id}...")
            note_result = await gorgias_client.post_internal_note(
                ticket_id=ticket_id,
                body_text=internal_note
            )
            note_posted = note_result is not None
            if note_posted:
                logger.info(f"✅ Internal note posted successfully to ticket {ticket_id}")
            else:
                logger.warning(f"⚠️  Failed to post internal note to ticket {ticket_id}")

    except Exception as e:
        logger.error(f"Error posting to Gorgias: {e}", exc_info=True)

    # Record successful webhook processing
    webhook_event = WebhookEvent(
        webhook_id=webhook_id,
        event_type="gorgias_ticket",
        ticket_id=str(ticket_id),
        processed_at=datetime.utcnow(),
        payload_hash=payload_hash,
        status="processed"
    )
    db.add(webhook_event)
    await db.commit()

    # Return webhook response
    return {
        "status": "processed",
        "webhook_id": webhook_id,
        "ticket_id": ticket_id,
        "order_number": order_number,
        "fulfillment_enriched": fulfillment_data is not None,
        "has_split_shipment": fulfillment_data.get("has_split_shipment") if fulfillment_data else False,
        "ai_draft_generated": ai_draft is not None,
        "internal_note_posted": note_posted,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/gorgias/status")
async def gorgias_webhook_status():
    """
    Check Gorgias webhook configuration status.

    Returns configuration and service health.
    """
    import os
    from app.integrations.shopify_fulfillment_service import get_fulfillment_service

    # Check if services are configured
    shopify_configured = bool(
        os.getenv("SHOPIFY_SHOP_NAME") and
        os.getenv("SHOPIFY_ACCESS_TOKEN")
    )

    gorgias_configured = bool(
        os.getenv("GORGIAS_DOMAIN") and
        os.getenv("GORGIAS_API_KEY")
    )

    # Check if fulfillment service is available
    fulfillment_service = get_fulfillment_service()

    # Check Gorgias API health
    gorgias_healthy = False
    if gorgias_configured:
        try:
            gorgias_healthy = await gorgias_client.health_check()
        except Exception:
            gorgias_healthy = False

    return {
        "status": "configured" if (shopify_configured and gorgias_configured) else "partial",
        "webhook_url": "/webhooks/gorgias/ticket",
        "services": {
            "shopify": "configured" if shopify_configured else "missing",
            "gorgias": "configured" if gorgias_configured else "missing",
            "gorgias_api": "connected" if gorgias_healthy else "disconnected",
            "fulfillment_service": "available" if fulfillment_service else "unavailable",
            "quimbi_brain": "connected" if quimbi_client.client else "disconnected"
        },
        "features": {
            "fulfillment_tracking": shopify_configured,
            "split_shipment_detection": shopify_configured,
            "ai_draft_generation": quimbi_client.client is not None,
            "gorgias_posting": gorgias_configured and gorgias_healthy
        }
    }


@router.delete("/gorgias/ticket/{ticket_id}/message/{message_id}")
async def delete_gorgias_message(ticket_id: int, message_id: int):
    """
    Delete a message from a Gorgias ticket.

    Use this to remove accidentally posted messages.
    """
    try:
        success = await gorgias_client.delete_message(
            ticket_id=ticket_id,
            message_id=message_id
        )

        return {
            "status": "deleted" if success else "failed",
            "ticket_id": ticket_id,
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error deleting message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gorgias/test-posting/{ticket_id}")
async def test_gorgias_posting(ticket_id: int):
    """
    Test Gorgias API posting directly.

    This is a debug endpoint to test posting to Gorgias without
    needing a full webhook payload.
    """
    test_message = """Hi there,

This is a test message from the AI-First CRM system.

If you're seeing this as a draft reply in Gorgias, then the posting functionality is working!

Best regards,
Your AI Assistant"""

    try:
        # Fetch ticket to get customer info
        ticket_data = await gorgias_client.get_ticket(ticket_id)
        customer_email = None
        customer_name = None

        if ticket_data:
            customer = ticket_data.get("customer", {})
            customer_email = customer.get("email")
            customer_name = customer.get("name") or f"{customer.get('firstname', '')} {customer.get('lastname', '')}".strip()

        # Test posting draft reply
        draft_result = await gorgias_client.post_draft_reply(
            ticket_id=ticket_id,
            body_text=test_message,
            customer_email=customer_email,
            customer_name=customer_name
        )

        # Test posting internal note
        note_result = await gorgias_client.post_internal_note(
            ticket_id=ticket_id,
            body_text="🤖 Test internal note from AI-First CRM webhook integration"
        )

        return {
            "status": "test_completed",
            "ticket_id": ticket_id,
            "draft_posted": draft_result is not None,
            "draft_response": draft_result if draft_result else "Failed - check logs",
            "note_posted": note_result is not None,
            "note_response": note_result if note_result else "Failed - check logs",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in test posting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shopify/order")
async def handle_shopify_webhook(
    request: Request,
    x_shopify_hmac_sha256: Optional[str] = Header(None, alias="X-Shopify-Hmac-Sha256")
):
    """
    Handle Shopify order webhooks.

    Triggered on:
    - Order created
    - Order fulfilled
    - Order updated

    Placeholder for future Shopify order tracking integration.
    """
    webhook_data = await request.json()

    logger.info(f"Received Shopify webhook: {webhook_data.get('id')}")

    # TODO: Implement Shopify webhook handling
    # This could trigger proactive customer notifications
    # when orders ship, deliver, etc.

    return {
        "status": "received",
        "order_id": webhook_data.get("id"),
        "message": "Shopify webhook processing not yet implemented"
    }
