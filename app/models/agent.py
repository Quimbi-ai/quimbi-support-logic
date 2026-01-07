"""
Agent Model
Support team members who handle customer tickets.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime
import uuid
import enum


class AgentRole(str, enum.Enum):
    """Agent role levels."""
    AGENT = "agent"  # Regular support agent
    SENIOR_AGENT = "senior_agent"  # Senior agent (can handle VIP, complex cases)
    TEAM_LEAD = "team_lead"  # Team lead (can reassign, view team metrics)
    MANAGER = "manager"  # Manager (full access, can configure SLA, rules)
    ADMIN = "admin"  # System admin (can create agents, manage system)


class AgentStatus(str, enum.Enum):
    """Agent current status."""
    ONLINE = "online"  # Available for new tickets
    BUSY = "busy"  # Online but at capacity
    AWAY = "away"  # Temporarily unavailable
    OFFLINE = "offline"  # Not working


class Agent(Base):
    """Agent model - Support team members."""
    __tablename__ = "agents"

    # Primary Key
    id = Column(String, primary_key=True, default=lambda: f"agent_{uuid.uuid4().hex[:12]}")

    # Authentication
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)

    # Profile
    name = Column(String, nullable=False)
    role = Column(SQLEnum(AgentRole), default=AgentRole.AGENT, nullable=False)
    department = Column(String, nullable=True)  # "Support", "Technical", "Billing", etc.
    avatar_url = Column(String, nullable=True)

    # Status
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.OFFLINE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Can be deactivated without deletion

    # Availability Settings
    max_concurrent_tickets = Column(Integer, default=10, nullable=False)
    accepts_new_tickets = Column(Boolean, default=True, nullable=False)

    # Specializations (skills, languages, expertise areas)
    # Example: ["billing", "technical", "vip", "es", "fr"]
    specializations = Column(JSON, default=list, nullable=False)

    # Performance Tracking (updated by background jobs)
    total_tickets_handled = Column(Integer, default=0, nullable=False)
    total_tickets_resolved = Column(Integer, default=0, nullable=False)
    avg_response_time_seconds = Column(Integer, nullable=True)  # Average first response time
    avg_resolution_time_seconds = Column(Integer, nullable=True)  # Average resolution time
    sla_compliance_rate = Column(Integer, nullable=True)  # Percentage (0-100)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True)  # Last activity (WebSocket heartbeat)

    # Relationships
    # assignments = relationship("TicketAssignment", back_populates="agent")
    # notes_created = relationship("Note", back_populates="agent")

    def __repr__(self):
        return f"<Agent {self.id} ({self.email}) - {self.role.value}>"

    @property
    def is_available(self) -> bool:
        """Check if agent is available for new assignments."""
        return (
            self.is_active
            and self.status == AgentStatus.ONLINE
            and self.accepts_new_tickets
        )

    @property
    def full_name(self) -> str:
        """Get full name for display."""
        return self.name

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "department": self.department,
            "avatar_url": self.avatar_url,
            "status": self.status.value,
            "is_active": self.is_active,
            "is_available": self.is_available,
            "max_concurrent_tickets": self.max_concurrent_tickets,
            "accepts_new_tickets": self.accepts_new_tickets,
            "specializations": self.specializations,
            "performance": {
                "total_tickets_handled": self.total_tickets_handled,
                "total_tickets_resolved": self.total_tickets_resolved,
                "avg_response_time_seconds": self.avg_response_time_seconds,
                "avg_resolution_time_seconds": self.avg_resolution_time_seconds,
                "sla_compliance_rate": self.sla_compliance_rate,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
