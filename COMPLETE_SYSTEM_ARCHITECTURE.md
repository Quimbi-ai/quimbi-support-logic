# Quimbi Platform - Complete System Architecture

**Date**: December 1, 2025
**Purpose**: Define the complete architecture, boundaries, and responsibilities for the entire Quimbi customer support platform
**Version**: 2.0 (Updated with Support Backend implementation details)

---

## Executive Summary

The Quimbi Platform consists of three distinct, purpose-built components working together to deliver an AI-powered customer support experience:

1. **Quimbi Intelligence Backend (AI/ML/Brains)** - Customer intelligence, predictions, and AI content generation
2. **Support Backend (Operations)** - Ticketing, messages, agent workflows, business logic
3. **Frontend (UI)** - React-based agent interface

This document defines the complete architecture, integration patterns, and service boundaries for the platform.

---

## System Architecture Overview

### Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React SPA)                    │
│                      Port: 5173 (dev)                        │
│                                                              │
│  Components:                                                 │
│  - InboxPage (ticket list with smart ordering)              │
│  - TicketDetailPage (conversation + AI tools)               │
│  - CustomerPage (profile + intelligence)                    │
│  - AnalyticsPage (metrics dashboard)                        │
│                                                              │
│  Tech: React 18, TypeScript, Vite, Tailwind CSS, Axios     │
│  Auth: JWT Bearer Token (from Support Backend)              │
└──────────────┬───────────────────────┬───────────────────────┘
               │                       │
               │ HTTP/REST             │ HTTP/REST (via proxy)
               │                       │
               ▼                       ▼
┌──────────────────────────┐  ┌───────────────────────────────────┐
│   Support Backend        │  │  Quimbi Intelligence Backend      │
│   Port: 8001 (local)     │──┤  (AI/ML/Brains)                   │
│   Railway (prod)         │  │  Railway (prod)                   │
│                          │  │                                    │
│  OWNS:                   │  │  OWNS:                            │
│  ✅ Tickets CRUD         │  │  ✅ Customer segmentation         │
│  ✅ Messages             │  │  ✅ Archetype classification       │
│  ✅ Agent auth (JWT)     │  │  ✅ Churn prediction              │
│  ✅ Agent workflow       │  │  ✅ LTV forecasting               │
│  ✅ SLA tracking         │  │  ✅ AI draft generation           │
│  ✅ Smart inbox ordering │  │  ✅ Recommendation engine         │
│  ✅ Assignment logic     │  │  ✅ Analytics aggregation         │
│                          │  │                                    │
│  PROXIES:                │  │  PROVIDES:                        │
│  🔄 AI features          │  │  - POST /api/intelligence/analyze │
│  🔄 Customer intelligence│  │  - POST /api/generation/message   │
│                          │  │  - POST /api/generation/actions   │
│  Tech:                   │  │                                    │
│  - Python 3.11           │  │  Tech:                            │
│  - FastAPI               │  │  - Python + FastAPI               │
│  - PostgreSQL (async)    │  │  - PostgreSQL                     │
│  - Redis (caching)       │  │  - ML models (scikit-learn)       │
│  - JWT auth (bcrypt)     │  │  - Claude API (Anthropic)         │
└──────────────┬───────────┘  └───────────────────────────────────┘
               │                         │
               │                         │
               ▼                         ▼
┌──────────────────────────┐  ┌───────────────────────────────────┐
│  Support Database        │  │  Intelligence Database            │
│  (PostgreSQL)            │  │  (PostgreSQL)                     │
│                          │  │                                    │
│  Tables:                 │  │  Schema: platform                 │
│  - customers (basic)     │  │  - customer_profiles              │
│  - tickets               │  │  - archetype_definitions          │
│  - messages              │  │  - segment_definitions            │
│  - agents                │  │                                    │
│  - ticket_assignments    │  │  Schema: shared                   │
│  - sla_policies          │  │  - mcp_queries (cache)            │
│  - sla_tracking          │  │  - analytics_cache                │
└──────────────────────────┘  └───────────────────────────────────┘
```

---

# Part 1: Quimbi Intelligence Backend (AI/ML/Brains)

## What This Backend IS

- **Customer Intelligence Engine**: Analyzes customer behavior and provides insights
- **ML/AI Service**: Runs segmentation, churn prediction, LTV forecasting
- **Recommendation Engine**: Suggests actions, content, and strategies
- **Analytics Platform**: Aggregates and analyzes behavioral data

## What This Backend IS NOT

- ❌ CRM System (customer records, contact management)
- ❌ Ticketing System (support tickets, queues, assignments)
- ❌ Customer Support Tool (workflows, SLAs, agent assignments)
- ❌ Transactional Database (orders, payments, shipments)

## Core Responsibilities

### 1. Customer Behavioral Intelligence

**Input Sources:**
- E-commerce platform data (Shopify, BigCommerce)
- Purchase history and transaction data
- Product interaction data
- Customer lifecycle events

**Outputs:**
- Customer segment memberships across 8 behavioral axes
- Archetype classification (strength, tendency, emerging)
- Segment membership scores and confidence levels
- Behavioral pattern recognition

### 2. Predictive Analytics

**ML Models:**
- Churn prediction model (probability of leaving)
- LTV prediction model (expected future value)
- Engagement scoring model
- Repurchase timing model

**Outputs:**
- Churn risk scores (0-1)
- Predicted LTV (dollar amount)
- Risk factors and drivers
- Confidence intervals

### 3. AI Content Generation

**Capabilities:**
- AI-powered draft response generation
- Personalized messaging based on archetype
- Next best action recommendations
- Customer behavior summarization

**Outputs:**
- Draft messages with tone/channel adaptation
- Prioritized action recommendations
- Personalization strategies
- Insight narratives

## Intelligence Backend API (Called by Support Backend)

```
POST /api/intelligence/analyze       # Full customer intelligence profile
POST /api/generation/message         # Generate draft response
POST /api/generation/actions         # Generate recommendations
GET  /api/segments/customer/{id}     # Get customer segments
GET  /api/archetypes/{id}            # Get archetype details
```

---

# Part 2: Support Backend (Operations)

## What This Backend IS

- **Ticketing System**: CRUD operations for support tickets
- **Message Management**: Customer and agent messages
- **Workflow Engine**: Ticket routing, assignments, SLAs
- **Agent Management**: Authentication, authorization, profiles
- **Operational Database**: Stores all support-related data
- **Integration Layer**: Orchestrates calls to Quimbi Intelligence

## What This Backend IS NOT

- ❌ Customer Intelligence (calls Intelligence Backend for that)
- ❌ AI/ML Service (calls Intelligence Backend for recommendations)
- ❌ Analytics Platform (calls Intelligence Backend for insights)

## Core Responsibilities

### 1. Ticket Lifecycle Management

**Operations:**
- Create, read, update, delete tickets
- Track ticket status (open, in_progress, pending, resolved, closed)
- Assign priority levels (low, normal, high, urgent)
- Route tickets across channels (email, chat, phone, SMS, form)
- Calculate smart urgency scores for inbox ordering

**Database Schema:**
```sql
CREATE TABLE tickets (
    id VARCHAR(255) PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(50) DEFAULT 'normal',
    channel VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- AI-derived fields (calculated locally)
    customer_sentiment DECIMAL(3,2) DEFAULT 0.5,
    smart_score DECIMAL(5,2) DEFAULT 0.0,
    estimated_difficulty DECIMAL(3,2) DEFAULT 0.5
);
```

**Smart Score Calculation:**
```python
smart_score = (
    priority_score +        # 0-4 points
    wait_time_score +       # 0-3 points (logarithmic)
    sentiment_score +       # 0-2 points (negative sentiment)
    customer_value_score +  # 0-2 points (high LTV from Quimbi)
    churn_risk_score +      # 0-3 points (at-risk from Quimbi)
    topic_alert_boost       # +5 points if matches keywords
)
```

### 2. Message & Conversation Management

**Operations:**
- Store customer messages and agent replies
- Maintain conversation threading
- Track message timestamps and authors
- Support rich content and attachments

**Database Schema:**
```sql
CREATE TABLE messages (
    id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL REFERENCES tickets(id),
    from_agent BOOLEAN DEFAULT FALSE,
    content TEXT NOT NULL,
    from_name VARCHAR(255),
    from_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),

    -- AI-derived metadata
    sentiment_score DECIMAL(3,2),
    detected_intent VARCHAR(100)
);
```

### 3. Agent Authentication & Authorization

**Features:**
- JWT-based authentication
- Role-based access control (RBAC)
- Agent profile management
- Session management (24-hour token expiry)
- Password hashing with bcrypt

**Agent Roles:**
```python
AgentRole = Enum([
    "agent",          # Basic access
    "senior_agent",   # Can view all tickets, assign
    "team_lead",      # Can manage team members
    "manager",        # Can modify SLA policies, reports
    "admin"           # Full system access
])
```

**Database Schema:**
```sql
CREATE TABLE agents (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'agent',
    status VARCHAR(50) DEFAULT 'offline',
    department VARCHAR(100),
    specializations JSON,
    max_concurrent_tickets INT DEFAULT 10,

    -- Performance metrics
    tickets_resolved_today INT DEFAULT 0,
    avg_response_time_seconds INT DEFAULT 0,
    customer_satisfaction_score DECIMAL(2,1) DEFAULT 0.0,

    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);
```

### 4. SLA Tracking

**Features:**
- Define SLA policies per priority level
- Track first response time and resolution time
- Calculate SLA breach risk and time remaining
- Support SLA pausing (e.g., awaiting customer response)

**SLA Policies (Default):**
| Priority | First Response | Resolution |
|----------|----------------|------------|
| Low | 24 hours | 7 days |
| Normal | 8 hours | 48 hours |
| High | 2 hours | 24 hours |
| Urgent | 30 minutes | 8 hours |

**Database Schema:**
```sql
CREATE TABLE sla_policies (
    id VARCHAR(255) PRIMARY KEY,
    priority VARCHAR(50) UNIQUE NOT NULL,
    first_response_target_seconds INT NOT NULL,
    resolution_target_seconds INT NOT NULL,
    warning_threshold_percent INT DEFAULT 80,
    business_hours_only BOOLEAN DEFAULT FALSE
);

CREATE TABLE sla_tracking (
    id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) UNIQUE NOT NULL REFERENCES tickets(id),

    first_response_status VARCHAR(50) DEFAULT 'pending',
    first_response_deadline TIMESTAMP NOT NULL,
    first_response_at TIMESTAMP,

    resolution_status VARCHAR(50) DEFAULT 'pending',
    resolution_deadline TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,

    is_paused BOOLEAN DEFAULT FALSE,
    paused_at TIMESTAMP,
    total_paused_seconds INT DEFAULT 0
);
```

### 5. AI Features (Proxy Layer)

**Pattern:**
Support Backend acts as an **orchestration layer**:
1. Receives AI feature request from frontend
2. Gathers context from local database (ticket, messages, customer)
3. Calls Quimbi Intelligence with enriched context
4. Caches response in Redis (15 min - 1 hour TTL)
5. Returns enriched result to frontend

**Proxy Endpoints:**
```
GET  /api/ai/tickets/{id}/draft-response       # Generate AI draft
POST /api/ai/tickets/{id}/regenerate-draft     # Regenerate with options
GET  /api/ai/tickets/{id}/recommendation       # Get next best actions
GET  /api/ai/customers/{id}/intelligence       # Get customer insights
```

**Example Flow: AI Draft Generation**
```
Frontend: GET /api/ai/tickets/123/draft-response
    ↓
Support Backend:
  1. SELECT * FROM tickets WHERE id='123'
  2. SELECT * FROM messages WHERE ticket_id='123'
  3. SELECT * FROM customers WHERE id=ticket.customer_id
  4. Cache check: Redis.get("quimbi:intel:customer_xyz")
  5. If miss: POST Quimbi /api/intelligence/analyze
  6. POST Quimbi /api/generation/message with full context
  7. Cache response: Redis.setex("draft:123:empathetic:medium", 3600, response)
  8. Return enriched draft to frontend
    ↓
Frontend: Display draft in editor
```

## Support Backend API

### Complete Endpoint List

```
# Health & Status
GET    /health                               # System health check

# Authentication
POST   /api/agents/login                     # Login → JWT token
POST   /api/agents/logout                    # Logout

# Tickets
GET    /api/tickets                          # List tickets (smart ordered)
  Query: status, channel, limit, page, topic_alerts
GET    /api/tickets/{id}                     # Get ticket details
POST   /api/tickets                          # Create ticket
PATCH  /api/tickets/{id}                     # Update ticket
DELETE /api/tickets/{id}                     # Delete ticket (admin)
GET    /api/tickets/{id}/score-breakdown     # Explain urgency score

# Messages
GET    /api/tickets/{id}/messages            # Get all messages
POST   /api/tickets/{id}/messages            # Send message

# AI Features (Proxy to Quimbi)
GET    /api/ai/tickets/{id}/draft-response
POST   /api/ai/tickets/{id}/regenerate-draft
GET    /api/ai/tickets/{id}/recommendation
GET    /api/ai/customers/{id}/intelligence

# Agents
GET    /api/agents/me                        # Get current agent
PATCH  /api/agents/me/status                 # Update agent status
GET    /api/agents                           # List agents (admin/manager)
POST   /api/agents                           # Create agent (admin/manager)
PATCH  /api/agents/{id}                      # Update agent (admin/manager)
DELETE /api/agents/{id}                      # Delete agent (admin)

# SLA Management
GET    /api/sla/policies                     # Get SLA policies
PATCH  /api/sla/policies/{priority}          # Update policy (admin/manager)
GET    /api/tickets/{id}/sla                 # Get SLA status
POST   /api/tickets/{id}/sla/pause           # Pause SLA clock
POST   /api/tickets/{id}/sla/resume          # Resume SLA clock

# Documentation
GET    /docs                                 # Swagger UI
GET    /openapi.json                         # OpenAPI spec
```

---

# Part 3: Frontend (React SPA)

## What The Frontend IS

- **Customer Support Interface**: Primary UI for support agents
- **Intelligence Dashboard**: Displays customer behavioral insights
- **Ticket Management UI**: View, respond to, and manage support tickets
- **AI Recommendation Display**: Shows AI-generated suggestions and drafts

## Technology Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **State Management**: React Query (TanStack Query)
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Auth**: JWT Bearer Token

## Frontend Pages

1. **InboxPage** - Ticket list with smart ordering and topic alerts
2. **TicketDetailPage** - Full ticket view with customer profile and AI tools
3. **CustomerPage** - Standalone customer profile view
4. **AnalyticsPage** - Dashboard with metrics

## Frontend Data Flow

### Current Flow (Implemented)

```
User opens ticket detail page
    ↓
Frontend makes parallel requests:
  ├─ Support Backend:
  │   GET /api/tickets/{id}             → Returns ticket + messages
  │
  └─ Support Backend (proxy):
      ├─ GET /api/ai/tickets/{id}/draft-response → AI draft
      └─ GET /api/ai/customers/{customer_id}/intelligence → Customer profile
    ↓
Support Backend internally:
  - Calls Quimbi Intelligence for customer data
  - Caches responses in Redis
  - Returns enriched data to frontend
    ↓
Frontend displays merged data
```

### Frontend API Client Example

```typescript
// src/lib/support-api-client.ts
const API_BASE = 'http://localhost:8001';

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/api/agents/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

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
    { headers: { 'Authorization': `Bearer ${token}` } }
  );

  return response.json();
}

export async function getAIDraft(ticketId: string) {
  const token = localStorage.getItem('token');

  const response = await fetch(
    `${API_BASE}/api/ai/tickets/${ticketId}/draft-response`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );

  return response.json();
}
```

---

# Integration Patterns

## Pattern 1: Intelligence Enrichment

```
┌──────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│   Frontend   │────1───→│  Support Backend    │────2───→│  Quimbi Intelligence│
│              │         │                     │         │                     │
│  Loads       │←───6────│  Returns ticket     │←───5────│  Returns profile    │
│  ticket      │         │  + customer profile │         │  + predictions      │
└──────────────┘         └─────────────────────┘         └─────────────────────┘
                                   ↓ 3
                         ┌─────────────────────┐
                         │  Redis Cache        │
                         │  (15 min - 1 hr TTL)│
                         └─────────────────────┘
                                   ↑ 4
```

**Steps:**
1. Frontend requests ticket with customer intelligence
2. Support Backend calls Quimbi Intelligence (if not cached)
3. Check Redis cache for customer profile
4. If cache miss, call Quimbi API
5. Quimbi returns archetype, segments, churn risk, LTV
6. Support Backend merges data and returns to frontend

## Pattern 2: AI Draft Generation

```
Agent opens ticket
    ↓
Frontend: GET /api/ai/tickets/{id}/draft-response
    ↓
Support Backend:
  1. Load ticket + messages from local DB
  2. Load customer basic info from local DB
  3. Check cache: Redis.get("draft:{ticket_id}:{tone}:{length}")
  4. If miss:
     a. Call Quimbi: POST /api/intelligence/analyze
     b. Call Quimbi: POST /api/generation/message
  5. Cache response (1 hour TTL)
  6. Return enriched draft
    ↓
Frontend: Display draft in editor
    ↓
Agent reviews, edits, and sends via Support Backend
```

## Pattern 3: Smart Inbox Ordering

```
Frontend: GET /api/tickets?status=open&topic_alerts=payment,chargeback
    ↓
Support Backend:
  1. Query tickets from local DB (status filter)
  2. For each ticket:
     a. Load customer from local DB
     b. Check cache: Redis.get("quimbi:intel:{customer_id}")
     c. If miss, call Quimbi for churn_risk + LTV
     d. Calculate smart_score:
        - Priority: +0-4 points
        - Wait time: +0-3 points
        - Sentiment: +0-2 points
        - Customer value: +0-2 points (from LTV)
        - Churn risk: +0-3 points (from Quimbi)
        - Topic alert match: +5 points if "payment" in subject
  3. Sort tickets by smart_score DESC
  4. Return paginated result
    ↓
Frontend: Display ordered ticket list
```

## Pattern 4: Authentication Flow

```
User enters email/password
    ↓
Frontend: POST /api/agents/login
    ↓
Support Backend:
  1. Query agents table for email
  2. Verify password: bcrypt.verify(password, hashed_password)
  3. If valid:
     a. Generate JWT token (24-hour expiry)
     b. Update agent status to "online"
     c. Update last_login_at timestamp
  4. Return { access_token, agent }
    ↓
Frontend:
  1. Store token in localStorage
  2. Include in all requests: "Authorization: Bearer {token}"
    ↓
Support Backend middleware:
  1. Extract token from Authorization header
  2. Verify JWT signature with SECRET_KEY
  3. Check expiry (24 hours)
  4. Load agent from database
  5. Attach agent to request context
```

---

# Service Boundaries

## Clear Ownership Matrix

| Capability | Owner | Storage |
|------------|-------|---------|
| **Tickets** | Support Backend | Support DB |
| **Messages** | Support Backend | Support DB |
| **Agents** | Support Backend | Support DB |
| **Assignments** | Support Backend | Support DB |
| **SLA Tracking** | Support Backend | Support DB |
| **Smart Scores** | Support Backend | Calculated + Redis |
| **Customer Intelligence** | Quimbi Intelligence | Intelligence DB + Redis |
| **Archetypes** | Quimbi Intelligence | Intelligence DB |
| **Segments** | Quimbi Intelligence | Intelligence DB |
| **Churn Predictions** | Quimbi Intelligence | Intelligence DB + Redis |
| **LTV Forecasts** | Quimbi Intelligence | Intelligence DB + Redis |
| **AI Draft Generation** | Quimbi Intelligence | Stateless (Claude API) |
| **Recommendations** | Quimbi Intelligence | Stateless (Claude API) |
| **Frontend UI** | Frontend | Browser (React state) |

## Integration Rules

### ✅ Allowed Patterns

1. **Frontend → Support Backend**: All ticket/agent operations
2. **Frontend → Support Backend → Quimbi Intelligence**: AI features (proxied)
3. **Support Backend → Quimbi Intelligence**: Customer enrichment
4. **Support Backend → Redis**: Caching Quimbi responses

### ❌ Forbidden Patterns

1. ~~Frontend → Quimbi Intelligence directly~~ (must go through Support Backend)
2. ~~Support Backend → Customer Intelligence storage~~ (read-only from Quimbi)
3. ~~Quimbi Intelligence → Ticket storage~~ (Support Backend owns tickets)
4. ~~Frontend → Direct database access~~ (always through APIs)

---

# Environment Configuration

## Support Backend Environment

```bash
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/support_db

# Security
SECRET_KEY=<openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_HOURS=24

# Quimbi Intelligence Integration
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

# CORS
CORS_ORIGINS=http://localhost:5173,https://frontend.quimbi.com

# Scoring
TOPIC_ALERT_BOOST=5.0
SCORING_CHURN_WEIGHT=3.0
SCORING_VALUE_WEIGHT=2.0
```

## Frontend Environment

```bash
# Support Backend API
VITE_API_BASE_URL=http://localhost:8001  # Local dev
# VITE_API_BASE_URL=https://support-backend.quimbi.com  # Production

# Feature Flags
VITE_DEMO_MODE_ENABLED=true
VITE_AI_RECOMMENDATIONS_ENABLED=true
```

## Quimbi Intelligence Backend Environment

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/intelligence_db

# E-commerce Platform
SHOPIFY_API_URL=https://shop.myshopify.com
SHOPIFY_API_KEY=...

# ML Models
MODEL_VERSION=v1.2.3
MODEL_UPDATE_SCHEDULE=0 2 * * *  # Daily at 2 AM

# API Configuration
API_KEY=sk_intelligence_xyz789...
RATE_LIMIT=500  # requests per minute

# Claude API (for AI generation)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

---

# Technology Stack Summary

## Support Backend
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Database**: PostgreSQL (async with asyncpg)
- **ORM**: SQLAlchemy (async)
- **Caching**: Redis
- **Auth**: JWT (python-jose) + bcrypt
- **HTTP Client**: httpx (for calling Quimbi)
- **Deployment**: Railway

## Quimbi Intelligence Backend
- **Language**: Python
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ML**: scikit-learn, pandas, numpy
- **AI**: Anthropic Claude API
- **Deployment**: Railway

## Frontend
- **Language**: TypeScript
- **Framework**: React 18
- **Build Tool**: Vite
- **State**: React Query (TanStack Query)
- **Styling**: Tailwind CSS
- **HTTP**: Axios
- **Routing**: React Router v6
- **Deployment**: Railway

---

# Performance & Scalability

## Current Performance

**Support Backend:**
- Health check: < 10ms (local), < 50ms (Railway)
- Ticket list (50 tickets): < 100ms (local), < 200ms (Railway)
- Ticket detail with messages: < 150ms (local), < 300ms (Railway)
- AI draft generation: 1-3 seconds (Quimbi latency)

**Caching Strategy:**
- Customer intelligence: 15 minutes TTL
- Churn predictions: 1 hour TTL
- LTV forecasts: 1 hour TTL
- AI drafts: 1 hour TTL (per ticket + parameters)
- Smart scores: 5 minutes TTL

## Scalability Considerations

### Horizontal Scaling
- **Support Backend**: Stateless, can run multiple instances behind load balancer
- **Quimbi Intelligence**: Stateless, can scale independently
- **Frontend**: CDN distribution, static assets

### Database Optimization
- **Indexes**: status, smart_score, created_at, customer_id
- **Connection Pooling**: SQLAlchemy AsyncEngine with pool_size=20
- **Read Replicas**: For analytics queries (future)

### Rate Limiting
- **Per-agent**: 1000 requests/minute
- **Per-IP**: 100 requests/minute (unauthenticated)
- **Quimbi API**: Exponential backoff with max 3 retries

---

# Deployment

## Current Deployment Status

| Component | Environment | URL | Status |
|-----------|-------------|-----|--------|
| Support Backend | Local | http://localhost:8001 | ✅ Running |
| Support Backend | Production | Railway (TBD) | 🔄 Pending |
| Quimbi Intelligence | Production | https://ecommerce-backend-staging-a14c.up.railway.app | ✅ Running |
| Frontend | Local | http://localhost:5173 | ✅ Running |
| Frontend | Production | Railway (TBD) | 🔄 Pending |

## Deployment Process

### Support Backend (Railway)
1. Push to `main` branch
2. Railway detects changes
3. Builds Docker image
4. Runs database migrations
5. Deploys to production
6. Health check before routing traffic

### Frontend (Railway)
1. Push to `main` branch
2. Railway builds Vite production bundle
3. Deploys static assets
4. CDN distribution

---

# Success Criteria

## Intelligence Backend
1. ✅ **Clear boundaries**: Everyone knows what belongs in Intelligence Backend
2. ✅ **Stateless intelligence**: No operational state, only calculated insights
3. ✅ **API-first**: All intelligence consumed via well-documented APIs
4. ✅ **Scalable**: Can handle 10,000+ intelligence requests/minute
5. ✅ **Fast**: 95th percentile response time < 200ms for cached queries

## Support Backend
1. ✅ **Reliable**: 99.9% uptime for ticket operations
2. ✅ **Fast**: Ticket CRUD operations < 100ms
3. ✅ **Scalable**: Can handle 1,000+ concurrent agents
4. ✅ **Data integrity**: Zero data loss, full audit trail
5. ✅ **JWT Auth**: Secure agent authentication with role-based access

## Frontend
1. ✅ **Performance**: < 1s time to interactive
2. ✅ **Reliability**: Graceful degradation on backend failures
3. ✅ **Security**: JWT authentication, no API keys in code
4. ✅ **Maintainability**: Clear separation of concerns, typed APIs

## Platform-Wide
1. ✅ **Observability**: Comprehensive health checks and logging
2. ✅ **Documentation**: All APIs documented (Swagger UI at /docs)
3. ✅ **Developer Experience**: Easy local setup, fast development cycle

---

# Glossary

**Agent**: Support team member who responds to tickets

**Archetype**: A cluster of customers with similar behavioral patterns (from Quimbi)

**Assignment**: The act of assigning a ticket to a specific agent

**Churn Risk**: Probability (0-1) that a customer will stop purchasing (from Quimbi)

**Draft Response**: AI-generated template message (from Quimbi via Support Backend)

**JWT (JSON Web Token)**: Stateless authentication token (24-hour expiry)

**LTV (Lifetime Value)**: Predicted total revenue from a customer (from Quimbi)

**Proxy Layer**: Support Backend's role in calling Quimbi Intelligence for AI features

**Quimbi Intelligence**: The AI/ML backend that provides customer insights

**RBAC (Role-Based Access Control)**: Permission system based on agent roles

**Redis**: In-memory cache for Quimbi responses and smart scores

**Segment**: A group of customers sharing a behavioral trait (from Quimbi)

**SLA (Service Level Agreement)**: Target response and resolution times

**Smart Score**: Calculated urgency score for inbox ordering (Support Backend calculates)

**Support Backend**: The operational backend handling tickets and agents (this service)

**Topic Alert**: Keyword-based filter to surface urgent tickets (+5 score boost)

**Ticket**: A customer support request or inquiry

---

**Document Owner**: Quimbi Engineering Team
**Last Updated**: December 1, 2025
**Next Review**: Quarterly
**Version**: 2.0
