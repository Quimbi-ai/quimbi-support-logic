"""
Gorgias API Client

Handles communication with Gorgias API for posting messages and notes to tickets.
"""
import logging
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class GorgiasClient:
    """Client for interacting with Gorgias API."""

    def __init__(self):
        """Initialize Gorgias client."""
        self.domain = settings.gorgias_domain
        self.api_key = settings.gorgias_api_key
        self.username = settings.gorgias_username
        self.base_url = f"https://{self.domain}.gorgias.com/api"
        self.timeout = 30.0

    async def post_draft_reply(
        self,
        ticket_id: int,
        body_text: str,
        body_html: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Post a draft reply to a Gorgias ticket.

        This creates a draft message that the agent can review and send.

        Args:
            ticket_id: Gorgias ticket ID
            body_text: Plain text version of the message
            body_html: HTML version of the message (optional)

        Returns:
            Response from Gorgias API or None if failed
        """
        try:
            # Convert plain text to HTML if not provided
            if not body_html:
                body_html = body_text.replace("\n", "<br>")

            # Payload with source field for draft reply
            payload = {
                "body_text": body_text,
                "body_html": body_html,
                "from_agent": True,
                "channel": "email",
                "via": "api",
                "source": {
                    "type": "email",
                    "from": {
                        "name": "AI Support Assistant",
                        "address": self.username
                    },
                    "to": [{
                        "name": customer_name or "",
                        "address": customer_email or ""
                    }]
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tickets/{ticket_id}/messages",
                    json=payload,
                    auth=(self.username, self.api_key),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )

                if response.status_code == 201:
                    logger.info(f"✅ Posted draft reply to ticket {ticket_id}")
                    return response.json()
                else:
                    # Log full error details (don't truncate)
                    logger.error(
                        f"Failed to post draft reply to ticket {ticket_id}",
                        extra={
                            "status_code": response.status_code,
                            "response_body": response.text,  # Full response
                            "request_id": response.headers.get("X-Request-Id"),
                            "ticket_id": ticket_id
                        }
                    )
                    # Return error details for debugging
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "response": response.text  # Return full response (not truncated)
                    }

        except Exception as e:
            logger.error(f"Error posting draft reply to ticket {ticket_id}: {e}", exc_info=True)
            return None

    async def post_internal_note(
        self,
        ticket_id: int,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Post an internal note to a Gorgias ticket.

        Internal notes are only visible to agents, not customers.

        Args:
            ticket_id: Gorgias ticket ID
            body_text: Plain text version of the note
            body_html: HTML version of the note (optional)

        Returns:
            Response from Gorgias API or None if failed
        """
        try:
            # Convert plain text to HTML if not provided
            if not body_html:
                body_html = body_text.replace("\n", "<br>")

            # Payload for internal note - simpler structure
            payload = {
                "body_text": body_text,
                "body_html": body_html,
                "from_agent": True,
                "channel": "internal-note",
                "via": "api",
                "source": {
                    "type": "internal-note",
                    "from": {
                        "name": "AI Support Assistant",
                        "address": self.username
                    }
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tickets/{ticket_id}/messages",
                    json=payload,
                    auth=(self.username, self.api_key),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )

                if response.status_code == 201:
                    logger.info(f"✅ Posted internal note to ticket {ticket_id}")
                    return response.json()
                else:
                    # Log full error details (don't truncate)
                    logger.error(
                        f"Failed to post internal note to ticket {ticket_id}",
                        extra={
                            "status_code": response.status_code,
                            "response_body": response.text,  # Full response
                            "request_id": response.headers.get("X-Request-Id"),
                            "ticket_id": ticket_id
                        }
                    )
                    # Return error details for debugging
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "response": response.text  # Return full response (not truncated)
                    }

        except Exception as e:
            logger.error(f"Error posting internal note to ticket {ticket_id}: {e}", exc_info=True)
            return None

    async def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a ticket from Gorgias API.

        Args:
            ticket_id: Gorgias ticket ID

        Returns:
            Ticket data or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/tickets/{ticket_id}",
                    auth=(self.username, self.api_key),
                    headers={"Accept": "application/json"}
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to fetch ticket {ticket_id}: "
                        f"Status {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error fetching ticket {ticket_id}: {e}", exc_info=True)
            return None

    async def delete_message(
        self,
        ticket_id: int,
        message_id: int
    ) -> bool:
        """
        Delete a message from a Gorgias ticket.

        Args:
            ticket_id: Gorgias ticket ID
            message_id: Message ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/tickets/{ticket_id}/messages/{message_id}",
                    auth=(self.username, self.api_key),
                    headers={"Accept": "application/json"}
                )

                if response.status_code in [200, 204]:
                    logger.info(f"✅ Deleted message {message_id} from ticket {ticket_id}")
                    return True
                else:
                    logger.error(
                        f"Failed to delete message {message_id} from ticket {ticket_id}: "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}", exc_info=True)
            return False

    async def health_check(self) -> bool:
        """
        Check if Gorgias API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/account",
                    auth=(self.username, self.api_key),
                    headers={"Accept": "application/json"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Gorgias health check failed: {e}")
            return False


# Global Gorgias client instance
gorgias_client = GorgiasClient()
