"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageSchema(BaseModel):
    """Message schema."""
    id: str
    ticket_id: str
    content: str
    from_agent: bool
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerSchema(BaseModel):
    """Customer schema."""
    id: str
    email: str
    name: Optional[str] = None
    lifetime_value: float
    total_orders: int
    churn_risk_score: float

    class Config:
        from_attributes = True


class TicketListSchema(BaseModel):
    """Ticket schema for list view."""
    id: str
    customer_id: Optional[str] = None  # Allow None for tickets without customer
    subject: str
    status: str
    priority: str
    channel: str
    created_at: datetime
    updated_at: datetime
    customer_sentiment: float
    smart_score: float
    estimated_difficulty: float
    matches_topic_alert: bool = False

    class Config:
        from_attributes = True


class TicketDetailSchema(BaseModel):
    """Ticket schema for detail view."""
    id: str
    customer_id: Optional[str] = None  # Allow None for tickets without customer
    subject: str
    status: str
    priority: str
    channel: str
    created_at: datetime
    updated_at: datetime
    customer_sentiment: float
    smart_score: float
    estimated_difficulty: float
    messages: List[MessageSchema]
    customer: Optional[CustomerSchema] = None

    class Config:
        from_attributes = True


class TicketCreateSchema(BaseModel):
    """Schema for creating a ticket."""
    customer_id: str
    subject: str
    priority: str = "normal"
    channel: str = "email"
    initial_message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None


class MessageCreateSchema(BaseModel):
    """Schema for creating a message."""
    content: str
    from_agent: bool = True
    from_name: Optional[str] = None
    from_email: Optional[str] = None


class TicketUpdateSchema(BaseModel):
    """Schema for updating a ticket."""
    status: Optional[str] = None
    priority: Optional[str] = None
