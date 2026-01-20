"""
QuimbiID Service

Handles all QuimbiID identity graph operations including:
- Looking up QuimbiIDs by any identifier (email, Shopify ID, Gorgias ID, etc.)
- Fetching complete customer profiles using QuimbiID
- Enriching customer data with intelligence from multiple sources
"""

from typing import Optional, Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def parse_segment_to_human_readable(segment_value: str) -> str:
    """
    Parse a segment value like 'purchase_value_high_purchase_value_h2d0s2_seg011'
    into human-readable form like 'High Purchase Value'
    """
    if not segment_value:
        return ""

    # Extract the meaningful part - usually the second occurrence of the axis name
    # Format: {axis}_{level}_{axis}_{code}_{segment_id}
    # Example: purchase_value_high_purchase_value_h2d0s2_seg011
    parts = segment_value.split('_')

    # Find "high", "medium", "low" indicators
    level = ""
    if "high" in parts:
        level = "High"
    elif "medium" in parts:
        level = "Medium"
    elif "low" in parts:
        level = "Low"

    # Get axis name (first part before level indicator)
    axis = parts[0] if parts else ""
    axis_name = axis.replace('_', ' ').title()

    if level:
        return f"{level} {axis_name}"
    else:
        return axis_name.title()


def infer_behaviors_from_metrics(ltv: float, total_orders: int, aov: float) -> List[str]:
    """
    Infer behavioral traits from business metrics when segment data isn't available
    """
    behaviors = []

    # Loyalty indicator (based on order count)
    if total_orders >= 20:
        behaviors.append("Loyal Customer")
    elif total_orders >= 10:
        behaviors.append("Regular Buyer")
    elif total_orders >= 5:
        behaviors.append("Repeat Customer")

    # Purchase value behavior
    if aov > 50:
        behaviors.append("Premium Buyer")
    elif aov > 30:
        behaviors.append("Mid-Tier Buyer")

    # Engagement level
    if ltv > 1000 and total_orders > 30:
        behaviors.append("Highly Engaged")

    return behaviors if behaviors else ["New Customer"]


def infer_dominant_segments_from_metrics(
    ltv: float,
    total_orders: int,
    aov: float,
    days_since_last_purchase: Optional[int],
    customer_tenure_days: Optional[int]
) -> Dict[str, str]:
    """
    Infer basic dominant segments from business metrics for immediate use.
    This provides interim segment data until the full ML segmentation pipeline runs.

    Returns segments compatible with frontend recommendation logic.
    """
    segments = {}

    # Purchase Value Segmentation
    if ltv > 2000:
        segments["purchase_value"] = "whale"  # VIP customer
    elif ltv > 500:
        segments["purchase_value"] = "premium"
    elif ltv > 100:
        segments["purchase_value"] = "mid_tier"
    else:
        segments["purchase_value"] = "low_value"

    # Price Sensitivity (inferred from AOV)
    if aov > 40:
        segments["price_sensitivity"] = "full_price"  # Not price sensitive
    elif aov > 25:
        segments["price_sensitivity"] = "strategic"  # Balanced
    else:
        segments["price_sensitivity"] = "deal_hunter"  # Price sensitive

    # Purchase Frequency
    if total_orders >= 50:
        segments["purchase_frequency"] = "power_buyer"
    elif total_orders >= 10:
        segments["purchase_frequency"] = "regular"
    elif total_orders >= 3:
        segments["purchase_frequency"] = "occasional"
    else:
        segments["purchase_frequency"] = "infrequent"

    # Shopping Maturity (based on customer tenure)
    if customer_tenure_days:
        if customer_tenure_days > 730:  # 2+ years
            segments["shopping_maturity"] = "long_term"
        elif customer_tenure_days > 180:  # 6+ months
            segments["shopping_maturity"] = "established"
        else:
            segments["shopping_maturity"] = "developing"

    # Return/Re-engagement pattern
    if days_since_last_purchase:
        if days_since_last_purchase < 30:
            segments["shopping_cadence"] = "weekday"  # Recent shopper
        elif days_since_last_purchase < 90:
            segments["shopping_cadence"] = "seasonal"  # Periodic
        else:
            segments["shopping_cadence"] = "weekend_crafter"  # Infrequent

    return segments


async def find_quimbi_id_by_any_identifier(
    db: AsyncSession,
    identifier: str
) -> Optional[str]:
    """
    Find QuimbiID by any identifier (email, Shopify ID, Gorgias ID, etc.)

    Args:
        db: Database session
        identifier: Any customer identifier

    Returns:
        QuimbiID if found, None otherwise
    """
    try:
        result = await db.execute(
            text("""
                SELECT quimbi_id
                FROM public.identity_graph
                WHERE id_value = :identifier
                LIMIT 1
            """),
            {"identifier": str(identifier)}
        )
        row = result.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error finding QuimbiID for identifier {identifier}: {e}")
        return None


async def find_quimbi_id_by_pii_hash(
    db: AsyncSession,
    email: Optional[str] = None,
    name: Optional[str] = None,
    address: Optional[str] = None
) -> Optional[str]:
    """
    Find QuimbiID by privacy-preserving PII hash lookup.

    Useful for resolving customer identities from unstructured data
    (e.g., Google Groups emails where name/address are in message body).

    Args:
        db: Database session
        email: Raw email address (will be normalized and hashed)
        name: Raw name (will be normalized and hashed)
        address: Raw address (will be normalized and hashed)

    Returns:
        QuimbiID if any hash matches, None otherwise

    Example:
        >>> quimbi_id = await find_quimbi_id_by_pii_hash(
        ...     db,
        ...     email="Molly@MoonTowerCoaching.com",
        ...     name="Molly Stevens"
        ... )
    """
    from app.services.pii_hash import hash_email, hash_name, hash_address

    try:
        # Try email hash first (most reliable - confidence 1.0)
        if email:
            email_h = hash_email(email)
            result = await db.execute(
                text("""
                    SELECT quimbi_id
                    FROM public.identity_graph
                    WHERE id_type = 'email_hash' AND id_value = :hash
                    LIMIT 1
                """),
                {"hash": email_h}
            )
            row = result.fetchone()
            if row:
                logger.info(f"Found QuimbiID via email_hash: {row[0]}")
                return row[0]

        # Try name hash (useful for Google Groups - confidence 0.9)
        if name:
            name_h = hash_name(name)
            result = await db.execute(
                text("""
                    SELECT quimbi_id
                    FROM public.identity_graph
                    WHERE id_type = 'name_hash' AND id_value = :hash
                    LIMIT 1
                """),
                {"hash": name_h}
            )
            row = result.fetchone()
            if row:
                logger.info(f"Found QuimbiID via name_hash: {row[0]}")
                return row[0]

        # Try address hash (least reliable but sometimes useful)
        if address:
            address_h = hash_address(address)
            result = await db.execute(
                text("""
                    SELECT quimbi_id
                    FROM public.identity_graph
                    WHERE id_type = 'address_hash' AND id_value = :hash
                    LIMIT 1
                """),
                {"hash": address_h}
            )
            row = result.fetchone()
            if row:
                logger.info(f"Found QuimbiID via address_hash: {row[0]}")
                return row[0]

        logger.info(f"No QuimbiID found via PII hash lookup")
        return None

    except Exception as e:
        logger.error(f"Error finding QuimbiID by PII hash: {e}")
        return None


async def get_customer_identifiers(
    db: AsyncSession,
    quimbi_id: str
) -> List[Dict[str, Any]]:
    """
    Get all linked identifiers for a QuimbiID

    Args:
        db: Database session
        quimbi_id: The QuimbiID

    Returns:
        List of identifier dictionaries
    """
    try:
        result = await db.execute(
            text("""
                SELECT id_type, id_value, source, confidence_score, verified
                FROM public.identity_graph
                WHERE quimbi_id = :qid
                ORDER BY id_type, created_at
            """),
            {"qid": quimbi_id}
        )

        identifiers = []
        for row in result.fetchall():
            identifiers.append({
                "type": row[0],
                "value": row[1],
                "source": row[2],
                "confidence": float(row[3]),
                "verified": row[4]
            })

        return identifiers
    except Exception as e:
        logger.error(f"Error getting identifiers for QuimbiID {quimbi_id}: {e}")
        return []


async def get_customer_intelligence(
    db: AsyncSession,
    quimbi_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get customer intelligence data using QuimbiID

    This fetches intelligence from platform.customer_profiles using the Shopify ID
    linked to the QuimbiID.

    Args:
        db: Database session
        quimbi_id: The QuimbiID

    Returns:
        Customer intelligence dict or None
    """
    try:
        # First get the Shopify ID from the identity graph
        result = await db.execute(
            text("""
                SELECT id_value
                FROM public.identity_graph
                WHERE quimbi_id = :qid AND id_type = 'shopify'
                LIMIT 1
            """),
            {"qid": quimbi_id}
        )

        shopify_row = result.fetchone()
        if not shopify_row:
            logger.info(f"No Shopify ID found for QuimbiID {quimbi_id}")
            return None

        shopify_id = shopify_row[0]

        # Get customer intelligence from platform.customer_profiles
        result = await db.execute(
            text("""
                SELECT
                    customer_id,
                    lifetime_value,
                    total_orders,
                    churn_risk_score,
                    avg_order_value,
                    days_since_last_purchase,
                    customer_tenure_days,
                    archetype_id,
                    archetype_level,
                    dominant_segments,
                    segment_memberships
                FROM platform.customer_profiles
                WHERE customer_id = :sid
            """),
            {"sid": shopify_id}
        )

        intel_row = result.fetchone()
        if not intel_row:
            logger.info(f"No intelligence found for Shopify ID {shopify_id}")
            return None

        # Extract values
        ltv = float(intel_row[1]) if intel_row[1] else 0.0
        total_orders = int(intel_row[2]) if intel_row[2] else 0
        avg_order_value = float(intel_row[4]) if intel_row[4] else 0.0
        days_since_last = int(intel_row[5]) if intel_row[5] else None
        customer_tenure = int(intel_row[6]) if intel_row[6] else None

        # Calculate AOV if it's 0 and we have data
        if avg_order_value == 0.0 and total_orders > 0 and ltv > 0:
            avg_order_value = ltv / total_orders

        # Calculate days_since_last_purchase and customer_tenure if null
        if days_since_last is None or customer_tenure is None:
            order_result = await db.execute(
                text("""
                    SELECT
                        MIN(created_at) as first_order,
                        MAX(created_at) as last_order
                    FROM public.combined_sales
                    WHERE customer_id = :sid
                """),
                {"sid": int(shopify_id) if shopify_id else None}
            )
            order_row = order_result.fetchone()
            if order_row and order_row[0] and order_row[1]:
                from datetime import datetime, timezone
                first_order = order_row[0]
                last_order = order_row[1]
                now = datetime.now(timezone.utc)

                # Ensure datetime objects are timezone-aware
                if first_order.tzinfo is None:
                    first_order = first_order.replace(tzinfo=timezone.utc)
                if last_order.tzinfo is None:
                    last_order = last_order.replace(tzinfo=timezone.utc)

                if days_since_last is None:
                    days_since_last = (now - last_order).days

                if customer_tenure is None:
                    customer_tenure = (now - first_order).days

        # Parse dominant segments and behaviors
        dominant_segments = intel_row[9] if intel_row[9] else {}
        segment_memberships = intel_row[10] if intel_row[10] else {}

        # If dominant_segments is empty, infer from metrics (interim solution until ML segmentation runs)
        if not dominant_segments or not isinstance(dominant_segments, dict) or len(dominant_segments) == 0:
            dominant_segments = infer_dominant_segments_from_metrics(
                ltv=ltv,
                total_orders=total_orders,
                aov=avg_order_value,
                days_since_last_purchase=days_since_last,
                customer_tenure_days=customer_tenure
            )

        # Build human-readable behaviors
        behaviors = []
        if dominant_segments and isinstance(dominant_segments, dict):
            # Parse each dominant segment
            for axis, segment_value in dominant_segments.items():
                readable = parse_segment_to_human_readable(segment_value)
                if readable:
                    behaviors.append(readable)

        # If no segments available, infer from metrics
        if not behaviors:
            behaviors = infer_behaviors_from_metrics(ltv, total_orders, avg_order_value)

        return {
            "shopify_customer_id": intel_row[0],
            "lifetime_value": ltv,
            "total_orders": total_orders,
            "churn_risk_score": float(intel_row[3]) if intel_row[3] else 0.0,
            "avg_order_value": avg_order_value,
            "days_since_last_purchase": days_since_last,
            "customer_tenure_days": customer_tenure,
            "archetype_id": intel_row[7],
            "archetype_level": intel_row[8],
            "dominant_segments": dominant_segments,
            "behaviors": behaviors  # Human-readable behavioral traits
        }

    except Exception as e:
        logger.error(f"Error getting intelligence for QuimbiID {quimbi_id}: {e}")
        return None


async def get_recent_orders(
    db: AsyncSession,
    quimbi_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get recent orders for a customer using QuimbiID

    Args:
        db: Database session
        quimbi_id: The QuimbiID
        limit: Number of orders to return

    Returns:
        List of recent orders
    """
    try:
        # Get Shopify ID
        result = await db.execute(
            text("""
                SELECT id_value
                FROM public.identity_graph
                WHERE quimbi_id = :qid AND id_type = 'shopify'
                LIMIT 1
            """),
            {"qid": quimbi_id}
        )

        shopify_row = result.fetchone()
        if not shopify_row:
            return []

        shopify_id = shopify_row[0]

        # Get recent orders with products and tracking
        result = await db.execute(
            text("""
                SELECT
                    order_id,
                    order_number,
                    order_date,
                    order_total,
                    financial_status,
                    fulfillment_status,
                    product_name,
                    line_item_sales,
                    product_type,
                    tracking_number,
                    tracking_url,
                    shipping_carrier
                FROM public.combined_sales
                WHERE customer_id = :cid
                ORDER BY order_date DESC, order_number DESC
                LIMIT :row_limit
            """),
            {"cid": int(shopify_id), "row_limit": limit * 10}  # Fetch more rows to get multiple line items per order
        )

        # Group line items by order
        orders_dict = {}
        for row in result.fetchall():
            order_id = row[0]
            if order_id not in orders_dict:
                # Collect tracking info (same for all line items in an order)
                tracking_number = row[9] if row[9] else None
                tracking_url = row[10] if row[10] else None
                shipping_carrier = row[11] if row[11] else None

                orders_dict[order_id] = {
                    "order_id": row[0],
                    "order_number": row[1],
                    "order_date": row[2].isoformat() if row[2] else None,
                    "total": float(row[3]) if row[3] else 0.0,
                    "financial_status": row[4],
                    "fulfillment_status": row[5],
                    "products": [],
                    "tracking_numbers": [tracking_number] if tracking_number else [],
                    "tracking_urls": [tracking_url] if tracking_url else [],
                    "shipping_carrier": shipping_carrier
                }

            # Add product if we have product name
            if row[6]:  # product_name
                orders_dict[order_id]["products"].append({
                    "title": row[6],
                    "quantity": 1,  # Quantity not available in this table structure
                    "price": str(float(row[7])) if row[7] else "0.00"  # line_item_sales
                })

        # Convert to list and limit to requested number of orders
        orders = list(orders_dict.values())[:limit]

        return orders

    except Exception as e:
        logger.error(f"Error getting orders for QuimbiID {quimbi_id}: {e}")
        return []


async def get_complete_customer_profile(
    db: AsyncSession,
    customer_id: str = None,
    email: str = None,
    name: str = None,
    address: str = None
) -> Optional[Dict[str, Any]]:
    """
    Get complete customer profile by any customer identifier or PII

    This is the main function to use - it will:
    1. Find the QuimbiID for the customer (by ID or PII hash)
    2. Get all linked identifiers
    3. Fetch customer intelligence
    4. Get recent orders
    5. Return complete unified profile

    Args:
        db: Database session
        customer_id: Any customer identifier (email, Shopify ID, Gorgias ID, etc.)
        email: Customer email (for PII hash lookup)
        name: Customer name (for PII hash lookup)
        address: Customer address (for PII hash lookup)

    Returns:
        Complete customer profile dict or None

    Examples:
        # By customer ID
        profile = await get_complete_customer_profile(db, customer_id="123456")

        # By PII hash (Google Groups email)
        profile = await get_complete_customer_profile(
            db,
            email="molly@moontowercoaching.com",
            name="Molly Stevens"
        )
    """
    try:
        # Find QuimbiID - try direct identifier first, then PII hash
        quimbi_id = None

        if customer_id:
            quimbi_id = await find_quimbi_id_by_any_identifier(db, customer_id)

        # Fallback to PII hash lookup if no direct match
        if not quimbi_id and (email or name or address):
            logger.info(f"Trying PII hash lookup for email={email}, name={name}")
            quimbi_id = await find_quimbi_id_by_pii_hash(db, email=email, name=name, address=address)

        if not quimbi_id:
            logger.info(f"No QuimbiID found for customer (id={customer_id}, email={email}, name={name})")
            return None

        # Get customer identity info
        result = await db.execute(
            text("""
                SELECT quimbi_id, primary_email, primary_name, created_at
                FROM public.quimbi_identities
                WHERE quimbi_id = :qid AND is_active = TRUE
            """),
            {"qid": quimbi_id}
        )

        identity_row = result.fetchone()
        if not identity_row:
            return None

        # Build complete profile
        profile = {
            "quimbi_id": identity_row[0],
            "email": identity_row[1],
            "name": identity_row[2],
            "customer_since": identity_row[3].isoformat() if identity_row[3] else None,
            "identifiers": await get_customer_identifiers(db, quimbi_id),
            "intelligence": await get_customer_intelligence(db, quimbi_id),
            "recent_orders": await get_recent_orders(db, quimbi_id)
        }

        return profile

    except Exception as e:
        logger.error(f"Error getting complete profile for customer {customer_id}: {e}")
        return None


async def enrich_ticket_with_customer_context(
    db: AsyncSession,
    ticket: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enrich a ticket with full customer context using QuimbiID

    Args:
        db: Database session
        ticket: Ticket dictionary

    Returns:
        Enriched ticket with customer context
    """
    try:
        customer_id = ticket.get("customer_id")
        if not customer_id:
            return ticket

        # Get complete customer profile
        profile = await get_complete_customer_profile(db, str(customer_id))

        if profile:
            ticket["customer_profile"] = profile

            # Add convenience flags
            if profile.get("intelligence"):
                intel = profile["intelligence"]
                ticket["customer_value_tier"] = _get_value_tier(intel.get("lifetime_value", 0))
                ticket["customer_churn_risk"] = _get_churn_risk_level(intel.get("churn_risk_score", 0))

        return ticket

    except Exception as e:
        logger.error(f"Error enriching ticket with customer context: {e}")
        return ticket


def _get_value_tier(ltv: float) -> str:
    """Determine customer value tier based on LTV"""
    if ltv >= 5000:
        return "VIP"
    elif ltv >= 1000:
        return "HIGH_VALUE"
    elif ltv >= 100:
        return "REGULAR"
    else:
        return "NEW"


def _get_churn_risk_level(churn_score: float) -> str:
    """Determine churn risk level"""
    if churn_score >= 0.7:
        return "HIGH"
    elif churn_score >= 0.4:
        return "MEDIUM"
    else:
        return "LOW"
