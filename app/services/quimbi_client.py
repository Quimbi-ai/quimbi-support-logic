"""
Quimbi Backend Client - Intelligence API Wrapper

Implements the Quimbi Platform API for customer intelligence and AI generation.
Based on API_REQUIREMENTS.md and INTEGRATION_GUIDE.md specifications.

Features:
- Customer intelligence analysis (DNA, archetype, segments)
- Churn risk predictions
- LTV forecasting
- AI message generation
- AI action recommendations
- Automatic retry with exponential backoff
- Redis caching for intelligence data
- Graceful error handling with fallback data
- Customer ID resolution (support IDs → e-commerce IDs)
"""
import httpx
from typing import Dict, Any, Optional, List
import json
import logging
import asyncio
from app.core.config import settings
from app.services.cache import redis_client
from app.services.customer_resolver import customer_resolver
from app.models.database import get_db

logger = logging.getLogger(__name__)


class QuimbiAPIError(Exception):
    """Base exception for Quimbi API errors."""
    pass


class QuimbiRateLimitError(QuimbiAPIError):
    """Rate limit exceeded."""
    pass


class QuimbiClient:
    """
    Client for Quimbi Platform Intelligence API.

    Usage:
        from app.services.quimbi_client import quimbi_client

        # Get customer intelligence
        intel = await quimbi_client.analyze_customer("cust_123")

        # Generate AI draft
        draft = await quimbi_client.generate_message(
            customer_profile=intel,
            goal="resolve_support_issue",
            conversation=[...],
            channel="email"
        )
    """

    def __init__(self):
        self.base_url = settings.quimbi_base_url
        self.api_key = settings.quimbi_api_key
        self.timeout = settings.quimbi_timeout
        self.max_retries = settings.quimbi_max_retries

        # HTTP client (initialized in startup)
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize HTTP client. Call during app startup."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                'X-API-Key': self.api_key,  # AI brain expects X-API-Key
                'Content-Type': 'application/json'
            },
            timeout=self.timeout
        )
        logger.info(f"Quimbi client initialized: {self.base_url}")

    async def close(self):
        """Close HTTP client. Call during app shutdown."""
        if self.client:
            await self.client.aclose()
            logger.info("Quimbi client closed")

    async def analyze_customer(
        self,
        customer_id: str,
        orders: Optional[List[Dict]] = None,
        interactions: Optional[List[Dict]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive customer intelligence.

        Endpoint: POST /api/intelligence/analyze

        Args:
            customer_id: Customer ID to analyze (support ID or e-commerce ID)
            orders: Optional recent orders for richer context
            interactions: Optional interaction history
            use_cache: Whether to use cached data (default: True)

        Returns:
            {
                "customer_id": "cust_123",
                "archetype": {
                    "id": "arch_premium_deal_hunter",
                    "level": "L2",
                    "segments": {
                        "purchase_value": "premium",
                        "price_sensitivity": "deal_hunter",
                        "shopping_maturity": "established",
                        ...13 total axes
                    }
                },
                "behavioral_metrics": {
                    "lifetime_value": 892.50,
                    "total_orders": 12,
                    "avg_order_value": 74.38,
                    "days_since_last_purchase": 15
                },
                "predictions": {
                    "churn_risk": 0.18,
                    "churn_risk_level": "low",
                    "ltv_12mo": 450.00
                },
                "communication_guidance": [
                    "Customer responds well to value propositions",
                    "Frequent shopper - they know the store well"
                ]
            }

        Cache TTL: 15 minutes (configurable via quimbi_cache_intelligence_ttl)
        """
        # STEP 1: Resolve support customer ID to e-commerce ID if needed
        original_customer_id = customer_id
        ecommerce_customer_id = customer_id

        # If customer ID starts with "cust_", resolve to e-commerce ID
        if customer_id.startswith("cust_"):
            logger.info(f"Resolving support customer ID: {customer_id}")

            # Get database session
            async for db in get_db():
                resolved_id = await customer_resolver.resolve_to_ecommerce_id(
                    db, customer_id
                )

                if resolved_id:
                    ecommerce_customer_id = str(resolved_id)
                    logger.info(
                        f"✅ Customer ID resolved: {customer_id} → {ecommerce_customer_id}"
                    )
                else:
                    logger.warning(
                        f"⚠️  No e-commerce mapping for {customer_id}. "
                        f"AI Brain will not have access to behavioral intelligence."
                    )
                    # Return fallback intelligence for unmapped customers
                    return self._get_fallback_intelligence(customer_id)

                break  # Exit after first iteration

        # STEP 2: Try cache first (use e-commerce ID for cache key)
        if use_cache:
            cached = await self._get_cached_intelligence(ecommerce_customer_id)
            if cached:
                logger.debug(f"Cache hit for customer {ecommerce_customer_id}")
                # Add original support ID to response
                cached["support_customer_id"] = original_customer_id
                return cached

        # STEP 3: Build request body with e-commerce customer ID
        request_body = {
            "customer_id": ecommerce_customer_id,  # Use e-commerce ID!
            "context": {}
        }

        if orders:
            request_body["context"]["orders"] = orders

        if interactions:
            request_body["context"]["interactions"] = interactions

        # STEP 4: Call Quimbi API (AI Brain)
        try:
            response = await self._post_with_retry(
                "/api/intelligence/analyze",
                request_body
            )

            # Add original support customer ID to response
            response["support_customer_id"] = original_customer_id
            response["ecommerce_customer_id"] = ecommerce_customer_id

            # Cache result (using e-commerce ID as key)
            await self._cache_intelligence(ecommerce_customer_id, response)

            logger.info(
                f"✅ Customer intelligence fetched for {original_customer_id} "
                f"(e-commerce ID: {ecommerce_customer_id}): "
                f"archetype={response.get('archetype', {}).get('id')}, "
                f"churn_risk={response.get('predictions', {}).get('churn_risk')}"
            )

            return response

        except QuimbiAPIError as e:
            logger.error(f"Quimbi API error for customer {ecommerce_customer_id}: {e}")
            # Return fallback data so app still works
            return self._get_fallback_intelligence(original_customer_id)

    async def predict_churn(
        self,
        customer_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get customer churn risk prediction.

        Endpoint: POST /api/intelligence/predict/churn

        Args:
            customer_id: Customer ID
            use_cache: Whether to use cached data (default: True)

        Returns:
            {
                "customer_id": "cust_123",
                "churn_risk_score": 0.28,
                "risk_level": "medium",
                "factors": [
                    {
                        "factor": "days_since_last_purchase",
                        "value": 45,
                        "impact": "high",
                        "direction": "increases_risk"
                    }
                ],
                "recommendations": [
                    "Send re-engagement campaign within 7 days",
                    "Offer personalized product recommendations"
                ]
            }

        Cache TTL: 1 hour
        """
        # Try cache
        if use_cache:
            cache_key = f"churn_prediction:{customer_id}"
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for churn prediction {customer_id}")
                return json.loads(cached)

        # Call API
        try:
            response = await self._post_with_retry(
                "/api/intelligence/predict/churn",
                {"customer_id": customer_id}
            )

            # Cache for 1 hour
            cache_key = f"churn_prediction:{customer_id}"
            await redis_client.setex(
                cache_key,
                settings.quimbi_cache_churn_ttl,
                json.dumps(response)
            )

            logger.info(
                f"Churn prediction for {customer_id}: "
                f"risk={response.get('churn_risk_score')} "
                f"level={response.get('risk_level')}"
            )

            return response

        except QuimbiAPIError as e:
            logger.error(f"Churn prediction error for {customer_id}: {e}")
            return {
                "customer_id": customer_id,
                "churn_risk_score": 0.5,
                "risk_level": "unknown",
                "factors": [],
                "recommendations": []
            }

    async def forecast_ltv(
        self,
        customer_id: str,
        horizon_months: int = 12,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Forecast customer lifetime value.

        Endpoint: POST /api/intelligence/predict/ltv

        Args:
            customer_id: Customer ID
            horizon_months: Forecast horizon (default: 12 months)
            use_cache: Whether to use cached data (default: True)

        Returns:
            {
                "customer_id": "cust_123",
                "horizon_months": 12,
                "forecasted_ltv": 450.00,
                "confidence_interval": {
                    "lower": 380.00,
                    "upper": 520.00,
                    "confidence_level": 0.95
                },
                "current_ltv": 892.50,
                "incremental_ltv": 450.00
            }

        Cache TTL: 1 hour
        """
        # Try cache
        if use_cache:
            cache_key = f"ltv_forecast:{customer_id}:{horizon_months}"
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for LTV forecast {customer_id}")
                return json.loads(cached)

        try:
            response = await self._post_with_retry(
                "/api/intelligence/predict/ltv",
                {
                    "customer_id": customer_id,
                    "horizon_months": horizon_months
                }
            )

            # Cache for 1 hour
            cache_key = f"ltv_forecast:{customer_id}:{horizon_months}"
            await redis_client.setex(
                cache_key,
                settings.quimbi_cache_ltv_ttl,
                json.dumps(response)
            )

            logger.info(
                f"LTV forecast for {customer_id}: "
                f"forecasted=${response.get('forecasted_ltv')}"
            )

            return response

        except QuimbiAPIError as e:
            logger.error(f"LTV forecast error for {customer_id}: {e}")
            return {
                "customer_id": customer_id,
                "horizon_months": horizon_months,
                "forecasted_ltv": 0,
                "confidence_interval": {},
                "current_ltv": 0,
                "incremental_ltv": 0
            }

    async def generate_message(
        self,
        customer_profile: Dict[str, Any],
        goal: str,
        conversation: List[Dict[str, str]],
        channel: str = "email",
        tone: str = "empathetic",
        length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate AI-powered message.

        Endpoint: POST /api/generation/message

        Args:
            customer_profile: Customer intelligence from analyze_customer()
            goal: "resolve_support_issue", "nurture_lead", "upsell", "win_back", "generic_communication"
            conversation: List of messages [{"from": "customer|agent", "content": "..."}]
            channel: "email", "sms", "chat", "phone_script"
            tone: "empathetic", "professional", "casual"
            length: "short", "medium", "long"

        Returns:
            {
                "message": "Generated message text...",
                "tone": "empathetic",
                "channel": "email",
                "personalization_applied": [
                    "Adjusted for beginner (shopping_maturity: new)",
                    "Avoided jargon",
                    "Provided detailed explanations"
                ]
            }

        NOTE: Does NOT cache (context-dependent, always fresh)
        """
        # Transform conversation format from Support Backend to AI Brain format
        # From: [{"from": "customer|agent", "content": "..."}]
        # To: [{"from_customer": bool, "text": "..."}]
        conversation_history = [
            {
                "from_customer": msg["from"] == "customer",
                "text": msg["content"]
            }
            for msg in conversation
        ]

        # Ensure customer_id is a string (AI Brain expects string)
        customer_id = customer_profile.get("customer_id")
        if customer_id is not None:
            customer_id = str(customer_id)

        request_body = {
            "customer_id": customer_id,
            "conversation_history": conversation_history,
            "goal": goal,
            "channel": channel,
            "tone": tone,
            "length": length
        }

        try:
            response = await self._post_with_retry(
                "/api/generation/message",
                request_body,
                timeout=30.0  # AI generation takes longer
            )

            logger.info(
                f"Message generated for customer {customer_profile.get('customer_id')}: "
                f"goal={goal}, channel={channel}, "
                f"personalizations={len(response.get('personalization_applied', []))}"
            )

            return response

        except QuimbiAPIError as e:
            logger.error(f"Message generation error: {e}")
            # Return fallback message
            return {
                "message": "Thank you for contacting us. We're looking into your issue and will respond shortly.",
                "tone": tone,
                "channel": channel,
                "personalization_applied": []
            }

    async def recommend_actions(
        self,
        customer_profile: Dict[str, Any],
        scenario: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get AI-recommended next best actions.

        Endpoint: POST /api/generation/actions

        Args:
            customer_profile: Customer intelligence data
            scenario: "support_ticket", "sales_opportunity", "marketing_campaign", "retention_risk"
            context: Scenario-specific context (e.g., ticket details, opportunity info)

        Returns:
            {
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
                "warnings": [
                    "Customer has high churn risk - handle with extra care",
                    "Revenue at risk: $780 (65% churn × $1200 LTV)"
                ],
                "talking_points": [
                    "Apologize sincerely for the inconvenience",
                    "Emphasize commitment to quality"
                ]
            }
        """
        request_body = {
            "customer_profile": customer_profile,
            "scenario": scenario,
            "context": context
        }

        try:
            response = await self._post_with_retry(
                "/api/generation/actions",
                request_body,
                timeout=30.0
            )

            logger.info(
                f"Actions recommended for customer {customer_profile.get('customer_id')}: "
                f"scenario={scenario}, actions={len(response.get('actions', []))}"
            )

            return response

        except QuimbiAPIError as e:
            logger.error(f"Action recommendation error: {e}")
            return {
                "actions": [],
                "warnings": ["AI recommendation service temporarily unavailable"],
                "talking_points": []
            }

    # ========== Private Helper Methods ==========

    async def _post_with_retry(
        self,
        endpoint: str,
        data: Dict[str, Any],
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        POST request with exponential backoff retry.

        Retries on:
        - 500, 503 (server errors)
        - Network errors

        Does NOT retry on:
        - 400, 404, 422 (client errors)
        - 401, 403 (auth errors)
        - 429 (rate limit - raises QuimbiRateLimitError)
        """
        if not self.client:
            raise QuimbiAPIError("Client not initialized. Call initialize() first.")

        max_retries = max_retries or self.max_retries

        for attempt in range(max_retries):
            try:
                response = await self.client.post(
                    endpoint,
                    json=data,
                    timeout=timeout or self.timeout
                )

                # Success
                if response.status_code == 200:
                    return response.json()

                # Rate limit
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise QuimbiRateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after}s"
                    )

                # Client errors - don't retry
                if 400 <= response.status_code < 500:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                    except:
                        error_msg = response.text

                    raise QuimbiAPIError(
                        f"API error {response.status_code}: {error_msg}"
                    )

                # Server errors - retry
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = (2 ** attempt) * 1.0  # 1s, 2s, 4s
                        logger.warning(
                            f"Quimbi API error {response.status_code} on {endpoint}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise QuimbiAPIError(
                            f"API error {response.status_code} after {max_retries} retries"
                        )

            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) * 1.0
                    logger.warning(
                        f"Network error on {endpoint}: {e}, retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise QuimbiAPIError(f"Network error after {max_retries} retries: {e}")

        raise QuimbiAPIError("Max retries exceeded")

    async def _get_cached_intelligence(self, customer_id: str) -> Optional[Dict]:
        """Get cached customer intelligence."""
        cache_key = f"customer_intel:{customer_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    async def _cache_intelligence(self, customer_id: str, data: Dict):
        """Cache customer intelligence (15 min TTL by default)."""
        cache_key = f"customer_intel:{customer_id}"
        await redis_client.setex(
            cache_key,
            settings.quimbi_cache_intelligence_ttl,
            json.dumps(data)
        )

    def _get_fallback_intelligence(self, customer_id: str) -> Dict:
        """Return fallback data when Quimbi API fails."""
        logger.warning(f"Using fallback intelligence for {customer_id}")
        return {
            "customer_id": customer_id,
            "archetype": {
                "id": "unknown",
                "level": "unknown",
                "segments": {}
            },
            "behavioral_metrics": {
                "lifetime_value": 0,
                "total_orders": 0,
                "avg_order_value": 0,
                "days_since_last_purchase": 0,
                "customer_tenure_days": 0
            },
            "predictions": {
                "churn_risk": 0.5,
                "churn_risk_level": "unknown",
                "ltv_12mo": 0
            },
            "communication_guidance": [
                "Customer intelligence temporarily unavailable"
            ]
        }


# Global instance
quimbi_client = QuimbiClient()
