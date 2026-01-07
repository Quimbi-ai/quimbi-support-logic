"""
Database initialization and seeding script.

Run with: python -m app.db_init
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from app.models.database import init_db, async_session_maker, Customer, Ticket, Message
from app.services.scoring_service import ScoringService


async def seed_database():
    """Seed database with sample data."""
    print("Creating database tables...")
    await init_db()

    print("Seeding sample data...")
    async with async_session_maker() as session:
        # Create sample customers
        customers = [
            Customer(
                id=f"c{i}",
                email=f"customer{i}@example.com",
                name=f"Customer {i}",
                lifetime_value=ltv,
                total_orders=orders,
                churn_risk_score=churn
            )
            for i, (ltv, orders, churn) in enumerate([
                (2500.0, 12, 0.75),  # High value, high risk
                (450.0, 3, 0.25),    # Low value, low risk
                (5200.0, 28, 0.85),  # Very high value, very high risk
                (1200.0, 8, 0.45),   # Medium value, medium risk
                (180.0, 1, 0.95),    # New customer, high risk
            ], 1)
        ]

        session.add_all(customers)
        await session.flush()

        # Create sample tickets
        scoring_service = ScoringService()
        now = datetime.utcnow()

        tickets_data = [
            {
                "customer_id": "c1",
                "subject": "Order not delivered",
                "priority": "high",
                "channel": "email",
                "created_at": now - timedelta(hours=2),
                "sentiment": 0.2,
                "message": "My order hasn't arrived and tracking shows no updates for 3 days. This is unacceptable!"
            },
            {
                "customer_id": "c2",
                "subject": "Need tracking number",
                "priority": "normal",
                "channel": "chat",
                "created_at": now - timedelta(minutes=30),
                "sentiment": 0.7,
                "message": "Can you send me the tracking number for order #12345?"
            },
            {
                "customer_id": "c3",
                "subject": "Product damaged - need refund",
                "priority": "urgent",
                "channel": "email",
                "created_at": now - timedelta(hours=5),
                "sentiment": 0.1,
                "message": "Product arrived damaged. Need refund immediately. This is the second time this has happened!"
            },
            {
                "customer_id": "c4",
                "subject": "Question about return policy",
                "priority": "low",
                "channel": "email",
                "created_at": now - timedelta(days=1),
                "sentiment": 0.8,
                "message": "Hi, I'd like to know what your return policy is for unopened items."
            },
            {
                "customer_id": "c5",
                "subject": "Wrong item shipped",
                "priority": "high",
                "channel": "email",
                "created_at": now - timedelta(hours=8),
                "sentiment": 0.3,
                "message": "I ordered a blue shirt size M but received a red shirt size L. Please fix this."
            },
            {
                "customer_id": "c1",
                "subject": "Chargeback initiated",
                "priority": "urgent",
                "channel": "email",
                "created_at": now - timedelta(hours=1),
                "sentiment": 0.05,
                "message": "Since you haven't responded to my previous ticket, I've initiated a chargeback with my bank."
            },
        ]

        tickets = []
        for ticket_data in tickets_data:
            ticket_id = str(uuid.uuid4())
            message_content = ticket_data.pop("message")
            sentiment = ticket_data.pop("sentiment")

            ticket = Ticket(
                id=ticket_id,
                **ticket_data,
                customer_sentiment=sentiment,
                estimated_difficulty=0.5,
                status="open"
            )

            # Calculate smart score
            customer = next(c for c in customers if c.id == ticket.customer_id)
            ticket.smart_score = scoring_service.calculate_ticket_score(
                ticket={
                    "created_at": ticket.created_at,
                    "priority": ticket.priority,
                    "customer_sentiment": ticket.customer_sentiment,
                    "estimated_difficulty": ticket.estimated_difficulty,
                    "subject": ticket.subject,
                },
                customer={
                    "business_metrics": {
                        "lifetime_value": customer.lifetime_value,
                        "total_orders": customer.total_orders,
                    },
                    "churn_risk": {
                        "churn_risk_score": customer.churn_risk_score,
                    },
                },
                topic_alerts=None
            )

            tickets.append(ticket)

            # Add initial message
            message = Message(
                id=str(uuid.uuid4()),
                ticket_id=ticket_id,
                content=message_content,
                from_agent=False,
                from_name=customer.name,
                from_email=customer.email,
                created_at=ticket.created_at,
                sentiment_score=sentiment
            )
            session.add(message)

        session.add_all(tickets)
        await session.commit()

    print(f"✓ Created {len(customers)} customers")
    print(f"✓ Created {len(tickets)} tickets")
    print("Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
