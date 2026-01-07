# Frontend API Integration Guide

## Quick Start

### Swagger UI (Interactive API Documentation)

**Local Development:**
```
http://localhost:8001/docs
```

**OpenAPI JSON Spec:**
```
http://localhost:8001/openapi.json
```

**Production (Railway):**
```
https://ecommerce-backend-staging-a14c.up.railway.app/docs
```

---

## Authentication

All agent-related endpoints require JWT authentication.

### Login
```http
POST /api/agents/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "agent": {
    "id": "agent_xyz",
    "email": "admin@example.com",
    "name": "Admin User",
    "role": "admin",
    "status": "online"
  }
}
```

### Using the Token

Include the token in all authenticated requests:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Available Endpoints

### Health Check
```http
GET /health
```
No authentication required. Returns server status.

---

### Tickets

#### List Tickets (Smart Ordering)
```http
GET /api/tickets?status=open&limit=50&page=1
```

**Query Parameters:**
- `status` (optional): Filter by status (default: "open")
- `channel` (optional): Filter by channel (email, chat, phone)
- `limit` (optional): Results per page (default: 50, max: 100)
- `page` (optional): Page number (default: 1)
- `topic_alerts` (optional): Comma-separated keywords to boost matching tickets

**Response:**
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
      "created_at": "2025-11-25T10:00:00Z",
      "urgency_score": 8.5,
      "ai_summary": "Customer unable to complete checkout due to payment error"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 100,
    "has_next": true,
    "has_prev": false
  },
  "topic_alerts_active": ["payment", "checkout"],
  "matches": 5
}
```

#### Get Single Ticket
```http
GET /api/tickets/{ticket_id}
```

**Response:**
```json
{
  "id": "ticket_abc123",
  "customer_id": "cust_xyz",
  "subject": "Payment not processing",
  "status": "open",
  "priority": "high",
  "channel": "email",
  "created_at": "2025-11-25T10:00:00Z",
  "updated_at": "2025-11-25T10:05:00Z",
  "urgency_score": 8.5,
  "ai_summary": "Customer unable to complete checkout",
  "customer": {
    "id": "cust_xyz",
    "email": "customer@example.com",
    "name": "John Doe"
  }
}
```

#### Get Ticket Messages
```http
GET /api/tickets/{ticket_id}/messages
```

**Response:**
```json
{
  "messages": [
    {
      "id": "msg_123",
      "ticket_id": "ticket_abc123",
      "sender_type": "customer",
      "sender_id": "cust_xyz",
      "content": "I can't complete my purchase. Getting an error.",
      "created_at": "2025-11-25T10:00:00Z",
      "metadata": {}
    },
    {
      "id": "msg_124",
      "ticket_id": "ticket_abc123",
      "sender_type": "agent",
      "sender_id": "agent_xyz",
      "content": "I'll look into this right away...",
      "created_at": "2025-11-25T10:02:00Z",
      "is_ai_generated": false
    }
  ]
}
```

#### Get Urgency Score Breakdown
```http
GET /api/tickets/{ticket_id}/score-breakdown
```

**Response:**
```json
{
  "ticket_id": "ticket_abc123",
  "total_score": 8.5,
  "breakdown": {
    "base_priority": 3.0,
    "sentiment_negative": 2.0,
    "wait_time": 1.5,
    "topic_alerts": 2.0
  },
  "factors": [
    {
      "name": "Priority Level",
      "value": 3.0,
      "explanation": "High priority ticket"
    },
    {
      "name": "Negative Sentiment",
      "value": 2.0,
      "explanation": "Customer expressed frustration"
    }
  ]
}
```

#### Update Ticket Status
```http
PATCH /api/tickets/{ticket_id}
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "resolved",
  "priority": "medium"
}
```

---

### AI Features

#### Get AI Recommendation
```http
GET /api/ai/tickets/{ticket_id}/recommendation
Authorization: Bearer {token}
```

**Response:**
```json
{
  "ticket_id": "ticket_abc123",
  "recommendation": {
    "action": "investigate_payment_logs",
    "confidence": 0.85,
    "reasoning": "Error pattern suggests payment gateway timeout",
    "suggested_priority": "high",
    "estimated_resolution_time": "15 minutes"
  }
}
```

#### Get Draft Response
```http
GET /api/ai/tickets/{ticket_id}/draft-response
Authorization: Bearer {token}
```

**Response:**
```json
{
  "ticket_id": "ticket_abc123",
  "draft": "Hi John,\n\nI've looked into your payment issue...",
  "tone": "professional_friendly",
  "confidence": 0.92
}
```

#### Regenerate Draft Response
```http
POST /api/ai/tickets/{ticket_id}/regenerate-draft
Content-Type: application/json
Authorization: Bearer {token}

{
  "tone": "formal",
  "include_details": ["order_id", "payment_method"]
}
```

#### Get Customer Intelligence
```http
GET /api/ai/customers/{customer_id}/intelligence
Authorization: Bearer {token}
```

**Response:**
```json
{
  "customer_id": "cust_xyz",
  "intelligence": {
    "lifetime_value": 1250.00,
    "sentiment_trend": "positive",
    "preferred_channel": "email",
    "common_issues": ["shipping", "returns"],
    "interaction_summary": "Long-time customer, generally satisfied",
    "risk_score": 0.15
  }
}
```

---

### Agent Management

#### Get Current Agent Profile
```http
GET /api/agents/me
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "agent_xyz",
  "email": "agent@example.com",
  "name": "Agent Smith",
  "role": "agent",
  "status": "online",
  "max_concurrent_tickets": 10,
  "specializations": ["billing", "technical"],
  "performance_metrics": {
    "tickets_resolved_today": 12,
    "avg_response_time_seconds": 245,
    "customer_satisfaction": 4.7
  }
}
```

#### Update Agent Status
```http
PATCH /api/agents/me/status
Content-Type: application/json
Authorization: Bearer {token}

{
  "status": "away"
}
```

**Valid statuses:** online, away, busy, offline

#### Logout
```http
POST /api/agents/logout
Authorization: Bearer {token}
```

---

## Database Seeding (For Testing)

If the database is empty, you can seed it with test data:

```bash
# Create admin agent
python3 seed_admin.py

# Login credentials
Email: admin@example.com
Password: admin123
```

---

## Error Handling

All endpoints return standard error responses:

### 401 Unauthorized
```json
{
  "detail": "Invalid credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Ticket not found"
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred. Please try again later."
  }
}
```

---

## Frontend Integration Example

### React/TypeScript Example

```typescript
// api.ts
const API_BASE = 'http://localhost:8001';

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/api/agents/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) throw new Error('Login failed');

  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data;
}

export async function getTickets(status = 'open', topicAlerts?: string[]) {
  const token = localStorage.getItem('token');
  const params = new URLSearchParams({ status });

  if (topicAlerts?.length) {
    params.set('topic_alerts', topicAlerts.join(','));
  }

  const response = await fetch(`${API_BASE}/api/tickets?${params}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) throw new Error('Failed to fetch tickets');
  return response.json();
}

export async function getTicketDraft(ticketId: string) {
  const token = localStorage.getItem('token');

  const response = await fetch(
    `${API_BASE}/api/ai/tickets/${ticketId}/draft-response`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (!response.ok) throw new Error('Failed to get draft');
  return response.json();
}
```

### Vue/Nuxt Example

```typescript
// composables/useApi.ts
export const useApi = () => {
  const config = useRuntimeConfig();
  const baseURL = config.public.apiBase || 'http://localhost:8001';

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  };

  return {
    async login(email: string, password: string) {
      const response = await $fetch(`${baseURL}/api/agents/login`, {
        method: 'POST',
        body: { email, password }
      });

      localStorage.setItem('token', response.access_token);
      return response;
    },

    async getTickets(params?: { status?: string; topicAlerts?: string[] }) {
      return $fetch(`${baseURL}/api/tickets`, {
        headers: getAuthHeaders(),
        query: {
          status: params?.status || 'open',
          ...(params?.topicAlerts && {
            topic_alerts: params.topicAlerts.join(',')
          })
        }
      });
    }
  };
};
```

---

## WebSocket Support (Future)

Real-time updates for ticket changes, new messages, etc. will be available via WebSocket in a future release.

**Planned endpoint:**
```
ws://localhost:8001/ws/tickets
```

---

## Rate Limiting

Current limits:
- **Public endpoints:** 100 requests/minute
- **Authenticated endpoints:** 1000 requests/minute per agent

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1701014400
```

---

## Support

For API issues or questions:
1. Check the [Swagger UI](http://localhost:8001/docs) for interactive testing
2. Review the OpenAPI spec at `/openapi.json`
3. Check server logs for detailed error messages

---

## Production Deployment Notes

### Railway Backend

**URL:** `https://ecommerce-backend-staging-a14c.up.railway.app`

**Known Issues (as of 2025-11-30):**
- API endpoints returning INTERNAL_ERROR
- Likely database connection issue
- Backend logs are outdated (November 1st)

**Recommended Actions:**
1. Check Railway database connection
2. Verify environment variables are set correctly
3. Review recent deployment logs
4. Test health endpoint: `GET /health`

### Environment Variables Required

```bash
# Required for production
SECRET_KEY=<generate with: openssl rand -hex 32>
DATABASE_URL=postgresql://...
QUIMBI_API_KEY=<your-quimbi-key>

# Optional
QUIMBI_API_URL=https://api.quimbi.ai
ENABLE_AI_FEATURES=true
LOG_LEVEL=info
```

---

## Testing Checklist

- [ ] Health check endpoint working
- [ ] Agent login successful
- [ ] Token authentication working
- [ ] Tickets list returns data
- [ ] Single ticket fetch working
- [ ] AI draft generation working
- [ ] Error responses formatted correctly
- [ ] Rate limiting headers present

---

**Last Updated:** 2025-11-30
**API Version:** 1.0.0
**Backend Status:** Running locally on port 8001
