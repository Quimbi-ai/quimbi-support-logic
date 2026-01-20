"""Customer ID resolution service.

This service resolves support system customer IDs (e.g., cust_3535104cbde4)
to e-commerce customer IDs (Shopify numeric IDs) using the customer_alias table.

This enables AI Brain to access real customer behavioral intelligence from
the fact_customer_current table.
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class CustomerResolver:
    """Resolves support customer IDs to e-commerce customer IDs."""

    @staticmethod
    async def resolve_to_ecommerce_id(
        db: AsyncSession,
        support_customer_id: str
    ) -> Optional[int]:
        """
        Convert support customer ID to e-commerce customer ID.

        Args:
            db: Database session
            support_customer_id: Support system ID (e.g., "cust_3535104cbde4")

        Returns:
            E-commerce customer ID as integer, or None if not found

        Example:
            >>> ecommerce_id = await resolver.resolve_to_ecommerce_id(db, "cust_3535104cbde4")
            >>> print(ecommerce_id)
            5971333382399
        """
        try:
            result = await db.execute(
                text("""
                    SELECT ecommerce_customer_id
                    FROM customer_alias
                    WHERE support_customer_id = :id
                """),
                {"id": support_customer_id}
            )
            row = result.fetchone()

            if row:
                ecommerce_id = row[0]
                logger.info(
                    f"Resolved customer ID: {support_customer_id} → {ecommerce_id}"
                )
                return ecommerce_id
            else:
                logger.warning(
                    f"No e-commerce mapping found for support customer: {support_customer_id}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Error resolving customer ID {support_customer_id}: {e}",
                exc_info=True
            )
            return None

    @staticmethod
    async def resolve_by_email(
        db: AsyncSession,
        email: str
    ) -> Optional[int]:
        """
        Resolve customer by email to e-commerce customer ID.

        This is critical for Gorgias integration where we only have email.

        Args:
            db: Database session
            email: Customer email address

        Returns:
            E-commerce (Shopify) customer ID as integer, or None if not found

        Example:
            >>> ecommerce_id = await resolver.resolve_by_email(db, "emily.chen@example.com")
            >>> print(ecommerce_id)
            5971333382399
        """
        if not email:
            return None

        try:
            # Try customer_alias first
            result = await db.execute(
                text("""
                    SELECT ecommerce_customer_id
                    FROM customer_alias
                    WHERE LOWER(email) = LOWER(:email)
                    LIMIT 1
                """),
                {"email": email}
            )
            row = result.fetchone()

            if row:
                ecommerce_id = row[0]
                logger.info(f"Resolved customer by email: {email} → {ecommerce_id}")
                return ecommerce_id

            logger.warning(f"No customer mapping found for email: {email}")
            return None

        except Exception as e:
            logger.error(f"Error resolving customer by email {email}: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_mapping_info(
        db: AsyncSession,
        support_customer_id: str
    ) -> Optional[dict]:
        """
        Get full mapping information for a support customer.

        Args:
            db: Database session
            support_customer_id: Support system ID

        Returns:
            Dictionary with mapping info, or None if not found

        Example:
            >>> info = await resolver.get_mapping_info(db, "cust_3535104cbde4")
            >>> print(info)
            {
                "support_customer_id": "cust_3535104cbde4",
                "ecommerce_customer_id": 5971333382399,
                "email": "emily.chen@example.com",
                "notes": "Mapped to real Shopify customer - LTV $523,710.49, 1817 orders",
                "created_at": "2026-01-09T04:22:04.172400Z"
            }
        """
        try:
            result = await db.execute(
                text("""
                    SELECT
                        support_customer_id,
                        ecommerce_customer_id,
                        email,
                        notes,
                        created_at,
                        updated_at
                    FROM customer_alias
                    WHERE support_customer_id = :id
                """),
                {"id": support_customer_id}
            )
            row = result.fetchone()

            if row:
                return {
                    "support_customer_id": row[0],
                    "ecommerce_customer_id": row[1],
                    "email": row[2],
                    "notes": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                }
            else:
                return None

        except Exception as e:
            logger.error(
                f"Error fetching mapping info for {support_customer_id}: {e}",
                exc_info=True
            )
            return None


# Singleton instance
customer_resolver = CustomerResolver()
