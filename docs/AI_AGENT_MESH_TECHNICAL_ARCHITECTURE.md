# AI Agent Mesh - Technical Architecture Document

**Version**: 1.0
**Date**: 2025-11-25
**Status**: Draft
**Owner**: Engineering Team
**Related Documents**: [PRD](./AI_AGENT_MESH_PRD.md), [API Spec](./AI_AGENT_MESH_API_SPEC.md)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [System Components](#3-system-components)
4. [Data Models](#4-data-models)
5. [API Architecture](#5-api-architecture)
6. [Processing Pipeline](#6-processing-pipeline)
7. [AI/ML Components](#7-aiml-components)
8. [Infrastructure](#8-infrastructure)
9. [Security Architecture](#9-security-architecture)
10. [Scalability & Performance](#10-scalability--performance)
11. [Monitoring & Observability](#11-monitoring--observability)
12. [Disaster Recovery](#12-disaster-recovery)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Web Dashboard│  │   AI Agents  │  │  GitHub App  │          │
│  │  (React SPA) │  │ (Claude Code)│  │  (OAuth)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ├──────────────────┴──────────────────┤
          │           API Gateway (Kong)         │
          │         /api/v1/* endpoints          │
          └──────────────────┬──────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                     CORE SERVICES LAYER                          │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────┐        │
│  │         API Service (FastAPI + Python 3.11)         │        │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │        │
│  │  │  Discovery  │  │   Detection  │  │   Auto-   │  │        │
│  │  │   Service   │  │    Service   │  │Fix Service│  │        │
│  │  └─────────────┘  └──────────────┘  └───────────┘  │        │
│  └──────────────────────────┬──────────────────────────┘        │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────┐        │
│  │          Background Workers (Celery)                │        │
│  │  • API Discovery Worker                             │        │
│  │  • Change Detection Worker                          │        │
│  │  • Code Generation Worker                           │        │
│  │  • GitHub Integration Worker                        │        │
│  └──────────────────────────┬──────────────────────────┘        │
└─────────────────────────────┼─────────────────────────────────┬─┘
                              │                                 │
┌─────────────────────────────▼─────────────────────────────────▼─┐
│                        DATA LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │     S3       │          │
│  │  (Primary    │  │   (Cache +   │  │(Code Samples,│          │
│  │   Database)  │  │    Queue)    │  │   Artifacts) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────────────────────────┘
           │                  │                  │
┌──────────▼──────────────────▼──────────────────▼────────────────┐
│                    EXTERNAL SERVICES                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   GitHub API │  │  Claude API  │  │   Sentry     │          │
│  │  (Webhooks,  │  │  (Code Gen)  │  │  (Error      │          │
│  │   REST API)  │  │              │  │  Tracking)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Frontend** | React 18 + TypeScript | Modern, type-safe, large ecosystem |
| **API Gateway** | Kong | Rate limiting, auth, routing |
| **Backend** | FastAPI (Python 3.11) | Async, fast, great for AI/ML integration |
| **Task Queue** | Celery + Redis | Proven, scalable background processing |
| **Primary DB** | PostgreSQL 15 | JSONB support, full-text search, reliability |
| **Cache** | Redis 7 | Fast, supports complex data structures |
| **Object Storage** | AWS S3 | Scalable, cheap, reliable |
| **Code Parsing** | libcst (Python), tree-sitter (multi-lang) | AST parsing, battle-tested |
| **AI/ML** | Claude API (Anthropic) | Best code generation quality |
| **Monitoring** | Sentry + Grafana + Prometheus | Error tracking + metrics |
| **Hosting** | AWS ECS Fargate | Serverless containers, auto-scaling |
| **CDN** | CloudFlare | Fast, DDoS protection |

---

## 2. Architecture Principles

### 2.1 Core Principles

1. **AI-First Design**: Every component assumes AI agents as primary consumers
2. **Event-Driven**: Use events for async processing (GitHub webhooks → queue → workers)
3. **Idempotent Operations**: All API calls can be retried safely
4. **Graceful Degradation**: System works (limited) even if AI services are down
5. **Security by Default**: No source code stored, read-only GitHub access
6. **Horizontal Scalability**: Add workers to handle load, no single bottleneck

### 2.2 Design Patterns

- **Repository Pattern**: Abstract data access behind interfaces
- **Strategy Pattern**: Pluggable parsers for different languages/frameworks
- **Observer Pattern**: Event subscriptions for change notifications
- **Command Pattern**: Background tasks as commands (retryable, logged)
- **Circuit Breaker**: Protect against external API failures (GitHub, Claude)

### 2.3 Non-Functional Requirements

| Requirement | Target | How We Achieve It |
|-------------|--------|-------------------|
| **Availability** | 99.9% uptime | Multi-AZ deployment, health checks, auto-restart |
| **Performance** | <2s API response | Caching, async workers, DB indexing |
| **Scalability** | 100k repos | Horizontal worker scaling, sharding |
| **Security** | SOC 2 Type II | Encryption, audit logs, pen testing |
| **Reliability** | <0.1% error rate | Retry logic, idempotency, monitoring |

---

## 3. System Components

### 3.1 Core Services

#### **3.1.1 API Service**

**Responsibilities**:
- Handle all HTTP requests from users and AI agents
- Authentication & authorization
- Rate limiting
- Request validation
- Serve web dashboard

**Tech Stack**:
- FastAPI (Python 3.11)
- Pydantic for validation
- JWT for authentication
- Redis for session storage

**Key Endpoints**:
```
POST   /api/v1/repos/sync               # Trigger repo discovery
GET    /api/v1/repos/{id}/apis          # List APIs in repo
GET    /api/v1/apis/{id}/consumers      # Who uses this API
POST   /api/v1/changes/{id}/auto-fix    # Generate migration PR
GET    /api/v1/dashboard/overview       # Dashboard data
```

**Scaling Strategy**:
- Stateless (can run multiple instances)
- Load balanced (ALB)
- Auto-scale based on CPU (50-80%)

---

#### **3.1.2 Discovery Service**

**Responsibilities**:
- Clone repositories (shallow clone, no history)
- Parse code to extract API definitions
- Detect framework (FastAPI, Express, Flask, etc.)
- Extract endpoints, schemas, auth requirements
- Build dependency graph

**Tech Stack**:
- libcst for Python AST parsing
- tree-sitter for multi-language parsing
- RegEx fallback for simple cases

**Algorithm**:
```python
async def discover_apis(repo_url: str) -> List[API]:
    # 1. Clone repo (shallow)
    repo = await git.clone(repo_url, depth=1)

    # 2. Detect framework
    framework = detect_framework(repo)  # Check requirements.txt, package.json

    # 3. Get parser strategy
    parser = ParserFactory.get_parser(framework)

    # 4. Parse code
    apis = []
    for file in repo.find_files(parser.file_pattern):
        tree = parser.parse(file)
        apis.extend(parser.extract_apis(tree))

    # 5. Store in database
    await db.bulk_insert_apis(apis)

    # 6. Update dependency graph
    await graph.update_dependencies(repo, apis)

    return apis
```

**Supported Frameworks (MVP)**:
- Python: FastAPI, Flask, Django REST Framework
- JavaScript: Express, NestJS
- TypeScript: Express, NestJS

**Performance**:
- Target: 1000 LOC/second
- Parallelization: 10 files at a time
- Avg repo (10k LOC): ~10 seconds

---

#### **3.1.3 Detection Service**

**Responsibilities**:
- Monitor GitHub webhooks for code changes
- Diff API schemas (old vs. new)
- Classify changes (breaking, warning, info)
- Find affected consumers
- Trigger notifications

**Algorithm**:
```python
async def detect_changes(commit: GitHubCommit) -> List[Change]:
    # 1. Get affected files
    changed_files = commit.files

    # 2. Re-parse only changed files
    old_apis = await db.get_apis(repo_id, before_commit)
    new_apis = await discover_apis_for_files(changed_files)

    # 3. Diff schemas
    changes = []
    for new_api in new_apis:
        old_api = find_matching(old_apis, new_api)
        if not old_api:
            changes.append(Change(type="NEW", api=new_api))
        else:
            diff = schema_diff(old_api.schema, new_api.schema)
            if diff.is_breaking:
                changes.append(Change(type="BREAKING", api=new_api, diff=diff))
            elif diff.is_warning:
                changes.append(Change(type="WARNING", api=new_api, diff=diff))

    # 4. Find consumers
    for change in changes:
        consumers = await graph.get_consumers(change.api.id)
        change.affected_repos = consumers

    # 5. Store changes
    await db.insert_changes(changes)

    # 6. Trigger notifications
    for change in changes:
        if change.type == "BREAKING":
            await notify_consumers(change)
            await block_ci_cd(commit) if settings.block_on_break else None

    return changes
```

**Breaking Change Rules**:
```python
def is_breaking_change(old_schema, new_schema) -> bool:
    # Removed endpoint
    if new_schema is None:
        return True

    # Changed HTTP method
    if old_schema.method != new_schema.method:
        return True

    # Removed required field from response
    for field in old_schema.response.required:
        if field not in new_schema.response.fields:
            return True

    # Added required field to request
    for field in new_schema.request.required:
        if field not in old_schema.request.required:
            return True

    # Changed field type
    for field_name in old_schema.response.fields:
        if field_name in new_schema.response.fields:
            if old_schema.response.fields[field_name].type != \
               new_schema.response.fields[field_name].type:
                return True

    return False
```

---

#### **3.1.4 Auto-Fix Service**

**Responsibilities**:
- Generate migration code for consumers
- Create GitHub Pull Requests
- Update type definitions, function calls, tests
- Provide migration instructions

**Tech Stack**:
- Claude API (Anthropic) for code generation
- libcst for Python AST rewriting
- ts-morph for TypeScript AST rewriting
- Black/Prettier for code formatting

**Algorithm**:
```python
async def generate_migration(change: Change, consumer_repo: Repo) -> PullRequest:
    # 1. Find affected code in consumer
    affected_files = await find_api_usages(consumer_repo, change.api)

    # 2. Generate migration code with Claude
    migration_code = await claude_generate_migration(
        old_schema=change.old_schema,
        new_schema=change.new_schema,
        affected_code=affected_files,
        language=consumer_repo.language
    )

    # 3. Apply changes (AST rewriting for precision)
    for file, new_code in migration_code.items():
        await ast_rewrite_file(file, new_code)

    # 4. Format code
    await format_code(migration_code.keys())

    # 5. Run tests (optional, if test suite exists)
    test_result = await run_tests(consumer_repo)

    # 6. Create PR
    pr = await github.create_pull_request(
        repo=consumer_repo,
        title=f"API Migration: {change.api.name}",
        body=generate_pr_description(change),
        branch=f"ai-agent-mesh/migration-{change.id}",
        files=migration_code
    )

    # 7. Add comment with instructions
    await github.add_pr_comment(pr, generate_instructions(change, test_result))

    return pr
```

**Claude Prompt Template**:
```python
MIGRATION_PROMPT = """
You are an expert software engineer helping migrate code to a new API version.

## API Change
**Endpoint**: {endpoint}
**Old Schema**:
```json
{old_schema}
```

**New Schema**:
```json
{new_schema}
```

**Change Type**: {change_type}
**Breaking**: {is_breaking}

## Code to Update
File: {filename}
```{language}
{old_code}
```

## Task
Generate the updated code that works with the new API schema.
- Update function calls to match new schema
- Update type definitions
- Handle new required fields appropriately
- Add error handling if needed
- Preserve existing logic

Return only the updated code, no explanations.
"""
```

---

### 3.2 Background Workers

#### **3.2.1 API Discovery Worker**

**Trigger**: GitHub webhook (push event) OR manual sync
**Frequency**: Real-time (webhook) or on-demand
**Duration**: 10-60 seconds per repo

**Implementation**:
```python
@celery.task(bind=True, max_retries=3)
async def discover_repo_apis(self, repo_id: str):
    try:
        repo = await db.get_repo(repo_id)
        apis = await DiscoveryService.discover_apis(repo.url)
        await db.update_repo_apis(repo_id, apis)

        # Trigger dependency graph update
        await update_dependency_graph.delay(repo_id)

        logger.info(f"Discovered {len(apis)} APIs in {repo.name}")
    except Exception as exc:
        # Exponential backoff: 1s, 2s, 4s
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

---

#### **3.2.2 Change Detection Worker**

**Trigger**: GitHub webhook (push event)
**Frequency**: Real-time
**Duration**: 5-30 seconds

**Implementation**:
```python
@celery.task(bind=True)
async def detect_api_changes(self, commit_sha: str, repo_id: str):
    commit = await github.get_commit(repo_id, commit_sha)
    changes = await DetectionService.detect_changes(commit)

    for change in changes:
        # Store change
        await db.insert_change(change)

        # Notify consumers
        if change.is_breaking:
            await notify_breaking_change.delay(change.id)

        # Update context files
        for consumer in change.affected_repos:
            await inject_context.delay(consumer.id, change.id)

    return len(changes)
```

---

#### **3.2.3 Context Injection Worker**

**Trigger**: Breaking change detected
**Frequency**: Real-time
**Duration**: 2-10 seconds

**Implementation**:
```python
@celery.task
async def inject_context(consumer_repo_id: str, change_id: str):
    change = await db.get_change(change_id)
    consumer = await db.get_repo(consumer_repo_id)

    # Generate context markdown
    context_md = generate_context_markdown(change)

    # Detect AI agent type
    ai_agent = detect_ai_agent(consumer)  # Claude Code, Cursor, Copilot

    # Write to appropriate context file
    context_file_path = AI_AGENT_CONTEXT_PATHS[ai_agent]

    await github.create_or_update_file(
        repo=consumer,
        path=context_file_path,
        content=context_md,
        message=f"AI Agent Mesh: API change detected in {change.provider_repo}"
    )

    logger.info(f"Injected context for {consumer.name} ({ai_agent})")
```

**AI Agent Context Paths**:
```python
AI_AGENT_CONTEXT_PATHS = {
    "claude_code": ".claude/api-changes.md",
    "cursor": ".cursor/context.md",
    "github_copilot": ".github/copilot/context.json",
    "cody": ".cody/context.md"
}
```

---

#### **3.2.4 Auto-Fix Worker**

**Trigger**: User clicks "Auto-Fix" button
**Frequency**: On-demand
**Duration**: 30-120 seconds (depends on Claude API)

**Implementation**:
```python
@celery.task(bind=True, max_retries=2)
async def generate_auto_fix(self, change_id: str, consumer_repo_id: str):
    try:
        change = await db.get_change(change_id)
        consumer = await db.get_repo(consumer_repo_id)

        # Generate migration
        pr = await AutoFixService.generate_migration(change, consumer)

        # Store PR reference
        await db.update_change(change_id, pr_url=pr.url)

        # Notify user
        await notify_pr_created(consumer.owner_email, pr.url)

        return pr.url
    except ClaudeAPIError as exc:
        # Retry on API errors
        raise self.retry(exc=exc, countdown=60)
```

---

## 4. Data Models

### 4.1 Entity-Relationship Diagram

```
┌────────────┐       ┌────────────┐       ┌────────────┐
│   User     │──────<│   Repo     │>─────<│    API     │
│            │       │            │       │            │
│ • id       │       │ • id       │       │ • id       │
│ • email    │       │ • url      │       │ • endpoint │
│ • name     │       │ • name     │       │ • method   │
│ • github_id│       │ • language │       │ • schema   │
└────────────┘       │ • framework│       │ • repo_id  │
                     └────────────┘       └────────────┘
                            │                     │
                            │                     │
                     ┌──────▼──────┐       ┌──────▼──────┐
                     │  APIChange  │       │ Dependency  │
                     │             │       │             │
                     │ • id        │       │ • id        │
                     │ • api_id    │       │ • provider  │
                     │ • old_schema│       │ • consumer  │
                     │ • new_schema│       │ • api_id    │
                     │ • type      │       └─────────────┘
                     │ • detected_at
                     └─────────────┘
                            │
                            │
                     ┌──────▼──────┐
                     │  Migration  │
                     │             │
                     │ • id        │
                     │ • change_id │
                     │ • pr_url    │
                     │ • status    │
                     │ • created_at│
                     └─────────────┘
```

### 4.2 Database Schema (PostgreSQL)

#### **users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    github_id INTEGER UNIQUE NOT NULL,
    github_access_token TEXT,
    plan VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_github_id ON users(github_id);
```

#### **repos**
```sql
CREATE TABLE repos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    github_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,  -- "owner/repo"
    url TEXT NOT NULL,
    language VARCHAR(50),
    framework VARCHAR(50),
    default_branch VARCHAR(100) DEFAULT 'main',
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_repos_user_id ON repos(user_id);
CREATE INDEX idx_repos_github_id ON repos(github_id);
CREATE INDEX idx_repos_full_name ON repos(full_name);
```

#### **apis**
```sql
CREATE TABLE apis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID REFERENCES repos(id) ON DELETE CASCADE,
    endpoint VARCHAR(500) NOT NULL,  -- "/api/v1/users/{id}"
    method VARCHAR(10) NOT NULL,     -- "GET", "POST", etc.
    file_path TEXT NOT NULL,         -- "app/api/users.py"
    line_number INTEGER,
    schema JSONB NOT NULL,           -- OpenAPI-like schema
    auth_type VARCHAR(50),           -- "bearer", "api_key", "none"
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(repo_id, endpoint, method)
);

CREATE INDEX idx_apis_repo_id ON apis(repo_id);
CREATE INDEX idx_apis_endpoint ON apis(endpoint);
CREATE INDEX idx_apis_method ON apis(method);
CREATE INDEX idx_apis_schema ON apis USING GIN (schema);  -- JSONB index
```

**Example schema JSONB**:
```json
{
  "request": {
    "parameters": [
      {"name": "id", "in": "path", "type": "string", "required": true}
    ],
    "body": {
      "type": "object",
      "properties": {
        "name": {"type": "string", "required": true},
        "email": {"type": "string", "required": false}
      }
    }
  },
  "response": {
    "200": {
      "type": "object",
      "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "created_at": {"type": "string", "format": "date-time"}
      }
    },
    "404": {
      "type": "object",
      "properties": {
        "error": {"type": "string"}
      }
    }
  }
}
```

#### **dependencies**
```sql
CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_api_id UUID REFERENCES apis(id) ON DELETE CASCADE,
    consumer_repo_id UUID REFERENCES repos(id) ON DELETE CASCADE,
    consumer_file_path TEXT NOT NULL,
    consumer_line_number INTEGER,
    detected_at TIMESTAMP DEFAULT NOW(),
    last_verified_at TIMESTAMP,

    UNIQUE(provider_api_id, consumer_repo_id, consumer_file_path)
);

CREATE INDEX idx_deps_provider ON dependencies(provider_api_id);
CREATE INDEX idx_deps_consumer ON dependencies(consumer_repo_id);
```

#### **api_changes**
```sql
CREATE TABLE api_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_id UUID REFERENCES apis(id) ON DELETE CASCADE,
    commit_sha VARCHAR(40) NOT NULL,
    old_schema JSONB,
    new_schema JSONB NOT NULL,
    change_type VARCHAR(20) NOT NULL,  -- "BREAKING", "WARNING", "INFO", "NEW"
    is_breaking BOOLEAN DEFAULT false,
    affected_repos_count INTEGER DEFAULT 0,
    detected_at TIMESTAMP DEFAULT NOW(),
    notified_at TIMESTAMP
);

CREATE INDEX idx_changes_api_id ON api_changes(api_id);
CREATE INDEX idx_changes_type ON api_changes(change_type);
CREATE INDEX idx_changes_breaking ON api_changes(is_breaking);
CREATE INDEX idx_changes_detected_at ON api_changes(detected_at DESC);
```

#### **migrations**
```sql
CREATE TABLE migrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_id UUID REFERENCES api_changes(id) ON DELETE CASCADE,
    consumer_repo_id UUID REFERENCES repos(id) ON DELETE CASCADE,
    pr_url TEXT,
    pr_number INTEGER,
    status VARCHAR(50) DEFAULT 'pending',  -- "pending", "pr_created", "merged", "failed"
    generated_code JSONB,  -- Map of file_path → new_code
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_migrations_change_id ON migrations(change_id);
CREATE INDEX idx_migrations_consumer ON migrations(consumer_repo_id);
CREATE INDEX idx_migrations_status ON migrations(status);
```

---

## 5. API Architecture

### 5.1 REST API Design

**Base URL**: `https://api.aigentmesh.com/v1`

**Authentication**: Bearer token (JWT)
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Error Format** (RFC 7807):
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

### 5.2 Key Endpoints

#### **POST /v1/repos/sync**
Trigger API discovery for a repository.

**Request**:
```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main"
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "estimated_duration": 30,
  "status_url": "/v1/jobs/job_abc123"
}
```

---

#### **GET /v1/repos/{repo_id}/apis**
List all APIs in a repository.

**Query Parameters**:
- `method`: Filter by HTTP method (GET, POST, etc.)
- `endpoint`: Search endpoint by pattern
- `limit`: Pagination limit (default: 50, max: 100)
- `offset`: Pagination offset

**Response**:
```json
{
  "apis": [
    {
      "id": "api_xyz789",
      "endpoint": "/api/v1/users/{id}",
      "method": "GET",
      "file_path": "app/api/users.py",
      "line_number": 42,
      "schema": {...},
      "consumers_count": 3,
      "last_changed_at": "2025-11-20T14:30:00Z"
    }
  ],
  "total": 23,
  "limit": 50,
  "offset": 0
}
```

---

#### **GET /v1/apis/{api_id}/consumers**
Get list of repositories that consume this API.

**Response**:
```json
{
  "api": {
    "id": "api_xyz789",
    "endpoint": "/api/intelligence/analyze",
    "provider_repo": "quimbi/ai-backend"
  },
  "consumers": [
    {
      "repo_id": "repo_abc123",
      "repo_name": "quimbi/support-backend",
      "file_path": "app/services/quimbi_client.py",
      "line_number": 45,
      "last_verified": "2025-11-25T10:00:00Z"
    },
    {
      "repo_id": "repo_def456",
      "repo_name": "quimbi/marketing-backend",
      "file_path": "app/services/intelligence.py",
      "line_number": 23,
      "last_verified": "2025-11-25T10:00:00Z"
    }
  ]
}
```

---

#### **POST /v1/changes/{change_id}/auto-fix**
Generate migration code and create PR.

**Request**:
```json
{
  "consumer_repo_id": "repo_abc123",
  "create_pr": true,
  "run_tests": false
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

#### **GET /v1/dashboard/overview**
Dashboard summary data.

**Response**:
```json
{
  "repos_count": 4,
  "apis_count": 23,
  "dependencies_count": 45,
  "breaking_changes_last_7_days": 2,
  "recent_changes": [
    {
      "id": "change_xyz",
      "api": {
        "endpoint": "/api/intelligence/analyze",
        "provider_repo": "quimbi/ai-backend"
      },
      "type": "BREAKING",
      "affected_repos": 2,
      "detected_at": "2025-11-25T10:30:00Z",
      "auto_fix_available": true
    }
  ],
  "dependency_graph": {
    "nodes": [
      {"id": "repo_1", "name": "quimbi/ai-backend", "type": "provider"},
      {"id": "repo_2", "name": "quimbi/support-backend", "type": "consumer"}
    ],
    "edges": [
      {"source": "repo_1", "target": "repo_2", "api_count": 3}
    ]
  }
}
```

---

## 6. Processing Pipeline

### 6.1 Discovery Pipeline

```
GitHub Webhook (push)
        │
        ▼
   ┌────────────────┐
   │ Webhook Handler│
   │   (FastAPI)    │
   └────────┬───────┘
            │
            ▼
   ┌────────────────┐
   │  Celery Queue  │
   │   (Redis)      │
   └────────┬───────┘
            │
            ▼
   ┌────────────────┐
   │Discovery Worker│
   └────────┬───────┘
            │
     ┌──────┴────────┬───────────┐
     │               │           │
     ▼               ▼           ▼
┌─────────┐   ┌──────────┐  ┌────────┐
│Git Clone│   │Parse Code│  │Extract │
│(shallow)│   │(AST/Regex│  │  APIs  │
└─────────┘   └──────────┘  └────────┘
     │               │           │
     └───────┬───────┴───────────┘
             │
             ▼
    ┌────────────────┐
    │  Store in DB   │
    │  (PostgreSQL)  │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │Update Dep Graph│
    └────────────────┘
```

**Latency Breakdown**:
- Webhook → Queue: <100ms
- Queue → Worker pickup: <1s
- Git clone (shallow): 2-5s
- Parse code: 5-20s (depends on size)
- Store in DB: <1s
- **Total: 10-30s for average repo**

---

### 6.2 Change Detection Pipeline

```
GitHub Webhook (push)
        │
        ▼
   ┌────────────────┐
   │ Webhook Handler│
   └────────┬───────┘
            │
            ▼
   ┌────────────────┐
   │Detection Worker│
   └────────┬───────┘
            │
     ┌──────┴────────┬─────────┐
     │               │         │
     ▼               ▼         ▼
┌─────────┐   ┌──────────┐  ┌────────┐
│Get Diff │   │Re-parse  │  │Schema  │
│(GitHub  │   │Changed   │  │  Diff  │
│  API)   │   │  Files   │  │        │
└─────────┘   └──────────┘  └────────┘
     │               │         │
     └───────┬───────┴─────────┘
             │
             ▼
    ┌────────────────┐
    │Classify Change │
    │(Breaking/Warn) │
    └────────┬───────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│Find      │  │Store     │
│Consumers │  │Change    │
└──────────┘  └──────────┘
      │             │
      └──────┬──────┘
             │
             ▼
    ┌────────────────┐
    │   Notify       │
    │• Context Inject│
    │• Email/Slack   │
    │• Block CI/CD   │
    └────────────────┘
```

**Latency Breakdown**:
- Webhook → Worker: <1s
- Get diff: <500ms
- Re-parse files: 2-10s
- Schema diff: <100ms
- Find consumers: <500ms (graph query)
- Notify: <2s
- **Total: 5-15s**

---

### 6.3 Auto-Fix Pipeline

```
User clicks "Auto-Fix"
        │
        ▼
   ┌────────────────┐
   │  API Endpoint  │
   └────────┬───────┘
            │
            ▼
   ┌────────────────┐
   │Auto-Fix Worker │
   └────────┬───────┘
            │
     ┌──────┴────────┬──────────┐
     │               │          │
     ▼               ▼          ▼
┌─────────┐   ┌──────────┐  ┌────────┐
│Find     │   │Clone     │  │Prepare │
│Affected │   │Consumer  │  │Context │
│ Code    │   │  Repo    │  │        │
└─────────┘   └──────────┘  └────────┘
     │               │          │
     └───────┬───────┴──────────┘
             │
             ▼
    ┌────────────────┐
    │  Claude API    │
    │(Code Generation│
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │  AST Rewrite   │
    │  (Apply Code)  │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ Format Code    │
    │(Black/Prettier)│
    └────────┬───────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│Run Tests │  │Create PR │
│(Optional)│  │(GitHub)  │
└──────────┘  └──────────┘
      │             │
      └──────┬──────┘
             │
             ▼
    ┌────────────────┐
    │   Notify User  │
    └────────────────┘
```

**Latency Breakdown**:
- Find affected code: 2-5s
- Clone repo: 3-5s
- Claude API call: 10-30s (depends on code size)
- AST rewrite: 1-3s
- Create PR: 1-2s
- **Total: 30-60s**

---

## 7. AI/ML Components

### 7.1 Code Generation (Claude API)

**Model**: Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)

**Why Claude?**:
- Best code generation quality (beats GPT-4 on benchmarks)
- 200k context window (can handle large files)
- Follows instructions precisely
- Good at multi-step reasoning

**Prompt Engineering**:
```python
SYSTEM_PROMPT = """
You are an expert software engineer specializing in API migrations.
Your goal is to update code to work with a new API version while:
1. Preserving existing business logic
2. Maintaining code style
3. Adding proper error handling
4. Updating type definitions
5. Being conservative (don't over-engineer)

Always return only the updated code, no explanations.
"""

USER_PROMPT_TEMPLATE = """
## API Change
Endpoint: {endpoint}
Change: {change_description}

**Old Schema**:
```json
{old_schema}
```

**New Schema**:
```json
{new_schema}
```

## Code to Update
File: {file_path}
```{language}
{current_code}
```

## Task
Update the code to work with the new schema.
Focus on lines {start_line}-{end_line} but provide full file.
"""
```

**Retry Strategy**:
```python
async def call_claude_with_retry(prompt: str, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except RateLimitError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
```

**Cost Estimation**:
- Input: ~$3 per 1M tokens
- Output: ~$15 per 1M tokens
- Average migration: 2k input + 2k output tokens = $0.04 per migration
- At 1000 migrations/month: $40/month in Claude API costs

---

### 7.2 Schema Diffing Algorithm

```python
def schema_diff(old: dict, new: dict) -> SchemaDiff:
    """
    Compute semantic difference between two API schemas.
    Returns classification and list of changes.
    """
    changes = []

    # Check HTTP method change
    if old.get("method") != new.get("method"):
        changes.append(Change(
            type="METHOD_CHANGED",
            severity="BREAKING",
            old_value=old.get("method"),
            new_value=new.get("method")
        ))

    # Check request schema changes
    req_changes = diff_request_schema(old.get("request"), new.get("request"))
    changes.extend(req_changes)

    # Check response schema changes
    resp_changes = diff_response_schema(old.get("response"), new.get("response"))
    changes.extend(resp_changes)

    # Classify overall severity
    if any(c.severity == "BREAKING" for c in changes):
        severity = "BREAKING"
    elif any(c.severity == "WARNING" for c in changes):
        severity = "WARNING"
    else:
        severity = "INFO"

    return SchemaDiff(
        severity=severity,
        changes=changes,
        is_breaking=severity == "BREAKING"
    )

def diff_request_schema(old: dict, new: dict) -> List[Change]:
    changes = []

    # New required parameter = BREAKING
    old_required = set(old.get("required", []))
    new_required = set(new.get("required", []))

    added_required = new_required - old_required
    for field in added_required:
        changes.append(Change(
            type="REQUEST_REQUIRED_ADDED",
            severity="BREAKING",
            field=field
        ))

    # Removed optional parameter = INFO
    removed_optional = old_required - new_required
    for field in removed_optional:
        if field not in new.get("properties", {}):
            changes.append(Change(
                type="REQUEST_FIELD_REMOVED",
                severity="WARNING",
                field=field
            ))

    # Type changes = BREAKING
    for field in old.get("properties", {}):
        if field in new.get("properties", {}):
            old_type = old["properties"][field].get("type")
            new_type = new["properties"][field].get("type")
            if old_type != new_type:
                changes.append(Change(
                    type="REQUEST_TYPE_CHANGED",
                    severity="BREAKING",
                    field=field,
                    old_value=old_type,
                    new_value=new_type
                ))

    return changes
```

---

## 8. Infrastructure

### 8.1 AWS Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Route 53 (DNS)                       │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                CloudFront (CDN)                          │
│  • TLS Termination                                       │
│  • DDoS Protection (AWS Shield)                          │
│  • Caching (static assets)                               │
└────────────────────────┬─────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌────────────────┐              ┌────────────────┐
│  S3 (Frontend) │              │      ALB       │
│   React App    │              │ (API Gateway)  │
└────────────────┘              └────────┬───────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │                             │
                          ▼                             ▼
                  ┌────────────────┐          ┌────────────────┐
                  │  ECS Fargate   │          │  ECS Fargate   │
                  │  (API Service) │          │   (Workers)    │
                  │                │          │                │
                  │  Auto-scaling  │          │  Auto-scaling  │
                  │  Min: 2        │          │  Min: 1        │
                  │  Max: 20       │          │  Max: 50       │
                  └────────┬───────┘          └────────┬───────┘
                           │                           │
                    ┌──────┴───────┬───────────────────┘
                    │              │
                    ▼              ▼
            ┌────────────┐  ┌────────────┐
            │ PostgreSQL │  │   Redis    │
            │   (RDS)    │  │(ElastiCache│
            │            │  │            │
            │ Multi-AZ   │  │ Cluster    │
            │ Replicas   │  │ Mode       │
            └────────────┘  └────────────┘
```

### 8.2 Resource Sizing (MVP)

| Component | Instance Type | Count | Specs | Monthly Cost |
|-----------|---------------|-------|-------|--------------|
| **ECS API** | Fargate 0.5 vCPU, 1GB | 2-10 | Auto-scale | ~$50-250 |
| **ECS Workers** | Fargate 1 vCPU, 2GB | 1-20 | Auto-scale | ~$50-500 |
| **RDS PostgreSQL** | db.t3.medium | 1 + 1 replica | 2 vCPU, 4GB | ~$150 |
| **ElastiCache Redis** | cache.t3.small | 2 node cluster | 2GB | ~$50 |
| **S3** | Standard | - | Frontend assets | ~$5 |
| **CloudFront** | Standard | - | CDN | ~$20 |
| **ALB** | Application | 1 | - | ~$20 |
| **Data Transfer** | - | - | 500GB/month | ~$50 |
| **Total** | | | | **~$400-1000/month** |

### 8.3 Scaling Strategy

**API Service**:
- Metric: CPU > 70% for 2 minutes → scale up
- Metric: CPU < 30% for 5 minutes → scale down
- Min: 2 (high availability)
- Max: 20

**Workers**:
- Metric: Queue depth > 100 → scale up
- Metric: Queue depth < 10 for 5 minutes → scale down
- Min: 1
- Max: 50

**Database**:
- Start: db.t3.medium (2 vCPU, 4GB RAM)
- At 1000 customers: db.r5.large (2 vCPU, 16GB RAM)
- Read replicas for read-heavy queries (dashboard)

---

## 9. Security Architecture

### 9.1 Authentication & Authorization

**User Authentication**:
- OAuth 2.0 with GitHub (primary)
- JWT tokens (1-day expiry)
- Refresh tokens (30-day expiry)
- Token stored in httpOnly cookie

**API Authentication**:
```python
# Every API request
Authorization: Bearer <jwt_token>

# JWT payload
{
  "sub": "user_abc123",
  "email": "user@example.com",
  "plan": "team",
  "exp": 1732578000
}
```

**GitHub Access**:
- Request only `repo` scope (read-only)
- User can revoke access anytime
- Access token encrypted at rest (AES-256)

**RBAC (Role-Based Access Control)**:
```python
PERMISSIONS = {
    "free": ["read_repos", "read_apis"],
    "starter": ["read_repos", "read_apis", "sync_repos", "create_auto_fix"],
    "team": ["*"],  # All permissions
    "enterprise": ["*", "admin"]
}

def require_permission(permission: str):
    def decorator(func):
        async def wrapper(request: Request):
            user = await get_current_user(request)
            if not has_permission(user.plan, permission):
                raise HTTPException(403, "Insufficient permissions")
            return await func(request)
        return wrapper
    return decorator

@router.post("/repos/{id}/sync")
@require_permission("sync_repos")
async def sync_repo(id: str):
    ...
```

### 9.2 Data Security

**Encryption**:
- At rest: AES-256 (RDS encryption, S3 encryption)
- In transit: TLS 1.3
- Secrets: AWS Secrets Manager

**Data Storage Policy**:
- ✅ API schemas (stored)
- ✅ File paths, line numbers (stored)
- ❌ Source code (NOT stored, only cloned temporarily)
- ❌ GitHub access tokens (encrypted at rest)

**Data Retention**:
- Free: 7 days
- Starter: 90 days
- Team: 1 year
- Enterprise: Custom

**GDPR Compliance**:
- Right to deletion: `DELETE /v1/users/me` (deletes all data)
- Right to export: `GET /v1/users/me/export` (JSON file)
- Privacy policy: Clear explanation of data usage

### 9.3 Security Best Practices

**Application Security**:
- [ ] SQL injection protection (Parameterized queries)
- [ ] XSS protection (React escapes by default)
- [ ] CSRF protection (SameSite cookies)
- [ ] Rate limiting (100 req/min per user)
- [ ] Input validation (Pydantic schemas)

**Infrastructure Security**:
- [ ] VPC with private subnets
- [ ] Security groups (least privilege)
- [ ] WAF (Web Application Firewall)
- [ ] DDoS protection (AWS Shield)
- [ ] Secrets rotation (90 days)

**Monitoring**:
- [ ] Sentry for error tracking
- [ ] CloudWatch for infra metrics
- [ ] Audit logs for sensitive operations
- [ ] Anomaly detection (unusual API usage)

---

## 10. Scalability & Performance

### 10.1 Performance Targets

| Operation | Target Latency | Current | Status |
|-----------|----------------|---------|--------|
| API List | <200ms (p95) | - | Not built |
| Dashboard Load | <2s | - | Not built |
| Discovery (avg repo) | <30s | - | Not built |
| Change Detection | <15s | - | Not built |
| Auto-Fix Generation | <60s | - | Not built |

### 10.2 Caching Strategy

**Layer 1: CDN (CloudFront)**
- Static assets (JS, CSS, images)
- TTL: 1 year (cache busting via hashes)

**Layer 2: Application Cache (Redis)**
```python
# API responses (for dashboard)
@cache(ttl=300)  # 5 minutes
async def get_dashboard_overview(user_id: str):
    ...

# Dependency graph
@cache(ttl=3600)  # 1 hour
async def get_dependency_graph(user_id: str):
    ...

# API schemas
@cache(ttl=1800)  # 30 minutes
async def get_api_schema(api_id: str):
    ...
```

**Layer 3: Database Query Cache**
- PostgreSQL query cache (automatic)
- Materialized views for complex queries

**Cache Invalidation**:
```python
# When API changes
async def on_api_change(api_id: str):
    await cache.delete(f"api:schema:{api_id}")
    await cache.delete(f"repo:apis:{api.repo_id}")
    await cache.delete(f"dashboard:overview:{api.user_id}")
    await cache.delete(f"graph:{api.user_id}")
```

### 10.3 Database Optimization

**Indexes**:
```sql
-- APIs table
CREATE INDEX idx_apis_repo_id ON apis(repo_id);
CREATE INDEX idx_apis_endpoint ON apis USING GIN (endpoint gin_trgm_ops);  -- Full-text search
CREATE INDEX idx_apis_schema ON apis USING GIN (schema);  -- JSONB search

-- Dependencies table
CREATE INDEX idx_deps_provider ON dependencies(provider_api_id);
CREATE INDEX idx_deps_consumer ON dependencies(consumer_repo_id);

-- Changes table
CREATE INDEX idx_changes_detected_at ON api_changes(detected_at DESC);
CREATE INDEX idx_changes_breaking ON api_changes(is_breaking) WHERE is_breaking = true;
```

**Query Optimization**:
```python
# Bad: N+1 query
repos = await db.query("SELECT * FROM repos WHERE user_id = ?", user_id)
for repo in repos:
    apis = await db.query("SELECT * FROM apis WHERE repo_id = ?", repo.id)

# Good: Join
result = await db.query("""
    SELECT r.*, array_agg(a.*) as apis
    FROM repos r
    LEFT JOIN apis a ON a.repo_id = r.id
    WHERE r.user_id = ?
    GROUP BY r.id
""", user_id)
```

**Read Replicas**:
- All writes → Primary DB
- All reads (dashboard, API list) → Read replica
- Eventual consistency acceptable (1-2 second lag)

### 10.4 Horizontal Scaling

**Stateless Services**:
- API service: Can run N instances
- Workers: Can run N instances
- No shared state (all state in DB/Redis)

**Load Balancing**:
- ALB distributes traffic across API instances
- Celery distributes tasks across workers

**Database Sharding** (Future - 10,000+ customers):
- Shard by user_id (consistent hashing)
- Each shard handles 1000-2000 customers

---

## 11. Monitoring & Observability

### 11.1 Metrics (Prometheus + Grafana)

**Application Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
http_request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['endpoint'])

# Business metrics
apis_discovered_total = Counter('apis_discovered_total', 'APIs discovered')
breaking_changes_detected = Counter('breaking_changes_detected', 'Breaking changes detected')
auto_fixes_generated = Counter('auto_fixes_generated', 'Auto-fixes generated', ['status'])

# System metrics
celery_queue_depth = Gauge('celery_queue_depth', 'Tasks in queue', ['queue'])
active_workers = Gauge('active_workers', 'Active worker count')
```

**Grafana Dashboards**:
1. **System Health**
   - Request rate, error rate, latency (p50, p95, p99)
   - Worker queue depth
   - Database connection pool usage

2. **Business Metrics**
   - APIs discovered per day
   - Breaking changes detected per day
   - Auto-fixes generated per day
   - User signups, churn

3. **Cost Dashboard**
   - AWS costs by service
   - Claude API costs
   - Per-customer cost

### 11.2 Logging (ELK Stack Alternative: Loki)

**Structured Logging**:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "api_discovered",
    repo_id=repo.id,
    repo_name=repo.name,
    api_count=len(apis),
    duration_seconds=elapsed,
    user_id=user.id
)
```

**Log Levels**:
- DEBUG: Detailed trace (disabled in prod)
- INFO: Normal operations (API discovered, change detected)
- WARNING: Unexpected but handled (Claude API timeout, retry)
- ERROR: Errors that need attention (DB connection failed)
- CRITICAL: System down (can't connect to Redis)

**Log Aggregation**:
- All logs → Loki (Grafana)
- Errors → Sentry
- Retention: 30 days

### 11.3 Alerting (PagerDuty)

**Critical Alerts** (wake someone up):
- API error rate > 5% for 5 minutes
- Database down
- All workers down
- Zero successful API discoveries for 1 hour

**Warning Alerts** (Slack):
- API error rate > 1% for 10 minutes
- Queue depth > 1000 for 10 minutes
- Claude API errors > 10% for 5 minutes

**Info Alerts** (Email):
- Daily usage report
- Weekly cost report

### 11.4 Tracing (Jaeger / Tempo)

**Distributed Tracing**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def discover_apis(repo_id: str):
    with tracer.start_as_current_span("discover_apis") as span:
        span.set_attribute("repo_id", repo_id)

        with tracer.start_as_current_span("git_clone"):
            repo = await git.clone(repo_url)

        with tracer.start_as_current_span("parse_code"):
            apis = await parser.extract_apis(repo)

        with tracer.start_as_current_span("db_insert"):
            await db.bulk_insert_apis(apis)
```

**Trace Example**:
```
discover_apis [32.4s]
  ├─ git_clone [3.2s]
  ├─ parse_code [28.1s]
  │   ├─ parse_file [0.8s] (x35 files)
  │   └─ extract_routes [0.4s] (x35 files)
  └─ db_insert [1.1s]
```

---

## 12. Disaster Recovery

### 12.1 Backup Strategy

**Database (RDS)**:
- Automated daily snapshots (retained 7 days)
- Point-in-time recovery (up to 5 minutes ago)
- Cross-region replication (for enterprise tier)

**S3 (Code samples, artifacts)**:
- Versioning enabled
- Cross-region replication
- Lifecycle policy (delete after 90 days for free tier)

**Secrets (AWS Secrets Manager)**:
- Automatic rotation every 90 days
- Version history (last 10 versions)

### 12.2 Failure Scenarios

| Scenario | Impact | Recovery | RTO | RPO |
|----------|--------|----------|-----|-----|
| **Single API instance down** | None (ALB routes to healthy) | Auto (health check) | 1 min | 0 |
| **All API instances down** | Dashboard unavailable | Manual restart | 5 min | 0 |
| **Database primary down** | Writes fail, reads work (replica) | Auto failover | 2 min | <1 min |
| **Redis down** | No caching, slower | Auto failover | 2 min | 0 (cache) |
| **Entire region down** | Service unavailable | Manual (cross-region) | 30 min | 5 min |
| **Data corruption** | Partial data loss | Restore from snapshot | 1 hour | Up to 24h |

**RTO** (Recovery Time Objective): How long before service is back
**RPO** (Recovery Point Objective): How much data can be lost

### 12.3 Runbooks

**Runbook: Database Failover**
```bash
# 1. Detect issue
aws rds describe-db-instances --db-instance-identifier prod-db

# 2. Check replica health
aws rds describe-db-instances --db-instance-identifier prod-db-replica

# 3. Promote replica to primary
aws rds promote-read-replica --db-instance-identifier prod-db-replica

# 4. Update connection string in API service
kubectl set env deployment/api-service DATABASE_URL=<new_url>

# 5. Verify
curl https://api.aigentmesh.com/health
```

**Runbook: Mass API Discovery Failure**
```bash
# 1. Check worker status
kubectl get pods -l app=worker

# 2. Check queue depth
redis-cli LLEN celery:discovery

# 3. Check recent errors
sentry-cli issues list --query "is:unresolved" --last 1h

# 4. If GitHub rate limit:
#    - Wait for rate limit reset (check headers)
#    - Or use enterprise GitHub token

# 5. Restart workers if needed
kubectl rollout restart deployment/workers
```

---

## 13. Open Technical Questions

1. **Should we support GraphQL APIs?**
   - Complexity: High (different schema format)
   - Demand: Unknown
   - Decision: Defer to post-MVP, validate demand first

2. **How to handle private/internal APIs?**
   - Issue: Some APIs are internal-only, not exposed externally
   - Options:
     - Auto-detect based on decorator (`@internal`)
     - Require manual tagging
     - Ignore (treat all APIs as potentially external)
   - Decision: TBD based on beta feedback

3. **Should workers run in same cluster as API?**
   - Pro: Simpler deployment
   - Con: Resource contention
   - Decision: Separate ECS services, can scale independently

4. **Database: Single table vs. separate tables per customer?**
   - Single table: Simpler, harder to scale
   - Separate tables: More complex, easier to shard
   - Decision: Single table for MVP, shard at 10k customers

---

## 14. Appendix

### 14.1 Technology Evaluation

| Technology | Evaluated | Decision | Reason |
|------------|-----------|----------|--------|
| **FastAPI vs Flask** | ✅ | FastAPI | Async, auto docs, Pydantic validation |
| **PostgreSQL vs MongoDB** | ✅ | PostgreSQL | JSONB for flexibility + relational for graphs |
| **Celery vs RQ vs Temporal** | ✅ | Celery | Mature, battle-tested, good monitoring |
| **Claude vs GPT-4** | ✅ | Claude | Better code quality, longer context |
| **ECS vs EKS** | ✅ | ECS Fargate | Simpler, serverless, lower ops burden |
| **Kong vs Nginx** | ✅ | Kong | Built-in rate limiting, plugins |

### 14.2 Reference Architecture

Based on:
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Twelve-Factor App](https://12factor.net/)
- [Microservices Patterns (Chris Richardson)](https://microservices.io/)

---

**Document Version History**:
- v1.0 (2025-11-25): Initial architecture

**Next Review**: 2025-12-09

**Approvals**:
- [ ] Engineering Lead
- [ ] DevOps Lead
- [ ] Security Lead
- [ ] CTO
