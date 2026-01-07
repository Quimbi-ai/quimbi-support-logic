"""
Ticket Assignment Model
Tracks which agent is handling which ticket, with full audit history.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime
import uuid
import enum


class AssignmentStatus(str, enum.Enum):
    """Status of the ticket assignment."""
    ASSIGNED = "assigned"  # Assigned but not yet accepted by agent
    ACCEPTED = "accepted"  # Agent has accepted the ticket
    IN_PROGRESS = "in_progress"  # Agent is actively working on it
    COMPLETED = "completed"  # Ticket resolved by this agent
    TRANSFERRED = "transferred"  # Transferred to another agent
    UNASSIGNED = "unassigned"  # Assignment was removed


class AssignmentReason(str, enum.Enum):
    """How the assignment was made."""
    MANUAL = "manual"  # Manually assigned by manager/team lead
    AUTO_ROUTING = "auto_routing"  # Auto-assigned by routing algorithm
    TRANSFER = "transfer"  # Transferred from another agent
    ESCALATION = "escalation"  # Escalated to this agent
    SELF_CLAIMED = "self_claimed"  # Agent claimed from unassigned queue


class TicketAssignment(Base):
    """Ticket Assignment model - Links tickets to agents with full audit trail."""
    __tablename__ = "ticket_assignments"

    # Primary Key
    id = Column(String, primary_key=True, default=lambda: f"assign_{uuid.uuid4().hex[:12]}")

    # Foreign Keys
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)

    # Assignment Details
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.ASSIGNED, nullable=False)
    reason = Column(SQLEnum(AssignmentReason), nullable=False)

    # Transfer/Escalation Context
    previous_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)  # If transferred
    transfer_reason = Column(Text, nullable=True)  # Why it was transferred
    assigned_by_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)  # Who made the assignment

    # Timestamps
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)  # When agent accepted
    started_at = Column(DateTime, nullable=True)  # When agent started working
    completed_at = Column(DateTime, nullable=True)  # When agent finished
    transferred_at = Column(DateTime, nullable=True)  # When transferred away

    # Performance Tracking
    time_to_accept_seconds = Column(Integer, nullable=True)  # Time from assign to accept
    time_to_first_response_seconds = Column(Integer, nullable=True)  # Time to first message
    time_to_resolution_seconds = Column(Integer, nullable=True)  # Time to complete

    # Active Assignment Flag (only one active assignment per ticket)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    # ticket = relationship("Ticket", back_populates="assignments")
    # agent = relationship("Agent", foreign_keys=[agent_id], back_populates="assignments")
    # previous_agent = relationship("Agent", foreign_keys=[previous_agent_id])
    # assigned_by = relationship("Agent", foreign_keys=[assigned_by_agent_id])

    def __repr__(self):
        return f"<TicketAssignment {self.id} - Ticket: {self.ticket_id} → Agent: {self.agent_id} ({self.status.value})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "reason": self.reason.value,
            "previous_agent_id": self.previous_agent_id,
            "transfer_reason": self.transfer_reason,
            "assigned_by_agent_id": self.assigned_by_agent_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "transferred_at": self.transferred_at.isoformat() if self.transferred_at else None,
            "is_active": self.is_active,
            "performance": {
                "time_to_accept_seconds": self.time_to_accept_seconds,
                "time_to_first_response_seconds": self.time_to_first_response_seconds,
                "time_to_resolution_seconds": self.time_to_resolution_seconds,
            },
        }

    @property
    def duration_seconds(self) -> int:
        """Calculate how long this assignment has been active."""
        if not self.is_active:
            end_time = self.completed_at or self.transferred_at or datetime.utcnow()
        else:
            end_time = datetime.utcnow()

        return int((end_time - self.assigned_at).total_seconds())
