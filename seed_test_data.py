"""
Seed script to create test data for frontend development.
Creates customers, tickets, and messages.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from app.models.database import get_db, Base, engine, Customer, Ticket, Message
from app.models.agent import Agent, AgentRole, AgentStatus
from app.services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def seed_all():
    """Create comprehensive test data."""
    print("🌱 Seeding test data...\n")

    async with AsyncSession(engine) as session:
        # 1. Create admin agent if not exists
        print("1️⃣  Creating admin agent...")
        result = await session.execute(select(Agent).where(Agent.email == "admin@example.com"))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = Agent(
                email="admin@example.com",
                hashed_password=AuthService.hash_password("admin123"),
                name="Admin User",
                role=AgentRole.ADMIN,
                department="Management",
                status=AgentStatus.OFFLINE,
                max_concurrent_tickets=20,
                specializations=["all"],
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            print(f"   ✅ Created admin: {admin.email}")
        else:
            print(f"   ℹ️  Admin already exists: {admin.email}")

        # 2. Create additional agents
        print("\n2️⃣  Creating support agents...")
        agents_data = [
            {
                "email": "sarah@example.com",
                "password": "password123",
                "name": "Sarah Johnson",
                "role": AgentRole.SENIOR_AGENT,
                "department": "Technical Support",
                "specializations": ["technical", "billing"],
            },
            {
                "email": "mike@example.com",
                "password": "password123",
                "name": "Mike Chen",
                "role": AgentRole.AGENT,
                "department": "Customer Support",
                "specializations": ["shipping", "returns"],
            },
        ]

        agents = {}
        for agent_data in agents_data:
            result = await session.execute(select(Agent).where(Agent.email == agent_data["email"]))
            agent = result.scalar_one_or_none()

            if not agent:
                agent = Agent(
                    email=agent_data["email"],
                    hashed_password=AuthService.hash_password(agent_data["password"]),
                    name=agent_data["name"],
                    role=agent_data["role"],
                    department=agent_data["department"],
                    status=AgentStatus.OFFLINE,
                    max_concurrent_tickets=10,
                    specializations=agent_data["specializations"],
                )
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                print(f"   ✅ Created agent: {agent.name} ({agent.email})")
            else:
                print(f"   ℹ️  Agent already exists: {agent.name}")

            agents[agent_data["email"]] = agent

        # 3. Create customers
        print("\n3️⃣  Creating customers...")
        customers_data = [
            {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "email": "john.doe@gmail.com",
                "name": "John Doe",
                "lifetime_value": 1250.00,
                "total_orders": 8,
                "churn_risk_score": 0.15,
            },
            {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "email": "jane.smith@yahoo.com",
                "name": "Jane Smith",
                "lifetime_value": 890.50,
                "total_orders": 5,
                "churn_risk_score": 0.25,
            },
            {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "email": "bob.wilson@outlook.com",
                "name": "Bob Wilson",
                "lifetime_value": 2100.00,
                "total_orders": 12,
                "churn_risk_score": 0.05,
            },
            {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "email": "alice.brown@gmail.com",
                "name": "Alice Brown",
                "lifetime_value": 340.00,
                "total_orders": 2,
                "churn_risk_score": 0.45,
            },
            {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "email": "charlie.davis@proton.me",
                "name": "Charlie Davis",
                "lifetime_value": 580.00,
                "total_orders": 4,
                "churn_risk_score": 0.30,
            },
        ]

        customers = {}  # Maps email -> customer_id
        for cust_data in customers_data:
            result = await session.execute(select(Customer).where(Customer.email == cust_data["email"]))
            customer = result.scalar_one_or_none()

            if not customer:
                customer = Customer(**cust_data)
                session.add(customer)
                await session.commit()
                await session.refresh(customer)
                print(f"   ✅ Created customer: {customer.name} ({customer.email})")
            else:
                print(f"   ℹ️  Customer already exists: {customer.name}")

            # Store customer ID instead of the object to avoid session expiry issues
            customers[cust_data["email"]] = customer.id

        # 4. Create tickets with messages
        print("\n4️⃣  Creating tickets...")
        tickets_data = [
            {
                "id": f"ticket_{uuid.uuid4().hex[:8]}",
                "customer_email": "john.doe@gmail.com",
                "subject": "Payment not processing",
                "status": "open",
                "priority": "high",
                "channel": "email",
                "customer_sentiment": 0.2,
                "smart_score": 8.5,
                "estimated_difficulty": 0.6,
                "created_at": datetime.utcnow() - timedelta(hours=2),
                "updated_at": datetime.utcnow() - timedelta(hours=2),
                "messages": [
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "I've been trying to complete my purchase for the last hour but keep getting an error message saying 'Payment declined'. My card is definitely valid and has sufficient funds. This is very frustrating!",
                        "from_agent": False,
                        "from_name": "John Doe",
                        "from_email": "john.doe@gmail.com",
                        "sentiment_score": 0.2,
                        "detected_intent": "payment_issue",
                        "created_at": datetime.utcnow() - timedelta(hours=2),
                    },
                ],
            },
            {
                "id": f"ticket_{uuid.uuid4().hex[:8]}",
                "customer_email": "jane.smith@yahoo.com",
                "subject": "Wrong item received",
                "status": "in_progress",
                "priority": "medium",
                "channel": "email",
                "customer_sentiment": 0.4,
                "smart_score": 6.5,
                "estimated_difficulty": 0.4,
                "created_at": datetime.utcnow() - timedelta(days=1),
                "updated_at": datetime.utcnow() - timedelta(hours=19),
                "messages": [
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "Hi, I ordered a blue t-shirt (size M) but received a red hoodie (size L). Order #12345. Can you help?",
                        "from_agent": False,
                        "from_name": "Jane Smith",
                        "from_email": "jane.smith@yahoo.com",
                        "sentiment_score": 0.5,
                        "detected_intent": "wrong_item",
                        "created_at": datetime.utcnow() - timedelta(days=1),
                    },
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "Hi Jane, I'm so sorry about this mix-up! I've checked your order and I can see the warehouse shipped the wrong item. I'm arranging a free return label and we'll send the correct blue t-shirt right away. You should receive the label via email within the next hour.",
                        "from_agent": True,
                        "from_name": "Sarah Johnson",
                        "from_email": "sarah@example.com",
                        "sentiment_score": 0.8,
                        "detected_intent": "resolution",
                        "created_at": datetime.utcnow() - timedelta(hours=20),
                    },
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "Thank you! Just to confirm - do I need to return the wrong item first, or will you send the correct one right away?",
                        "from_agent": False,
                        "from_name": "Jane Smith",
                        "from_email": "jane.smith@yahoo.com",
                        "sentiment_score": 0.7,
                        "detected_intent": "clarification",
                        "created_at": datetime.utcnow() - timedelta(hours=19),
                    },
                ],
            },
            {
                "id": f"ticket_{uuid.uuid4().hex[:8]}",
                "customer_email": "bob.wilson@outlook.com",
                "subject": "Shipping delay inquiry",
                "status": "open",
                "priority": "low",
                "channel": "chat",
                "customer_sentiment": 0.6,
                "smart_score": 4.5,
                "estimated_difficulty": 0.3,
                "created_at": datetime.utcnow() - timedelta(hours=5),
                "updated_at": datetime.utcnow() - timedelta(hours=5),
                "messages": [
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "Hey, my order was supposed to arrive yesterday but the tracking says it's still in transit. Any update?",
                        "from_agent": False,
                        "from_name": "Bob Wilson",
                        "from_email": "bob.wilson@outlook.com",
                        "sentiment_score": 0.5,
                        "detected_intent": "shipping_delay",
                        "created_at": datetime.utcnow() - timedelta(hours=5),
                    },
                ],
            },
            {
                "id": f"ticket_{uuid.uuid4().hex[:8]}",
                "customer_email": "alice.brown@gmail.com",
                "subject": "Account login issues",
                "status": "open",
                "priority": "high",
                "channel": "email",
                "customer_sentiment": 0.3,
                "smart_score": 7.8,
                "estimated_difficulty": 0.5,
                "created_at": datetime.utcnow() - timedelta(minutes=30),
                "updated_at": datetime.utcnow() - timedelta(minutes=30),
                "messages": [
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "I can't log into my account! I've tried resetting my password twice but the reset emails aren't coming through. I've checked spam folder too. I have an order I need to track urgently.",
                        "from_agent": False,
                        "from_name": "Alice Brown",
                        "from_email": "alice.brown@gmail.com",
                        "sentiment_score": 0.3,
                        "detected_intent": "account_access",
                        "created_at": datetime.utcnow() - timedelta(minutes=30),
                    },
                ],
            },
            {
                "id": f"ticket_{uuid.uuid4().hex[:8]}",
                "customer_email": "charlie.davis@proton.me",
                "subject": "Question about refund policy",
                "status": "resolved",
                "priority": "low",
                "channel": "email",
                "customer_sentiment": 0.8,
                "smart_score": 2.0,
                "estimated_difficulty": 0.2,
                "created_at": datetime.utcnow() - timedelta(days=3),
                "updated_at": datetime.utcnow() - timedelta(days=2, hours=23),
                "messages": [
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "What's your refund policy for items bought during a sale?",
                        "from_agent": False,
                        "from_name": "Charlie Davis",
                        "from_email": "charlie.davis@proton.me",
                        "sentiment_score": 0.6,
                        "detected_intent": "policy_question",
                        "created_at": datetime.utcnow() - timedelta(days=3),
                    },
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "Hi Charlie! Sale items follow the same 30-day return policy as regular items. As long as the item is unused and in original packaging, you can return it for a full refund within 30 days of delivery. Is there something specific you're looking to return?",
                        "from_agent": True,
                        "from_name": "Mike Chen",
                        "from_email": "mike@example.com",
                        "sentiment_score": 0.85,
                        "detected_intent": "answer_policy",
                        "created_at": datetime.utcnow() - timedelta(days=3, hours=2),
                    },
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "No, just wanted to know before I purchased. Thanks!",
                        "from_agent": False,
                        "from_name": "Charlie Davis",
                        "from_email": "charlie.davis@proton.me",
                        "sentiment_score": 0.9,
                        "detected_intent": "satisfied",
                        "created_at": datetime.utcnow() - timedelta(days=3, hours=1),
                    },
                ],
            },
            {
                "id": f"ticket_{uuid.uuid4().hex[:8]}",
                "customer_email": "john.doe@gmail.com",
                "subject": "Discount code not working",
                "status": "open",
                "priority": "medium",
                "channel": "chat",
                "customer_sentiment": 0.4,
                "smart_score": 5.5,
                "estimated_difficulty": 0.3,
                "created_at": datetime.utcnow() - timedelta(hours=1),
                "updated_at": datetime.utcnow() - timedelta(hours=1),
                "messages": [
                    {
                        "id": f"msg_{uuid.uuid4().hex[:8]}",
                        "content": "I received an email with discount code SAVE20 but it's saying invalid when I try to use it at checkout",
                        "from_agent": False,
                        "from_name": "John Doe",
                        "from_email": "john.doe@gmail.com",
                        "sentiment_score": 0.4,
                        "detected_intent": "promo_code_issue",
                        "created_at": datetime.utcnow() - timedelta(hours=1),
                    },
                ],
            },
        ]

        ticket_count = 0
        message_count = 0

        for ticket_data in tickets_data:
            customer_id = customers[ticket_data["customer_email"]]  # Get customer_id from dict
            messages_data = ticket_data.pop("messages")
            customer_email = ticket_data.pop("customer_email")

            # Check if ticket already exists (by subject and customer)
            result = await session.execute(
                select(Ticket).where(
                    Ticket.customer_id == customer_id,
                    Ticket.subject == ticket_data["subject"]
                )
            )
            ticket = result.scalar_one_or_none()

            if not ticket:
                ticket = Ticket(
                    customer_id=customer_id,
                    **ticket_data
                )
                session.add(ticket)
                await session.commit()
                await session.refresh(ticket)
                ticket_count += 1
                print(f"   ✅ Created ticket: {ticket.subject}")

                # Create messages for this ticket
                for msg_data in messages_data:
                    message = Message(
                        ticket_id=ticket.id,
                        **msg_data
                    )
                    session.add(message)
                    message_count += 1

                await session.commit()
            else:
                print(f"   ℹ️  Ticket already exists: {ticket.subject}")

        print(f"\n   📝 Created {message_count} messages")

        # 5. Summary
        print("\n" + "="*60)
        print("✅ Seeding completed successfully!\n")
        print(f"👤 Agents: 3 (admin + 2 support)")
        print(f"👥 Customers: 5")
        print(f"🎫 Tickets: {ticket_count} new tickets created")
        print(f"💬 Messages: {message_count} new messages created")
        print("\n" + "="*60)
        print("\n🔐 Login credentials:")
        print("   Admin:")
        print("   - Email: admin@example.com")
        print("   - Password: admin123")
        print("\n   Agents:")
        print("   - Email: sarah@example.com / Password: password123")
        print("   - Email: mike@example.com / Password: password123")
        print("\n🌐 API Endpoints:")
        print("   - Swagger UI: http://localhost:8001/docs")
        print("   - Health Check: http://localhost:8001/health")
        print("   - List Tickets: http://localhost:8001/api/tickets")
        print("\n📚 Documentation:")
        print("   - Frontend API Guide: ./FRONTEND_API_GUIDE.md")
        print("   - Quick Reference: ./API_QUICK_REFERENCE.md")
        print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(seed_all())
