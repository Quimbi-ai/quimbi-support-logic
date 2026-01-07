# AI Agent Mesh - API Specification

**Version**: 1.0
**Date**: 2025-11-25
**Base URL**: `https://api.aigentmesh.com/v1`
**Authentication**: Bearer Token (JWT)

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Repos API](#2-repos-api)
3. [APIs Management](#3-apis-management)
4. [Changes & Detection](#4-changes--detection)
5. [Migrations & Auto-Fix](#5-migrations--auto-fix)
6. [Dashboard & Analytics](#6-dashboard--analytics)
7. [Webhooks](#7-webhooks)
8. [Errors](#8-errors)

---

## 1. Authentication

### 1.1 OAuth Flow (GitHub)

**Step 1: Redirect to GitHub**
```
GET https://github.com/login/oauth/authorize
  ?client_id=YOUR_CLIENT_ID
  &redirect_uri=https://aigentmesh.com/auth/callback
  &scope=repo
```

**Step 2: Exchange Code for Token**
```http
POST /v1/auth/github/callback
Content-Type: application/json

{
  "code": "github_oauth_code_here"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": "user_abc123",
    "email": "user@example.com",
    "name": "John Doe",
    "github_login": "johndoe",
    "plan": "free"
  }
}
```

### 1.2 Using the Access Token

All subsequent requests:
```http
GET /v1/repos
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 1.3 Refresh Token

```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token_here"
}
```

**Response**: Same as OAuth callback

---

## 2. Repos API

### 2.1 List Repositories

```http
GET /v1/repos
Authorization: Bearer {token}
```

**Query Parameters**:
- `language` (optional): Filter by language (python, javascript, typescript)
- `framework` (optional): Filter by framework (fastapi, express, flask)
- `limit` (optional): Number of results (default: 50, max: 100)
- `offset` (optional): Pagination offset

**Response**:
```json
{
  "repos": [
    {
      "id": "repo_abc123",
      "name": "support-backend",
      "full_name": "myorg/support-backend",
      "url": "https://github.com/myorg/support-backend",
      "language": "python",
      "framework": "fastapi",
      "default_branch": "main",
      "apis_count": 12,
      "last_synced_at": "2025-11-25T10:30:00Z",
      "created_at": "2025-11-20T14:00:00Z"
    }
  ],
  "total": 4,
  "limit": 50,
  "offset": 0
}
```

---

### 2.2 Get Repository

```http
GET /v1/repos/{repo_id}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "id": "repo_abc123",
  "name": "support-backend",
  "full_name": "myorg/support-backend",
  "url": "https://github.com/myorg/support-backend",
  "language": "python",
  "framework": "fastapi",
  "default_branch": "main",
  "apis_count": 12,
  "consumers_count": 0,
  "providers_count": 2,
  "last_synced_at": "2025-11-25T10:30:00Z",
  "sync_status": "completed",
  "apis": [
    {
      "id": "api_xyz789",
      "endpoint": "/api/tickets",
      "method": "POST",
      "consumers_count": 1
    }
  ]
}
```

---

### 2.3 Sync Repository (Trigger Discovery)

```http
POST /v1/repos/{repo_id}/sync
Authorization: Bearer {token}
Content-Type: application/json

{
  "branch": "main",  // optional, defaults to default_branch
  "force": false     // optional, re-scan even if recently synced
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "job_def456",
  "status": "queued",
  "estimated_duration": 30,
  "status_url": "/v1/jobs/job_def456"
}
```

---

### 2.4 Add Repository

```http
POST /v1/repos
Authorization: Bearer {token}
Content-Type: application/json

{
  "repo_url": "https://github.com/myorg/new-backend",
  "auto_sync": true  // Automatically sync on push events
}
```

**Response** (201 Created):
```json
{
  "id": "repo_ghi789",
  "name": "new-backend",
  "full_name": "myorg/new-backend",
  "url": "https://github.com/myorg/new-backend",
  "auto_sync": true,
  "sync_job_id": "job_xyz123",
  "created_at": "2025-11-25T11:00:00Z"
}
```

---

### 2.5 Remove Repository

```http
DELETE /v1/repos/{repo_id}
Authorization: Bearer {token}
```

**Response** (204 No Content)

---

## 3. APIs Management

### 3.1 List APIs in Repository

```http
GET /v1/repos/{repo_id}/apis
Authorization: Bearer {token}
```

**Query Parameters**:
- `method`: Filter by HTTP method (GET, POST, PUT, DELETE, PATCH)
- `endpoint`: Search by endpoint pattern (supports wildcards: `/api/users/*`)
- `has_consumers`: Only show APIs with consumers (`true`/`false`)
- `limit`, `offset`: Pagination

**Response**:
```json
{
  "apis": [
    {
      "id": "api_xyz789",
      "endpoint": "/api/tickets",
      "method": "POST",
      "file_path": "app/api/tickets.py",
      "line_number": 42,
      "auth_type": "bearer",
      "is_public": false,
      "consumers_count": 2,
      "last_changed_at": "2025-11-24T15:30:00Z",
      "schema_summary": {
        "request_fields": ["subject", "customer_id", "priority"],
        "response_fields": ["id", "status", "created_at"]
      }
    }
  ],
  "total": 12,
  "limit": 50,
  "offset": 0
}
```

---

### 3.2 Get API Details

```http
GET /v1/apis/{api_id}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "id": "api_xyz789",
  "endpoint": "/api/tickets",
  "method": "POST",
  "file_path": "app/api/tickets.py",
  "line_number": 42,
  "auth_type": "bearer",
  "is_public": false,
  "repo": {
    "id": "repo_abc123",
    "name": "support-backend",
    "full_name": "myorg/support-backend"
  },
  "schema": {
    "request": {
      "type": "object",
      "properties": {
        "subject": {"type": "string", "required": true},
        "customer_id": {"type": "string", "required": true},
        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]}
      }
    },
    "response": {
      "200": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "status": {"type": "string"},
          "created_at": {"type": "string", "format": "date-time"}
        }
      }
    }
  },
  "consumers": [
    {
      "repo_id": "repo_def456",
      "repo_name": "myorg/frontend",
      "file_path": "src/services/api.ts",
      "line_number": 23
    }
  ],
  "recent_changes": [
    {
      "id": "change_abc",
      "type": "WARNING",
      "detected_at": "2025-11-24T15:30:00Z",
      "summary": "Added optional field: tags"
    }
  ]
}
```

---

### 3.3 Get API Consumers

```http
GET /v1/apis/{api_id}/consumers
Authorization: Bearer {token}
```

**Response**:
```json
{
  "api": {
    "id": "api_xyz789",
    "endpoint": "/api/intelligence/analyze",
    "method": "POST",
    "provider_repo": "myorg/quimbi-backend"
  },
  "consumers": [
    {
      "repo_id": "repo_abc123",
      "repo_name": "myorg/support-backend",
      "file_path": "app/services/quimbi_client.py",
      "line_number": 45,
      "function_name": "analyze_customer",
      "last_verified": "2025-11-25T10:00:00Z"
    },
    {
      "repo_id": "repo_def456",
      "repo_name": "myorg/marketing-backend",
      "file_path": "app/services/intelligence.py",
      "line_number": 23,
      "function_name": "get_customer_intel",
      "last_verified": "2025-11-25T10:00:00Z"
    }
  ],
  "total_consumers": 2
}
```

---

## 4. Changes & Detection

### 4.1 List Recent Changes

```http
GET /v1/changes
Authorization: Bearer {token}
```

**Query Parameters**:
- `repo_id`: Filter by repository
- `type`: Filter by type (BREAKING, WARNING, INFO, NEW)
- `is_breaking`: Only breaking changes (`true`)
- `since`: ISO datetime (e.g., `2025-11-20T00:00:00Z`)
- `limit`, `offset`: Pagination

**Response**:
```json
{
  "changes": [
    {
      "id": "change_abc123",
      "api_id": "api_xyz789",
      "api_endpoint": "/api/intelligence/analyze",
      "api_method": "POST",
      "provider_repo": "myorg/quimbi-backend",
      "type": "BREAKING",
      "is_breaking": true,
      "summary": "Added required field: customer_segment",
      "affected_repos_count": 2,
      "detected_at": "2025-11-25T10:30:00Z",
      "commit_sha": "a1b2c3d4",
      "commit_message": "Add customer segmentation to analysis",
      "has_auto_fix": true
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

---

### 4.2 Get Change Details

```http
GET /v1/changes/{change_id}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "id": "change_abc123",
  "api": {
    "id": "api_xyz789",
    "endpoint": "/api/intelligence/analyze",
    "method": "POST",
    "provider_repo": "myorg/quimbi-backend"
  },
  "type": "BREAKING",
  "is_breaking": true,
  "summary": "Added required field: customer_segment",
  "description": "The analyze endpoint now requires a customer_segment field to provide more accurate analysis.",
  "commit": {
    "sha": "a1b2c3d4e5f6",
    "message": "Add customer segmentation to analysis",
    "author": "johndoe",
    "committed_at": "2025-11-25T10:25:00Z",
    "url": "https://github.com/myorg/quimbi-backend/commit/a1b2c3d4"
  },
  "schema_diff": {
    "old_schema": {
      "request": {
        "properties": {
          "customer_id": {"type": "string", "required": true}
        }
      }
    },
    "new_schema": {
      "request": {
        "properties": {
          "customer_id": {"type": "string", "required": true},
          "customer_segment": {"type": "string", "required": true}  // ADDED
        }
      }
    },
    "changes": [
      {
        "type": "REQUEST_REQUIRED_ADDED",
        "field": "customer_segment",
        "severity": "BREAKING"
      }
    ]
  },
  "affected_repos": [
    {
      "repo_id": "repo_abc123",
      "repo_name": "myorg/support-backend",
      "affected_files": [
        {
          "file_path": "app/services/quimbi_client.py",
          "line_number": 45,
          "function_name": "analyze_customer"
        }
      ],
      "migration_status": "pr_created",
      "migration_pr_url": "https://github.com/myorg/support-backend/pull/123"
    }
  ],
  "detected_at": "2025-11-25T10:30:00Z",
  "notified_at": "2025-11-25T10:31:00Z"
}
```

---

### 4.3 Dismiss Change

```http
POST /v1/changes/{change_id}/dismiss
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "We're not using this API anymore"
}
```

**Response**:
```json
{
  "id": "change_abc123",
  "status": "dismissed",
  "dismissed_at": "2025-11-25T11:00:00Z",
  "dismissed_reason": "We're not using this API anymore"
}
```

---

## 5. Migrations & Auto-Fix

### 5.1 Generate Migration (Auto-Fix)

```http
POST /v1/changes/{change_id}/auto-fix
Authorization: Bearer {token}
Content-Type: application/json

{
  "consumer_repo_id": "repo_abc123",
  "create_pr": true,       // Create GitHub PR (default: true)
  "run_tests": false,      // Run tests before creating PR (default: false)
  "target_branch": "main"  // Branch to create PR against (default: default_branch)
}
```

**Response** (202 Accepted):
```json
{
  "migration_id": "mig_xyz789",
  "status": "generating",
  "estimated_duration": 60,
  "status_url": "/v1/migrations/mig_xyz789"
}
```

---

### 5.2 Get Migration Status

```http
GET /v1/migrations/{migration_id}
Authorization: Bearer {token}
```

**Response** (while generating):
```json
{
  "id": "mig_xyz789",
  "change_id": "change_abc123",
  "consumer_repo_id": "repo_abc123",
  "status": "generating",  // queued, generating, pr_created, merged, failed
  "progress": 60,          // Percentage (0-100)
  "started_at": "2025-11-25T11:00:00Z"
}
```

**Response** (completed):
```json
{
  "id": "mig_xyz789",
  "change_id": "change_abc123",
  "consumer_repo_id": "repo_abc123",
  "status": "pr_created",
  "pr_url": "https://github.com/myorg/support-backend/pull/123",
  "pr_number": 123,
  "generated_files": [
    {
      "file_path": "app/services/quimbi_client.py",
      "changes_count": 3,
      "preview_url": "/v1/migrations/mig_xyz789/files/app/services/quimbi_client.py"
    },
    {
      "file_path": "tests/test_quimbi_integration.py",
      "changes_count": 2,
      "preview_url": "/v1/migrations/mig_xyz789/files/tests/test_quimbi_integration.py"
    }
  ],
  "test_results": null,  // If run_tests was true
  "started_at": "2025-11-25T11:00:00Z",
  "completed_at": "2025-11-25T11:01:15Z"
}
```

---

### 5.3 Preview Migration Code

```http
GET /v1/migrations/{migration_id}/files/{file_path}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "file_path": "app/services/quimbi_client.py",
  "old_code": "result = await self.post(\n    '/api/intelligence/analyze',\n    json={'customer_id': customer_id}\n)",
  "new_code": "result = await self.post(\n    '/api/intelligence/analyze',\n    json={\n        'customer_id': customer_id,\n        'customer_segment': customer.segment  # Added\n    }\n)",
  "diff": "@@ -45,7 +45,8 @@\n result = await self.post(\n     '/api/intelligence/analyze',\n-    json={'customer_id': customer_id}\n+    json={\n+        'customer_id': customer_id,\n+        'customer_segment': customer.segment\n+    }\n )",
  "explanation": "Added the required customer_segment field to the API request based on the schema change."
}
```

---

### 5.4 List Migrations

```http
GET /v1/migrations
Authorization: Bearer {token}
```

**Query Parameters**:
- `repo_id`: Filter by repository
- `status`: Filter by status (generating, pr_created, merged, failed)
- `limit`, `offset`: Pagination

**Response**:
```json
{
  "migrations": [
    {
      "id": "mig_xyz789",
      "change_summary": "Added required field: customer_segment",
      "consumer_repo": "myorg/support-backend",
      "status": "pr_created",
      "pr_url": "https://github.com/myorg/support-backend/pull/123",
      "created_at": "2025-11-25T11:00:00Z"
    }
  ],
  "total": 8,
  "limit": 50,
  "offset": 0
}
```

---

## 6. Dashboard & Analytics

### 6.1 Dashboard Overview

```http
GET /v1/dashboard/overview
Authorization: Bearer {token}
```

**Response**:
```json
{
  "summary": {
    "repos_count": 4,
    "apis_count": 23,
    "dependencies_count": 45,
    "breaking_changes_last_7_days": 2
  },
  "recent_changes": [
    {
      "id": "change_abc123",
      "api_endpoint": "/api/intelligence/analyze",
      "provider_repo": "myorg/quimbi-backend",
      "type": "BREAKING",
      "affected_repos": 2,
      "detected_at": "2025-11-25T10:30:00Z",
      "has_auto_fix": true
    }
  ],
  "dependency_graph": {
    "nodes": [
      {
        "id": "repo_abc123",
        "name": "support-backend",
        "type": "consumer",
        "apis_provided": 12,
        "apis_consumed": 3
      },
      {
        "id": "repo_def456",
        "name": "quimbi-backend",
        "type": "provider",
        "apis_provided": 8,
        "apis_consumed": 0
      }
    ],
    "edges": [
      {
        "source": "repo_def456",
        "target": "repo_abc123",
        "apis": ["POST /api/intelligence/analyze", "POST /api/generation/message"],
        "count": 2
      }
    ]
  }
}
```

---

### 6.2 Analytics: API Usage

```http
GET /v1/analytics/api-usage
Authorization: Bearer {token}
```

**Query Parameters**:
- `repo_id`: Filter by repository
- `period`: Time period (7d, 30d, 90d)

**Response**:
```json
{
  "period": "7d",
  "data": [
    {
      "date": "2025-11-25",
      "apis_discovered": 12,
      "changes_detected": 3,
      "breaking_changes": 1
    },
    {
      "date": "2025-11-24",
      "apis_discovered": 0,
      "changes_detected": 1,
      "breaking_changes": 0
    }
  ]
}
```

---

## 7. Webhooks

### 7.1 Configure Webhook

```http
POST /v1/webhooks
Authorization: Bearer {token}
Content-Type: application/json

{
  "url": "https://your-server.com/webhooks/ai-agent-mesh",
  "events": ["change.detected", "migration.completed"],
  "secret": "your_webhook_secret"  // For HMAC verification
}
```

**Response**:
```json
{
  "id": "webhook_abc123",
  "url": "https://your-server.com/webhooks/ai-agent-mesh",
  "events": ["change.detected", "migration.completed"],
  "created_at": "2025-11-25T12:00:00Z",
  "status": "active"
}
```

---

### 7.2 Webhook Events

#### **change.detected**
```json
{
  "event": "change.detected",
  "timestamp": "2025-11-25T10:30:00Z",
  "data": {
    "change_id": "change_abc123",
    "api_endpoint": "/api/intelligence/analyze",
    "provider_repo": "myorg/quimbi-backend",
    "type": "BREAKING",
    "affected_repos": ["myorg/support-backend", "myorg/marketing-backend"]
  }
}
```

#### **migration.completed**
```json
{
  "event": "migration.completed",
  "timestamp": "2025-11-25T11:01:15Z",
  "data": {
    "migration_id": "mig_xyz789",
    "change_id": "change_abc123",
    "consumer_repo": "myorg/support-backend",
    "pr_url": "https://github.com/myorg/support-backend/pull/123",
    "status": "pr_created"
  }
}
```

---

## 8. Errors

### 8.1 Error Format

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.aigentmesh.com/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have exceeded 100 requests per minute. Try again in 32 seconds.",
  "instance": "/v1/repos/123/sync",
  "retry_after": 32
}
```

### 8.2 Common Error Codes

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 400 | `bad_request` | Invalid request parameters |
| 401 | `unauthorized` | Missing or invalid access token |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not_found` | Resource not found |
| 409 | `conflict` | Resource conflict (e.g., repo already added) |
| 422 | `validation_error` | Request validation failed |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `internal_error` | Server error |
| 503 | `service_unavailable` | Service temporarily unavailable |

---

### 8.3 Rate Limits

| Plan | Rate Limit | Burst |
|------|------------|-------|
| Free | 100 req/hour | 20 req/min |
| Starter | 1000 req/hour | 100 req/min |
| Team | 10000 req/hour | 500 req/min |
| Enterprise | Custom | Custom |

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1732578000
```

---

## 9. Appendix

### 9.1 OpenAPI Specification

Full OpenAPI 3.0 spec available at:
```
GET /v1/openapi.json
```

### 9.2 SDKs

Official SDKs:
- Python: `pip install ai-agent-mesh`
- JavaScript/TypeScript: `npm install @aigentmesh/sdk`
- Go: `go get github.com/aigentmesh/go-sdk`

### 9.3 API Versioning

- Current version: `v1`
- Breaking changes will increment major version (`v2`)
- Backward-compatible changes stay in same version
- Deprecated endpoints supported for 12 months

---

**Last Updated**: 2025-11-25
**Contact**: api-support@aigentmesh.com
