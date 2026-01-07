# Customer Support Backend - Complete Architecture Document

**Service Name**: Quimbi Support Backend (Operations Layer)
**Version**: 1.0
**Date**: December 1, 2025
**Status**: In Production (Local Development)
**Repository**: q.ai-customer-support

---

## Executive Summary

The **Customer Support Backend** is the operational backbone of the Quimbi customer support platform. It manages all support-specific business logic, ticketing workflows, agent management, and serves as the integration layer between the frontend and the Quimbi Intelligence Backend (AI/ML).

**Key Responsibilities:**
- Ticket lifecycle management (CRUD, status, routing)
- Message and conversation threading
- Agent authentication, authorization, and workflow management
- SLA tracking and assignment logic
- Smart inbox ordering with topic alerts
- Proxy layer for AI-powered features (calls Quimbi Intelligence)

**What It Is NOT:**
- ❌ Customer intelligence engine (that's Quimbi Intelligence Backend)
- ❌ ML/AI service (calls Quimbi for predictions/recommendations)
- ❌ E-commerce transactional system (integrates with external platforms)

---

## System Context

### Architecture Position

```
┌─────────────────────────────────────────────────────────────┐
│                  Frontend (React SPA)                        │
│                                                              │
│  - Ticket list and detail views                             │
│  - Customer profile display                                 │
│  - AI recommendations UI                                    │
│                                                              │
│  Auth: JWT Bearer Token                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP/REST
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│           SUPPORT BACKEND (THIS SERVICE)                     │
│                                                              │
│  Responsibilities:                                           │
│  ✅ Tickets CRUD & lifecycle management                     │
│  ✅ Messages & conversation threading                       │
│  ✅ Agent authentication & authorization (JWT)              │
│  ✅ Agent workflow (assignments, status, performance)       │
│  ✅ SLA tracking & alerts                                   │
│  ✅ Smart inbox ordering with topic alerts                  │
│  ✅ Proxy to Quimbi Intelligence for AI features            │
│                                                              │
│  Tech Stack:                                                │
│  - Python 3.11 + FastAPI                                    │
│  - PostgreSQL (async with SQLAlchemy)                       │
│  - Redis (caching Quimbi responses)                         │
│  - JWT auth (bcrypt password hashing)                       │
│                                                              │
│  Deployment: Railway (production), localhost:8001 (dev)     │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ Calls for enrichment
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│        Quimbi Intelligence Backend (AI/ML/Brains)           │
│                                                              │
│  Provides:                                                  │
│  - Customer segmentation & archetype classification         │
│  - Churn prediction & LTV forecasting                       │
│  - AI draft response generation                             │
│  - Next best action recommendations                         │
│  - Behavioral analytics & insights                          │
│                                                              │
│  Endpoints Used:                                            │
│  - POST /api/intelligence/analyze                           │
│  - POST /api/generation/message                             │
│  - POST /api/generation/actions                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Responsibilities

### 1. Ticket Lifecycle Management

**What It Does:**
- Create, read, update, delete tickets
- Track ticket status (open, pending, resolved, closed)
- Assign priority levels (low, medium, high, urgent)
- Route tickets across channels (email, chat, phone, SMS, form)
- Calculate and maintain smart urgency scores
- Support bulk operations and filtering

**Database Entities:**
```python
class Ticket(Base):
    id: str (UUID primary key)
    customer_id: str (references external customer)
    subject: str
    status: str (open, in_progress, pending, resolved, closed)
    priority: str (low, normal, high, urgent)
    channel: str (email, chat, phone, sms, form)
    created_at: datetime
    updated_at: datetime

    # AI-derived fields (calculated by Support Backend)
    customer_sentiment: float (0-1, derived from messages)
    smart_score: float (urgency score for inbox ordering)
    estimated_difficulty: float (0-1, complexity estimate)
```

**API Endpoints:**
```
GET    /api/tickets                    # List tickets with filters
GET    /api/tickets/{id}               # Get ticket details
POST   /api/tickets                    # Create new ticket
PATCH  /api/tickets/{id}               # Update ticket metadata
DELETE /api/tickets/{id}               # Delete ticket (admin only)
GET    /api/tickets/{id}/score-breakdown  # Explain urgency score
```

**Smart Inbox Ordering:**
The Support Backend calculates a `smart_score` for each ticket based on:
- **Priority level** (+0-4 points based on low/normal/high/urgent)
- **Wait time** (+0-3 points, logarithmic scale)
- **Customer sentiment** (+0-2 points if negative sentiment detected)
- **Customer value** (+0-2 points for high LTV customers)
- **Churn risk** (+0-3 points for at-risk customers)
- **Topic alerts** (+5 points if matches agent-specified keywords)

### 2. Message & Conversation Management

**What It Does:**
- Store customer messages and agent replies
- Maintain conversation threading
- Track message timestamps and authors
- Support rich content (text, attachments)
- Preserve message history for context

**Database Entities:**
```python
class Message(Base):
    id: str (UUID primary key)
    ticket_id: str (foreign key to tickets)
    from_agent: bool (true if agent sent, false if customer)
    content: str (message text)
    from_name: str (author name)
    from_email: str (author email)
    created_at: datetime

    # AI-derived metadata
    sentiment_score: float (0-1, message-level sentiment)
    detected_intent: str (e.g., "complaint", "question", "feedback")
```

**API Endpoints:**
```
GET    /api/tickets/{id}/messages      # Get all messages for ticket
POST   /api/tickets/{id}/messages      # Send message (customer or agent)
PATCH  /api/tickets/{id}/messages/{msg_id}  # Edit message
DELETE /api/tickets/{id}/messages/{msg_id}  # Delete message
```

**Conversation Threading:**
Messages are ordered chronologically and displayed as a chat thread in the frontend. The Support Backend maintains the complete message history but does NOT generate AI responses—it proxies generation requests to Quimbi Intelligence.

### 3. Agent Authentication & Authorization

**What It Does:**
- JWT-based authentication for agents
- Role-based access control (RBAC)
- Agent profile management
- Session management and token lifecycle
- Password hashing with bcrypt

**Database Entities:**
```python
class Agent(Base):
    id: str (UUID primary key)
    email: str (unique, login identifier)
    hashed_password: str (bcrypt hashed)
    name: str
    role: AgentRole (agent, senior_agent, team_lead, manager, admin)
    status: AgentStatus (online, away, busy, offline)
    department: str
    specializations: list[str] (e.g., ["billing", "technical"])
    max_concurrent_tickets: int (workload capacity)

    # Performance tracking
    tickets_resolved_today: int
    avg_response_time_seconds: int
    customer_satisfaction_score: float (0-5)
    last_login_at: datetime
```

**Agent Roles:**
- **agent**: Basic access, can view/respond to assigned tickets
- **senior_agent**: Can view all tickets, assign to others
- **team_lead**: Can manage team members, view team metrics
- **manager**: Can access reports, modify SLA policies
- **admin**: Full system access, user management

**API Endpoints:**
```
POST   /api/agents/login               # Login → JWT token
POST   /api/agents/logout              # Logout (invalidate token)
GET    /api/agents/me                  # Get current agent profile
PATCH  /api/agents/me/status           # Update agent status
GET    /api/agents                     # List agents (admin/manager)
POST   /api/agents                     # Create agent (admin/manager)
PATCH  /api/agents/{id}                # Update agent (admin/manager)
DELETE /api/agents/{id}                # Delete agent (admin only)
```

**JWT Token Format:**
```json
{
  "sub": "agent_xyz123",
  "email": "agent@example.com",
  "role": "agent",
  "exp": 1733039247  // 24-hour expiry
}
```

### 4. Agent Workflow & Assignment

**What It Does:**
- Track ticket assignments to agents
- Manage assignment history and transfers
- Monitor agent workload and capacity
- Track assignment metrics (time to accept, resolution time)
- Support manual and automatic assignment

**Database Entities:**
```python
class TicketAssignment(Base):
    id: str (UUID primary key)
    ticket_id: str (foreign key)
    agent_id: str (foreign key)
    status: AssignmentStatus (pending, accepted, in_progress, completed)
    reason: AssignmentReason (manual, auto_route, escalation, transfer)
    assigned_at: datetime
    accepted_at: datetime (nullable)
    completed_at: datetime (nullable)

    # Transfer tracking
    previous_agent_id: str (nullable, if transferred)
    transfer_reason: str (nullable)

    # Performance metrics
    time_to_accept_seconds: int
    time_to_complete_seconds: int
    is_active: bool (only one active assignment per ticket)
```

**Assignment Logic:**
Currently manual assignment by agents/managers. Future: auto-routing based on:
- Agent specializations matching ticket category
- Agent current workload vs. max_concurrent_tickets
- Agent performance metrics (response time, satisfaction)
- Ticket priority and complexity

### 5. SLA (Service Level Agreement) Tracking

**What It Does:**
- Define SLA policies per priority level
- Track first response time and resolution time
- Calculate SLA breach risk and time remaining
- Generate alerts when SLA at risk
- Support SLA pausing (e.g., awaiting customer response)

**Database Entities:**
```python
class SLAPolicy(Base):
    id: str (UUID primary key)
    priority: SLAPriority (low, normal, high, urgent)
    first_response_target_seconds: int
    resolution_target_seconds: int
    warning_threshold_percent: int (default 80%, alert at 80% of time)
    business_hours_only: bool

class SLATracking(Base):
    id: str (UUID primary key)
    ticket_id: str (foreign key, unique per ticket)
    first_response_status: SLAStatus (met, at_risk, breached)
    first_response_deadline: datetime
    first_response_at: datetime (nullable)

    resolution_status: SLAStatus (met, at_risk, breached)
    resolution_deadline: datetime
    resolved_at: datetime (nullable)

    # Pausing SLA clock
    is_paused: bool (e.g., awaiting customer response)
    paused_at: datetime (nullable)
    total_paused_seconds: int (accumulated pause time)
```

**SLA Policies (Default):**
| Priority | First Response | Resolution |
|----------|----------------|------------|
| Low | 24 hours | 7 days |
| Normal | 8 hours | 48 hours |
| High | 2 hours | 24 hours |
| Urgent | 30 minutes | 8 hours |

**API Endpoints:**
```
GET    /api/sla/policies               # Get SLA policies
PATCH  /api/sla/policies/{priority}    # Update policy (admin/manager)
GET    /api/tickets/{id}/sla           # Get SLA status for ticket
POST   /api/tickets/{id}/sla/pause     # Pause SLA clock
POST   /api/tickets/{id}/sla/resume    # Resume SLA clock
```

### 6. AI Features (Proxy Layer)

**What It Does:**
The Support Backend does NOT perform AI/ML operations itself. Instead, it acts as a **proxy and enrichment layer** that:
1. Gathers context from local database (ticket, messages, customer)
2. Calls Quimbi Intelligence Backend with enriched context
3. Caches Quimbi responses in Redis for performance
4. Returns enriched results to frontend

**AI Endpoints (Proxy to Quimbi):**
```
GET    /api/ai/tickets/{id}/draft-response       # Generate AI draft
POST   /api/ai/tickets/{id}/regenerate-draft     # Regenerate with options
GET    /api/ai/tickets/{id}/recommendation       # Get next best actions
GET    /api/ai/customers/{id}/intelligence       # Get customer insights
```

**Flow Example: AI Draft Generation**
```
Frontend requests draft
    ↓
Support Backend:
  1. Loads ticket + messages from local DB
  2. Loads customer basic info from local DB
  3. Calls Quimbi: POST /api/intelligence/analyze
     → Returns customer archetype, segments, churn risk
  4. Calls Quimbi: POST /api/generation/message
     → Returns AI-generated draft with personalization
  5. Caches response in Redis (1 hour TTL)
  6. Returns enriched draft to frontend
    ↓
Frontend displays draft in editor
```

**Caching Strategy:**
- **Customer intelligence** (archetype, segments): 15 minutes TTL
- **Churn predictions**: 1 hour TTL
- **LTV forecasts**: 1 hour TTL
- **AI drafts**: 1 hour TTL (per ticket + tone + length combo)

**Quimbi Client Implementation:**
```python
class QuimbiClient:
    """Client for Quimbi Intelligence Backend."""

    async def analyze_customer(self, customer_id: str) -> dict:
        """Get customer intelligence (archetype, segments, predictions)."""
        cache_key = f"quimbi:intel:{customer_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        response = await http_client.post(
            f"{quimbi_base_url}/api/intelligence/analyze",
            json={"customer_id": customer_id},
            headers={"X-API-Key": quimbi_api_key}
        )

        await redis.setex(cache_key, 900, response.text)  # 15 min
        return response.json()

    async def generate_message(
        self,
        customer_profile: dict,
        goal: str,
        conversation: list,
        channel: str,
        tone: str,
        length: str
    ) -> dict:
        """Generate AI draft message."""
        response = await http_client.post(
            f"{quimbi_base_url}/api/generation/message",
            json={
                "customer_profile": customer_profile,
                "goal": goal,
                "conversation": conversation,
                "channel": channel,
                "tone": tone,
                "length": length
            },
            headers={"X-API-Key": quimbi_api_key}
        )
        return response.json()
```

---

## Data Architecture

### Database Schema

```sql
-- Customers (basic info, not full CRM)
CREATE TABLE customers (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),

    -- Business metrics (cached from e-commerce platform)
    lifetime_value DECIMAL(10,2) DEFAULT 0.0,
    total_orders INT DEFAULT 0,

    -- Churn risk (cached from Quimbi Intelligence)
    churn_risk_score DECIMAL(3,2) DEFAULT 0.0
);

-- Tickets
CREATE TABLE tickets (
    id VARCHAR(255) PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL REFERENCES customers(id),
    subject VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',  -- open, in_progress, pending, resolved, closed
    priority VARCHAR(50) DEFAULT 'normal',  -- low, normal, high, urgent
    channel VARCHAR(50) NOT NULL,  -- email, chat, phone, sms, form
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- AI-derived fields (calculated locally)
    customer_sentiment DECIMAL(3,2) DEFAULT 0.5,  -- 0-1 scale
    smart_score DECIMAL(5,2) DEFAULT 0.0,  -- Urgency score for inbox
    estimated_difficulty DECIMAL(3,2) DEFAULT 0.5,  -- 0-1 complexity

    INDEX idx_status (status),
    INDEX idx_channel (channel),
    INDEX idx_smart_score (smart_score DESC),
    INDEX idx_created_at (created_at DESC)
);

-- Messages
CREATE TABLE messages (
    id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    from_agent BOOLEAN DEFAULT FALSE,
    content TEXT NOT NULL,
    from_name VARCHAR(255),
    from_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),

    -- AI-derived metadata
    sentiment_score DECIMAL(3,2),
    detected_intent VARCHAR(100),

    INDEX idx_ticket_id (ticket_id),
    INDEX idx_created_at (created_at)
);

-- Agents
CREATE TABLE agents (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'agent',  -- agent, senior_agent, team_lead, manager, admin
    status VARCHAR(50) DEFAULT 'offline',  -- online, away, busy, offline
    department VARCHAR(100),
    specializations JSON,  -- ["billing", "technical", "returns"]
    max_concurrent_tickets INT DEFAULT 10,

    -- Performance metrics
    tickets_resolved_today INT DEFAULT 0,
    avg_response_time_seconds INT DEFAULT 0,
    customer_satisfaction_score DECIMAL(2,1) DEFAULT 0.0,  -- 0-5 scale

    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,

    INDEX idx_email (email),
    INDEX idx_status (status)
);

-- Ticket Assignments
CREATE TABLE ticket_assignments (
    id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(id),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, accepted, in_progress, completed
    reason VARCHAR(50),  -- manual, auto_route, escalation, transfer
    assigned_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Transfer tracking
    previous_agent_id VARCHAR(255) REFERENCES agents(id),
    transfer_reason TEXT,

    -- Performance metrics
    time_to_accept_seconds INT,
    time_to_complete_seconds INT,
    is_active BOOLEAN DEFAULT TRUE,

    INDEX idx_ticket_id (ticket_id),
    INDEX idx_agent_id (agent_id),
    INDEX idx_status (status)
);

-- SLA Policies
CREATE TABLE sla_policies (
    id VARCHAR(255) PRIMARY KEY,
    priority VARCHAR(50) UNIQUE NOT NULL,  -- low, normal, high, urgent
    first_response_target_seconds INT NOT NULL,
    resolution_target_seconds INT NOT NULL,
    warning_threshold_percent INT DEFAULT 80,
    business_hours_only BOOLEAN DEFAULT FALSE
);

-- SLA Tracking (per ticket)
CREATE TABLE sla_tracking (
    id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) UNIQUE NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,

    -- First response SLA
    first_response_status VARCHAR(50) DEFAULT 'pending',  -- pending, met, at_risk, breached
    first_response_deadline TIMESTAMP NOT NULL,
    first_response_at TIMESTAMP,

    -- Resolution SLA
    resolution_status VARCHAR(50) DEFAULT 'pending',  -- pending, met, at_risk, breached
    resolution_deadline TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,

    -- SLA pausing
    is_paused BOOLEAN DEFAULT FALSE,
    paused_at TIMESTAMP,
    total_paused_seconds INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_ticket_id (ticket_id),
    INDEX idx_first_response_deadline (first_response_deadline),
    INDEX idx_resolution_deadline (resolution_deadline)
);
```

### What This Backend Does NOT Store

❌ **Customer Intelligence Data** (stored in Quimbi Intelligence):
- Archetype definitions and classifications
- Segment memberships and scores
- Behavioral patterns and traits
- ML model outputs

❌ **E-commerce Transactional Data** (stays in Shopify/BigCommerce):
- Orders, payments, shipments
- Product catalog and inventory
- Pricing and promotions

❌ **Marketing/Sales Data** (separate CRM if needed):
- Lead tracking, opportunity management
- Sales pipeline data
- Marketing campaign data

---

## API Architecture

### API Endpoint Organization

```
/health                             # Health check
/api/tickets/*                      # Ticket operations
/api/agents/*                       # Agent management
/api/ai/*                           # AI features (proxy to Quimbi)
/api/sla/*                          # SLA policies and tracking
/docs                               # Swagger UI (OpenAPI)
/openapi.json                       # OpenAPI specification
```

### Complete API Reference

#### Health & Status
```
GET    /health                      # System health check
```

#### Tickets
```
GET    /api/tickets                 # List tickets (smart ordered)
  Query params:
    - status: str (open, in_progress, pending, resolved, closed)
    - channel: str (email, chat, phone, sms, form)
    - limit: int (1-100, default 50)
    - page: int (default 1)
    - topic_alerts: str (comma-separated keywords)

GET    /api/tickets/{id}            # Get ticket details with messages
POST   /api/tickets                 # Create new ticket
PATCH  /api/tickets/{id}            # Update ticket (status, priority, etc.)
DELETE /api/tickets/{id}            # Delete ticket (admin only)
GET    /api/tickets/{id}/score-breakdown  # Explain urgency score calculation
```

#### Messages
```
GET    /api/tickets/{id}/messages   # Get all messages for ticket
POST   /api/tickets/{id}/messages   # Send message
  Body: {
    "content": str,
    "from_agent": bool,
    "from_name": str (optional),
    "from_email": str (optional)
  }
```

#### AI Features (Proxy to Quimbi)
```
GET    /api/ai/tickets/{id}/draft-response
  Returns: {
    "ticket_id": str,
    "draft_content": str,
    "tone": str,
    "channel": str,
    "personalization_applied": [str],
    "customer_dna": {...},
    "churn_risk": float
  }

POST   /api/ai/tickets/{id}/regenerate-draft
  Body: {
    "tone": str (empathetic, professional, friendly),
    "length": str (short, medium, long),
    "include_details": [str] (optional)
  }

GET    /api/ai/tickets/{id}/recommendation
  Returns: {
    "ticket_id": str,
    "next_best_actions": [{
      "action": str,
      "priority": int,
      "reasoning": str,
      "expected_impact": str
    }],
    "churn_risk": float,
    "customer_value": str
  }

GET    /api/ai/customers/{id}/intelligence
  Returns: {
    "customer_id": str,
    "archetype": {...},
    "segments": {...},
    "predictions": {
      "churn_risk": float,
      "churn_risk_level": str,
      "lifetime_value": float
    },
    "behavioral_metrics": {...}
  }
```

#### Agents
```
POST   /api/agents/login            # Login → JWT token
  Body: {
    "email": str,
    "password": str
  }
  Returns: {
    "access_token": str,
    "agent": {...}
  }

POST   /api/agents/logout           # Logout
GET    /api/agents/me               # Get current agent profile
PATCH  /api/agents/me/status        # Update agent status
  Body: {
    "status": str (online, away, busy, offline)
  }

GET    /api/agents                  # List all agents (admin/manager)
POST   /api/agents                  # Create agent (admin/manager)
PATCH  /api/agents/{id}             # Update agent (admin/manager)
DELETE /api/agents/{id}             # Delete agent (admin only)
```

#### SLA Management
```
GET    /api/sla/policies            # Get SLA policies
PATCH  /api/sla/policies/{priority} # Update policy (admin/manager)
GET    /api/tickets/{id}/sla        # Get SLA status for ticket
POST   /api/tickets/{id}/sla/pause  # Pause SLA clock
POST   /api/tickets/{id}/sla/resume # Resume SLA clock
```

### Authentication & Authorization

**Authentication Method**: JWT Bearer Token

**Login Flow:**
```
1. Frontend: POST /api/agents/login with email/password
2. Backend: Verify credentials (bcrypt.verify)
3. Backend: Generate JWT token (24-hour expiry)
4. Frontend: Store token in localStorage
5. Frontend: Include "Authorization: Bearer {token}" in all requests
```

**Authorization (RBAC):**
```python
# Permission matrix by role
Permissions = {
    "agent": ["view_own_tickets", "respond_to_tickets"],
    "senior_agent": ["view_all_tickets", "assign_tickets"],
    "team_lead": ["manage_team", "view_team_metrics"],
    "manager": ["manage_sla", "view_reports"],
    "admin": ["all_permissions", "manage_agents"]
}
```

**Protected Endpoint Example:**
```python
@router.post("/api/agents")
async def create_agent(
    agent_data: AgentCreate,
    current_agent: Agent = Depends(require_role(AgentRole.ADMIN, AgentRole.MANAGER))
):
    # Only admins and managers can create agents
    ...
```

---

## Technology Stack

### Backend Framework
- **Python 3.11** - Modern Python with type hints
- **FastAPI** - Async, high-performance REST API framework
- **Uvicorn** - ASGI server for production
- **Pydantic** - Request/response validation and settings

### Database & Caching
- **PostgreSQL** - Primary database (supports JSONB for flexible schemas)
- **SQLAlchemy (async)** - ORM with async support via `asyncpg`
- **Alembic** - Database migrations
- **Redis** - Caching Quimbi responses, session management

### Authentication & Security
- **JWT (JSON Web Tokens)** - Stateless authentication
- **bcrypt** - Password hashing (via `passlib`)
- **python-jose** - JWT encoding/decoding
- **CORS middleware** - Cross-origin request handling

### HTTP & Integration
- **httpx** - Async HTTP client for calling Quimbi API
- **tenacity** - Retry logic with exponential backoff

### Development & Testing
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Code coverage
- **black** - Code formatting
- **mypy** - Static type checking

### Deployment
- **Railway** - Production hosting (https://ecommerce-backend-staging-a14c.up.railway.app)
- **Docker** - Containerization (optional)
- **GitHub Actions** - CI/CD pipeline

---

## Configuration & Environment

### Environment Variables

```bash
# Environment
ENVIRONMENT=development  # development, staging, production

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/support_db

# Security
SECRET_KEY=<openssl rand -hex 32>  # JWT signing key
ACCESS_TOKEN_EXPIRE_HOURS=24

# API Configuration
API_KEY=<your-api-key>  # For frontend to authenticate
API_BASE_URL=http://localhost:8001  # This backend's URL

# Quimbi Intelligence Backend Integration
QUIMBI_BASE_URL=https://ecommerce-backend-staging-a14c.up.railway.app
QUIMBI_API_KEY=<quimbi-api-key>
QUIMBI_TIMEOUT=30.0
QUIMBI_MAX_RETRIES=3

# Quimbi Caching (Redis TTL in seconds)
QUIMBI_CACHE_INTELLIGENCE_TTL=900  # 15 minutes
QUIMBI_CACHE_CHURN_TTL=3600  # 1 hour
QUIMBI_CACHE_LTV_TTL=3600  # 1 hour

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:5173,https://frontend.quimbi.com

# Scoring Service
SCORING_RECALCULATION_INTERVAL=300  # 5 minutes
SCORING_CHURN_WEIGHT=3.0
SCORING_VALUE_WEIGHT=2.0
SCORING_URGENCY_WEIGHT=1.5
TOPIC_ALERT_BOOST=5.0

# AI Features
DRAFT_CACHE_TTL=3600  # 1 hour
DRAFT_LLM_PROVIDER=anthropic  # openai or anthropic (via Quimbi)
DRAFT_MODEL=claude-3-5-sonnet-20241022

# Context Gathering
CONTEXT_MAX_PAST_TICKETS=5
CONTEXT_MAX_RECENT_ORDERS=3
```

### Configuration Management

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with type validation."""

    environment: str = "development"
    database_url: str
    secret_key: str
    access_token_expire_hours: int = 24

    quimbi_base_url: str
    quimbi_api_key: str
    quimbi_timeout: float = 30.0

    redis_url: str = "redis://localhost:6379/0"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## Service Boundaries

### What This Backend OWNS

✅ **Ticket Data**
- Ticket lifecycle (status, priority, assignments)
- Messages and conversation history
- Ticket metadata (channel, subject, timestamps)

✅ **Agent Data**
- Agent profiles and authentication
- Agent roles and permissions
- Agent performance metrics
- Agent status and availability

✅ **Operational Data**
- SLA policies and tracking
- Assignment history
- Workflow state

✅ **Smart Inbox Logic**
- Urgency score calculation
- Topic alert matching
- Ticket ordering and filtering

### What This Backend DOES NOT OWN

❌ **Customer Intelligence** (Quimbi Intelligence owns this)
- Archetype classification
- Segment memberships
- Behavioral patterns
- Churn predictions
- LTV forecasts

❌ **AI/ML Operations** (Quimbi Intelligence owns this)
- Draft response generation
- Recommendation engine
- Sentiment analysis models
- ML model training and deployment

❌ **E-commerce Data** (External platforms own this)
- Orders, payments, shipments
- Product catalog
- Pricing and promotions
- Inventory

### Integration Pattern

```
Support Backend Role: Orchestrator & Enrichment Layer

1. Frontend requests ticket with AI draft
    ↓
2. Support Backend:
   a. Loads ticket + messages from local DB
   b. Loads customer basic info from local DB
   c. Calls Quimbi: "analyze this customer"
   d. Calls Quimbi: "generate draft given this context"
   e. Caches Quimbi responses in Redis
   f. Returns merged result to frontend
    ↓
3. Frontend displays ticket + customer profile + AI draft

Support Backend NEVER:
- Runs ML models itself
- Generates AI content directly
- Stores customer intelligence permanently
- Makes business intelligence decisions
```

---

## Performance & Scalability

### Current Performance

**Local Development (localhost:8001):**
- Health check: < 10ms
- Ticket list (50 tickets): < 100ms
- Ticket detail with messages: < 150ms
- AI draft generation: 1-3 seconds (Quimbi latency)

**Production (Railway):**
- Health check: < 50ms
- Ticket list: < 200ms
- Ticket detail: < 300ms
- AI draft generation: 2-5 seconds

### Caching Strategy

**Redis Caching Layers:**
1. **Quimbi Intelligence Responses** (15 min - 1 hour TTL)
   - Customer archetype/segments: 15 minutes
   - Churn predictions: 1 hour
   - LTV forecasts: 1 hour
   - AI drafts: 1 hour (per ticket + parameters)

2. **Smart Score Calculations** (5 min TTL)
   - Urgency scores recalculated every 5 minutes
   - Topic alert matches cached

3. **Agent Session Data** (24 hour TTL)
   - JWT tokens valid for 24 hours
   - Agent status cached

**Cache Invalidation:**
- Ticket updated → invalidate smart score cache
- Message added → invalidate ticket cache
- Customer data synced → invalidate Quimbi cache for that customer

### Scalability Considerations

**Horizontal Scaling:**
- Stateless backend (all state in PostgreSQL/Redis)
- Can run multiple instances behind load balancer
- JWT authentication allows any instance to verify tokens

**Database Optimization:**
- Indexes on frequently queried fields (status, smart_score, created_at)
- Connection pooling with SQLAlchemy AsyncEngine
- Read replicas for analytics queries (future)

**Rate Limiting:**
- Per-agent rate limits (1000 requests/minute)
- Per-IP rate limits (100 requests/minute for unauthenticated)
- Quimbi API rate limits respected (exponential backoff)

**Monitoring:**
- FastAPI middleware logs all requests
- Prometheus metrics exported (future)
- Sentry error tracking (future)

---

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Git

### Local Setup

```bash
# Clone repository
git clone <repo-url>
cd q.ai-customer-support

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Generate SECRET_KEY
openssl rand -hex 32

# Run database migrations
alembic upgrade head

# Seed test data
python3 seed_test_data.py

# Start server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Server running at: http://localhost:8001
# Swagger UI: http://localhost:8001/docs
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_tickets.py

# Run with output
pytest -v -s
```

---

## Deployment

### Railway Deployment

**Current Production URL:**
```
https://ecommerce-backend-staging-a14c.up.railway.app
```

**Deployment Process:**
1. Push to `main` branch
2. Railway automatically detects changes
3. Builds Docker image
4. Deploys to production
5. Runs database migrations
6. Health check before routing traffic

**Environment Variables (Railway):**
Set in Railway dashboard under "Variables" tab.

### Docker Deployment (Alternative)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t support-backend .
docker run -p 8001:8000 --env-file .env support-backend
```

---

## API Integration Examples

### Frontend Integration (TypeScript)

```typescript
// src/lib/support-api-client.ts
const API_BASE = 'http://localhost:8001';

export interface LoginCredentials {
  email: string;
  password: string;
}

export async function login(credentials: LoginCredentials) {
  const response = await fetch(`${API_BASE}/api/agents/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials)
  });

  if (!response.ok) throw new Error('Login failed');

  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data;
}

export async function getTickets(params?: {
  status?: string;
  topicAlerts?: string[];
}) {
  const token = localStorage.getItem('token');
  const queryParams = new URLSearchParams();

  if (params?.status) queryParams.set('status', params.status);
  if (params?.topicAlerts?.length) {
    queryParams.set('topic_alerts', params.topicAlerts.join(','));
  }

  const response = await fetch(
    `${API_BASE}/api/tickets?${queryParams}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Failed to fetch tickets');
  return response.json();
}

export async function getAIDraft(ticketId: string) {
  const token = localStorage.getItem('token');

  const response = await fetch(
    `${API_BASE}/api/ai/tickets/${ticketId}/draft-response`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Failed to get AI draft');
  return response.json();
}
```

---

## Future Enhancements

### Phase 1: Current State ✅
- ✅ Ticket CRUD operations
- ✅ Message management
- ✅ Agent authentication (JWT)
- ✅ Smart inbox ordering
- ✅ Topic alerts
- ✅ AI features (proxy to Quimbi)
- ✅ SLA tracking models

### Phase 2: Enhanced Workflow (Next 3 Months)
- [ ] Auto-assignment based on agent skills and workload
- [ ] Real-time SLA breach alerts
- [ ] Agent performance dashboard
- [ ] Bulk ticket operations
- [ ] Advanced filtering and search
- [ ] Ticket templates and canned responses

### Phase 3: Advanced Features (6-12 Months)
- [ ] WebSocket support for real-time updates
- [ ] Multi-channel support (SMS, WhatsApp, social media)
- [ ] Knowledge base integration
- [ ] Customer self-service portal
- [ ] Advanced analytics and reporting
- [ ] Workflow automation (triggers, actions)

### Phase 4: Enterprise Features (12+ Months)
- [ ] Multi-tenant support (multiple businesses)
- [ ] Custom fields and ticket types
- [ ] Integration marketplace (Salesforce, Zendesk, etc.)
- [ ] Advanced RBAC with custom roles
- [ ] API webhooks for external integrations
- [ ] White-label customization

---

## Appendix A: Glossary

**Agent**: Support team member who responds to tickets

**Assignment**: The act of assigning a ticket to a specific agent

**Churn Risk**: Probability (0-1) that a customer will stop purchasing (from Quimbi)

**Draft Response**: AI-generated template message (from Quimbi)

**LTV (Lifetime Value)**: Predicted total revenue from a customer (from Quimbi)

**Quimbi Intelligence**: The AI/ML backend that provides customer insights

**SLA (Service Level Agreement)**: Target response and resolution times

**Smart Score**: Calculated urgency score for inbox ordering

**Topic Alert**: Keyword-based filter to surface urgent tickets

**Ticket**: A customer support request or inquiry

---

## Appendix B: API Response Examples

### GET /api/tickets
```json
{
  "tickets": [
    {
      "id": "ticket_abc123",
      "customer_id": "cust_xyz",
      "subject": "Payment not processing",
      "status": "open",
      "priority": "high",
      "channel": "email",
      "created_at": "2025-12-01T01:46:45.064388Z",
      "updated_at": "2025-12-01T01:46:45.064394Z",
      "customer_sentiment": 0.2,
      "smart_score": 9.95,
      "estimated_difficulty": 0.6,
      "matches_topic_alert": false
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 6,
    "has_next": false,
    "has_prev": false
  },
  "topic_alerts_active": [],
  "matches": 0
}
```

### GET /api/ai/tickets/{id}/draft-response
```json
{
  "ticket_id": "ticket_abc123",
  "draft_content": "Hi John,\n\nI'm sorry to hear you're experiencing issues with payment processing...",
  "tone": "empathetic",
  "channel": "email",
  "personalization_applied": [
    "Used customer's first name",
    "Referenced previous positive interaction",
    "Acknowledged frustration"
  ],
  "customer_dna": {
    "dominant_segments": ["whale", "quality_seeker"],
    "archetype_level": "strength"
  },
  "churn_risk": 0.18,
  "churn_risk_level": "low",
  "lifetime_value": 1250.00
}
```

---

**Document Owner**: Quimbi Engineering Team
**Last Updated**: December 1, 2025
**Next Review**: Quarterly
**Version**: 1.0
