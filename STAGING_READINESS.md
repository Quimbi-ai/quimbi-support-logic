# Staging Environment Readiness - Gorgias Integration

**Status**: ⚠️ **NOT READY FOR STAGING DEPLOYMENT**
**Review Date**: January 6, 2026
**Target**: Gorgias Webhook Integration Testing

---

## Executive Summary

System has **8 critical blockers** preventing safe staging deployment. Estimated fix time: **5-7 days**.

**Critical Issues**: Security vulnerabilities, missing credentials, broken features
**Recommendation**: Fix Phase 1 issues before any Gorgias connection (staging or production)

---

## 🚨 Critical Blockers (MUST FIX)

### 1. Missing Webhook Signature Verification
**File**: `app/api/webhooks.py:29`
**Issue**: X-Gorgias-Signature header captured but never validated
**Impact**: Anyone can POST fake webhooks - complete security bypass
**Effort**: 2 hours

```python
# Required fix:
import hmac, hashlib

async def handle_gorgias_webhook(request: Request, x_gorgias_signature: str = Header(...)):
    body = await request.body()
    expected = hmac.new(settings.gorgias_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(x_gorgias_signature, expected):
        raise HTTPException(401, "Invalid signature")
```

---

### 2. Demo Credentials in Production Config
**File**: `.env:49-52`
**Issue**: All Gorgias credentials set to "demo" placeholder values
**Impact**: Every Gorgias API call will fail with 401/403
**Effort**: 30 minutes

**Required Changes**:
```bash
GORGIAS_DOMAIN=lindas  # Replace "demo"
GORGIAS_API_KEY=<real-api-key>  # Replace "demo-api-key"
GORGIAS_USERNAME=support@yourdomain.com  # Replace "demo@example.com"
GORGIAS_WEBHOOK_SECRET=<real-secret>  # Replace "demo-webhook-secret"
```

---

### 3. Missing Shopify Configuration
**File**: `.env` (variables not present)
**Issue**: No Shopify credentials configured
**Impact**: Split shipment detection completely broken, order tracking non-functional
**Effort**: 1 hour

**Required Additions**:
```bash
# Add to .env:
SHOPIFY_SHOP_NAME=lindas-electric-quilters
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxx
SHOPIFY_API_VERSION=2024-10
```

---

### 4. Missing Python Dependency
**File**: `app/integrations/ticket_fulfillment_enricher.py:297`
**Issue**: `python-dateutil` imported but not in requirements.txt
**Impact**: Runtime ImportError crash on first order date parsing
**Effort**: 5 minutes

**Fix**:
```bash
# Add to requirements.txt:
python-dateutil==2.8.2

# Reinstall:
pip install -r requirements.txt
```

---

### 5. No Database Migrations
**File**: `alembic/versions/` (directory missing)
**Issue**: No Alembic migration files exist, schema only via create_all()
**Impact**: Cannot version schema changes, no rollback capability
**Effort**: 1 hour

**Fix**:
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

---

### 6. Missing Foreign Key Cascade Rules
**File**: `app/models/database.py:40,63`
**Issue**: ForeignKey constraints lack ondelete="CASCADE"
**Impact**: Orphaned records accumulate when deleting customers/tickets
**Effort**: 30 minutes

**Fix**:
```python
customer_id = Column(String, ForeignKey("customers.id", ondelete="CASCADE"))
ticket_id = Column(String, ForeignKey("tickets.id", ondelete="CASCADE"))
```

---

### 7. No Webhook Deduplication
**File**: `app/api/webhooks.py:26-236`
**Issue**: Every webhook processed as new event, no duplicate detection
**Impact**: 2-3x API costs, duplicate AI drafts, agent confusion
**Effort**: 3 hours

**Fix**: Add webhook_events table, check for duplicate webhook_id before processing

---

### 8. .env File in Git Repository
**File**: `.env` (tracked in git)
**Issue**: Credentials committed to repository
**Impact**: Security risk, secrets in git history
**Effort**: 30 minutes

**Fix**:
```bash
# Remove from git
git rm --cached .env
echo ".env" >> .gitignore
git commit -m "Remove .env from repository"

# Create .env.example with placeholders
cp .env .env.example
# Replace secrets with placeholders in .env.example
git add .env.example .gitignore
git commit -m "Add .env.example template"
```

---

## ⚠️ High Priority Issues (Security)

### 9. No Rate Limiting
Webhook endpoint has no rate limiting - easy DoS vector
**Effort**: 2 hours

### 10. JWT Secret Static Across Environments
SECRET_KEY shared between dev/staging/prod
**Effort**: 1 hour

### 11. No Webhook Payload Size Limit
Can send massive JSON payloads causing memory exhaustion
**Effort**: 1 hour

### 12. Database Connection Pool Not Configured
Default pool size (5) too small for production webhook volume
**Effort**: 30 minutes

### 13. CORS Too Permissive
Allows all methods (DELETE, PUT) and all headers
**Effort**: 15 minutes

---

## ⚙️ Medium Priority Issues (Reliability)

### 14. Health Check Doesn't Test Live Services
`/health` checks startup flags, not current connectivity
**Effort**: 1 hour

### 15. No Structured Logging
String logs hard to parse in log aggregators
**Effort**: 2 hours

### 16. Redis Failures Silent
Cache failures logged but no alerting/monitoring
**Effort**: 1 hour

### 17. Customer ID Format Inconsistency
Gorgias (numeric) vs Quimbi (string) IDs cause cache misses
**Effort**: 2 hours

---

## Staging Environment Checklist

### Pre-Deployment Requirements

**Configuration**:
- [ ] Replace all demo credentials with real staging values
- [ ] Add Shopify staging credentials
- [ ] Generate unique JWT secret for staging
- [ ] Remove .env from git, add .env.example
- [ ] Configure staging-specific CORS origins

**Dependencies**:
- [ ] Add python-dateutil to requirements.txt
- [ ] Run pip install -r requirements.txt
- [ ] Verify all Python packages install successfully

**Database**:
- [ ] Create initial Alembic migration
- [ ] Test migration on fresh database
- [ ] Add CASCADE rules to foreign keys
- [ ] Configure connection pool (pool_size=20)

**Security**:
- [ ] Implement webhook signature verification
- [ ] Add webhook deduplication logic
- [ ] Add rate limiting middleware
- [ ] Add payload size limits (1MB max)
- [ ] Restrict CORS to staging frontend only

**Testing**:
- [ ] Create test Gorgias account (not production)
- [ ] Configure test webhook endpoint
- [ ] Test webhook signature validation
- [ ] Test order fulfillment lookup
- [ ] Test AI draft generation
- [ ] Test duplicate webhook handling
- [ ] Verify internal notes post to Gorgias

---

## Implementation Timeline

### Phase 1: Critical Blockers (2-3 days)
**Cannot deploy without these fixes**

| Task | Effort | Priority |
|------|--------|----------|
| Webhook signature verification | 2h | P0 |
| Replace demo credentials | 30m | P0 |
| Add Shopify configuration | 1h | P0 |
| Add python-dateutil dependency | 5m | P0 |
| Create database migrations | 1h | P0 |
| Add foreign key CASCADE | 30m | P0 |
| Implement webhook deduplication | 3h | P0 |
| Remove .env from git | 30m | P0 |

**Total**: ~8.5 hours

---

### Phase 2: Security Hardening (1-2 days)
**Should fix before staging**

| Task | Effort | Priority |
|------|--------|----------|
| Add rate limiting | 2h | P1 |
| Generate staging JWT secret | 1h | P1 |
| Add payload size limits | 1h | P1 |
| Configure DB connection pool | 30m | P1 |
| Restrict CORS | 15m | P1 |

**Total**: ~4.75 hours

---

### Phase 3: Operational Readiness (2-3 days)
**Recommended before production**

| Task | Effort | Priority |
|------|--------|----------|
| Structured logging | 2h | P2 |
| Live health checks | 1h | P2 |
| Redis failure monitoring | 1h | P2 |
| Customer ID normalization | 2h | P2 |
| Error tracking (Sentry) | 2h | P2 |
| Deployment runbook | 3h | P2 |

**Total**: ~11 hours

---

## Deployment Strategy

### Staging Deployment Plan

1. **Fix Phase 1 issues** (all 8 critical blockers)
2. **Deploy to staging environment**
3. **Configure staging Gorgias webhook**:
   - URL: `https://staging-api.yourdomain.com/webhooks/gorgias/ticket`
   - Secret: Generate with `openssl rand -hex 32`
   - Test events: ticket.created, message.created
4. **Test for 48 hours** with staging Gorgias account
5. **Monitor**:
   - Webhook processing success rate
   - AI draft generation rate
   - Shopify fulfillment lookup success
   - Internal note posting success
   - Error rates in logs

### Success Criteria (Staging)

- [ ] 100% of webhooks authenticated successfully
- [ ] 0 runtime crashes (missing dependencies)
- [ ] >95% webhook processing success rate
- [ ] >90% Shopify fulfillment data retrieval success
- [ ] >90% AI draft generation success (when Quimbi available)
- [ ] >95% Gorgias internal note posting success
- [ ] No duplicate webhook processing observed
- [ ] Health check shows all services connected
- [ ] No security vulnerabilities in staging environment

---

## Risk Assessment

### If Deployed Today (Without Fixes)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Webhook forgery attack | 90% | CRITICAL | Cannot deploy without signature verification |
| All API calls fail (demo creds) | 100% | CRITICAL | Replace credentials first |
| Split shipment feature broken | 100% | HIGH | Add Shopify config before deploy |
| Runtime crash on webhook | 80% | CRITICAL | Add python-dateutil dependency |
| Duplicate processing | 70% | HIGH | Implement deduplication |
| DoS via webhooks | 60% | HIGH | Add rate limiting |
| Secrets exposed in git | 100% | CRITICAL | Remove .env from repository |

**Overall Risk Level**: 🔴 **CRITICAL - DO NOT DEPLOY**

---

## Recommended Next Steps

### Immediate Actions (Today)

1. **Do NOT configure Gorgias webhook yet** - system not ready
2. **Create .env.example** and remove .env from git
3. **Gather credentials**:
   - Real Gorgias API credentials (staging account)
   - Shopify Admin API token for staging
   - Generate new JWT secret
4. **Create task board** with Phase 1 issues

### This Week (Days 1-3)

1. **Fix all 8 critical blockers** (Phase 1)
2. **Test locally** with mock webhooks
3. **Deploy to staging** (Railway/Heroku/etc)
4. **Basic smoke testing**

### Next Week (Days 4-7)

1. **Fix security issues** (Phase 2)
2. **Configure Gorgias staging webhook**
3. **Monitor for 48 hours**
4. **Fix any issues discovered**

### Week 3+ (Production Prep)

1. **Complete Phase 3** (operational readiness)
2. **Load test webhook endpoint**
3. **Create runbook for production deployment**
4. **Deploy to production**

---

## Contact & Resources

**Gorgias API Documentation**: https://developers.gorgias.com/
**Shopify Admin API**: https://shopify.dev/docs/api/admin
**Webhook Security Best Practices**: https://webhooks.fyi/security/hmac

**Questions?** Review full security audit in agent conversation history.

---

**Last Updated**: January 6, 2026
**Next Review**: After Phase 1 completion
**Reviewer**: Claude (Security & Integration Audit)
