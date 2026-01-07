# Customer Support Backend - Frontend Integration Guide

## TL;DR - Start Here

**Swagger UI:** http://localhost:8001/docs
**Backend Status:** Running on localhost:8001 ✅
**Test Data:** 5 customers, 6 tickets, 10+ messages ✅

---

## Quick Start (3 Steps)

### 1. Open Swagger UI
Visit: http://localhost:8001/docs

This interactive documentation lets you test every endpoint before writing code.

### 2. Login to Get Token
In Swagger UI, click on `/api/agents/login` → Try it out:
```json
{
  "email": "admin@example.com",
  "password": "admin123"
}
```

Copy the `access_token` from the response.

### 3. Authorize & Test
Click the "Authorize" button at the top of Swagger UI, paste your token, then test any endpoint.

---

## Documentation Files

| File | Purpose |
|------|---------|
| **[FRONTEND_INTEGRATION_SUMMARY.md](./FRONTEND_INTEGRATION_SUMMARY.md)** | Complete integration guide with code examples |
| **[FRONTEND_API_GUIDE.md](./FRONTEND_API_GUIDE.md)** | Detailed API documentation |
| **[API_QUICK_REFERENCE.md](./API_QUICK_REFERENCE.md)** | Quick reference for common tasks |

---

## Key Endpoints for Frontend

### Authentication
```
POST /api/agents/login       # Login → get token
POST /api/agents/logout      # Logout
GET  /api/agents/me          # Get current agent info
PATCH /api/agents/me/status  # Update agent status
```

### Tickets (Core Features)
```
GET  /api/tickets                      # List tickets (smart ordered)
GET  /api/tickets/{id}                 # Get ticket details + messages
GET  /api/tickets/{id}/messages        # Get messages only
PATCH /api/tickets/{id}                # Update ticket status/priority
GET  /api/tickets/{id}/score-breakdown # See urgency score calculation
```

### AI Features
```
GET  /api/ai/tickets/{id}/draft-response     # Get AI-generated reply
GET  /api/ai/tickets/{id}/recommendation     # Get AI recommendation
POST /api/ai/tickets/{id}/regenerate-draft   # Regenerate draft
GET  /api/ai/customers/{id}/intelligence     # Get customer insights
```

---

## Authentication Flow

```typescript
// 1. Login
const response = await fetch('http://localhost:8001/api/agents/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'admin@example.com',
    password: 'admin123'
  })
});

const { access_token, agent } = await response.json();

// 2. Store token
localStorage.setItem('token', access_token);

// 3. Use token in subsequent requests
const tickets = await fetch('http://localhost:8001/api/tickets', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

---

## Test Data Available

### Agents (3)
- **admin@example.com** / admin123 (Admin)
- **sarah@example.com** / password123 (Senior Agent)
- **mike@example.com** / password123 (Agent)

### Customers (5)
- John Doe - 2 tickets (payment & discount issues)
- Jane Smith - 1 ticket (wrong item)
- Bob Wilson - 1 ticket (shipping delay)
- Alice Brown - 1 ticket (login issues)
- Charlie Davis - 1 ticket (refund policy - resolved)

### Tickets (6)
All tickets have realistic customer messages. Some have multi-message conversations with agent responses.

---

## Smart Inbox Features

### 1. Smart Ordering (Urgency Score)
Tickets are automatically ordered by urgency score (0-10), calculated from:
- Priority level (high = urgent)
- Customer sentiment (negative = higher priority)
- Wait time (older = higher priority)
- Topic alerts (matching keywords get boosted)

**Example:**
```
GET /api/tickets?status=open
```
Returns tickets ordered by smart_score (highest first).

### 2. Topic Alerts
Boost tickets matching specific keywords:
```
GET /api/tickets?topic_alerts=payment,chargeback,fraud
```
Matching tickets get +5.0 score boost.

### 3. Filters
```
GET /api/tickets?status=open&channel=email&limit=20&page=1
```

---

## Response Examples

### GET /api/tickets
```json
{
  "tickets": [
    {
      "id": "ticket_abd5965f",
      "customer_id": "cust_0e3311ba",
      "subject": "Payment not processing",
      "status": "open",
      "priority": "high",
      "channel": "email",
      "created_at": "2025-12-01T01:46:45.064388",
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

### GET /api/tickets/{id}
```json
{
  "id": "ticket_abd5965f",
  "customer_id": "cust_0e3311ba",
  "subject": "Payment not processing",
  "status": "open",
  "priority": "high",
  "channel": "email",
  "created_at": "2025-12-01T01:46:45.064388",
  "customer_sentiment": 0.2,
  "smart_score": 9.95,
  "estimated_difficulty": 0.6,
  "messages": [
    {
      "id": "msg_123",
      "ticket_id": "ticket_abd5965f",
      "content": "I've been trying to complete my purchase...",
      "from_agent": false,
      "from_name": "John Doe",
      "from_email": "john.doe@gmail.com",
      "created_at": "2025-12-01T01:46:45.064388"
    }
  ],
  "customer": {
    "id": "cust_0e3311ba",
    "email": "john.doe@gmail.com",
    "name": "John Doe",
    "lifetime_value": 1250.00,
    "total_orders": 8,
    "churn_risk_score": 0.15
  }
}
```

---

## Frontend Checklist

### Phase 1: Basic Integration
- [ ] Login page
- [ ] Tickets list view
- [ ] Ticket detail view
- [ ] Message display
- [ ] Basic routing

### Phase 2: Enhanced Features
- [ ] Agent status management
- [ ] Ticket filtering (status, channel)
- [ ] Pagination
- [ ] Real-time updates (future)

### Phase 3: AI Features
- [ ] Display AI draft responses
- [ ] Show AI recommendations
- [ ] Customer intelligence panel
- [ ] Urgency score breakdown

---

## Common Frontend Patterns

### React Component Example
```typescript
function TicketsList() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTickets() {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8001/api/tickets', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setTickets(data.tickets);
      setLoading(false);
    }

    fetchTickets();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {tickets.map(ticket => (
        <TicketCard key={ticket.id} ticket={ticket} />
      ))}
    </div>
  );
}
```

### Vue Composition API Example
```vue
<script setup>
import { ref, onMounted } from 'vue';

const tickets = ref([]);
const loading = ref(true);

onMounted(async () => {
  const token = localStorage.getItem('token');
  const response = await fetch('http://localhost:8001/api/tickets', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  tickets.value = data.tickets;
  loading.value = false;
});
</script>

<template>
  <div v-if="loading">Loading...</div>
  <div v-else>
    <TicketCard
      v-for="ticket in tickets"
      :key="ticket.id"
      :ticket="ticket"
    />
  </div>
</template>
```

---

## Error Handling

### 401 Unauthorized → Redirect to Login
```typescript
if (response.status === 401) {
  localStorage.removeItem('token');
  router.push('/login');
}
```

### 403 Forbidden → Insufficient Permissions
```typescript
if (response.status === 403) {
  showError('You do not have permission for this action');
}
```

### 500 Server Error → Show Error Message
```typescript
if (response.status === 500) {
  showError('Server error. Please try again later.');
}
```

---

## UI/UX Recommendations

### Ticket List
- **Sort by:** smart_score (desc) - most urgent first
- **Color coding:**
  - Red: high priority
  - Yellow: medium priority
  - Green: low priority
- **Sentiment indicator:** 😡 😐 😊 based on customer_sentiment
- **Status badges:** Open, In Progress, Resolved

### Ticket Detail
- **Customer info panel:** Show lifetime_value, total_orders, churn_risk_score
- **Message thread:** Chat-style UI with agent vs customer message distinction
- **AI suggestions:** Show draft response in a preview panel
- **Urgency breakdown:** Visual representation of score calculation

### Smart Inbox
- **Topic alerts input:** Allow agents to set keywords they want to monitor
- **Auto-refresh:** Poll for new tickets every 30 seconds
- **Unread indicator:** Highlight tickets with new messages

---

## Performance Tips

1. **Pagination:** Don't load all tickets at once. Use page/limit params.
2. **Caching:** Cache ticket list for 10 seconds to reduce API calls.
3. **Optimistic Updates:** Update UI immediately, then sync with API.
4. **Debouncing:** Debounce search/filter inputs to reduce API calls.

---

## Next Steps

1. **Explore Swagger UI:** http://localhost:8001/docs
2. **Read Integration Summary:** [FRONTEND_INTEGRATION_SUMMARY.md](./FRONTEND_INTEGRATION_SUMMARY.md)
3. **Review API Guide:** [FRONTEND_API_GUIDE.md](./FRONTEND_API_GUIDE.md)
4. **Start Building:** Create login page and tickets list view

---

## Need Help?

- **Swagger UI:** http://localhost:8001/docs (test endpoints interactively)
- **OpenAPI Spec:** http://localhost:8001/openapi.json (programmatic access)
- **Health Check:** http://localhost:8001/health (verify backend is running)

---

**Backend Status:** ✅ Running on localhost:8001
**Test Data:** ✅ Seeded and ready
**Documentation:** ✅ Complete

**Ready for Frontend Integration!**
