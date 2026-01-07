"""
Database models and connection setup.
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import AsyncGenerator
from app.core.config import settings

Base = declarative_base()


class Customer(Base):
    """Customer model."""
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Business metrics
    lifetime_value = Column(Float, default=0.0)
    total_orders = Column(Integer, default=0)

    # Churn risk
    churn_risk_score = Column(Float, default=0.0)

    # Relationships
    tickets = relationship("Ticket", back_populates="customer")


class Ticket(Base):
    """Ticket model."""
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    subject = Column(String)
    status = Column(String, default="open", index=True)  # open, pending, closed
    priority = Column(String, default="normal")  # low, normal, high, urgent
    channel = Column(String, index=True)  # email, chat, phone
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # AI/ML derived fields
    customer_sentiment = Column(Float, default=0.5)  # 0-1 scale
    smart_score = Column(Float, default=0.0, index=True)
    estimated_difficulty = Column(Float, default=0.5)  # 0-1 scale

    # Relationships
    customer = relationship("Customer", back_populates="tickets")
    messages = relationship("Message", back_populates="ticket", order_by="Message.created_at")


class Message(Base):
    """Message model for ticket conversations."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    ticket_id = Column(String, ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    content = Column(Text)
    from_agent = Column(Boolean, default=False)
    from_name = Column(String)
    from_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # AI generated metadata
    sentiment_score = Column(Float)
    detected_intent = Column(String)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")


class WebhookEvent(Base):
    """Track processed webhook events for deduplication."""
    __tablename__ = "webhook_events"

    webhook_id = Column(String, primary_key=True)
    event_type = Column(String, index=True)  # gorgias_ticket, gorgias_message, shopify_order
    ticket_id = Column(String, index=True, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, index=True)
    payload_hash = Column(String, index=True)  # SHA256 hash of payload for extra safety
    status = Column(String, default="processed")  # processed, failed, skipped


# Database connection (lazy initialization)
engine = None
async_session_maker = None


def init_engine():
    """Initialize database engine lazily."""
    global engine, async_session_maker
    if engine is None:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.environment == "development",
            future=True,
            pool_size=20,  # Max persistent connections
            max_overflow=10,  # Additional connections when pool exhausted
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True  # Verify connections before use
        )
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage:
        @router.get("/tickets")
        async def get_tickets(db: AsyncSession = Depends(get_db)):
            ...
    """
    init_engine()  # Ensure engine is initialized
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    init_engine()  # Ensure engine is initialized
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
