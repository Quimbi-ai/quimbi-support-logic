# Customer Support Backend - System Architecture

**Service Name**: `beecommerce-production` (Customer Support Backend)
**Deployment**: `https://beecommerce-production.up.railway.app`
**Repository**: `Quimbi-ai/q.ai-customer-support`
**Purpose**: Customer support automation and agent assistance

---

## Purpose & Role

This backend service serves as the **Customer Support Automation Layer** in the Quimbi ecosystem. It acts as a middleware between customer support platforms (like Gorgias) and the QuimbiBrain AI intelligence backend.

### Primary Functions:

1. **Webhook Processing** - Receive and process support ticket webhooks from external platforms
2. **Context Enrichment** - Gather order, fulfillment, and customer data to enrich support tickets
3. **AI Draft Generation** - Leverage QuimbiBrain to generate contextual response drafts
4. **Agent Assistance** - Provide internal notes and recommendations to human agents
5. **Multi-Warehouse Intelligence** - Detect and explain split shipments across fulfillment locations

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         QUIMBI ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────────┐         │
│  │   Gorgias (CX)   │────────▶│  Customer Support    │         │
│  │  Help Desk       │ Webhook │  Backend (THIS)      │         │
│  │                  │◀────────│ beecommerce-prod     │         │
│  └──────────────────┘         └──────────────────────┘         │
│         ▲                              │                        │
│         │                              │                        │
│         │ Internal Note                │ Intelligence API       │
│         │                              ▼                        │
│         │                     ┌──────────────────────┐         │
│         │                     │   QuimbiBrain API    │         │
│         │                     │ (AI Intelligence)    │         │
│         │                     │ quimbibrainbev10     │         │
│         │                     └──────────────────────┘         │
│         │                              │                        │
│         │                              │                        │
│  ┌──────────────────┐                 │                        │
│  │  Shopify Store   │◀────────────────┘                        │
│  │ (E-commerce)     │  Order/Fulfillment Data                  │
│  └──────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Gorgias (Customer Experience Platform)

**Type**: Inbound webhook, Outbound API
**Purpose**: Receive support ticket events, post internal notes back

#### Webhook Flow:
```
Gorgias Ticket Created/Updated
  ↓
POST /webhooks/gorgias/ticket
  ↓
Extract ticket data (customer, message, order references)
  ↓
Enrich with Shopify + QuimbiBrain data
  ↓
Generate AI draft
  ↓
POST internal note back to Gorgias ticket
```

**Gorgias Events Handled**:
- `ticket.created` - New support ticket
- `message.created` - New message on existing ticket

**Gorgias API Calls Made**:
- `POST /api/tickets/{id}/messages` - Add internal note with AI draft

**Configuration Required**:
```bash
GORGIAS_DOMAIN=lindas
GORGIAS_API_KEY=******
GORGIAS_USERNAME=lindas.quimbiai@proton.me
```

---

### 2. QuimbiBrain (AI Intelligence Backend)

**Type**: Outbound API (RESTful)
**Purpose**: Customer intelligence analysis and AI message generation

#### API Endpoints Used:

**Customer Intelligence**:
```
GET /api/intelligence/customer/{customer_id}
→ Returns customer DNA, archetype, LTV, churn risk
```

**Message Generation**:
```
POST /api/intelligence/generate-message
Body: {
  customer_profile: {...},
  goal: "resolve_support_issue",
  conversation: [...],
  channel: "email",
  tone: "empathetic"
}
→ Returns AI-generated response draft
```

**Configuration Required**:
```bash
QUIMBI_BASE_URL=https://quimbibrainbev10-production.up.railway.app
QUIMBI_API_KEY=******
```

**Why Separate Service?**
QuimbiBrain is the **centralized AI/ML intelligence layer** used across all Quimbi products (CRM, marketing, analytics). This customer support backend is a **specialized application** that consumes QuimbiBrain's intelligence for support-specific workflows.

---

### 3. Shopify (E-commerce Platform)

**Type**: Outbound API (GraphQL)
**Purpose**: Fetch order and fulfillment data for ticket context

#### GraphQL Queries Used:

**Order Lookup**:
```graphql
query {
  order(id: "gid://shopify/Order/123") {
    name
    displayFulfillmentStatus
    fulfillmentOrders {
      assignedLocation { name }
      fulfillments { trackingInfo }
      lineItems { title, quantity }
    }
  }
}
```

**Use Cases**:
- Verify order status mentioned in ticket
- Get tracking numbers for "where's my order" tickets
- Detect split shipments (multiple warehouses)
- Provide fulfillment timeline context

**Configuration Required**:
```bash
SHOPIFY_SHOP_NAME=lindas-electric-quilters
SHOPIFY_ACCESS_TOKEN=shpat_******
```

---

## Core Workflows

### Workflow 1: Support Ticket Processing

**Trigger**: Gorgias webhook received

```python
# 1. Webhook ingestion
POST /webhooks/gorgias/ticket
  ↓
# 2. Extract order number (AI-powered probabilistic matching)
order_number = extract_order_number_from_ticket(ticket_data)
# Checks: custom fields, subject, body text, tags, Shopify integration data
# Uses: date extraction, product matching, fuzzy search
  ↓
# 3. Fetch Shopify fulfillment data (if order found)
fulfillment_data = fetch_shopify_fulfillment(order_number)
# Returns: status, tracking, locations, split shipment detection
  ↓
# 4. Get customer intelligence from QuimbiBrain
customer_profile = quimbi_client.analyze_customer(customer_id)
# Returns: DNA, archetype, LTV, sentiment, preferences
  ↓
# 5. Generate AI draft response
ai_draft = quimbi_client.generate_message(
    customer_profile=customer_profile,
    conversation=ticket_messages,
    fulfillment_context=fulfillment_data
)
  ↓
# 6. Post internal note to Gorgias ticket
internal_note = f"""
🤖 AI-Generated Draft Response:

{ai_draft}

📦 Split Shipment Alert: [if detected]

📋 Fulfillment Context: [order details]
"""
gorgias_client.post_internal_note(ticket_id, internal_note)
  ↓
# 7. Return success response
return {
    "status": "processed",
    "internal_note_posted": true
}
```

**Processing Time**: ~5-6 seconds per ticket

---

### Workflow 2: Multi-Warehouse Split Shipment Detection

**Purpose**: Alert agents when customer's order ships from multiple warehouses

**Detection Logic**:
```python
# Analyze fulfillment orders
fulfillment_orders = order["fulfillmentOrders"]

locations = set()
for fo in fulfillment_orders:
    locations.add(fo["assignedLocation"]["name"])

if len(locations) > 1:
    # SPLIT SHIPMENT DETECTED
    # Generate explanation for agent
```

**Agent Note Example**:
```
📦 Split Shipment Alert:

This order is being fulfilled from multiple warehouses:

Warehouse 1: Linda's Main (Nashville, TN)
- 2x Hobbs Batting Roll
- Tracking: USPS 9400...
- Shipped: Dec 28

Warehouse 2: Overflow Storage (Memphis, TN)
- 1x Quilting Thread Set
- Tracking: UPS 1Z...
- Ships: Dec 31

Customer may receive 2 separate packages on different dates.
```

---

## Service Boundaries

### What This Service DOES:

✅ **Process support ticket webhooks** from platforms like Gorgias
✅ **Extract order information** from ticket content using AI
✅ **Fetch fulfillment data** from Shopify for ticket context
✅ **Call QuimbiBrain** for customer intelligence and AI drafts
✅ **Post internal notes** back to support platform for agents
✅ **Detect split shipments** across multiple warehouses
✅ **Provide agent assistance** with AI-powered recommendations

### What This Service DOES NOT DO:

❌ **Store customer data** - QuimbiBrain owns customer intelligence
❌ **Send messages to customers** - Only internal notes for agents
❌ **Train AI models** - QuimbiBrain handles all ML/AI
❌ **Manage support queues** - Gorgias owns ticket routing
❌ **Process payments** - Shopify handles all transactions
❌ **Auto-respond to customers** - Human agents review and send

---

## Data Flow

### Inbound Data:

**From Gorgias**:
- Ticket ID, subject, status
- Customer name, email
- Message history
- Shopify order integration data

**From Shopify**:
- Order number, line items
- Fulfillment status
- Tracking numbers
- Warehouse locations

**From QuimbiBrain**:
- Customer DNA profile
- Purchase history insights
- Sentiment analysis
- AI-generated message drafts

### Outbound Data:

**To Gorgias**:
- Internal notes with AI drafts
- Fulfillment context
- Split shipment alerts

**To QuimbiBrain**:
- Customer inquiry context
- Message generation requests
- Conversation history

---

## API Endpoints Reference

### Customer Support Webhooks

#### `POST /webhooks/gorgias/ticket`
Process Gorgias ticket webhook

**Request**:
```json
{
  "ticket": {
    "id": 246553453,
    "subject": "Order status inquiry",
    "customer": {
      "email": "customer@example.com",
      "name": "John Doe"
    }
  },
  "message": {
    "body_text": "Where is my order #224055?"
  }
}
```

**Response**:
```json
{
  "status": "processed",
  "ticket_id": 246553453,
  "order_number": 224055,
  "fulfillment_enriched": true,
  "has_split_shipment": false,
  "ai_draft_generated": true,
  "internal_note_posted": true,
  "timestamp": "2025-12-30T22:28:11Z"
}
```

---

#### `GET /webhooks/gorgias/status`
Health check and configuration status

**Response**:
```json
{
  "status": "configured",
  "services": {
    "shopify": "configured",
    "gorgias": "configured",
    "gorgias_api": "connected",
    "quimbi_brain": "connected"
  },
  "features": {
    "fulfillment_tracking": true,
    "split_shipment_detection": true,
    "ai_draft_generation": true,
    "gorgias_posting": true
  }
}
```

---

#### `DELETE /webhooks/gorgias/ticket/{ticket_id}/message/{message_id}`
Delete a message from Gorgias ticket (cleanup)

**Response**:
```json
{
  "status": "deleted",
  "ticket_id": 246553453,
  "message_id": 607029421
}
```

---

## Key Components

### 1. Ticket Fulfillment Enricher
**File**: `app/integrations/ticket_fulfillment_enricher.py`

**Purpose**: Extract order numbers and fetch Shopify fulfillment data

**Key Functions**:
- `extract_order_number_from_ticket()` - AI-powered order matching
- `enrich_ticket_with_fulfillments()` - Fetch Shopify fulfillment data
- `detect_split_shipment()` - Multi-warehouse detection
- `format_fulfillment_for_internal_note()` - Human-readable summary

**Intelligence Features**:
- **Date extraction**: "I ordered on December 11th" → matches order date
- **Product matching**: "batting order" → matches "Hobbs Batting Roll"
- **Status prioritization**: Unfulfilled orders ranked higher than fulfilled
- **Recency scoring**: Recent orders weighted higher

---

### 2. QuimbiBrain Client
**File**: `app/services/quimbi_client.py`

**Purpose**: Interface with QuimbiBrain AI intelligence backend

**Key Methods**:
```python
# Get customer intelligence
customer_profile = await quimbi_client.analyze_customer(customer_id)

# Generate AI message
ai_draft = await quimbi_client.generate_message(
    customer_profile=customer_profile,
    goal="resolve_support_issue",
    conversation=messages,
    tone="empathetic"
)
```

---

### 3. Gorgias Client
**File**: `app/services/gorgias_client.py`

**Purpose**: Interface with Gorgias API for posting notes

**Key Methods**:
```python
# Post internal note (agent-only)
result = await gorgias_client.post_internal_note(
    ticket_id=246553453,
    body_text="🤖 AI Draft: [message]"
)

# Delete message (cleanup)
success = await gorgias_client.delete_message(ticket_id, message_id)

# Health check
healthy = await gorgias_client.health_check()
```

---

### 4. Shopify Fulfillment Service
**File**: `app/integrations/shopify_fulfillment_service.py`

**Purpose**: Fetch order and fulfillment data from Shopify GraphQL API

**Key Functions**:
- `get_order_fulfillment()` - Fetch order details
- `detect_split_shipment()` - Check for multiple warehouses
- `format_tracking_info()` - Format tracking numbers

---

## Environment Configuration

### Required Variables:

```bash
# Gorgias Integration
GORGIAS_DOMAIN=lindas
GORGIAS_API_KEY=******
GORGIAS_USERNAME=lindas.quimbiai@proton.me

# QuimbiBrain AI Backend
QUIMBI_BASE_URL=https://quimbibrainbev10-production.up.railway.app
QUIMBI_API_KEY=******

# Shopify E-commerce
SHOPIFY_SHOP_NAME=lindas-electric-quilters
SHOPIFY_ACCESS_TOKEN=shpat_******

# Application
SECRET_KEY=******
DATABASE_URL=sqlite+aiosqlite:///./test_support.db
REDIS_URL=redis://localhost:6379/0
```

---

## Use Cases

### Use Case 1: "Where's My Order?" Ticket

**Customer Message**: *"I ordered batting on December 11th, has this been shipped?"*

**System Response**:
1. ✅ Extracts order #218874 using AI (date + product matching)
2. ✅ Fetches fulfillment from Shopify → "Partially Fulfilled"
3. ✅ Gets customer profile from QuimbiBrain
4. ✅ Generates empathetic AI draft with tracking info
5. ✅ Posts internal note to Gorgias for agent

**Agent Sees**:
```
🤖 AI-Generated Draft Response:

Hi Lori,

Thank you for reaching out! I can see your Hobbs Heirloom batting
order from December 11th (Order #218874) is currently in transit.

Tracking: USPS 9400111899223617474449
Expected delivery: January 2nd

Let me know if you have any other questions!

📋 Fulfillment Context:

Order #218874
Status: Partially Fulfilled
Warehouse: Linda's Main (Nashville, TN)
```

---

### Use Case 2: Split Shipment Detection

**Customer Message**: *"I only received half my order"*

**System Response**:
1. ✅ Identifies order #224123
2. ✅ Detects 2 fulfillment locations (split shipment)
3. ✅ Generates explanation for agent
4. ✅ Posts internal note with both tracking numbers

**Agent Sees**:
```
🤖 AI-Generated Draft Response:

Hi Sarah,

Your order is being fulfilled from two warehouses, so you'll receive
two separate packages...

📦 Split Shipment Alert:

Package 1 (Delivered Dec 28):
- 3x Thread Spools
- Tracking: USPS 9400...

Package 2 (Arriving Jan 2):
- 1x Quilting Ruler Set
- Tracking: UPS 1Z...
```

---

### Use Case 3: Billing Question (No Order Context)

**Customer Message**: *"I was charged twice for my subscription"*

**System Response**:
1. ✅ No order number found (billing question)
2. ✅ Gets customer profile from QuimbiBrain
3. ✅ Generates AI draft addressing billing concern
4. ✅ Posts internal note without fulfillment context

**Agent Sees**:
```
🤖 AI-Generated Draft Response:

Hi John,

I'm sorry to hear about the duplicate charge. Let me look into this
right away. Can you confirm which payment method was charged twice?

I'll process a refund immediately once verified.

[No fulfillment data - billing issue]
```

---

## Performance & Scalability

**Average Response Time**: 5-6 seconds per webhook
**Concurrent Webhooks**: Async processing (FastAPI)
**Rate Limiting**: None (trusted internal service)
**Caching**: Redis for customer intelligence (15min TTL)

**Bottlenecks**:
- QuimbiBrain AI generation: ~3-4 seconds
- Shopify GraphQL queries: ~1-2 seconds
- Gorgias API posting: ~500ms

---

## Monitoring & Logging

**Logs Include**:
- Webhook received events
- Order number extraction results
- QuimbiBrain API calls
- Gorgias posting success/failure
- Split shipment detections

**Example Log**:
```
INFO: Received Gorgias webhook for ticket 246553453
INFO: Extracted order number: 224055
INFO: Fetching fulfillment data from Shopify...
INFO: Split shipment detected: 2 warehouses
INFO: Calling QuimbiBrain for AI draft generation...
INFO: ✅ Internal note posted successfully to ticket 246553453
```

---

## Deployment

**Platform**: Railway
**Project**: `authentic-comfort`
**Service**: `beecommerce-production`
**Auto-Deploy**: GitHub `main` branch

**Deployment Command**:
```bash
git push origin main
# Railway auto-deploys in ~30-40 seconds
```

**Health Check**:
```bash
curl https://beecommerce-production.up.railway.app/webhooks/gorgias/status
```

---

## For AI Agents & Engineers

### Quick Start Integration:

1. **Webhook Setup** → Configure Gorgias webhook to POST to `/webhooks/gorgias/ticket`
2. **Environment Variables** → Set Gorgias, QuimbiBrain, Shopify credentials
3. **Test Webhook** → Send test ticket, verify internal note appears in Gorgias
4. **Monitor Logs** → Check Railway logs for processing success

### Key Files to Review:

- `app/api/webhooks.py` - Main webhook handlers
- `app/integrations/ticket_fulfillment_enricher.py` - Order extraction logic
- `app/services/quimbi_client.py` - QuimbiBrain integration
- `app/services/gorgias_client.py` - Gorgias API client

### Common Modifications:

**Add new support platform** → Create new webhook handler in `app/api/webhooks.py`
**Change AI prompt** → Modify `quimbi_client.generate_message()` parameters
**Customize internal note format** → Edit note building in webhook handler

---

## Version History

- **v1.0** (Dec 2024) - Initial Gorgias integration with AI drafts
- **v1.1** (Dec 2024) - Added split shipment detection
- **v1.2** (Dec 2024) - Intelligent order matching (AI-powered)
- **v1.3** (Dec 2024) - Internal notes only (removed draft posting)

---

**Last Updated**: December 30, 2024
**Maintained By**: Quimbi Engineering
**Contact**: See repository for current maintainers

🤖 Generated with [Claude Code](https://claude.com/claude-code)
