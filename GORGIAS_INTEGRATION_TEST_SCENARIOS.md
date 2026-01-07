# Gorgias Integration Test Scenarios

This document demonstrates the end-to-end flow of the Gorgias webhook integration with customer intelligence from the ML clustering system.

## Flow Overview

```
1. Gorgias Webhook → q.ai-customer-support
2. Extract customer_id from ticket
3. Call QuimbiBrain API → quimbi-platform
4. QuimbiBrain looks up customer in database:
   - Fuzzy C-Means cluster memberships (868 behavioral archetypes)
   - Hierarchical clustering segments (13 axes)
   - Customer "thumbprint" (top-2 fuzzy memberships per axis)
5. Return enriched customer profile with:
   - Archetype ID & level
   - Dominant segments across 13 axes
   - Behavioral metrics (LTV, AOV, churn risk)
   - Communication guidance
6. AI generates context-aware response
7. Post internal note to Gorgias ticket

```

---

## Test Scenario 1: Budget-Conscious New Customer with Accidental Charge

### Webhook Payload (from Gorgias)

```json
{
  "ticket": {
    "id": 246402999,
    "subject": "Accidental charge - Contact Us",
    "customer": {
      "id": 510999888,
      "email": "ajax.sori@example.com",
      "firstname": "Ajax",
      "lastname": "Sori",
      "external_id": "8234567890"
    },
    "integrations": {
      "82185": {
        "orders": [{
          "id": 6525999888777,
          "order_number": 224055,
          "name": "#224055",
          "financial_status": "pending",
          "fulfillment_status": "unfulfilled",
          "created_at": "2025-12-29T10:30:00Z",
          "line_items": [
            {
              "title": "Premium Quilting Thread - Set of 12",
              "quantity": 1,
              "price": "29.99"
            }
          ]
        }]
      }
    }
  },
  "message": {
    "id": 606999777,
    "body_text": "i just ordered 1 item and i accidentally selected the additional charge and it says i owe 16 dollars but i dont have the money, it was like 30 dollars and now it wants me to pay 45",
    "subject": "Accidental charge - Contact Us",
    "from_agent": false
  }
}
```

### Customer Intelligence Response (from QuimbiBrain)

**API Call**: `POST /api/intelligence/analyze`

```json
{
  "customer_id": "8234567890",
  "archetype": {
    "id": "arch_budget_conscious_new_shopper",
    "level": "L2",
    "segments": {
      "purchase_value": "budget",
      "price_sensitivity": "highly_deal_oriented",
      "shopping_maturity": "new",
      "purchase_frequency": "first_time",
      "product_diversity": "single_category",
      "brand_loyalty": "exploring",
      "seasonal_behavior": "non_seasonal",
      "cart_behavior": "decisive",
      "return_behavior": "no_history",
      "channel_preference": "mobile_web",
      "weekend_affinity": "weekend_shopper",
      "promotional_responsiveness": "coupon_seeker",
      "cart_abandonment": "low_abandoner"
    }
  },
  "fuzzy_memberships": {
    "price_sensitivity": [
      {"segment": "highly_deal_oriented", "membership": 0.92},
      {"segment": "deal_hunter", "membership": 0.78}
    ],
    "shopping_maturity": [
      {"segment": "new", "membership": 0.95},
      {"segment": "beginner", "membership": 0.45}
    ],
    "purchase_value": [
      {"segment": "budget", "membership": 0.88},
      {"segment": "value", "membership": 0.52}
    ]
  },
  "behavioral_metrics": {
    "lifetime_value": 29.99,
    "total_orders": 1,
    "avg_order_value": 29.99,
    "days_since_last_purchase": 0,
    "customer_tenure_days": 0,
    "total_items_purchased": 1
  },
  "predictions": {
    "churn_risk": 0.72,
    "churn_risk_level": "high",
    "ltv_12mo": 45.00,
    "next_purchase_days": 45,
    "reasoning": "First-time buyer with price sensitivity - high early churn risk until second purchase"
  },
  "communication_guidance": [
    "⚠️ CRITICAL: First-time buyer - this interaction sets the tone for relationship",
    "Price-conscious customer - unexpected charges will cause immediate churn",
    "New to shopping with us - may need extra explanation and reassurance",
    "Mobile shopper - keep responses concise and scannable",
    "High churn risk - resolve immediately and exceed expectations",
    "Avoid upselling - focus 100% on resolving the issue quickly"
  ],
  "risk_factors": [
    {
      "factor": "first_time_buyer",
      "impact": "critical",
      "reasoning": "No relationship established - this ticket will determine if they become a repeat customer"
    },
    {
      "factor": "price_sensitivity_mismatch",
      "impact": "high",
      "reasoning": "Customer expected $30, now seeing $45 - violates their budget constraints"
    },
    {
      "factor": "financial_stress_signals",
      "impact": "high",
      "reasoning": "Explicitly stated 'i dont have the money' - immediate resolution required"
    }
  ]
}
```

### AI-Generated Response

**API Call**: `POST /api/generation/message`

**Request**:
```json
{
  "customer_profile": { /* see above */ },
  "context": {
    "goal": "resolve_support_issue",
    "channel": "email",
    "conversation": [
      {
        "from": "customer",
        "content": "i just ordered 1 item and i accidentally selected the additional charge and it says i owe 16 dollars but i dont have the money, it was like 30 dollars and now it wants me to pay 45"
      }
    ],
    "constraints": {
      "tone": "empathetic",
      "length": "medium"
    }
  }
}
```

**Response**:
```json
{
  "message": "Hi Ajax,\n\nI completely understand your concern - seeing an unexpected $16 charge can be really stressful, especially when you didn't mean to add it.\n\nGood news: I can fix this for you right away. I've cancelled the additional charge on order #224055. You'll only be charged the $29.99 for your Premium Quilting Thread set, exactly as you intended.\n\nYou should see the corrected amount of $29.99 within the next few minutes. If you don't see it update, just reply to this email and I'll take care of it immediately.\n\nThanks for bringing this to our attention, and welcome to our store!\n\nBest,\nCustomer Support Team",
  "tone": "empathetic",
  "channel": "email",
  "personalization_applied": [
    "Addressed financial concern immediately (price_sensitivity: highly_deal_oriented)",
    "Provided immediate resolution without requiring follow-up (shopping_maturity: new)",
    "Kept language simple and direct (mobile_web preference)",
    "Avoided any upselling or cross-selling (high churn risk)",
    "Included warm welcome message (first-time buyer)",
    "Used reassuring tone to build trust (churn_risk: 0.72)"
  ],
  "customer_segment_summary": "🆕 First-time buyer | 💰 Budget-conscious | ⚠️ High churn risk - Handle with care"
}
```

### Internal Note Posted to Gorgias

```
🤖 AI-Generated Draft Response:

Hi Ajax,

I completely understand your concern - seeing an unexpected $16 charge can be really stressful, especially when you didn't mean to add it.

Good news: I can fix this for you right away. I've cancelled the additional charge on order #224055. You'll only be charged the $29.99 for your Premium Quilting Thread set, exactly as you intended.

You should see the corrected amount of $29.99 within the next few minutes. If you don't see it update, just reply to this email and I'll take care of it immediately.

Thanks for bringing this to our attention, and welcome to our store!

Best,
Customer Support Team

---

📊 Customer Intelligence Summary:
🆕 First-time buyer | 💰 Budget-conscious | ⚠️ High churn risk (72%)

Archetype: budget_conscious_new_shopper (L2)
LTV: $29.99 | Orders: 1 | AOV: $29.99

⚠️ CRITICAL CONTEXT:
- First interaction - sets tone for entire relationship
- Explicitly stated financial stress ("i dont have the money")
- Price-sensitive (highly_deal_oriented segment)
- This ticket will determine if they become a repeat customer

Recommended Actions:
1. Resolve immediately - remove the $16 charge
2. Send confirmation email with corrected amount
3. Consider small gesture (5% off next order) to build loyalty
4. DO NOT upsell or cross-sell in this interaction

Revenue at Risk: $45 (12-month LTV forecast)
```

---

## Test Scenario 2: High-Value Established Customer with Fulfillment Question

### Webhook Payload

```json
{
  "ticket": {
    "id": 246402461,
    "subject": "Order status - Contact Us",
    "customer": {
      "id": 510146235,
      "email": "lorilynn26@hotmail.com",
      "firstname": "Lori",
      "lastname": "Westendorf",
      "external_id": "7845123456"
    },
    "integrations": {
      "82185": {
        "orders": [{
          "id": 6525640278271,
          "order_number": 218874,
          "name": "#218874",
          "financial_status": "paid",
          "fulfillment_status": "partial",
          "line_items": [
            {
              "title": "Hobb's Heirloom Batting - 96\" Wide Queen Roll",
              "quantity": 1,
              "price": "89.99"
            }
          ]
        }]
      }
    }
  },
  "message": {
    "id": 606589613,
    "body_text": "I order a roll of Hobb's Heirloom batting on December 11th, has this been shipped? I have no heard anything. Please let me know. Thank you",
    "subject": "Order status - Contact Us",
    "from_agent": false
  }
}
```

### Customer Intelligence Response

```json
{
  "customer_id": "7845123456",
  "archetype": {
    "id": "arch_premium_loyal_enthusiast",
    "level": "L4",
    "segments": {
      "purchase_value": "premium",
      "price_sensitivity": "quality_focused",
      "shopping_maturity": "expert",
      "purchase_frequency": "power_buyer",
      "product_diversity": "multi_category",
      "brand_loyalty": "highly_loyal",
      "seasonal_behavior": "year_round",
      "cart_behavior": "thoughtful",
      "return_behavior": "rarely_returns",
      "channel_preference": "desktop",
      "weekend_affinity": "weekday_shopper",
      "promotional_responsiveness": "brand_driven",
      "cart_abandonment": "low_abandoner"
    }
  },
  "fuzzy_memberships": {
    "price_sensitivity": [
      {"segment": "quality_focused", "membership": 0.89},
      {"segment": "premium_buyer", "membership": 0.76}
    ],
    "shopping_maturity": [
      {"segment": "expert", "membership": 0.94},
      {"segment": "established", "membership": 0.68}
    ],
    "purchase_value": [
      {"segment": "premium", "membership": 0.91},
      {"segment": "high_value", "membership": 0.73}
    ]
  },
  "behavioral_metrics": {
    "lifetime_value": 1847.32,
    "total_orders": 23,
    "avg_order_value": 80.32,
    "days_since_last_purchase": 8,
    "customer_tenure_days": 487,
    "total_items_purchased": 67
  },
  "predictions": {
    "churn_risk": 0.08,
    "churn_risk_level": "low",
    "ltv_12mo": 890.00,
    "next_purchase_days": 21,
    "reasoning": "Highly loyal power buyer with consistent purchasing pattern"
  },
  "communication_guidance": [
    "💎 VIP Customer - high lifetime value ($1,847) with excellent retention",
    "Expert shopper - knows products well, keep explanations professional",
    "Quality-focused - emphasize product care and shipping protection",
    "Power buyer - likely has other orders in progress, check for cross-sell opportunities",
    "Rarely contacts support - when they do, it's important to them",
    "Desktop user - detailed tracking info and links are welcome"
  ],
  "risk_factors": [
    {
      "factor": "shipping_delay_concern",
      "impact": "medium",
      "reasoning": "18 days since order - customer expecting delivery by now"
    },
    {
      "factor": "communication_gap",
      "impact": "low",
      "reasoning": "Customer states 'no heard anything' - may be missing tracking emails"
    }
  ]
}
```

### AI-Generated Response

```json
{
  "message": "Hi Lori,\n\nThank you for reaching out about order #218874!\n\nI can see your Hobb's Heirloom Batting (96\" Queen Roll) was ordered on December 11th. This is a premium item that ships directly from our specialty warehouse to ensure it arrives in perfect condition.\n\nGood news: Your order shipped on December 15th via USPS Priority Mail. Here's your tracking information:\n\nTracking #: 9400111899562847123456\nEstimated Delivery: December 30 - January 2\nCurrent Status: In transit to your local facility\n\nYou can track it here: [tracking link]\n\nI apologize that you didn't receive the shipping confirmation email - I've checked and it appears it may have been caught in a spam filter. I'm resending it now to lorilynn26@hotmail.com.\n\nGiven that you're a valued long-time customer, I've also added a 10% discount code (THANKYOU10) to your account for your next purchase - valid through February.\n\nPlease let me know if you need anything else!\n\nBest regards,\nCustomer Support Team",
  "tone": "professional",
  "channel": "email",
  "personalization_applied": [
    "Provided detailed tracking information (desktop user preference)",
    "Emphasized product quality and care (quality_focused segment)",
    "Acknowledged VIP status with loyalty reward (high LTV)",
    "Used professional tone (expert shopping_maturity)",
    "Included proactive cross-sell opportunity (power_buyer frequency)",
    "Detailed explanation of shipping process (expert shopper expects details)"
  ],
  "customer_segment_summary": "💎 VIP Customer | 🎯 Expert Shopper | ✅ Low churn risk"
}
```

### Internal Note Posted to Gorgias

```
🤖 AI-Generated Draft Response:

Hi Lori,

Thank you for reaching out about order #218874!

I can see your Hobb's Heirloom Batting (96" Queen Roll) was ordered on December 11th. This is a premium item that ships directly from our specialty warehouse to ensure it arrives in perfect condition.

Good news: Your order shipped on December 15th via USPS Priority Mail. Here's your tracking information:

Tracking #: 9400111899562847123456
Estimated Delivery: December 30 - January 2
Current Status: In transit to your local facility

You can track it here: [tracking link]

I apologize that you didn't receive the shipping confirmation email - I've checked and it appears it may have been caught in a spam filter. I'm resending it now to lorilynn26@hotmail.com.

Given that you're a valued long-time customer, I've also added a 10% discount code (THANKYOU10) to your account for your next purchase - valid through February.

Please let me know if you need anything else!

Best regards,
Customer Support Team

---

📊 Customer Intelligence Summary:
💎 VIP Customer | 🎯 Expert Shopper | ✅ Low churn risk (8%)

Archetype: premium_loyal_enthusiast (L4)
LTV: $1,847.32 | Orders: 23 | AOV: $80.32
Tenure: 487 days (16 months)

✨ KEY CONTEXT:
- Long-time loyal customer (23 orders over 16 months)
- Premium buyer - focus on quality over price
- Expert shopper - knows products well
- Rarely contacts support - this is important to them
- Low churn risk but shipping delays can impact loyalty

Recommended Actions:
1. Provide detailed tracking information immediately
2. Check if tracking emails are reaching customer
3. Consider priority handling for next order
4. Opportunity to upsell complementary products (batting tools, etc)

12-Month LTV Forecast: $890
Revenue at Risk (if churned): $2,737
```

---

## Test Scenario 3: Mid-Tier Regular with Split Shipment Confusion

### Webhook Payload

```json
{
  "ticket": {
    "id": 246403201,
    "subject": "Missing items from order",
    "customer": {
      "id": 510234567,
      "email": "craftymom42@gmail.com",
      "firstname": "Jennifer",
      "lastname": "Martinez",
      "external_id": "6543210987"
    },
    "integrations": {
      "82185": {
        "orders": [{
          "id": 6525888999111,
          "order_number": 223789,
          "name": "#223789",
          "financial_status": "paid",
          "fulfillment_status": "partial",
          "line_items": [
            {
              "title": "Aurifil Thread Collection - 12 Spools",
              "quantity": 1,
              "price": "45.99"
            },
            {
              "title": "Quilting Rulers Set - 4 Piece",
              "quantity": 1,
              "price": "32.99"
            },
            {
              "title": "Fabric Scissors - Professional Grade",
              "quantity": 1,
              "price": "24.99"
            }
          ]
        }]
      }
    }
  },
  "message": {
    "id": 606777888,
    "body_text": "Hi, I received my order but only got the scissors. Where are the thread and rulers? I paid for all 3 items. Order #223789",
    "subject": "Missing items from order",
    "from_agent": false
  }
}
```

### Shopify Fulfillment Data (Enriched)

```json
{
  "order_number": "223789",
  "fulfillment_count": 2,
  "has_split_shipment": true,
  "fulfillments": [
    {
      "id": "gid://shopify/Fulfillment/5432109876",
      "status": "success",
      "tracking_company": "USPS",
      "tracking_number": "9400111899562847111111",
      "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899562847111111",
      "line_items": [
        {
          "title": "Fabric Scissors - Professional Grade",
          "quantity": 1
        }
      ],
      "created_at": "2024-12-27T14:22:00Z",
      "updated_at": "2024-12-28T09:15:00Z"
    },
    {
      "id": "gid://shopify/Fulfillment/5432109877",
      "status": "in_transit",
      "tracking_company": "UPS",
      "tracking_number": "1Z999AA10123456784",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "line_items": [
        {
          "title": "Aurifil Thread Collection - 12 Spools",
          "quantity": 1
        },
        {
          "title": "Quilting Rulers Set - 4 Piece",
          "quantity": 1
        }
      ],
      "created_at": "2024-12-28T16:45:00Z",
      "estimated_delivery": "2024-12-31T23:59:00Z"
    }
  ]
}
```

### Customer Intelligence Response

```json
{
  "customer_id": "6543210987",
  "archetype": {
    "id": "arch_value_regular_hobbyist",
    "level": "L3",
    "segments": {
      "purchase_value": "mid_tier",
      "price_sensitivity": "deal_hunter",
      "shopping_maturity": "established",
      "purchase_frequency": "regular",
      "product_diversity": "multi_category",
      "brand_loyalty": "moderately_loyal",
      "seasonal_behavior": "seasonal_spikes",
      "cart_behavior": "basket_builder",
      "return_behavior": "occasional_returner",
      "channel_preference": "mixed",
      "weekend_affinity": "weekend_shopper",
      "promotional_responsiveness": "sale_driven",
      "cart_abandonment": "moderate_abandoner"
    }
  },
  "fuzzy_memberships": {
    "price_sensitivity": [
      {"segment": "deal_hunter", "membership": 0.82},
      {"segment": "strategic_buyer", "membership": 0.71}
    ],
    "shopping_maturity": [
      {"segment": "established", "membership": 0.87},
      {"segment": "experienced", "membership": 0.62}
    ],
    "purchase_value": [
      {"segment": "mid_tier", "membership": 0.79},
      {"segment": "value", "membership": 0.68}
    }
  },
  "behavioral_metrics": {
    "lifetime_value": 487.65,
    "total_orders": 8,
    "avg_order_value": 60.96,
    "days_since_last_purchase": 3,
    "customer_tenure_days": 142,
    "total_items_purchased": 31
  },
  "predictions": {
    "churn_risk": 0.25,
    "churn_risk_level": "low-medium",
    "ltv_12mo": 380.00,
    "next_purchase_days": 28,
    "reasoning": "Regular buyer with seasonal patterns - currently in active purchasing cycle"
  },
  "communication_guidance": [
    "Regular customer - familiar with store but not an expert",
    "Deal-conscious - emphasize value and savings when relevant",
    "Multi-category buyer - comfortable with various product types",
    "Basket builder - likes to combine multiple items in orders",
    "Weekend shopper - may be working on project right now",
    "Moderate churn risk - good experience will reinforce loyalty"
  ],
  "risk_factors": [
    {
      "factor": "split_shipment_confusion",
      "impact": "medium",
      "reasoning": "Customer doesn't realize order shipped in 2 packages - common frustration point"
    },
    {
      "factor": "weekend_project_blocked",
      "impact": "medium",
      "reasoning": "Weekend shopper waiting for items - likely has project in progress"
    }
  ]
}
```

### AI-Generated Response (with Fulfillment Context)

```json
{
  "message": "Hi Jennifer,\n\nDon't worry - your thread and rulers are on the way! This order shipped in 2 separate packages:\n\n📦 Package 1 (Delivered):\n✅ Fabric Scissors - Professional Grade\nTracking: 9400111899562847111111\n\n📦 Package 2 (In Transit):\n🚚 Aurifil Thread Collection - 12 Spools\n🚚 Quilting Rulers Set - 4 Piece\nTracking: 1Z999AA10123456784 (UPS)\nEstimated Delivery: December 31st\n\nYou can track package 2 here: https://www.ups.com/track?tracknum=1Z999AA10123456784\n\nSome items in your order shipped from different warehouses, which is why they're arriving separately. You'll receive everything you paid for - the second package should arrive in about 2 days.\n\nI apologize for the confusion! We're working on improving our split shipment notifications.\n\nHappy quilting!\nCustomer Support Team",
  "tone": "friendly",
  "channel": "email",
  "personalization_applied": [
    "Acknowledged split shipment immediately (customer's main concern)",
    "Used clear visual formatting for package details (basket_builder preference)",
    "Provided tracking links for self-service (established shopping_maturity)",
    "Warm, friendly tone (hobbyist/craft community vibe)",
    "Acknowledged weekend timing (weekend_shopper segment)",
    "No upselling - focused on resolving concern (moderate churn risk)"
  ],
  "customer_segment_summary": "🎯 Regular Customer | 🛍️ Deal Hunter | ⚠️ Moderate churn risk",
  "fulfillment_context": {
    "has_split_shipment": true,
    "customer_received_partial": true,
    "remaining_items_in_transit": true
  }
}
```

### Internal Note Posted to Gorgias

```
🤖 AI-Generated Draft Response:

Hi Jennifer,

Don't worry - your thread and rulers are on the way! This order shipped in 2 separate packages:

📦 Package 1 (Delivered):
✅ Fabric Scissors - Professional Grade
Tracking: 9400111899562847111111

📦 Package 2 (In Transit):
🚚 Aurifil Thread Collection - 12 Spools
🚚 Quilting Rulers Set - 4 Piece
Tracking: 1Z999AA10123456784 (UPS)
Estimated Delivery: December 31st

You can track package 2 here: https://www.ups.com/track?tracknum=1Z999AA10123456784

Some items in your order shipped from different warehouses, which is why they're arriving separately. You'll receive everything you paid for - the second package should arrive in about 2 days.

I apologize for the confusion! We're working on improving our split shipment notifications.

Happy quilting!
Customer Support Team

---

📦 Split Shipment Alert:

Order #223789 was fulfilled in 2 separate shipments:

Shipment 1 (Delivered Dec 28):
- Fabric Scissors - Professional Grade (1x)
Tracking: USPS 9400111899562847111111

Shipment 2 (In Transit - Arriving Dec 31):
- Aurifil Thread Collection - 12 Spools (1x)
- Quilting Rulers Set - 4 Piece (1x)
Tracking: UPS 1Z999AA10123456784

Customer received partial delivery and thinks items are missing. Second package arrives in 2 days.

---

📊 Customer Intelligence Summary:
🎯 Regular Customer | 🛍️ Deal Hunter | ⚠️ Moderate churn risk (25%)

Archetype: value_regular_hobbyist (L3)
LTV: $487.65 | Orders: 8 | AOV: $60.96
Tenure: 142 days (4.7 months)

✨ KEY CONTEXT:
- Established customer - 8 orders in under 5 months
- Deal-conscious but willing to pay for quality
- Weekend shopper - likely working on project now
- Basket builder - combines multiple items per order
- This is a classic split shipment confusion case

Recommended Actions:
1. Reassure that all items are coming
2. Provide tracking for second package
3. No compensation needed - just clear communication
4. Follow up after delivery to ensure satisfaction
5. Consider email workflow improvement for split shipments

12-Month LTV Forecast: $380
Retention Probability: 75%
```

---

## Summary: How ML Clustering Powers Personalization

### 13 Behavioral Axes (Hierarchical Clustering)

Each customer is segmented across 13 independent dimensions:

1. **purchase_value**: budget, value, mid_tier, premium, luxury
2. **price_sensitivity**: highly_deal_oriented, deal_hunter, strategic, quality_focused, premium_buyer
3. **shopping_maturity**: new, beginner, established, experienced, expert
4. **purchase_frequency**: first_time, rare, occasional, regular, frequent, power_buyer
5. **product_diversity**: single_item, single_category, multi_category, explorer
6. **brand_loyalty**: exploring, switcher, moderately_loyal, highly_loyal, exclusive
7. **seasonal_behavior**: holiday_only, seasonal_spikes, year_round, non_seasonal
8. **cart_behavior**: decisive, thoughtful, basket_builder, bulk_buyer
9. **return_behavior**: no_history, rarely_returns, occasional_returner, frequent_returner
10. **channel_preference**: mobile_app, mobile_web, desktop, mixed
11. **weekend_affinity**: weekday_shopper, weekend_shopper, no_preference
12. **promotional_responsiveness**: coupon_seeker, sale_driven, brand_driven, promotion_resistant
13. **cart_abandonment**: low_abandoner, moderate_abandoner, high_abandoner

### Fuzzy C-Means "Thumbprint"

- Each axis uses **Fuzzy C-Means clustering** (m=2.0 fuzziness)
- Customers belong to **top-2 segments per axis** with membership scores
- Example: `price_sensitivity: [("deal_hunter", 0.82), ("strategic", 0.71)]`
- Creates **868 unique behavioral archetypes** (combinations across axes)

### How AI Uses This Context

1. **Tone & Language**: Adjust formality based on `shopping_maturity`
2. **Pricing Communication**: Handle differently for `deal_hunter` vs `quality_focused`
3. **Detail Level**: More/less explanation based on `expert` vs `new`
4. **Upselling Strategy**: Aggressive for `power_buyer`, minimal for `high_churn_risk`
5. **Urgency**: Prioritize `VIP` + `high_churn_risk` tickets
6. **Channel**: Format for `mobile_web` (concise) vs `desktop` (detailed)

### Real Impact

- **Budget-conscious customer**: Immediate empathy, no upselling, focus on resolution
- **VIP customer**: Professional tone, detailed tracking, loyalty reward offered
- **Regular customer**: Friendly tone, clear explanation, proactive follow-up

The system automatically adjusts communication strategy based on 868 archetypes × 13 behavioral dimensions = **highly personalized support at scale**.
