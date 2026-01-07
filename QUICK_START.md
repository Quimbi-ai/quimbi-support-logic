# Quick Start: Quimbi Integration

## 🎯 What We Built

The Customer Support Backend now integrates with **Quimbi Backend** for AI intelligence:
- ✅ Customer DNA analysis (13-axis behavioral segmentation)
- ✅ Churn risk predictions
- ✅ LTV forecasting
- ✅ AI draft generation (Claude-powered)
- ✅ AI action recommendations
- ✅ Redis caching (15 min TTL for intelligence)
- ✅ Retry logic with exponential backoff
- ✅ Graceful error handling

---

## 🚀 Getting Started

### Step 1: Get Quimbi API Key

Contact the Quimbi Backend administrator to get:
- **API Key**: `qpk_live_...` (production) or `qpk_test_...` (staging)
- **Base URL**: `https://ecommerce-backend-staging-a14c.up.railway.app`

### Step 2: Set Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and set these REQUIRED variables:
QUIMBI_BASE_URL=https://ecommerce-backend-staging-a14c.up.railway.app
QUIMBI_API_KEY=your-api-key-here  # <-- Get this from admin

# Also set your database URL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/support_db
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Start Redis (Required for Caching)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# OR using Homebrew (macOS)
brew install redis
brew services start redis

# OR using apt (Linux)
sudo apt-get install redis-server
sudo systemctl start redis
```

### Step 5: Initialize Database

```bash
# Seed with sample data
python -m app.db_init
```

### Step 6: Run the Application

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 7: Test Integration

```bash
# Check health endpoint
curl http://localhost:8000/health

# Should return:
# {
#   "status": "healthy",
#   "services": {
#     "database": "connected",
#     "redis_cache": "connected",
#     "quimbi_api": "connected"  # <-- Should be "connected"
#   },
#   "features": {
#     "ai_draft_generation": true,
#     "customer_intelligence": true
#   }
# }
```

---

## 📋 API Endpoints

### Get Customer Intelligence

```bash
GET /api/ai/customers/{customer_id}/intelligence

# Example:
curl http://localhost:8000/api/ai/customers/cust_123/intelligence \
  -H "Content-Type: application/json"

# Response:
{
  "customer_id": "cust_123",
  "archetype": {
    "id": "arch_premium_deal_hunter",
    "segments": {
      "purchase_value": "premium",
      "price_sensitivity": "deal_hunter",
      ...
    }
  },
  "behavioral_metrics": {
    "lifetime_value": 892.50,
    "total_orders": 12
  },
  "predictions": {
    "churn_risk": 0.18,
    "churn_risk_level": "low"
  },
  "communication_guidance": [...]
}
```

### Generate AI Draft

```bash
GET /api/ai/tickets/{ticket_id}/draft-response

# Example:
curl http://localhost:8000/api/ai/tickets/ticket_123/draft-response

# Response:
{
  "ticket_id": "ticket_123",
  "draft_content": "Hi Sarah, I understand your concern about...",
  "tone": "empathetic",
  "channel": "email",
  "personalization_applied": [
    "Adjusted for beginner",
    "Avoided jargon"
  ],
  "customer_dna": {...},
  "churn_risk": 0.18
}
```

### Get AI Recommendations

```bash
GET /api/ai/tickets/{ticket_id}/recommendation

# Response:
{
  "ticket_id": "ticket_123",
  "actions": [
    {
      "action": "Send immediate replacement with expedited shipping",
      "priority": 1,
      "reasoning": "High-value customer with elevated churn risk",
      "estimated_impact": {
        "retention_probability": 0.85,
        "revenue_at_risk": 780.00
      }
    }
  ],
  "warnings": ["Customer has high churn risk"],
  "talking_points": ["Apologize sincerely", ...]
}
```

### Regenerate Draft (Clear Cache)

```bash
POST /api/ai/tickets/{ticket_id}/regenerate-draft

# Clears cached customer intelligence and generates fresh draft
```

---

## 🔧 Configuration

### Caching Settings

```bash
# .env
QUIMBI_CACHE_INTELLIGENCE_TTL=900  # 15 minutes (customer DNA)
QUIMBI_CACHE_CHURN_TTL=3600        # 1 hour (churn predictions)
QUIMBI_CACHE_LTV_TTL=3600          # 1 hour (LTV forecasts)
```

**What gets cached:**
- ✅ Customer intelligence (DNA, archetype, metrics) - 15 min
- ✅ Churn predictions - 1 hour
- ✅ LTV forecasts - 1 hour
- ❌ AI-generated messages - NOT cached (always fresh)

### Retry Configuration

```bash
# .env
QUIMBI_TIMEOUT=30.0       # API timeout (seconds)
QUIMBI_MAX_RETRIES=3      # Number of retry attempts
```

**Retry behavior:**
- ✅ Retries on: 500, 503 (server errors), network errors
- ❌ No retry on: 400, 404, 422 (client errors), 401, 403 (auth errors)
- ⚠️ Rate limit (429): Respects `Retry-After` header

---

## 🐛 Troubleshooting

### Issue: "Quimbi API connected: unavailable"

**Problem:** `GET /health` shows `"quimbi_api": "unavailable"`

**Solution:**
1. Check `QUIMBI_API_KEY` is set in `.env`
2. Verify key is valid (not expired)
3. Check network connectivity to Quimbi Backend:
   ```bash
   curl -X POST https://ecommerce-backend-staging-a14c.up.railway.app/api/intelligence/analyze \
     -H "X-API-Key: your-key-here" \
     -H "Content-Type: application/json" \
     -d '{"customer_id": "test_customer_high_ltv", "context": {}}'
   ```

### Issue: "Redis cache: unavailable"

**Problem:** Caching is disabled

**Solution:**
1. Start Redis: `redis-server`
2. Check connection: `redis-cli ping` (should return `PONG`)
3. Verify `REDIS_URL` in `.env`: `redis://localhost:6379/0`

**Graceful Degradation:** App still works without Redis, but:
- No caching → More API calls to Quimbi
- Slower response times

### Issue: AI Service Temporarily Unavailable (503)

**Problem:** API returns 503 error on `/draft-response` or `/recommendation`

**Causes:**
1. Quimbi Backend is down
2. Network issues
3. Rate limit exceeded (429)

**Solution:**
1. Check Quimbi Backend health: `curl https://ecommerce-backend-staging-a14c.up.railway.app/health`
2. Wait 60 seconds and retry (rate limit cooldown)
3. Check logs: `tail -f logs/app.log`

**Fallback behavior:** App returns generic messages when Quimbi is unavailable.

### Issue: Customer Not Found (404)

**Problem:** `/api/ai/customers/{id}/intelligence` returns 404

**Cause:** Customer doesn't exist in local database

**Solution:**
1. Verify customer exists: `SELECT * FROM customers WHERE id = 'customer_id';`
2. Run database seed: `python -m app.db_init`
3. Create customer manually via `/api/tickets` (creates customer + ticket)

---

## 📊 Monitoring

### Check Service Health

```bash
# Detailed health check
curl http://localhost:8000/health | jq

# Quick check
curl http://localhost:8000/health | jq '.services'
```

### View Logs

```bash
# Application logs
tail -f logs/app.log

# Filter for Quimbi API calls
tail -f logs/app.log | grep "Quimbi"

# Filter for errors
tail -f logs/app.log | grep "ERROR"
```

### Cache Statistics

```bash
# Connect to Redis
redis-cli

# Check keys
KEYS customer_intel:*
KEYS churn_prediction:*

# Check TTL
TTL customer_intel:cust_123

# View cached data
GET customer_intel:cust_123
```

---

## 🎯 Next Steps

### Week 1: Basic Integration (✅ DONE)
- [x] Quimbi client service
- [x] Redis caching
- [x] AI endpoints (draft, recommendations, intelligence)
- [x] Error handling & retries
- [x] Health checks

### Week 2: Enhanced Features (TODO)
- [ ] Enrich ticket list with customer DNA
- [ ] Show churn risk in ticket views
- [ ] Add revenue-at-risk calculations
- [ ] Display communication guidance to agents

### Week 3: Agent Management (TODO)
- [ ] Agent models & authentication
- [ ] Ticket assignment system
- [ ] Agent performance tracking

### Week 4: SLA Tracking (TODO)
- [ ] SLA policy configuration
- [ ] Response time tracking
- [ ] Breach alerting

---

## 📚 Documentation

- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Quimbi integration patterns
- **[API_REQUIREMENTS.md](API_REQUIREMENTS.md)** - Complete API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[ROADMAP.md](ROADMAP.md)** - 16-week development plan

---

## 🆘 Support

**Quimbi Backend Issues:**
- Status Page: https://ecommerce-backend-staging-a14c.up.railway.app/health
- Contact: Quimbi backend team

**Support Backend Issues:**
- Check logs: `tail -f logs/app.log`
- Health check: `GET /health`
- GitHub Issues: [Report bugs](https://github.com/your-org/q.ai-customer-support/issues)

---

## ✅ Integration Checklist

Before deploying to production:

- [ ] Quimbi API key configured (production key, not test)
- [ ] Redis running and connected
- [ ] Database migrations applied
- [ ] Health endpoint returns all "connected"
- [ ] Test AI draft generation manually
- [ ] Test AI recommendations manually
- [ ] Test customer intelligence endpoint
- [ ] Verify caching works (check Redis keys)
- [ ] Review error logs (no critical errors)
- [ ] Test retry logic (simulate network errors)
- [ ] Test fallback behavior (stop Quimbi temporarily)
- [ ] Configure CORS for production frontend URL
- [ ] Set up monitoring/alerting
- [ ] Document deployment runbook

---

**🎉 Integration Complete!** You're now using Quimbi Backend for AI intelligence.

**Questions?** Review the [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for detailed integration patterns.
