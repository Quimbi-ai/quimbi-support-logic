# Quimbi Identity Graph System

## Overview

The Quimbi Identity Graph is a unified customer identity system that links all customer identifiers (Shopify IDs, Gorgias IDs, emails, etc.) under a single **QuimbiID**.

This solves the problem of customers having multiple IDs across different systems (e-commerce, support, etc.) and enables a unified view of customer data.

## Architecture

### Database Schema

The identity graph consists of 3 main tables:

#### 1. `quimbi_identities`
The master table for unified customer identities.

```sql
- quimbi_id (PK)          # Unique identifier (format: QID_<timestamp>_<random>)
- primary_email            # Main email address
- primary_name             # Customer name
- created_at / updated_at
- merged_from              # If merged from another QuimbiID
- is_active                # Soft delete flag
```

#### 2. `identity_graph`
Links all external identifiers to QuimbiIDs.

```sql
- quimbi_id (FK)          # References quimbi_identities
- id_type                 # Type: 'shopify', 'gorgias', 'email', 'phone', etc.
- id_value                # The actual ID value
- confidence_score        # 0.0 to 1.0
- source                  # Where this linkage came from
- verified                # Boolean flag
- created_at / updated_at
```

**Unique constraint**: `(id_type, id_value)` - prevents duplicate identifiers

#### 3. `identity_resolution_log`
Audit trail for all identity operations.

```sql
- quimbi_id
- resolution_type         # 'merge', 'split', 'new', 'link'
- details (JSONB)
- performed_by
- created_at
```

### Database Functions

- **`generate_quimbi_id()`** - Generates unique QuimbiIDs
- **`find_quimbi_id(id_type, id_value)`** - Find QuimbiID by any identifier
- **`link_identity(...)`** - Link an identifier to a QuimbiID

### Views

- **`customer_identity_view`** - Convenient view for looking up complete customer identities with all linked IDs

## PII Hashing System

The identity graph includes privacy-preserving **PII hashing** to enable customer identity resolution from unstructured data (e.g., Google Groups emails where names/addresses appear in message bodies).

### How It Works

1. **Hash Generation** - Customer PII (emails, names, addresses) is normalized and hashed using SHA256 with a secret salt
2. **Storage** - Hashes are stored in `identity_graph` as additional id_types: `email_hash`, `name_hash`, `address_hash`
3. **Lookup** - When resolving customer identity, we hash the incoming PII and look up the hash in the identity graph
4. **Privacy** - Original PII is never stored, only hashes (one-way encryption)

### Supported Hash Types

- **email_hash** - Hashed email addresses (confidence: 1.0)
  - Normalized: lowercase, strip whitespace, Gmail dot removal
  - Example: `molly@moontowercoaching.com` == `Molly@MoonTowerCoaching.com`

- **name_hash** - Hashed customer names (confidence: 0.9)
  - Normalized: lowercase, remove punctuation, remove suffixes (Jr, Sr, III)
  - Example: `Molly Stevens` == `molly stevens` == `Molly-Stevens`

- **address_hash** - Hashed physical addresses (confidence: 0.7)
  - Normalized: lowercase, expand abbreviations, remove apartment numbers
  - Example: `6004 Twin Valley Cv.` == `6004 Twin Valley Cove`

### Scripts

#### PII Hashing Scripts

**`app/services/pii_hash.py`** - Core PII hashing utility
- `hash_email(email)` - Hash email address
- `hash_name(name)` - Hash customer name
- `hash_address(address)` - Hash physical address
- Includes normalization functions for consistent hashing

**`populate_pii_hashes.py`** - Populate identity graph with PII hashes
- Reads all active QuimbiIDs from `quimbi_identities`
- Hashes their email and name
- Inserts hashes into `identity_graph`

Usage:
```bash
# Populate all customers
python3 populate_pii_hashes.py

# Test with limited customers
python3 populate_pii_hashes.py --limit 100
```

**`app/services/quimbi_id_service.py`** - Identity resolution functions
- `find_quimbi_id_by_pii_hash(db, email, name, address)` - Find QuimbiID by PII hash lookup
- Tries email hash first (most reliable), then name hash, then address hash
- Returns QuimbiID if any hash matches

**`test_pii_lookup.py`** - Test script for PII hash lookups
- Verifies email/name normalization
- Tests case insensitivity
- Validates hash matching

Usage:
```bash
python3 test_pii_lookup.py
```

### 1. `create_identity_graph.sql`
Creates all database tables, indexes, functions, and views.

**Usage**:
```bash
psql -h <host> -U <user> -d <database> -f create_identity_graph.sql
```

### 2. `build_identity_graph.py`
Main script to build the identity graph from existing data.

**What it does**:
1. Creates QuimbiIDs for all Shopify customers in `combined_sales`
2. Links Gorgias customer IDs from `public.customers`
3. Links email addresses
4. Resolves conflicts and merges duplicate identities

**Usage**:
```bash
python3 build_identity_graph.py
```

**Note**: This processes ALL customers (~94K). For testing, use the limited version.

### 3. `build_identity_graph_limited.py`
Limited version that processes only the first 1,000 Shopify customers for faster testing.

**Usage**:
```bash
python3 build_identity_graph_limited.py
```

**Output**:
```
Total Active Customers: 1,030
Identifiers by Type:
  shopify              1,000
  email                   31
  gorgias                 30
```

### 4. `query_identity_graph.py`
Query tool to look up customers by any identifier.

**Usage**:
```bash
# Show summary statistics
python3 query_identity_graph.py

# Find customer by any ID (email, Shopify ID, Gorgias ID, or QuimbiID)
python3 query_identity_graph.py debbymiller@centurylink.net
python3 query_identity_graph.py 4595328254127
python3 query_identity_graph.py QID_1768865976_239396
```

**Example Output**:
```
✓ Found Customer Identity
--------------------------------------------------------------------------------
QuimbiID:      QID_1768865976_239396
Email:         debbymiller@centurylink.net
Name:          Debby Stanford-Miller
Created:       2026-01-19 23:39:36.326795

Linked Identifiers (2):
--------------------------------------------------------------------------------
  [✓] email        debbymiller@centurylink.net    (from: public.customers, confidence: 1.00)
  [✓] shopify      4595328254127                  (from: combined_sales, confidence: 1.00)

📊 Purchase History:
   Orders: 202
   Total Sales: $8,047.77

🎫 Support Tickets: 1
```

## Use Cases

### 1. Customer Lookup
Look up a customer by any identifier (email, Shopify ID, Gorgias ID) and get their complete identity across all systems.

```python
# In your application
quimbi_id = find_quimbi_id('email', 'customer@example.com')
customer = get_customer_identity(quimbi_id)
# Returns all linked IDs, purchase history, tickets, etc.
```

### 2. Identity Resolution
When a new customer interacts with the system (e.g., creates a support ticket), automatically link their identifier to an existing QuimbiID or create a new one.

```python
# New Gorgias ticket received
gorgias_customer_id = "508639575"
email = "mrsjulieruch@gmail.com"

# Check if this customer exists
quimbi_id = find_quimbi_id('email', email)
if not quimbi_id:
    quimbi_id = create_new_identity(email)

# Link the Gorgias ID
link_identity(quimbi_id, 'gorgias', gorgias_customer_id)
```

### 3. Cross-System Analytics
Analyze customer behavior across e-commerce and support systems.

```sql
SELECT
    qi.quimbi_id,
    qi.primary_email,
    COUNT(DISTINCT t.id) as ticket_count,
    COUNT(DISTINCT cs.order_id) as order_count,
    SUM(cs.line_item_sales) as total_revenue
FROM quimbi_identities qi
LEFT JOIN identity_graph ig_shopify ON qi.quimbi_id = ig_shopify.quimbi_id AND ig_shopify.id_type = 'shopify'
LEFT JOIN combined_sales cs ON ig_shopify.id_value::bigint = cs.customer_id
LEFT JOIN identity_graph ig_any ON qi.quimbi_id = ig_any.quimbi_id
LEFT JOIN tickets t ON ig_any.id_value = t.customer_id::text
WHERE qi.is_active = TRUE
GROUP BY qi.quimbi_id, qi.primary_email
HAVING COUNT(DISTINCT t.id) > 0
ORDER BY total_revenue DESC;
```

## Current Status

### Statistics (Limited Build - 1,000 customers)
- **1,030 QuimbiIDs** created
- **1,061 identity links**:
  - 1,000 Shopify IDs
  - 31 emails
  - 30 Gorgias IDs
- **31 customers** with multiple ID types
- **0 customers** with BOTH Shopify + Gorgias IDs (in limited dataset)

### Next Steps

1. **Run full build** - Process all 94,686 Shopify customers
2. **Update import scripts** - Modify Gorgias import to use identity graph
3. **Add phone numbers** - Link phone numbers as identifiers
4. **Add Stripe IDs** - Link payment customer IDs
5. **API endpoints** - Create REST API for identity lookups
6. **Frontend integration** - Update support frontend to use QuimbiIDs

## Benefits

1. **Unified Customer View** - Single ID across all systems
2. **Better Analytics** - Link support tickets to purchase history
3. **Improved Support** - See complete customer context
4. **Data Quality** - Automatic deduplication and conflict resolution
5. **Scalability** - Add new ID types without schema changes
6. **Audit Trail** - Complete history of all identity operations

## PII Hash Use Cases

### Use Case 1: Google Groups Email Resolution

**Problem**: Emails from Google Groups (e.g., `linda@lindaselectricquilters.com`) don't have a structured `from_email` - customer name and contact info are in the message body.

**Solution**: Extract name/email from message body and use PII hash lookup:

```python
from app.services.quimbi_id_service import find_quimbi_id_by_pii_hash

# Extract from email body
customer_name = "Molly Stevens"
customer_email = "molly@moontowercoaching.com"

# Find QuimbiID via PII hash
quimbi_id = await find_quimbi_id_by_pii_hash(
    db,
    email=customer_email,
    name=customer_name
)

if quimbi_id:
    # Found existing customer - load their profile
    customer_profile = await get_complete_customer_profile(db, quimbi_id)
else:
    # New customer - create QuimbiID
    quimbi_id = await create_new_quimbi_identity(db, customer_email, customer_name)
```

### Use Case 2: Fuzzy Name Matching

**Problem**: Customer name appears in different formats across systems:
- Shopify: "John Smith, Jr."
- Support ticket: "john smith"
- Google Groups: "John Smith"

**Solution**: All variations hash to the same value due to normalization:

```python
from app.services.pii_hash import hash_name

hash1 = hash_name("John Smith, Jr.")
hash2 = hash_name("john smith")
hash3 = hash_name("John Smith")

# All produce identical hashes
assert hash1 == hash2 == hash3
```

### Use Case 3: Email Case Insensitivity

**Problem**: Same email appears with different casing:
- `Molly@MoonTowerCoaching.com` (Shopify)
- `molly@moontowercoaching.com` (Support ticket)

**Solution**: Email normalization ensures consistent hashing:

```python
from app.services.pii_hash import hash_email

hash1 = hash_email("Molly@MoonTowerCoaching.com")
hash2 = hash_email("molly@moontowercoaching.com")

# Identical hashes
assert hash1 == hash2
```

## Technical Notes

### ID Types Supported
- `shopify` - Shopify customer IDs
- `gorgias` - Gorgias customer IDs
- `email` - Email addresses (plaintext)
- `email_hash` - Hashed email addresses (privacy-preserving)
- `name_hash` - Hashed customer names (privacy-preserving)
- `address_hash` - Hashed physical addresses (privacy-preserving)
- `phone` - Phone numbers (to be added)
- `stripe` - Stripe customer IDs (to be added)
- Custom types can be added without schema changes

### Confidence Scores
- **1.0** - Exact match, verified
- **0.9** - High confidence (e.g., email match)
- **0.7** - Medium confidence (e.g., name + phone match)
- **0.5** - Low confidence (e.g., fuzzy name match)

### Merging Identities
When two QuimbiIDs are found to represent the same customer:
1. Pick primary QuimbiID (usually the older one)
2. Move all identity links to primary
3. Mark secondary as `is_active = FALSE`
4. Set `merged_from` field
5. Log the merge operation

## Example Queries

### Find all customers with both Shopify and Gorgias IDs
```sql
SELECT
    qi.quimbi_id,
    qi.primary_email,
    qi.primary_name,
    ig_shopify.id_value as shopify_id,
    ig_gorgias.id_value as gorgias_id
FROM quimbi_identities qi
INNER JOIN identity_graph ig_shopify ON qi.quimbi_id = ig_shopify.quimbi_id AND ig_shopify.id_type = 'shopify'
INNER JOIN identity_graph ig_gorgias ON qi.quimbi_id = ig_gorgias.quimbi_id AND ig_gorgias.id_type = 'gorgias'
WHERE qi.is_active = TRUE;
```

### Count identifiers by type
```sql
SELECT id_type, COUNT(*) as count
FROM identity_graph
GROUP BY id_type
ORDER BY count DESC;
```

### Find customers with most linked identities
```sql
SELECT
    quimbi_id,
    COUNT(DISTINCT id_type) as type_count,
    array_agg(DISTINCT id_type) as types
FROM identity_graph
GROUP BY quimbi_id
ORDER BY type_count DESC
LIMIT 10;
```

## Maintenance

### Regular Tasks
1. **Rebuild graph** - When adding large batches of customers
2. **Resolve duplicates** - Periodically check for and merge duplicates
3. **Clean up temp emails** - Replace `shopify_*@temp.quimbi.com` with real emails
4. **Verify linkages** - Mark high-confidence links as verified

### Monitoring
Monitor the `identity_resolution_log` table for:
- Unusual merge patterns
- Low confidence linkages
- Failed resolution attempts
