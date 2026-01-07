"""
Agent API Endpoints
Manage support team members.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

from app.models.database import get_db
from app.models.agent import Agent, AgentRole, AgentStatus
from app.services.auth import (
    AuthService,
    get_current_agent,
    require_role,
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


# ========== Pydantic Schemas ==========

class AgentCreate(BaseModel):
    """Schema for creating a new agent."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    role: AgentRole = AgentRole.AGENT
    department: Optional[str] = None
    max_concurrent_tickets: int = Field(10, ge=1, le=50)
    specializations: List[str] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    name: Optional[str] = None
    role: Optional[AgentRole] = None
    department: Optional[str] = None
    status: Optional[AgentStatus] = None
    max_concurrent_tickets: Optional[int] = Field(None, ge=1, le=50)
    accepts_new_tickets: Optional[bool] = None
    specializations: Optional[List[str]] = None
    avatar_url: Optional[str] = None


class AgentLogin(BaseModel):
    """Schema for agent login."""
    email: EmailStr
    password: str


class AgentLoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"
    agent: dict


# ========== Endpoints ==========

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_role(AgentRole.ADMIN, AgentRole.MANAGER))
):
    """
    Create a new agent (Admin/Manager only).

    Permissions: Admin, Manager
    """
    # Check if email already exists
    result = await db.execute(select(Agent).where(Agent.email == agent_data.email))
    existing_agent = result.scalar_one_or_none()

    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent with email {agent_data.email} already exists"
        )

    # Hash password
    hashed_password = AuthService.hash_password(agent_data.password)

    # Create agent
    agent = Agent(
        email=agent_data.email,
        hashed_password=hashed_password,
        name=agent_data.name,
        role=agent_data.role,
        department=agent_data.department,
        max_concurrent_tickets=agent_data.max_concurrent_tickets,
        specializations=agent_data.specializations,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    logger.info(f"Agent created: {agent.email} by {current_agent.email}")

    return agent.to_dict()


@router.get("")
async def list_agents(
    status: Optional[AgentStatus] = None,
    role: Optional[AgentRole] = None,
    is_active: Optional[bool] = None,
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    List all agents with optional filters.

    Filters:
    - status: Filter by agent status (online, busy, away, offline)
    - role: Filter by role (agent, senior_agent, team_lead, manager, admin)
    - is_active: Filter by active status
    - available_only: Only show agents available for assignment
    """
    query = select(Agent)

    # Apply filters
    if status:
        query = query.where(Agent.status == status)
    if role:
        query = query.where(Agent.role == role)
    if is_active is not None:
        query = query.where(Agent.is_active == is_active)
    if available_only:
        query = query.where(
            Agent.is_active == True,
            Agent.status == AgentStatus.ONLINE,
            Agent.accepts_new_tickets == True
        )

    # Execute query
    result = await db.execute(query)
    agents = result.scalars().all()

    return {
        "agents": [agent.to_dict() for agent in agents],
        "count": len(agents)
    }


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Get agent details by ID.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    return agent.to_dict()


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    updates: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Update agent details.

    Permissions:
    - Agents can update their own status, accepts_new_tickets
    - Team Leads+ can update any agent
    - Only Admin/Manager can change roles
    """
    # Fetch agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Permission check
    is_self = agent_id == current_agent.id
    can_edit_others = current_agent.role in [AgentRole.TEAM_LEAD, AgentRole.MANAGER, AgentRole.ADMIN]

    if not is_self and not can_edit_others:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    # Role changes require admin/manager
    if updates.role and updates.role != agent.role:
        if current_agent.role not in [AgentRole.ADMIN, AgentRole.MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin/Manager can change agent roles"
            )

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    logger.info(f"Agent updated: {agent.email} by {current_agent.email}")

    return agent.to_dict()


@router.delete("/{agent_id}")
async def deactivate_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_role(AgentRole.ADMIN, AgentRole.MANAGER))
):
    """
    Deactivate an agent (soft delete).

    Permissions: Admin, Manager
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Can't deactivate yourself
    if agent_id == current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    agent.is_active = False
    agent.status = AgentStatus.OFFLINE

    await db.commit()

    logger.info(f"Agent deactivated: {agent.email} by {current_agent.email}")

    return {"message": f"Agent {agent.email} deactivated successfully"}


@router.post("/login")
async def login(
    credentials: AgentLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Agent login endpoint.

    Returns JWT access token.
    """
    # Authenticate agent
    agent = await AuthService.authenticate_agent(credentials.email, credentials.password, db)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = AuthService.create_access_token(
        data={"sub": agent.id, "email": agent.email, "role": agent.role.value}
    )

    # Update last login time
    agent.last_login_at = datetime.utcnow()
    agent.status = AgentStatus.ONLINE
    await db.commit()

    logger.info(f"Agent logged in: {agent.email}")

    return AgentLoginResponse(
        access_token=access_token,
        agent=agent.to_dict()
    )


@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Agent logout endpoint.

    Sets agent status to offline.
    """
    current_agent.status = AgentStatus.OFFLINE
    await db.commit()

    logger.info(f"Agent logged out: {current_agent.email}")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_agent_info(
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Get current authenticated agent's information.
    """
    return current_agent.to_dict()


@router.patch("/me/status")
async def update_my_status(
    status: AgentStatus,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Update your own status (online, busy, away, offline).
    """
    current_agent.status = status
    current_agent.last_active_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Agent status updated: {current_agent.email} → {status.value}")

    return current_agent.to_dict()
