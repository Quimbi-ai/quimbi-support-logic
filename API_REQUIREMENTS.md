# Quimbi Platform API Requirements for External Teams

**Version:** 1.0
**Last Updated:** 2025-11-24
**Audience:** Frontend developers, application backend developers, Claude Code instances

---

## Overview

Quimbi Platform provides customer intelligence as a service. Your application (Support, Marketing, Sales, Analytics) calls Quimbi APIs to get:
- Customer behavioral analysis (DNA, segments, archetypes)
- ML predictions (churn risk, LTV forecasting)
- AI-generated content (drafts, recommendations, personalized messages)

**Base URL:** `https://platform.quimbi.ai` (or your deployment URL)

---

## Authentication

All API requests require authentication via API key.

### Request Headers

```http
X-API-Key: your-api-key-here
Content-Type: application/json
```

### Getting an API Key

Contact your Quimbi administrator to provision an API key for your tenant.

**Important:** Each company/tenant has their own API key that routes to their isolated database.

---

## Core Endpoints

### 1. Customer Intelligence Analysis

**Endpoint:** `POST /api/intelligence/analyze`

**Purpose:** Get comprehensive behavioral analysis for a customer.

**Request:**
```json
{
  "customer_id": "string (required)",
  "context": {
    "orders": [
      {
        "order_id": "string",
        "total_price": 150.00,
        "order_date": "2024-01-15T10:30:00Z",
        "items": [
          {
            "product_id": "prod_123",
            "product_name": "Premium Quilting Cotton",
            "category": "fabric",
            "quantity": 3,
            "price": 50.00
          }
        ]
      }
    ],
    "interactions": [
      {
        "type": "support_ticket",
        "timestamp": "2024-02-20T14:00:00Z",
        "channel": "email"
      }
    ]
  }
}
```

**Response:**
```json
{
  "customer_id": "cust_12345",
  "archetype": {
    "id": "arch_premium_deal_hunter",
    "level": "L2",
    "segments": {
      "purchase_value": "premium",
      "price_sensitivity": "deal_hunter",
      "shopping_maturity": "established",
      "purchase_frequency": "power_buyer",
      "return_behavior": "careful_buyer",
      "category_affinity": "multi_category",
      "shopping_cadence": "regular",
      "repurchase_behavior": "loyal"
    }
  },
  "behavioral_metrics": {
    "lifetime_value": 892.50,
    "total_orders": 12,
    "avg_order_value": 74.38,
    "days_since_last_purchase": 15,
    "customer_tenure_days": 456
  },
  "predictions": {
    "churn_risk": 0.18,
    "churn_risk_level": "low",
    "ltv_12mo": 450.00
  },
  "communication_guidance": [
    "Customer responds well to value propositions",
    "Frequent shopper - they know the store well",
    "This customer rarely returns - take their concerns seriously"
  ]
}
```

**Use Cases:**
- Enrich ticket views with customer intelligence
- Personalize marketing campaigns
- Prioritize high-value leads in sales

---

### 2. Churn Prediction

**Endpoint:** `POST /api/intelligence/predict/churn`

**Purpose:** Get customer churn risk prediction.

**Request:**
```json
{
  "customer_id": "cust_12345"
}
```

**Response:**
```json
{
  "customer_id": "cust_12345",
  "churn_risk_score": 0.28,
  "risk_level": "medium",
  "factors": [
    {
      "factor": "days_since_last_purchase",
      "value": 45,
      "impact": "high",
      "direction": "increases_risk"
    },
    {
      "factor": "purchase_frequency_decline",
      "value": -0.3,
      "impact": "medium",
      "direction": "increases_risk"
    }
  ],
  "recommendations": [
    "Send re-engagement campaign within 7 days",
    "Offer personalized product recommendations",
    "Consider win-back discount (10-15%)"
  ]
}
```

**Use Cases:**
- Trigger retention campaigns
- Flag at-risk customers in support tickets
- Prioritize outreach in sales

---

### 3. LTV Forecasting

**Endpoint:** `POST /api/intelligence/predict/ltv`

**Purpose:** Forecast customer lifetime value.

**Request:**
```json
{
  "customer_id": "cust_12345",
  "horizon_months": 12
}
```

**Response:**
```json
{
  "customer_id": "cust_12345",
  "horizon_months": 12,
  "forecasted_ltv": 450.00,
  "confidence_interval": {
    "lower": 380.00,
    "upper": 520.00,
    "confidence_level": 0.95
  },
  "current_ltv": 892.50,
  "incremental_ltv": 450.00
}
```

**Use Cases:**
- Customer segmentation in marketing
- ROI calculation for retention efforts
- Sales opportunity scoring

---

### 4. AI Message Generation

**Endpoint:** `POST /api/generation/message`

**Purpose:** Generate personalized message for any context.

**Request:**
```json
{
  "customer_profile": {
    "customer_id": "cust_12345",
    "archetype": {
      "segments": {
        "price_sensitivity": "deal_hunter",
        "shopping_maturity": "new"
      }
    },
    "behavioral_metrics": {
      "lifetime_value": 150.00,
      "total_orders": 2
    }
  },
  "context": {
    "goal": "resolve_support_issue",
    "channel": "email",
    "conversation": [
      {
        "from": "customer",
        "content": "I'm making my first quilt and overwhelmed by batting options. What do you recommend for a baby quilt?"
      },
      {
        "from": "agent",
        "content": "Hi! Let me help you with that."
      }
    ],
    "constraints": {
      "tone": "empathetic",
      "length": "medium"
    }
  }
}
```

**Response:**
```json
{
  "message": "For a baby quilt that will be washed frequently, I recommend Warm & Natural 100% cotton batting. It's an excellent choice for beginners because it's machine washable and dryable, pre-shrunk so it won't distort after washing, and soft and lightweight perfect for baby quilts.\n\nThe 100% cotton composition makes it breathable and gentle for infants. For a baby quilt, I suggest getting the crib size (45\" x 60\"), which will give you some extra working room.\n\nWould you like some tips on preparing the batting before quilting?",
  "tone": "empathetic",
  "channel": "email",
  "personalization_applied": [
    "Adjusted for beginner (shopping_maturity: new)",
    "Avoided jargon",
    "Provided detailed explanations"
  ]
}
```

**Supported Goals:**
- `resolve_support_issue` - Customer support response
- `nurture_lead` - Marketing nurture email
- `upsell` - Product recommendation for upsell
- `win_back` - Re-engagement campaign
- `generic_communication` - General message

**Supported Channels:**
- `email`
- `sms`
- `chat`
- `phone_script`

**Use Cases:**
- AI drafts in support tickets
- Personalized marketing emails
- Sales outreach templates
- Chatbot responses

---

### 5. Recommended Actions

**Endpoint:** `POST /api/generation/actions`

**Purpose:** Get AI-recommended next best actions for any scenario.

**Request:**
```json
{
  "customer_profile": {
    "customer_id": "cust_12345",
    "churn_risk": 0.65,
    "lifetime_value": 1200.00
  },
  "scenario": "support_ticket",
  "context": {
    "ticket": {
      "subject": "Order arrived damaged",
      "priority": "high",
      "channel": "email"
    }
  }
}
```

**Response:**
```json
{
  "actions": [
    {
      "action": "Send immediate replacement shipment with expedited shipping",
      "priority": 1,
      "reasoning": "High-value customer (LTV $1200) with elevated churn risk (65%). Quick resolution critical for retention.",
      "estimated_impact": {
        "retention_probability": 0.85,
        "revenue_at_risk": 780.00
      }
    },
    {
      "action": "Include handwritten apology note and small gift with replacement",
      "priority": 2,
      "reasoning": "Personal touch reinforces value to high-LTV customer"
    },
    {
      "action": "Follow up 2 days after delivery to ensure satisfaction",
      "priority": 3,
      "reasoning": "Proactive follow-up shows commitment to service quality"
    }
  ],
  "warnings": [
    "Customer has high churn risk - handle with extra care",
    "Revenue at risk: $780 (65% churn × $1200 LTV)"
  ],
  "talking_points": [
    "Apologize sincerely for the inconvenience",
    "Emphasize commitment to quality",
    "Offer direct contact for any future concerns"
  ]
}
```

**Supported Scenarios:**
- `support_ticket`
- `sales_opportunity`
- `marketing_campaign`
- `retention_risk`

**Use Cases:**
- Guide support agents on ticket handling
- Suggest next steps in sales process
- Recommend campaign actions in marketing

---

## Data Ingestion (Optional)

If you're building an application that generates behavioral data, you can push it to Quimbi for analysis.

### Ingest Orders

**Endpoint:** `POST /api/data/ingest_orders`

**Request:**
```json
{
  "source": "shopify",
  "orders": [
    {
      "customer_id": "cust_12345",
      "order_id": "order_789",
      "order_date": "2024-03-15T14:30:00Z",
      "total_price": 125.50,
      "items": [
        {
          "product_id": "prod_456",
          "product_name": "Cotton Batting - Queen Size",
          "category": "batting",
          "quantity": 1,
          "price": 45.00
        },
        {
          "product_id": "prod_789",
          "product_name": "Quilting Thread Set",
          "category": "notions",
          "quantity": 3,
          "price": 26.83
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "ingested_count": 1,
  "status": "success",
  "customer_profiles_updated": ["cust_12345"]
}
```

### Ingest Interactions

**Endpoint:** `POST /api/data/ingest_interactions`

**Request:**
```json
{
  "source": "support_app",
  "interactions": [
    {
      "customer_id": "cust_12345",
      "interaction_type": "support_ticket",
      "timestamp": "2024-03-20T10:15:00Z",
      "channel": "email",
      "metadata": {
        "ticket_id": "T-123",
        "subject": "Question about batting",
        "resolved": true,
        "resolution_time_hours": 2.5
      }
    }
  ]
}
```

**Response:**
```json
{
  "ingested_count": 1,
  "status": "success"
}
```

---

## Industry Benchmarks (Optional)

Compare your metrics to anonymized cross-company benchmarks.

### Get Industry Benchmarks

**Endpoint:** `GET /api/insights/benchmarks/{industry}`

**Parameters:**
- `industry` - Industry identifier (e.g., "retail", "ecommerce", "saas")

**Response:**
```json
{
  "industry": "retail",
  "based_on_companies": 8,
  "avg_ltv": 425.00,
  "avg_churn": 0.265,
  "ltv_percentiles": {
    "p25": 280.00,
    "p50": 420.00,
    "p75": 580.00
  },
  "churn_percentiles": {
    "p25": 0.18,
    "p50": 0.26,
    "p75": 0.34
  }
}
```

### Compare Your Position

**Endpoint:** `GET /api/insights/my-position`

**Response:**
```json
{
  "my_metrics": {
    "churn": 0.22,
    "ltv": 450.00
  },
  "industry_benchmarks": {
    "avg_churn": 0.265,
    "avg_ltv": 425.00
  },
  "comparison": {
    "churn_vs_industry": "better",
    "ltv_percentile": "top_50%"
  }
}
```

---

## Error Handling

All errors follow standard HTTP status codes with JSON error responses.

### Error Response Format

```json
{
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "Customer with ID 'cust_99999' not found",
    "details": {
      "customer_id": "cust_99999"
    }
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 401 | `INVALID_API_KEY` | API key is missing or invalid |
| 403 | `INSUFFICIENT_PERMISSIONS` | API key lacks required permissions |
| 404 | `CUSTOMER_NOT_FOUND` | Customer ID doesn't exist |
| 404 | `ENDPOINT_NOT_FOUND` | Invalid API endpoint |
| 422 | `VALIDATION_ERROR` | Request body validation failed |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests (see rate limits) |
| 500 | `INTERNAL_ERROR` | Server error (contact support) |
| 503 | `SERVICE_UNAVAILABLE` | Temporary outage (retry with backoff) |

### Retry Logic

Implement exponential backoff for transient errors (500, 503):

```javascript
async function callQuimbiWithRetry(endpoint, data, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        return await response.json();
      }

      // Retry on 5xx errors
      if (response.status >= 500 && attempt < maxRetries - 1) {
        const delay = Math.pow(2, attempt) * 1000; // 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      // Don't retry 4xx errors
      throw new Error(`API error: ${response.status}`);

    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
    }
  }
}
```

---

## Rate Limits

**Current Limits:**
- 100 requests per minute per API key
- 1000 requests per hour per API key

**Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1615478400
```

When rate limit is exceeded, you'll receive:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 60 seconds."
  }
}
```

---

## Caching Recommendations

### Client-Side Caching

**Customer Intelligence:**
- Cache TTL: 5-15 minutes
- Invalidate on: Customer places order, submits ticket, updates profile

**Churn Predictions:**
- Cache TTL: 1 hour
- Invalidate on: Customer activity (order, interaction)

**AI-Generated Messages:**
- Cache TTL: Do NOT cache (context-dependent)
- Generate fresh for each conversation update

### Example Caching Strategy

```javascript
const cache = new Map();

async function getCustomerIntelligence(customerId) {
  const cacheKey = `customer_intel:${customerId}`;
  const cached = cache.get(cacheKey);

  // Check if cached and not expired (15 min TTL)
  if (cached && Date.now() - cached.timestamp < 15 * 60 * 1000) {
    return cached.data;
  }

  // Call API
  const data = await callQuimbi('/api/intelligence/analyze', {
    customer_id: customerId,
    context: {}
  });

  // Cache result
  cache.set(cacheKey, {
    data: data,
    timestamp: Date.now()
  });

  return data;
}
```

---

## SDK Examples

### JavaScript/TypeScript

```typescript
// quimbi-client.ts

interface QuimbiConfig {
  baseUrl: string;
  apiKey: string;
}

class QuimbiClient {
  private baseUrl: string;
  private apiKey: string;

  constructor(config: QuimbiConfig) {
    this.baseUrl = config.baseUrl;
    this.apiKey = config.apiKey;
  }

  async analyzeCustomer(customerId: string, context?: any) {
    const response = await fetch(`${this.baseUrl}/api/intelligence/analyze`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        customer_id: customerId,
        context: context || {}
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Quimbi API Error: ${error.error.message}`);
    }

    return await response.json();
  }

  async generateMessage(customerProfile: any, context: any) {
    const response = await fetch(`${this.baseUrl}/api/generation/message`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        customer_profile: customerProfile,
        context: context
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Quimbi API Error: ${error.error.message}`);
    }

    return await response.json();
  }

  async predictChurn(customerId: string) {
    const response = await fetch(`${this.baseUrl}/api/intelligence/predict/churn`, {
      method: 'POST',
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ customer_id: customerId })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Quimbi API Error: ${error.error.message}`);
    }

    return await response.json();
  }
}

// Usage
const quimbi = new QuimbiClient({
  baseUrl: 'https://platform.quimbi.ai',
  apiKey: process.env.QUIMBI_API_KEY
});

// In your support ticket view
const customerIntel = await quimbi.analyzeCustomer('cust_12345');
const aiDraft = await quimbi.generateMessage(
  customerIntel,
  {
    goal: 'resolve_support_issue',
    conversation: ticketMessages
  }
);
```

### Python

```python
# quimbi_client.py

import httpx
from typing import Dict, Any, Optional

class QuimbiClient:
    """Client for Quimbi Platform API"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(
            base_url=base_url,
            headers={'X-API-Key': api_key},
            timeout=30.0
        )

    async def analyze_customer(
        self,
        customer_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get customer intelligence."""
        response = await self.http_client.post(
            '/api/intelligence/analyze',
            json={'customer_id': customer_id, 'context': context or {}}
        )
        response.raise_for_status()
        return response.json()

    async def generate_message(
        self,
        customer_profile: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate AI message."""
        response = await self.http_client.post(
            '/api/generation/message',
            json={
                'customer_profile': customer_profile,
                'context': context
            }
        )
        response.raise_for_status()
        return response.json()

    async def predict_churn(self, customer_id: str) -> Dict[str, Any]:
        """Predict customer churn risk."""
        response = await self.http_client.post(
            '/api/intelligence/predict/churn',
            json={'customer_id': customer_id}
        )
        response.raise_for_status()
        return response.json()


# Usage
from quimbi_client import QuimbiClient

quimbi = QuimbiClient(
    base_url='https://platform.quimbi.ai',
    api_key=os.getenv('QUIMBI_API_KEY')
)

# In your support ticket endpoint
customer_intel = await quimbi.analyze_customer('cust_12345')
ai_draft = await quimbi.generate_message(
    customer_profile=customer_intel,
    context={
        'goal': 'resolve_support_issue',
        'conversation': ticket_messages
    }
)
```

---

## Testing

### Test API Key

Contact your administrator for a test API key with access to sample data.

### Sample Customer IDs

Use these customer IDs for testing (available in all tenant databases):

- `test_customer_low_ltv` - Low-value customer, high churn risk
- `test_customer_high_ltv` - High-value customer, low churn risk
- `test_customer_new` - New customer, no purchase history

### Example Test Request

```bash
curl -X POST https://platform.quimbi.ai/api/intelligence/analyze \
  -H "X-API-Key: test_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_customer_high_ltv",
    "context": {}
  }'
```

---

## Support

**Documentation:** https://docs.quimbi.ai
**API Status:** https://status.quimbi.ai
**Support Email:** api-support@quimbi.ai
**Slack Channel:** #quimbi-api-support (for partners)

---

## Versioning

Current version: **v1**

All endpoints are prefixed with `/api/` and are versioned implicitly. Breaking changes will be announced 60 days in advance with migration guides.

---

## Changelog

### 2025-11-24 - v1.0 Initial Release
- Customer intelligence analysis
- Churn prediction
- LTV forecasting
- AI message generation
- Recommended actions
- Industry benchmarks
