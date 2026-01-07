"""
Shopify Fulfillment Service - Multi-Warehouse Tracking Support

Fetches fulfillment data from Shopify including:
- Multiple fulfillments per order (split shipments)
- Warehouse/location information
- Per-item tracking numbers
- Carrier information
- Delivery status

Usage:
    from integrations.shopify_fulfillment_service import get_fulfillment_service

    service = get_fulfillment_service()
    if service:
        fulfillments = await service.get_order_fulfillments("gid://shopify/Order/12345")
        # Returns detailed fulfillment data with warehouse info
"""
import os
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ShopifyFulfillmentService:
    """Fetch and process Shopify order fulfillment data including multi-warehouse tracking."""

    def __init__(self, shop_name: str, access_token: str, api_version: str = "2024-10"):
        """
        Initialize Shopify Fulfillment Service.

        Args:
            shop_name: Shopify shop name (e.g., "lindas-electric-quilters")
            access_token: Shopify Admin API access token (starts with shpat_)
            api_version: Shopify API version (default: 2024-10)
        """
        self.shop_name = shop_name
        self.access_token = access_token
        self.api_version = api_version
        self.graphql_url = f"https://{shop_name}.myshopify.com/admin/api/{api_version}/graphql.json"
        self.http_client = httpx.AsyncClient(timeout=15.0)
        logger.info(f"Initialized Shopify Fulfillment Service for shop: {shop_name}")

    async def get_order_fulfillments(self, order_id: str) -> Dict[str, Any]:
        """
        Get all fulfillments for a Shopify order.

        Fetches complete fulfillment information including:
        - Tracking numbers and URLs
        - Carrier information
        - Fulfillment status
        - Items in each fulfillment
        - Warehouse/location data
        - Estimated delivery dates

        Args:
            order_id: Shopify order ID (can be GID like "gid://shopify/Order/12345"
                     or legacy numeric ID like "12345")

        Returns:
            Dictionary with order and fulfillment data:
            {
                "order_id": "12345",
                "order_name": "#1001",
                "order_number": 1001,
                "created_at": "2025-01-15T10:00:00Z",
                "total_items": 5,
                "fulfillment_status": "PARTIALLY_FULFILLED",
                "fulfillments": [
                    {
                        "fulfillment_id": "gid://shopify/Fulfillment/67890",
                        "status": "SUCCESS",
                        "created_at": "2025-01-15T12:00:00Z",
                        "updated_at": "2025-01-16T08:00:00Z",
                        "tracking_info": [
                            {
                                "number": "1Z999AA10123456784",
                                "company": "UPS",
                                "url": "https://www.ups.com/track?tracknum=1Z999..."
                            }
                        ],
                        "location": {
                            "id": "gid://shopify/Location/123",
                            "name": "New Jersey Distribution Center",
                            "address": "Newark, NJ"
                        },
                        "estimated_delivery_at": "2025-01-17",
                        "delivered_at": null,
                        "items": [
                            {
                                "line_item_id": "gid://shopify/LineItem/1",
                                "title": "Rose Thread Bundle",
                                "sku": "THREAD-ROSE-001",
                                "quantity": 2
                            }
                        ]
                    },
                    ...
                ],
                "unfulfilled_items": [
                    {
                        "line_item_id": "gid://shopify/LineItem/2",
                        "title": "Blue Fabric Roll",
                        "sku": "FABRIC-BLUE-002",
                        "quantity": 3,
                        "fulfillment_status": "NOT_ELIGIBLE"
                    }
                ]
            }

        Raises:
            httpx.HTTPError: On network/API errors
            ValueError: If order_id is invalid
        """
        if not order_id:
            raise ValueError("order_id cannot be empty")

        # Normalize to GID format if numeric
        if not order_id.startswith("gid://"):
            order_id = f"gid://shopify/Order/{order_id}"

        logger.info(f"🔍 Fetching fulfillments for order: {order_id}")

        try:
            # GraphQL query for order with fulfillments
            query = """
            query GetOrderFulfillments($id: ID!) {
              order(id: $id) {
                id
                legacyResourceId
                name
                orderNumber
                createdAt
                displayFulfillmentStatus
                lineItems(first: 100) {
                  edges {
                    node {
                      id
                      title
                      sku
                      quantity
                      fulfillmentStatus
                      product {
                        id
                        title
                      }
                      variant {
                        id
                        title
                      }
                    }
                  }
                }
                fulfillments(first: 50) {
                  edges {
                    node {
                      id
                      legacyResourceId
                      status
                      createdAt
                      updatedAt
                      deliveredAt
                      estimatedDeliveryAt
                      inTransitAt
                      displayStatus
                      trackingInfo {
                        number
                        company
                        url
                      }
                      location {
                        id
                        legacyResourceId
                        name
                        address {
                          address1
                          address2
                          city
                          provinceCode
                          zip
                          countryCode
                        }
                      }
                      fulfillmentLineItems(first: 100) {
                        edges {
                          node {
                            id
                            quantity
                            lineItem {
                              id
                              title
                              sku
                              quantity
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            """

            # Execute GraphQL request
            response = await self.http_client.post(
                self.graphql_url,
                json={
                    "query": query,
                    "variables": {"id": order_id}
                },
                headers={
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                logger.error(f"❌ Shopify API error: {response.status_code} - {response.text}")
                raise httpx.HTTPError(f"Shopify API returned {response.status_code}")

            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                logger.error(f"❌ Shopify GraphQL errors: {data['errors']}")
                raise ValueError(f"GraphQL errors: {data['errors']}")

            # Extract order data
            order = data.get("data", {}).get("order")
            if not order:
                logger.warning(f"❌ Order not found: {order_id}")
                return {
                    "order_id": order_id,
                    "error": "Order not found",
                    "fulfillments": [],
                    "unfulfilled_items": []
                }

            # Process the order data
            result = self._process_order_data(order)

            logger.info(f"✅ Retrieved {len(result['fulfillments'])} fulfillment(s) for order {result['order_name']}")
            return result

        except httpx.TimeoutException:
            logger.error(f"⏱️  Shopify API timeout for order: {order_id}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error fetching fulfillments: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching fulfillments: {e}", exc_info=True)
            raise

    def _process_order_data(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw Shopify order data into structured fulfillment information.

        Args:
            order: Raw order data from Shopify GraphQL

        Returns:
            Processed fulfillment data dictionary
        """
        order_id = order.get("legacyResourceId")
        order_name = order.get("name", f"#{order_id}")

        # Process all line items
        line_items = []
        for edge in order.get("lineItems", {}).get("edges", []):
            item = edge["node"]
            line_items.append({
                "line_item_id": item["id"],
                "title": item.get("title", ""),
                "sku": item.get("sku", ""),
                "quantity": item.get("quantity", 0),
                "fulfillment_status": item.get("fulfillmentStatus", "NOT_ELIGIBLE"),
                "product_title": item.get("product", {}).get("title", ""),
                "variant_title": item.get("variant", {}).get("title", "")
            })

        # Process fulfillments
        fulfillments = []
        fulfilled_item_ids = set()

        for edge in order.get("fulfillments", {}).get("edges", []):
            fulfillment = edge["node"]

            # Extract tracking information
            tracking_info_list = []
            for tracking in fulfillment.get("trackingInfo", []):
                tracking_info_list.append({
                    "number": tracking.get("number", ""),
                    "company": tracking.get("company", ""),
                    "url": tracking.get("url", "")
                })

            # Extract location information
            location_data = fulfillment.get("location") or {}
            location_address = location_data.get("address") or {}
            location = {
                "id": location_data.get("legacyResourceId", ""),
                "name": location_data.get("name", "Unknown Warehouse"),
                "address": self._format_address(location_address)
            }

            # Extract fulfilled items
            fulfilled_items = []
            for item_edge in fulfillment.get("fulfillmentLineItems", {}).get("edges", []):
                item_node = item_edge["node"]
                line_item = item_node.get("lineItem") or {}

                fulfilled_items.append({
                    "line_item_id": line_item.get("id", ""),
                    "title": line_item.get("title", ""),
                    "sku": line_item.get("sku", ""),
                    "quantity": item_node.get("quantity", 0)
                })

                # Track which items have been fulfilled
                fulfilled_item_ids.add(line_item.get("id"))

            # Build fulfillment object
            fulfillments.append({
                "fulfillment_id": fulfillment.get("legacyResourceId", ""),
                "status": fulfillment.get("status", ""),
                "display_status": fulfillment.get("displayStatus", ""),
                "created_at": fulfillment.get("createdAt", ""),
                "updated_at": fulfillment.get("updatedAt", ""),
                "delivered_at": fulfillment.get("deliveredAt"),
                "estimated_delivery_at": fulfillment.get("estimatedDeliveryAt"),
                "in_transit_at": fulfillment.get("inTransitAt"),
                "tracking_info": tracking_info_list,
                "location": location,
                "items": fulfilled_items,
                "item_count": len(fulfilled_items)
            })

        # Identify unfulfilled items
        unfulfilled_items = [
            item for item in line_items
            if item["line_item_id"] not in fulfilled_item_ids
            and item["fulfillment_status"] != "FULFILLED"
        ]

        # Count total items
        total_items = sum(item["quantity"] for item in line_items)
        fulfilled_items_count = sum(
            item["quantity"] for fulfillment in fulfillments
            for item in fulfillment["items"]
        )

        return {
            "order_id": order_id,
            "order_name": order_name,
            "order_number": order.get("orderNumber"),
            "created_at": order.get("createdAt", ""),
            "fulfillment_status": order.get("displayFulfillmentStatus", "UNFULFILLED"),
            "total_items": total_items,
            "fulfilled_items_count": fulfilled_items_count,
            "unfulfilled_items_count": total_items - fulfilled_items_count,
            "fulfillments": fulfillments,
            "unfulfilled_items": unfulfilled_items,
            "all_line_items": line_items,
            "has_split_shipments": len(fulfillments) > 1,
            "fulfillment_count": len(fulfillments)
        }

    def _format_address(self, address: Dict[str, Any]) -> str:
        """
        Format Shopify address into a readable string.

        Args:
            address: Shopify address object

        Returns:
            Formatted address string (e.g., "Newark, NJ 07102")
        """
        if not address:
            return ""

        parts = []
        if address.get("city"):
            parts.append(address["city"])
        if address.get("provinceCode"):
            parts.append(address["provinceCode"])
        if address.get("zip"):
            parts.append(address["zip"])

        return ", ".join(parts) if parts else "Unknown Location"

    async def get_order_by_number(self, order_number: int) -> Optional[Dict[str, Any]]:
        """
        Get fulfillments by order number (e.g., 1001 instead of full ID).

        Args:
            order_number: Shopify order number (the number shown to customers)

        Returns:
            Fulfillment data dictionary or None if not found
        """
        logger.info(f"🔍 Looking up order by number: #{order_number}")

        try:
            # Query to find order by order number
            query = """
            query FindOrderByNumber($query: String!) {
              orders(first: 1, query: $query) {
                edges {
                  node {
                    id
                    legacyResourceId
                  }
                }
              }
            }
            """

            response = await self.http_client.post(
                self.graphql_url,
                json={
                    "query": query,
                    "variables": {"query": f"name:#{order_number}"}
                },
                headers={
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                logger.error(f"❌ Shopify API error: {response.status_code}")
                return None

            data = response.json()
            edges = data.get("data", {}).get("orders", {}).get("edges", [])

            if not edges:
                logger.warning(f"❌ Order not found: #{order_number}")
                return None

            order_id = edges[0]["node"]["id"]

            # Now fetch full fulfillment data
            return await self.get_order_fulfillments(order_id)

        except Exception as e:
            logger.error(f"❌ Error looking up order by number: {e}", exc_info=True)
            return None

    def detect_split_shipment_scenario(self, fulfillment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze fulfillment data to detect split shipment scenarios.

        Identifies:
        - Multiple warehouses shipping same order
        - Partial shipments with remaining items
        - Different carriers used
        - Staggered delivery dates

        Args:
            fulfillment_data: Processed fulfillment data from get_order_fulfillments()

        Returns:
            Analysis dictionary:
            {
                "is_split_shipment": True,
                "fulfillment_count": 2,
                "warehouse_count": 2,
                "unique_carriers": ["UPS", "FedEx"],
                "estimated_delivery_range": {
                    "earliest": "2025-01-17",
                    "latest": "2025-01-20"
                },
                "items_by_warehouse": {
                    "New Jersey DC": ["Item A", "Item B"],
                    "California DC": ["Item C"]
                },
                "customer_message_suggestion": "Your order will arrive in 2 separate shipments..."
            }
        """
        fulfillments = fulfillment_data.get("fulfillments", [])

        if not fulfillments:
            return {
                "is_split_shipment": False,
                "message": "No fulfillments found - order not yet shipped"
            }

        # Detect split shipment
        is_split = len(fulfillments) > 1

        # Count unique warehouses
        warehouses = set(f.get("location", {}).get("name", "") for f in fulfillments)
        warehouse_count = len([w for w in warehouses if w])

        # Count unique carriers
        carriers = set()
        for fulfillment in fulfillments:
            for tracking in fulfillment.get("tracking_info", []):
                carrier = tracking.get("company", "")
                if carrier:
                    carriers.add(carrier)

        # Find delivery date range
        delivery_dates = [
            f.get("estimated_delivery_at") or f.get("delivered_at")
            for f in fulfillments
        ]
        delivery_dates = [d for d in delivery_dates if d]

        # Group items by warehouse
        items_by_warehouse = {}
        for fulfillment in fulfillments:
            warehouse_name = fulfillment.get("location", {}).get("name", "Unknown")
            items = [item["title"] for item in fulfillment.get("items", [])]
            items_by_warehouse[warehouse_name] = items

        # Generate customer-friendly message
        if is_split:
            customer_message = self._generate_split_shipment_message(
                fulfillments, warehouse_count, delivery_dates
            )
        else:
            customer_message = "Your complete order shipped from one location."

        return {
            "is_split_shipment": is_split,
            "fulfillment_count": len(fulfillments),
            "warehouse_count": warehouse_count,
            "unique_carriers": list(carriers),
            "estimated_delivery_range": {
                "earliest": min(delivery_dates) if delivery_dates else None,
                "latest": max(delivery_dates) if delivery_dates else None
            },
            "items_by_warehouse": items_by_warehouse,
            "customer_message_suggestion": customer_message,
            "unfulfilled_items_count": fulfillment_data.get("unfulfilled_items_count", 0)
        }

    def _generate_split_shipment_message(self, fulfillments: List[Dict],
                                         warehouse_count: int,
                                         delivery_dates: List[str]) -> str:
        """Generate customer-friendly message for split shipments."""
        messages = []

        if warehouse_count > 1:
            messages.append(
                f"Your order will arrive in {len(fulfillments)} separate shipments "
                f"from {warehouse_count} different warehouses."
            )
        else:
            messages.append(
                f"Your order was split into {len(fulfillments)} shipments "
                "for faster delivery."
            )

        # Add tracking info preview
        for i, fulfillment in enumerate(fulfillments, 1):
            tracking = fulfillment.get("tracking_info", [])
            if tracking:
                tracking_num = tracking[0].get("number", "")
                carrier = tracking[0].get("company", "")
                messages.append(
                    f"Shipment {i}: {carrier} tracking {tracking_num}"
                )

        return " ".join(messages)

    async def close(self):
        """Close HTTP client connection."""
        await self.http_client.aclose()
        logger.info("Closed Shopify Fulfillment Service")


# Module-level singleton instance (lazy initialization)
_fulfillment_service: Optional[ShopifyFulfillmentService] = None


def get_fulfillment_service() -> Optional[ShopifyFulfillmentService]:
    """
    Get or create Shopify fulfillment service instance.

    Reads configuration from environment variables:
    - SHOPIFY_SHOP_NAME: Shop name (e.g., "lindas-electric-quilters")
    - SHOPIFY_ACCESS_TOKEN: Admin API token (starts with shpat_)
    - SHOPIFY_API_VERSION: API version (optional, defaults to 2024-10)

    Returns:
        ShopifyFulfillmentService instance or None if credentials not configured
    """
    global _fulfillment_service

    if _fulfillment_service is None:
        shop_name = os.getenv("SHOPIFY_SHOP_NAME")
        access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        api_version = os.getenv("SHOPIFY_API_VERSION", "2024-10")

        if not shop_name or not access_token:
            logger.warning(
                "Shopify fulfillment service not configured - missing environment variables: "
                "SHOPIFY_SHOP_NAME, SHOPIFY_ACCESS_TOKEN"
            )
            return None

        _fulfillment_service = ShopifyFulfillmentService(
            shop_name=shop_name,
            access_token=access_token,
            api_version=api_version
        )

        logger.info("✅ Shopify fulfillment service initialized")

    return _fulfillment_service
