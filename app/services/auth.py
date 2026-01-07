"""
Authentication Service
JWT-based authentication for agents.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.agent import Agent, AgentRole
from app.models.database import get_db
import logging

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token extractor
security = HTTPBearer()


class AuthService:
    """Authentication service for agents."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data (should include "sub" with agent ID)
            expires_delta: Token expiration time (default: 24 hours)

        Returns:
            JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """
        Decode and verify a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None

    @staticmethod
    async def authenticate_agent(email: str, password: str, db: AsyncSession) -> Optional[Agent]:
        """
        Authenticate an agent by email and password.

        Args:
            email: Agent email
            password: Plain text password
            db: Database session

        Returns:
            Agent object if authenticated, None otherwise
        """
        # Find agent by email
        result = await db.execute(select(Agent).where(Agent.email == email))
        agent = result.scalar_one_or_none()

        if not agent:
            logger.warning(f"Authentication failed: Agent not found - {email}")
            return None

        if not agent.is_active:
            logger.warning(f"Authentication failed: Agent inactive - {email}")
            return None

        # Verify password
        if not AuthService.verify_password(password, agent.hashed_password):
            logger.warning(f"Authentication failed: Invalid password - {email}")
            return None

        logger.info(f"Agent authenticated successfully: {email}")
        return agent

    @staticmethod
    async def get_agent_from_token(token: str, db: AsyncSession) -> Optional[Agent]:
        """
        Get agent from JWT token.

        Args:
            token: JWT token string
            db: Database session

        Returns:
            Agent object or None if invalid
        """
        payload = AuthService.decode_access_token(token)
        if not payload:
            return None

        agent_id: str = payload.get("sub")
        if not agent_id:
            return None

        # Fetch agent from database
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent or not agent.is_active:
            return None

        return agent


# Dependency: Get current agent from Authorization header
async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    """
    Dependency to get the current authenticated agent.

    Usage:
        @router.get("/me")
        async def get_me(agent: Agent = Depends(get_current_agent)):
            return agent.to_dict()
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    agent = await AuthService.get_agent_from_token(token, db)
    if agent is None:
        raise credentials_exception

    return agent


# Dependency: Require specific role
def require_role(*allowed_roles: AgentRole):
    """
    Dependency factory to require specific agent roles.

    Usage:
        @router.delete("/agents/{id}")
        async def delete_agent(
            agent: Agent = Depends(require_role(AgentRole.ADMIN, AgentRole.MANAGER))
        ):
            ...
    """
    async def role_checker(agent: Agent = Depends(get_current_agent)) -> Agent:
        if agent.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}"
            )
        return agent

    return role_checker


# Optional: Get current agent (returns None if not authenticated)
async def get_current_agent_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[Agent]:
    """
    Dependency to optionally get the current agent (doesn't raise exception if not authenticated).

    Useful for endpoints that change behavior based on authentication but don't require it.
    """
    if not credentials:
        return None

    token = credentials.credentials
    agent = await AuthService.get_agent_from_token(token, db)
    return agent
