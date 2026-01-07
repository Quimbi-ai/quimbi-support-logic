# API Quick Reference

## Swagger UI Locations

### Local Development
```
http://localhost:8001/docs
```

### Production (Railway)
```
https://ecommerce-backend-staging-a14c.up.railway.app/docs
```

---

## Authentication

### 1. Login
```bash
curl -X POST http://localhost:8001/api/agents/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### 2. Use Token
```bash
Authorization: Bearer <token>
```

---

## Essential Endpoints

### Health Check (No Auth)
```
GET /health
```

### Tickets
```
GET  /api/tickets                          # List tickets
GET  /api/tickets/{id}                     # Get ticket details
GET  /api/tickets/{id}/messages            # Get ticket messages
GET  /api/tickets/{id}/score-breakdown     # See urgency score
PATCH /api/tickets/{id}                    # Update ticket
```

### AI Features (Auth Required)
```
GET  /api/ai/tickets/{id}/recommendation   # Get AI recommendation
GET  /api/ai/tickets/{id}/draft-response   # Get draft reply
POST /api/ai/tickets/{id}/regenerate-draft # Regenerate draft
GET  /api/ai/customers/{id}/intelligence   # Get customer insights
```

### Agent
```
GET   /api/agents/me                       # Get current agent
PATCH /api/agents/me/status                # Update status
POST  /api/agents/logout                   # Logout
```

---

## Quick Test Commands

### Test Backend
```bash
# Check if running
curl http://localhost:8001/health

# Login
curl -X POST http://localhost:8001/api/agents/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# Get tickets (replace TOKEN)
curl http://localhost:8001/api/tickets \
  -H "Authorization: Bearer TOKEN"
```

---

## Common Query Parameters

### GET /api/tickets
```
?status=open              # Filter by status
?channel=email            # Filter by channel
?limit=50                 # Results per page (max 100)
?page=1                   # Page number
?topic_alerts=payment     # Boost matching keywords
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Not authenticated |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 500 | Server error |

---

## Environment Setup

### Create .env
```bash
SECRET_KEY=<openssl rand -hex 32>
DATABASE_URL=sqlite+aiosqlite:///./test_support.db
QUIMBI_API_KEY=test-quimbi-key
```

### Seed Admin User
```bash
python3 seed_admin.py
```

**Login:**
- Email: `admin@example.com`
- Password: `admin123`

---

## Frontend Integration

```typescript
// Login
const response = await fetch('http://localhost:8001/api/agents/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});

const { access_token } = await response.json();

// Get tickets
const tickets = await fetch('http://localhost:8001/api/tickets', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

---

## Server Status

**Local:** Running on port 8001 ✅
**Production:** Railway deployment (check `/health`)

For detailed documentation, see [FRONTEND_API_GUIDE.md](./FRONTEND_API_GUIDE.md)
