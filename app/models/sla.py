"""
SLA Tracking Models
Service Level Agreement policies and tracking.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.database import Base
from datetime import datetime, timedelta
import uuid
import enum


class SLAPriority(str, enum.Enum):
    """SLA priority levels."""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class SLAStatus(str, enum.Enum):
    """SLA compliance status."""
    WITHIN_SLA = "within_sla"  # Still within target
    AT_RISK = "at_risk"  # Approaching breach (e.g., 80% of time elapsed)
    BREACHED = "breached"  # SLA target exceeded


class SLAPolicy(Base):
    """SLA Policy - Defines target response and resolution times."""
    __tablename__ = "sla_policies"

    # Primary Key
    id = Column(String, primary_key=True, default=lambda: f"sla_policy_{uuid.uuid4().hex[:12]}")

    # Policy Name
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Priority Level
    priority = Column(SQLEnum(SLAPriority), nullable=False, unique=True, index=True)

    # Targets (in seconds)
    first_response_target_seconds = Column(Integer, nullable=False)  # Time to first agent reply
    resolution_target_seconds = Column(Integer, nullable=False)  # Time to resolve ticket

    # Business Hours Configuration
    business_hours_only = Column(Boolean, default=False, nullable=False)  # Only count business hours
    business_hours_config = Column(JSON, nullable=True)  # {"start": "09:00", "end": "17:00", "timezone": "UTC"}
    exclude_weekends = Column(Boolean, default=False, nullable=False)

    # Warning Threshold (percentage)
    warning_threshold_percent = Column(Integer, default=80, nullable=False)  # Warn at 80% of target

    # Active Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # sla_tracking = relationship("SLATracking", back_populates="policy")

    def __repr__(self):
        return f"<SLAPolicy {self.id} - {self.priority.value}: {self.first_response_target_seconds}s / {self.resolution_target_seconds}s>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "targets": {
                "first_response_seconds": self.first_response_target_seconds,
                "first_response_hours": round(self.first_response_target_seconds / 3600, 2),
                "resolution_seconds": self.resolution_target_seconds,
                "resolution_hours": round(self.resolution_target_seconds / 3600, 2),
            },
            "business_hours_only": self.business_hours_only,
            "business_hours_config": self.business_hours_config,
            "exclude_weekends": self.exclude_weekends,
            "warning_threshold_percent": self.warning_threshold_percent,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SLATracking(Base):
    """SLA Tracking - Tracks SLA compliance for each ticket."""
    __tablename__ = "sla_tracking"

    # Primary Key
    id = Column(String, primary_key=True, default=lambda: f"sla_{uuid.uuid4().hex[:12]}")

    # Foreign Keys
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, unique=True, index=True)
    policy_id = Column(String, ForeignKey("sla_policies.id"), nullable=False)

    # SLA Status
    first_response_status = Column(SQLEnum(SLAStatus), default=SLAStatus.WITHIN_SLA, nullable=False)
    resolution_status = Column(SQLEnum(SLAStatus), default=SLAStatus.WITHIN_SLA, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When ticket created
    first_response_at = Column(DateTime, nullable=True)  # When first agent message sent
    resolved_at = Column(DateTime, nullable=True)  # When ticket marked resolved
    closed_at = Column(DateTime, nullable=True)  # When ticket marked closed

    # Pause/Resume Tracking (when ticket is "pending customer")
    is_paused = Column(Boolean, default=False, nullable=False)
    paused_at = Column(DateTime, nullable=True)
    total_paused_seconds = Column(Integer, default=0, nullable=False)  # Total time paused

    # Elapsed Time (excluding paused time)
    first_response_elapsed_seconds = Column(Integer, nullable=True)  # Actual time to first response
    resolution_elapsed_seconds = Column(Integer, nullable=True)  # Actual time to resolution

    # Breach Details
    first_response_breached_at = Column(DateTime, nullable=True)
    resolution_breached_at = Column(DateTime, nullable=True)
    breach_reason = Column(String, nullable=True)  # Why it breached (e.g., "High volume", "Agent shortage")

    # Warning Flags
    first_response_warning_sent = Column(Boolean, default=False, nullable=False)
    resolution_warning_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    # ticket = relationship("Ticket", back_populates="sla_tracking")
    # policy = relationship("SLAPolicy", back_populates="sla_tracking")

    def __repr__(self):
        return f"<SLATracking {self.id} - Ticket: {self.ticket_id} - Response: {self.first_response_status.value}, Resolution: {self.resolution_status.value}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "policy_id": self.policy_id,
            "first_response": {
                "status": self.first_response_status.value,
                "elapsed_seconds": self.first_response_elapsed_seconds,
                "breached_at": self.first_response_breached_at.isoformat() if self.first_response_breached_at else None,
                "responded_at": self.first_response_at.isoformat() if self.first_response_at else None,
            },
            "resolution": {
                "status": self.resolution_status.value,
                "elapsed_seconds": self.resolution_elapsed_seconds,
                "breached_at": self.resolution_breached_at.isoformat() if self.resolution_breached_at else None,
                "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            },
            "is_paused": self.is_paused,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "total_paused_seconds": self.total_paused_seconds,
            "breach_reason": self.breach_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def calculate_elapsed_time(self, target_type: str = "first_response") -> int:
        """
        Calculate elapsed time for SLA target (excluding paused time).

        Args:
            target_type: "first_response" or "resolution"

        Returns:
            Elapsed time in seconds
        """
        # Determine end time
        if target_type == "first_response":
            end_time = self.first_response_at or datetime.utcnow()
        else:  # resolution
            end_time = self.resolved_at or datetime.utcnow()

        # Calculate total elapsed
        total_elapsed = (end_time - self.created_at).total_seconds()

        # Subtract paused time
        elapsed = total_elapsed - self.total_paused_seconds

        return int(elapsed)

    def calculate_remaining_time(self, policy: SLAPolicy, target_type: str = "first_response") -> int:
        """
        Calculate remaining time before SLA breach.

        Args:
            policy: SLAPolicy object
            target_type: "first_response" or "resolution"

        Returns:
            Remaining seconds (negative if breached)
        """
        elapsed = self.calculate_elapsed_time(target_type)

        if target_type == "first_response":
            target = policy.first_response_target_seconds
        else:
            target = policy.resolution_target_seconds

        return target - elapsed

    def is_at_risk(self, policy: SLAPolicy, target_type: str = "first_response") -> bool:
        """Check if SLA is at risk (exceeded warning threshold)."""
        elapsed = self.calculate_elapsed_time(target_type)

        if target_type == "first_response":
            target = policy.first_response_target_seconds
        else:
            target = policy.resolution_target_seconds

        threshold = target * (policy.warning_threshold_percent / 100)
        return elapsed >= threshold
