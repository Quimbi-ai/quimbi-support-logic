# Quimbi Support Backend

**Full-Featured Customer Support Operations Platform** - The system of record for all support operations, enriched with AI-powered customer intelligence

## 🎯 Purpose

This is **NOT a thin proxy** to Quimbi Backend. This is a **complete operational CRM** that manages the full lifecycle of customer support operations.

### What This Backend Owns (System of Record)
- ✅ **Tickets** - Complete ticket lifecycle, status, metadata
- ✅ **Messages** - Full conversation history and threading
- ✅ **Agents** - Team members, roles, permissions, authentication
- ✅ **Assignments** - Ticket routing, workload distribution, transfer history
- ✅ **SLA Tracking** - Response/resolution time policies, breach detection, escalation
- ✅ **Rules Engine** - Custom prioritization rules, automation workflows
- ✅ **Integrations** - Gorgias, Zendesk, email, SMS, chat connectors

### What Quimbi Backend Provides (Intelligence Layer)
- 🧠 **Customer DNA** - 13-axis behavioral segmentation
- 🧠 **Churn Predictions** - Risk scoring and contributing factors
- 🧠 **LTV Forecasting** - Lifetime value predictions
- 🧠 **AI Draft Generation** - Claude-powered response drafting
- 🧠 **Recommendations** - Intelligent action suggestions

**Architecture Philosophy**: This backend is the **operational engine** for support teams. It integrates with Quimbi Backend to enrich support decisions with customer intelligence, but remains fully functional even when Quimbi is unavailable.

## 🏗️ Architecture

Part of the Quimbi ecosystem, but maintains operational independence:
- **Support Frontends** → Call this API for all support operations
- **Quimbi AI Backend** → Provides customer intelligence (this backend caches it)
- **This Backend** → System of record for tickets, agents, SLA, assignments

## 📁 Project Structure

```
quimbi-support-backend/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── api/
│   │   └── v1/
│   │       ├── tickets.py   # Ticket endpoints
│   │       ├── messages.py  # Message endpoints
│   │       └── rules.py     # Prioritization rules
│   ├── models/
│   │   ├── ticket.py
│   │   ├── message.py
│   │   └── rule.py
│   ├── services/
│   │   ├── ticket_service.py
│   │   ├── prioritization.py
│   │   └── integrations/
│   │       ├── gorgias.py
│   │       └── zendesk.py
│   └── db/
│       └── database.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (or SQLite for dev)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your config

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8001
# API runs at http://localhost:8001
```

### With Docker

```bash
docker build -t quimbi-support-backend .
docker run -p 8001:8001 quimbi-support-backend
```

## 📡 API Endpoints

### Tickets

```
GET    /api/v1/tickets
  Query: { status, priority, assigned_to, topic_alerts, apply_rules }
  Returns: List of tickets with optional rule-based scoring

GET    /api/v1/tickets/{id}
  Returns: Full ticket with messages and customer profile

POST   /api/v1/tickets
  Body: { customer_id, subject, channel, priority, initial_message }
  Returns: Created ticket

PATCH  /api/v1/tickets/{id}
  Body: { status, priority, assigned_to }
  Returns: Updated ticket

POST   /api/v1/tickets/{id}/reset
  Creates duplicate ticket with only initial message (for demos)
```

### Messages

```
POST   /api/v1/tickets/{id}/messages
  Body: { content, from_agent, author_name, author_email }
  Returns: Created message

GET    /api/v1/tickets/{id}/messages
  Returns: All messages for ticket
```

### Prioritization Rules

```
GET    /api/v1/rules
  Returns: All active prioritization rules

POST   /api/v1/rules
  Body: { name, type, keywords, boost_amount }
  Returns: Created rule

POST   /api/v1/tickets/prioritize
  Body: { ticket_ids, rule_ids }
  Returns: Tickets with updated scores
```

## 🔧 Technologies

- **FastAPI** - Python web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Pydantic** - Data validation
- **Alembic** - Database migrations
- **Redis** - Caching (optional)

## 🔌 External Integrations

### Gorgias
- Sync tickets from Gorgias
- Push responses back to Gorgias
- Webhook handlers for real-time updates

### Zendesk
- Import tickets from Zendesk
- Bi-directional sync

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_tickets.py
```

## 🚢 Deployment

### Railway

```bash
railway up
```

### Environment Variables

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
GORGIAS_API_KEY=your-gorgias-key
GORGIAS_DOMAIN=your-domain.gorgias.com
REDIS_URL=redis://localhost:6379
API_KEY=your-api-key
CORS_ORIGINS=https://your-frontend.com
```

## 📊 Database Schema

### Tickets Table
- id (UUID)
- customer_id (UUID, FK to CRM)
- subject (String)
- status (Enum: open, pending, closed)
- priority (Enum: low, normal, high, urgent)
- channel (Enum: email, sms, chat, phone)
- smart_score (Float, nullable)
- assigned_to (UUID, nullable)
- created_at, updated_at

### Messages Table
- id (UUID)
- ticket_id (UUID, FK)
- content (Text)
- from_agent (Boolean)
- author_name (String)
- author_email (String, nullable)
- created_at

### Rules Table
- id (UUID)
- name (String)
- type (Enum: vip, churn, time_sensitive, custom)
- keywords (JSON Array)
- boost_amount (Float)
- active (Boolean)
- created_at

## 🔑 Key Business Logic

### Smart Prioritization (Owned by This Backend)
1. **Base Score** - Computed from ticket properties (age, priority, channel)
2. **Customer Intelligence Boost** - Enriched with LTV, churn risk from Quimbi
3. **Keyword Rules** - Custom rules stored in this backend's database
4. **SLA Urgency** - Time-to-breach calculations from this backend's SLA engine
5. **Final Ranking** - Sorted ticket queue for agent assignment

### Ticket Lifecycle (Managed by This Backend)
```
Created → Open → Assigned → In Progress → Pending → Resolved → Closed
          ↓                                   ↓
        Routed                             Escalated
          ↓
    Agent Queue
```

### Agent Workload Management (Future - Week 3)
- Automatic ticket assignment based on agent skills, capacity, and performance
- Workload balancing across team members
- Transfer and reassignment with full audit history

### SLA Tracking (Future - Week 4)
- Configurable SLA policies per channel, priority, customer tier
- Real-time breach detection and alerting
- Automatic escalation on approaching deadlines

## 📖 Related Systems

- **Support Frontends** - React/Vue/Angular UIs that integrate with this backend
- **Quimbi Backend** - AI/ML intelligence platform (https://ecommerce-backend-staging-a14c.up.railway.app)
  - Provides customer DNA, churn predictions, LTV forecasts, AI generation
  - This backend caches Quimbi data to reduce API calls and maintain independence

## 🛣️ Development Roadmap

### ✅ Week 1: Quimbi Integration (COMPLETE)
- [x] Quimbi API client with retry logic
- [x] Redis caching layer
- [x] AI endpoints (draft generation, recommendations, customer intelligence)
- [x] Health checks and monitoring

### 🚧 Week 2-3: Operational Features (IN PROGRESS)
- [ ] **Agent Management** - Authentication, roles, permissions
- [ ] **Ticket Assignment** - Manual assignment, auto-routing, workload balancing
- [ ] **Agent Performance** - Tracking resolution time, customer satisfaction
- [ ] **Audit Trail** - Complete history of ticket changes, assignments, transfers

### 📅 Week 4-5: SLA & Escalation
- [ ] **SLA Policies** - Configurable per channel, priority, customer tier
- [ ] **SLA Monitoring** - Real-time tracking, breach detection
- [ ] **Auto-Escalation** - Rules-based escalation when SLA at risk
- [ ] **Manager Dashboard** - Team performance, SLA compliance

### 📅 Week 6+: Advanced Features
- [ ] **Multi-tenant Support** - Multiple companies/brands
- [ ] **Advanced Routing** - Skills-based routing, business hours
- [ ] **Webhooks** - Real-time notifications to external systems
- [ ] **Analytics API** - Support metrics, agent performance data

## 📄 License

Proprietary - Quimbi.ai
