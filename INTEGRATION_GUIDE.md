# Quimbi Platform Integration Guide for Application Developers

**Audience:** Developers building applications (Support, Marketing, Sales) that integrate with Quimbi Platform
**Goal:** Get your application integrated with Quimbi in one day

---

## Quick Start (30 minutes)

### Step 1: Get Credentials (5 min)

1. Contact Quimbi administrator for:
   - **API Key** (e.g., `qpk_live_abc123xyz`)
   - **Base URL** (e.g., `https://platform.quimbi.ai`)
   - **Tenant ID** (e.g., `linda_quilting`)

2. Add to your environment variables:
```bash
QUIMBI_API_KEY=qpk_live_abc123xyz
QUIMBI_BASE_URL=https://platform.quimbi.ai
```

### Step 2: Test Connection (5 min)

```bash
# Test API connection
curl -X POST $QUIMBI_BASE_URL/api/intelligence/analyze \
  -H "X-API-Key: $QUIMBI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_customer_high_ltv",
    "context": {}
  }'

# Should return customer intelligence JSON
```

### Step 3: Install Client Library (5 min)

**JavaScript/TypeScript:**
```bash
npm install @quimbi/platform-client
# OR copy the client from API_REQUIREMENTS.md
```

**Python:**
```bash
pip install quimbi-platform-client
# OR copy the client from API_REQUIREMENTS.md
```

### Step 4: First Integration (15 min)

**Add customer intelligence to your ticket view:**

```typescript
// In your ticket detail endpoint/component

import { QuimbiClient } from '@quimbi/platform-client';

const quimbi = new QuimbiClient({
  baseUrl: process.env.QUIMBI_BASE_URL,
  apiKey: process.env.QUIMBI_API_KEY
});

async function getTicketDetails(ticketId: string) {
  // 1. Fetch ticket from your database
  const ticket = await db.tickets.findById(ticketId);

  // 2. Get customer intelligence from Quimbi
  const customerIntel = await quimbi.analyzeCustomer(ticket.customerId);

  // 3. Return enriched response
  return {
    ticket: ticket,
    customer: {
      dna: customerIntel.archetype,
      churnRisk: customerIntel.predictions.churn_risk,
      ltv: customerIntel.behavioral_metrics.lifetime_value,
      communicationGuidance: customerIntel.communication_guidance
    }
  };
}
```

**Done!** You now have customer intelligence in your ticket view.

---

## Common Integration Patterns

### Pattern 1: Enrich Customer Views

**Use Case:** Show customer DNA in support tickets, sales leads, marketing profiles

**Implementation:**
```typescript
// Support App: Ticket Detail Component
async function loadTicket(ticketId: string) {
  const ticket = await fetchTicket(ticketId);

  // Call Quimbi for customer intelligence
  const intel = await quimbi.analyzeCustomer(ticket.customerId, {
    orders: await getRecentOrders(ticket.customerId),
    interactions: await getRecentInteractions(ticket.customerId)
  });

  return {
    ...ticket,
    customerDNA: intel.archetype.segments,
    churnRisk: intel.predictions.churn_risk,
    ltv: intel.behavioral_metrics.lifetime_value,
    howToTalk: intel.communication_guidance
  };
}
```

**UI Display:**
```tsx
// React component example
function CustomerIntelligenceCard({ intel }) {
  return (
    <div className="customer-dna">
      <h3>Customer Intelligence</h3>

      <div className="archetype">
        <span className="label">Archetype:</span>
        <span>{intel.archetype.segments.purchase_value}</span>
        <span>{intel.archetype.segments.price_sensitivity}</span>
      </div>

      <div className="metrics">
        <div className="metric">
          <span className="label">LTV:</span>
          <span className="value">${intel.behavioral_metrics.lifetime_value}</span>
        </div>
        <div className="metric">
          <span className="label">Churn Risk:</span>
          <span className={`value risk-${intel.predictions.churn_risk_level}`}>
            {(intel.predictions.churn_risk * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="guidance">
        <h4>How to Talk to This Customer:</h4>
        <ul>
          {intel.communication_guidance.map(tip => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

---

### Pattern 2: AI Draft Generation

**Use Case:** Generate AI-powered response drafts in support tickets

**Implementation:**
```typescript
async function generateTicketDraft(ticketId: string) {
  const ticket = await fetchTicket(ticketId);

  // Get customer intelligence first
  const customerIntel = await quimbi.analyzeCustomer(ticket.customerId);

  // Generate AI draft
  const draft = await quimbi.generateMessage(
    customerIntel,
    {
      goal: 'resolve_support_issue',
      channel: ticket.channel,
      conversation: ticket.messages.map(m => ({
        from: m.fromAgent ? 'agent' : 'customer',
        content: m.content
      })),
      constraints: {
        tone: 'empathetic',
        length: 'medium'
      }
    }
  );

  return {
    draftMessage: draft.message,
    personalizationApplied: draft.personalization_applied
  };
}
```

**UI Integration:**
```tsx
function TicketReplyBox({ ticketId }) {
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);

  async function generateDraft() {
    setLoading(true);
    const response = await fetch(`/api/tickets/${ticketId}/ai-draft`);
    const data = await response.json();
    setDraft(data.draftMessage);
    setLoading(false);
  }

  return (
    <div className="reply-box">
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Type your response or click 'Generate AI Draft'"
      />
      <button onClick={generateDraft} disabled={loading}>
        {loading ? 'Generating...' : '✨ Generate AI Draft'}
      </button>
    </div>
  );
}
```

---

### Pattern 3: Smart Prioritization

**Use Case:** Prioritize tickets/leads/campaigns based on customer value and churn risk

**Implementation:**
```typescript
async function getTicketQueue(agentId: string) {
  // Fetch assigned tickets
  const tickets = await db.tickets.findByAgent(agentId);

  // Enrich with Quimbi intelligence
  const enrichedTickets = await Promise.all(
    tickets.map(async (ticket) => {
      const intel = await quimbi.analyzeCustomer(ticket.customerId);

      // Calculate priority score
      const priorityScore = calculatePriority(ticket, intel);

      return {
        ...ticket,
        customerIntel: intel,
        priorityScore: priorityScore
      };
    })
  );

  // Sort by priority
  return enrichedTickets.sort((a, b) => b.priorityScore - a.priorityScore);
}

function calculatePriority(ticket: Ticket, intel: CustomerIntel) {
  let score = 0;

  // Base priority from ticket
  const priorityMap = { urgent: 100, high: 75, normal: 50, low: 25 };
  score += priorityMap[ticket.priority] || 50;

  // Boost for high LTV customers
  if (intel.behavioral_metrics.lifetime_value > 1000) {
    score += 50;
  } else if (intel.behavioral_metrics.lifetime_value > 500) {
    score += 25;
  }

  // Boost for high churn risk
  if (intel.predictions.churn_risk > 0.7) {
    score += 40;
  } else if (intel.predictions.churn_risk > 0.5) {
    score += 20;
  }

  // Boost for time-sensitive
  const hoursSinceCreated = (Date.now() - ticket.createdAt) / (1000 * 60 * 60);
  if (hoursSinceCreated > 24) score += 30;
  if (hoursSinceCreated > 48) score += 50;

  return score;
}
```

---

### Pattern 4: Real-Time Recommendations

**Use Case:** Show recommended next actions to agents/marketers/salespeople

**Implementation:**
```typescript
async function getRecommendedActions(ticketId: string) {
  const ticket = await fetchTicket(ticketId);
  const customerIntel = await quimbi.analyzeCustomer(ticket.customerId);

  const recommendations = await quimbi.recommendActions(
    customerIntel,
    'support_ticket',
    {
      ticket: {
        subject: ticket.subject,
        priority: ticket.priority,
        channel: ticket.channel,
        messages: ticket.messages
      }
    }
  );

  return recommendations;
}
```

**UI Display:**
```tsx
function RecommendedActions({ ticketId }) {
  const [actions, setActions] = useState(null);

  useEffect(() => {
    loadActions();
  }, [ticketId]);

  async function loadActions() {
    const data = await fetch(`/api/tickets/${ticketId}/recommendations`);
    setActions(await data.json());
  }

  if (!actions) return <div>Loading recommendations...</div>;

  return (
    <div className="recommended-actions">
      <h3>🎯 Recommended Actions</h3>

      {actions.warnings.length > 0 && (
        <div className="warnings">
          {actions.warnings.map(warning => (
            <div className="warning" key={warning}>⚠️ {warning}</div>
          ))}
        </div>
      )}

      <ul className="actions-list">
        {actions.actions.map(action => (
          <li key={action.action} className={`priority-${action.priority}`}>
            <div className="action-text">{action.action}</div>
            <div className="reasoning">{action.reasoning}</div>
            {action.estimated_impact && (
              <div className="impact">
                Retention: {(action.estimated_impact.retention_probability * 100).toFixed(0)}%
                {action.estimated_impact.revenue_at_risk > 0 && (
                  <span> | At Risk: ${action.estimated_impact.revenue_at_risk}</span>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>

      <div className="talking-points">
        <h4>💬 Talking Points:</h4>
        <ul>
          {actions.talking_points.map(point => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

---

### Pattern 5: Batch Processing

**Use Case:** Enrich marketing campaigns with customer intelligence for segmentation

**Implementation:**
```typescript
async function enrichCampaignAudience(campaignId: string) {
  const campaign = await db.campaigns.findById(campaignId);
  const customerIds = campaign.targetCustomers;

  // Batch fetch intelligence (with rate limiting)
  const batchSize = 10;
  const enrichedCustomers = [];

  for (let i = 0; i < customerIds.length; i += batchSize) {
    const batch = customerIds.slice(i, i + batchSize);

    const batchResults = await Promise.all(
      batch.map(customerId => quimbi.analyzeCustomer(customerId))
    );

    enrichedCustomers.push(...batchResults);

    // Respect rate limits (100/min)
    if (i + batchSize < customerIds.length) {
      await sleep(600); // 600ms between batches = ~100 requests/min
    }
  }

  // Segment by archetype
  const segments = groupBy(enrichedCustomers, c => c.archetype.id);

  return {
    campaignId,
    totalCustomers: customerIds.length,
    segments: Object.entries(segments).map(([archetype, customers]) => ({
      archetype,
      count: customers.length,
      avgLtv: avg(customers.map(c => c.behavioral_metrics.lifetime_value)),
      avgChurnRisk: avg(customers.map(c => c.predictions.churn_risk))
    }))
  };
}

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

---

## Best Practices

### 1. Caching Strategy

**Always cache customer intelligence:**

```typescript
// In-memory cache (for single-instance apps)
const cache = new Map<string, { data: any, timestamp: number }>();

async function getCachedCustomerIntel(customerId: string) {
  const cacheKey = `customer_intel:${customerId}`;
  const cached = cache.get(cacheKey);

  // Cache TTL: 15 minutes
  if (cached && Date.now() - cached.timestamp < 15 * 60 * 1000) {
    return cached.data;
  }

  const intel = await quimbi.analyzeCustomer(customerId);

  cache.set(cacheKey, {
    data: intel,
    timestamp: Date.now()
  });

  return intel;
}
```

**Redis cache (for multi-instance apps):**

```typescript
import Redis from 'ioredis';
const redis = new Redis();

async function getCachedCustomerIntel(customerId: string) {
  const cacheKey = `customer_intel:${customerId}`;

  // Try cache first
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // Call Quimbi
  const intel = await quimbi.analyzeCustomer(customerId);

  // Cache for 15 minutes
  await redis.setex(cacheKey, 900, JSON.stringify(intel));

  return intel;
}
```

### 2. Error Handling

**Always handle Quimbi errors gracefully:**

```typescript
async function getCustomerIntelWithFallback(customerId: string) {
  try {
    return await quimbi.analyzeCustomer(customerId);
  } catch (error) {
    console.error('Quimbi API error:', error);

    // Return fallback data so your app still works
    return {
      customer_id: customerId,
      archetype: { segments: {} },
      behavioral_metrics: {
        lifetime_value: 0,
        total_orders: 0
      },
      predictions: {
        churn_risk: 0.5, // Neutral default
        churn_risk_level: 'unknown'
      },
      communication_guidance: []
    };
  }
}
```

### 3. Background Jobs

**For non-real-time use cases, use background jobs:**

```typescript
// Queue job when ticket is created
async function createTicket(ticketData: CreateTicketData) {
  const ticket = await db.tickets.create(ticketData);

  // Queue background job to fetch intelligence
  await jobQueue.add('enrich-ticket', {
    ticketId: ticket.id,
    customerId: ticket.customerId
  });

  return ticket;
}

// Background worker
jobQueue.process('enrich-ticket', async (job) => {
  const { ticketId, customerId } = job.data;

  const intel = await quimbi.analyzeCustomer(customerId);

  await db.tickets.update(ticketId, {
    customerIntel: intel
  });
});
```

### 4. Incremental Adoption

**Don't integrate everything at once:**

**Week 1:** Add customer intelligence to ticket detail view (read-only display)
**Week 2:** Add AI draft generation button
**Week 3:** Add smart queue ordering
**Week 4:** Add recommended actions panel

### 5. User Feedback Loop

**Track what features agents/users actually use:**

```typescript
// Track when AI draft is used
async function sendAiDraft(ticketId: string) {
  await analytics.track('ai_draft_sent', {
    ticketId,
    timestamp: new Date()
  });

  // Later: analyze which archetypes/scenarios AI drafts work best
}
```

---

## Troubleshooting

### Issue: "Invalid API Key"

**Problem:** 401 error with `INVALID_API_KEY`

**Solutions:**
1. Check environment variable is set correctly
2. Verify API key hasn't expired
3. Ensure you're using correct base URL (production vs staging)
4. Contact admin to regenerate key

---

### Issue: "Customer Not Found"

**Problem:** 404 error with `CUSTOMER_NOT_FOUND`

**Solutions:**
1. Verify customer exists in Quimbi database
2. Check if you need to sync customer data first via `/api/data/ingest_orders`
3. Ensure you're using correct customer ID format

---

### Issue: Slow Response Times

**Problem:** API calls taking > 1 second

**Solutions:**
1. **Add caching** (see caching strategy above)
2. **Use background jobs** for non-real-time needs
3. **Parallel calls:** Fetch multiple customers in parallel
4. **Reduce context size:** Only send recent orders, not entire history

```typescript
// Bad: Sending entire order history
const intel = await quimbi.analyzeCustomer(customerId, {
  orders: await getAllOrders(customerId) // Could be 1000+ orders
});

// Good: Send recent orders only
const intel = await quimbi.analyzeCustomer(customerId, {
  orders: await getRecentOrders(customerId, { limit: 20 })
});
```

---

### Issue: Rate Limit Exceeded

**Problem:** 429 error with `RATE_LIMIT_EXCEEDED`

**Solutions:**
1. **Add rate limiting in your app:**

```typescript
import Bottleneck from 'bottleneck';

const limiter = new Bottleneck({
  maxConcurrent: 10,
  minTime: 600 // 100 requests per minute
});

const quimbiWithRateLimit = {
  analyzeCustomer: (customerId: string) =>
    limiter.schedule(() => quimbi.analyzeCustomer(customerId))
};
```

2. **Cache more aggressively** to reduce API calls
3. **Contact admin** to increase rate limits if needed

---

## Testing Your Integration

### Unit Tests

**Mock Quimbi responses:**

```typescript
// __tests__/ticket-service.test.ts

import { QuimbiClient } from '@quimbi/platform-client';

jest.mock('@quimbi/platform-client');

describe('Ticket Service', () => {
  beforeEach(() => {
    (QuimbiClient.prototype.analyzeCustomer as jest.Mock).mockResolvedValue({
      customer_id: 'test123',
      archetype: {
        segments: {
          purchase_value: 'premium',
          price_sensitivity: 'deal_hunter'
        }
      },
      behavioral_metrics: {
        lifetime_value: 1200.00,
        total_orders: 15
      },
      predictions: {
        churn_risk: 0.25,
        churn_risk_level: 'low'
      }
    });
  });

  it('should enrich ticket with customer intelligence', async () => {
    const ticket = await getTicketDetails('ticket123');

    expect(ticket.customer.ltv).toBe(1200.00);
    expect(ticket.customer.churnRisk).toBe(0.25);
  });
});
```

### Integration Tests

**Test against Quimbi staging environment:**

```typescript
// __tests__/integration/quimbi.test.ts

import { QuimbiClient } from '@quimbi/platform-client';

describe('Quimbi Integration', () => {
  const quimbi = new QuimbiClient({
    baseUrl: process.env.QUIMBI_STAGING_URL,
    apiKey: process.env.QUIMBI_TEST_API_KEY
  });

  it('should fetch customer intelligence', async () => {
    const intel = await quimbi.analyzeCustomer('test_customer_high_ltv');

    expect(intel.customer_id).toBe('test_customer_high_ltv');
    expect(intel.archetype).toBeDefined();
    expect(intel.behavioral_metrics.lifetime_value).toBeGreaterThan(0);
  });
});
```

---

## Example: Complete Support App Integration

**File: `src/services/quimbi.service.ts`**

```typescript
import { QuimbiClient } from '@quimbi/platform-client';
import Redis from 'ioredis';

const redis = new Redis();
const quimbi = new QuimbiClient({
  baseUrl: process.env.QUIMBI_BASE_URL!,
  apiKey: process.env.QUIMBI_API_KEY!
});

export async function getCustomerIntelligence(customerId: string) {
  const cacheKey = `customer_intel:${customerId}`;

  // Try cache
  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);

  // Fetch from Quimbi
  try {
    const intel = await quimbi.analyzeCustomer(customerId);
    await redis.setex(cacheKey, 900, JSON.stringify(intel)); // 15 min TTL
    return intel;
  } catch (error) {
    console.error('Quimbi error:', error);
    return null; // Graceful degradation
  }
}

export async function generateTicketDraft(
  customerId: string,
  messages: Message[]
) {
  const customerIntel = await getCustomerIntelligence(customerId);

  if (!customerIntel) {
    throw new Error('Cannot generate draft without customer intelligence');
  }

  return await quimbi.generateMessage(customerIntel, {
    goal: 'resolve_support_issue',
    channel: 'email',
    conversation: messages.map(m => ({
      from: m.fromAgent ? 'agent' : 'customer',
      content: m.content
    })),
    constraints: { tone: 'empathetic', length: 'medium' }
  });
}
```

**File: `src/api/tickets.controller.ts`**

```typescript
import { getCustomerIntelligence, generateTicketDraft } from '../services/quimbi.service';

export async function getTicket(req, res) {
  const { ticketId } = req.params;

  const ticket = await db.tickets.findById(ticketId);
  const customerIntel = await getCustomerIntelligence(ticket.customerId);

  res.json({
    ticket,
    customer: {
      dna: customerIntel?.archetype.segments,
      churnRisk: customerIntel?.predictions.churn_risk,
      ltv: customerIntel?.behavioral_metrics.lifetime_value,
      guidance: customerIntel?.communication_guidance
    }
  });
}

export async function getAiDraft(req, res) {
  const { ticketId } = req.params;

  const ticket = await db.tickets.findById(ticketId);
  const messages = await db.messages.findByTicket(ticketId);

  const draft = await generateTicketDraft(ticket.customerId, messages);

  res.json({ draft: draft.message });
}
```

---

## Next Steps

1. **Read API Requirements:** See [API_REQUIREMENTS.md](./API_REQUIREMENTS.md) for complete endpoint docs
2. **Get Credentials:** Contact admin for API key and base URL
3. **Start Small:** Integrate one feature (customer intel in ticket view)
4. **Add Features Incrementally:** AI drafts → smart ordering → recommendations
5. **Monitor Usage:** Track API calls, response times, error rates
6. **Provide Feedback:** Let Quimbi team know what works and what doesn't

---

## Resources

- **API Reference:** [API_REQUIREMENTS.md](./API_REQUIREMENTS.md)
- **Architecture Overview:** [web_structure/PLATFORM_ARCHITECTURE.md](./web_structure/PLATFORM_ARCHITECTURE.md)
- **Support:** api-support@quimbi.ai
- **Status Page:** https://status.quimbi.ai
