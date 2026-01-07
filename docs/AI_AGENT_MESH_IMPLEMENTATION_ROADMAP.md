# AI Agent Mesh - Implementation Roadmap

**Version**: 1.0
**Date**: 2025-11-25
**Timeline**: 12 weeks to MVP
**Related**: [PRD](./AI_AGENT_MESH_PRD.md), [Architecture](./AI_AGENT_MESH_TECHNICAL_ARCHITECTURE.md), [API Spec](./AI_AGENT_MESH_API_SPEC.md)

---

## Executive Summary

This roadmap details the 12-week journey from concept to MVP for AI Agent Mesh. The implementation is broken into 4 major phases:

1. **Weeks 1-3**: Foundation (Auth, Database, Basic Discovery)
2. **Weeks 4-6**: Core Features (Change Detection, Context Injection)
3. **Weeks 7-9**: Auto-Fix (Code Generation, PR Creation)
4. **Weeks 10-12**: Polish (Dashboard, Testing, Launch Prep)

**Team Required**: 1-2 full-stack engineers
**Budget**: ~$2,000 (infrastructure + Claude API)
**Success Criteria**: 50 beta users with >80% week-1 retention

---

## Phase 1: Foundation (Weeks 1-3)

### Week 1: Infrastructure & Authentication

**Goal**: Set up core infrastructure and GitHub OAuth

#### **Tasks**

**Day 1-2: Project Setup**
- [ ] Create GitHub organization + repositories
  ```bash
  # Create repos
  mkdir ai-agent-mesh
  cd ai-agent-mesh
  mkdir backend frontend docs

  # Initialize backend (FastAPI)
  cd backend
  python3 -m venv venv
  source venv/bin/activate
  pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic-settings

  # Create basic structure
  mkdir app
  touch app/main.py app/__init__.py
  ```

- [ ] Set up PostgreSQL database (local or RDS)
  ```bash
  # Local Docker for development
  docker run --name postgres -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:15

  # Create database
  psql -h localhost -U postgres -c "CREATE DATABASE aigentmesh_dev;"
  ```

- [ ] Set up Redis (local or ElastiCache)
  ```bash
  docker run --name redis -p 6379:6379 -d redis:7
  ```

- [ ] Initialize Alembic for migrations
  ```bash
  alembic init alembic
  # Configure alembic.ini with DB connection
  ```

**Day 3-4: GitHub OAuth**
- [ ] Register GitHub OAuth app (https://github.com/settings/developers)
  - Homepage URL: http://localhost:3000 (dev)
  - Callback URL: http://localhost:3000/auth/callback
  - Scopes: `repo` (read), `user:email`

- [ ] Implement OAuth flow
  ```python
  # app/api/auth.py
  @router.get("/auth/github")
  async def github_login():
      redirect_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo user:email"
      return RedirectResponse(redirect_url)

  @router.post("/auth/github/callback")
  async def github_callback(code: str):
      # Exchange code for access token
      # Create/update user in database
      # Generate JWT token
      pass
  ```

- [ ] Implement JWT auth middleware
  ```python
  # app/services/auth.py
  def create_access_token(data: dict) -> str:
      expire = datetime.utcnow() + timedelta(hours=24)
      to_encode = data.copy()
      to_encode.update({"exp": expire})
      return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

  async def get_current_user(token: str = Depends(oauth2_scheme)):
      # Verify JWT
      # Load user from database
      pass
  ```

**Day 5: Database Models**
- [ ] Create initial models
  ```python
  # app/models.py
  class User(Base):
      __tablename__ = "users"
      id = Column(UUID, primary_key=True)
      github_id = Column(Integer, unique=True)
      email = Column(String)
      github_access_token = Column(String)  # Encrypted
      plan = Column(String, default="free")

  class Repo(Base):
      __tablename__ = "repos"
      id = Column(UUID, primary_key=True)
      user_id = Column(UUID, ForeignKey("users.id"))
      github_id = Column(Integer, unique=True)
      name = Column(String)
      url = Column(String)
  ```

- [ ] Create migrations
  ```bash
  alembic revision --autogenerate -m "Initial schema"
  alembic upgrade head
  ```

**Deliverables**:
- ✅ FastAPI backend running on http://localhost:8000
- ✅ GitHub OAuth flow working
- ✅ Database schema created
- ✅ JWT auth working

---

### Week 2: API Discovery (Python/FastAPI)

**Goal**: Build API discovery engine for FastAPI

#### **Tasks**

**Day 1-2: GitHub Integration**
- [ ] Implement GitHub API client
  ```python
  # app/services/github_client.py
  import httpx

  class GitHubClient:
      def __init__(self, access_token: str):
          self.client = httpx.AsyncClient(
              headers={"Authorization": f"token {access_token}"}
          )

      async def list_repos(self):
          resp = await self.client.get("https://api.github.com/user/repos")
          return resp.json()

      async def get_repo_content(self, owner: str, repo: str, path: str):
          url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
          resp = await self.client.get(url)
          return resp.json()

      async def clone_repo(self, clone_url: str, dest: str):
          # Use GitPython or subprocess
          import git
          repo = git.Repo.clone_from(clone_url, dest, depth=1)
          return repo
  ```

**Day 3-5: FastAPI Parser**
- [ ] Implement AST parser for FastAPI
  ```python
  # app/parsers/fastapi_parser.py
  import libcst as cst

  class FastAPIParser:
      def parse_file(self, file_path: str) -> List[API]:
          with open(file_path) as f:
              tree = cst.parse_module(f.read())

          visitor = FastAPIVisitor()
          tree.walk(visitor)
          return visitor.apis

  class FastAPIVisitor(cst.CSTVisitor):
      def __init__(self):
          self.apis = []

      def visit_FunctionDef(self, node):
          # Look for @router.get, @router.post decorators
          for decorator in node.decorators:
              if self._is_route_decorator(decorator):
                  api = self._extract_api_info(node, decorator)
                  self.apis.append(api)

      def _is_route_decorator(self, decorator):
          # Check if decorator is router.get/post/etc
          pass

      def _extract_api_info(self, func_node, decorator):
          # Extract endpoint, method, parameters, return type
          endpoint = self._get_endpoint_from_decorator(decorator)
          method = self._get_method_from_decorator(decorator)

          # Parse function signature for request schema
          request_schema = self._parse_parameters(func_node.params)

          # Parse return type for response schema
          response_schema = self._parse_return_type(func_node.returns)

          return API(
              endpoint=endpoint,
              method=method,
              request_schema=request_schema,
              response_schema=response_schema,
              file_path=file_path,
              line_number=func_node.lineno
          )
  ```

- [ ] Test parser on real FastAPI projects
  ```python
  # tests/test_fastapi_parser.py
  def test_parse_get_endpoint():
      code = '''
      @router.get("/users/{user_id}")
      async def get_user(user_id: str) -> User:
          pass
      '''
      apis = FastAPIParser().parse_code(code)
      assert len(apis) == 1
      assert apis[0].endpoint == "/users/{user_id}"
      assert apis[0].method == "GET"
  ```

**Deliverables**:
- ✅ GitHub API integration
- ✅ FastAPI parser with >90% accuracy
- ✅ Test suite with 10+ test cases

---

### Week 3: Discovery Pipeline

**Goal**: End-to-end API discovery working

#### **Tasks**

**Day 1-2: Celery Setup**
- [ ] Set up Celery with Redis
  ```python
  # app/celery_app.py
  from celery import Celery

  celery_app = Celery(
      "aigentmesh",
      broker="redis://localhost:6379/0",
      backend="redis://localhost:6379/0"
  )

  @celery_app.task
  async def discover_repo_apis(repo_id: str):
      repo = await db.get_repo(repo_id)

      # Clone repo
      temp_dir = f"/tmp/repos/{repo_id}"
      await github.clone_repo(repo.url, temp_dir)

      # Discover APIs
      parser = FastAPIParser()
      apis = await parser.discover_apis(temp_dir)

      # Store in database
      await db.bulk_insert_apis(repo_id, apis)

      # Cleanup
      shutil.rmtree(temp_dir)

      return len(apis)
  ```

- [ ] Test Celery worker
  ```bash
  # Terminal 1: Start worker
  celery -A app.celery_app worker --loglevel=info

  # Terminal 2: Test task
  python -c "from app.celery_app import discover_repo_apis; discover_repo_apis.delay('repo_123')"
  ```

**Day 3-4: API Endpoints**
- [ ] POST /v1/repos (add repository)
  ```python
  @router.post("/repos")
  async def add_repo(
      repo_url: str,
      current_user: User = Depends(get_current_user)
  ):
      # Verify user has access to repo
      # Create repo record
      # Trigger discovery job
      job_id = await discover_repo_apis.delay(repo.id)
      return {"repo_id": repo.id, "job_id": job_id}
  ```

- [ ] GET /v1/repos (list repositories)
- [ ] GET /v1/repos/{id}/apis (list discovered APIs)

**Day 5: Integration Test**
- [ ] Test full flow: Add repo → Wait → Check APIs
  ```python
  async def test_full_discovery_flow():
      # Add test repo
      resp = await client.post("/v1/repos", json={
          "repo_url": "https://github.com/test/fastapi-example"
      })
      repo_id = resp.json()["repo_id"]

      # Wait for discovery (poll job status)
      await asyncio.sleep(30)

      # Check APIs were discovered
      resp = await client.get(f"/v1/repos/{repo_id}/apis")
      apis = resp.json()["apis"]
      assert len(apis) > 0
  ```

**Deliverables**:
- ✅ Celery workers running
- ✅ API discovery working end-to-end
- ✅ At least 1 real repo successfully discovered

---

## Phase 2: Core Features (Weeks 4-6)

### Week 4: Change Detection

**Goal**: Detect API changes from Git commits

#### **Tasks**

**Day 1-2: GitHub Webhooks**
- [ ] Set up webhook receiver
  ```python
  @router.post("/webhooks/github")
  async def github_webhook(
      request: Request,
      x_github_event: str = Header(None)
  ):
      # Verify webhook signature
      payload = await request.json()

      if x_github_event == "push":
          await handle_push_event.delay(payload)

      return {"status": "ok"}

  @celery_app.task
  async def handle_push_event(payload: dict):
      repo_id = find_repo_by_github_id(payload["repository"]["id"])
      commits = payload["commits"]

      for commit in commits:
          await detect_api_changes.delay(repo_id, commit["id"])
  ```

- [ ] Register webhooks for user repos
  ```python
  async def register_webhook(repo_full_name: str, access_token: str):
      url = f"https://api.github.com/repos/{repo_full_name}/hooks"
      await github.post(url, json={
          "config": {
              "url": "https://api.aigentmesh.com/webhooks/github",
              "content_type": "json"
          },
          "events": ["push"]
      })
  ```

**Day 3-5: Schema Diffing**
- [ ] Implement schema comparison algorithm
  ```python
  # app/services/schema_diff.py
  def diff_schemas(old: dict, new: dict) -> SchemaDiff:
      changes = []

      # Check request schema
      if old.get("request") != new.get("request"):
          req_changes = diff_request_schema(old["request"], new["request"])
          changes.extend(req_changes)

      # Check response schema
      if old.get("response") != new.get("response"):
          resp_changes = diff_response_schema(old["response"], new["response"])
          changes.extend(resp_changes)

      # Classify severity
      is_breaking = any(c.severity == "BREAKING" for c in changes)

      return SchemaDiff(changes=changes, is_breaking=is_breaking)

  def diff_request_schema(old, new):
      changes = []

      # New required field = BREAKING
      old_required = set(old.get("required", []))
      new_required = set(new.get("required", []))

      for field in (new_required - old_required):
          changes.append(Change(
              type="REQUEST_REQUIRED_ADDED",
              field=field,
              severity="BREAKING"
          ))

      return changes
  ```

- [ ] Test suite for edge cases
  ```python
  def test_added_required_field_is_breaking():
      old = {"request": {"required": ["id"]}}
      new = {"request": {"required": ["id", "name"]}}
      diff = diff_schemas(old, new)
      assert diff.is_breaking == True

  def test_added_optional_field_is_not_breaking():
      old = {"request": {"required": ["id"]}}
      new = {"request": {"required": ["id"], "optional": ["name"]}}
      diff = diff_schemas(old, new)
      assert diff.is_breaking == False
  ```

**Deliverables**:
- ✅ GitHub webhooks receiving push events
- ✅ Schema diffing with >95% accuracy
- ✅ Breaking changes correctly identified

---

### Week 5: Dependency Graph

**Goal**: Build dependency graph (which repos use which APIs)

#### **Tasks**

**Day 1-3: Code Analysis for API Calls**
- [ ] Implement consumer detection
  ```python
  # app/parsers/consumer_detector.py
  import libcst as cst

  class APICallDetector(cst.CSTVisitor):
      def __init__(self, api_endpoints: List[str]):
          self.api_endpoints = api_endpoints
          self.calls = []

      def visit_Call(self, node):
          # Detect HTTP calls: requests.get(), httpx.post(), etc.
          if self._is_http_call(node):
              url = self._extract_url(node)
              if self._matches_api_endpoint(url):
                  self.calls.append({
                      "endpoint": url,
                      "line_number": node.lineno
                  })

  async def find_api_consumers(api_id: str):
      api = await db.get_api(api_id)
      consumers = []

      # Search all other repos
      repos = await db.get_all_repos()
      for repo in repos:
          if repo.id == api.repo_id:
              continue  # Skip provider repo

          # Clone repo and search for API calls
          temp_dir = f"/tmp/search/{repo.id}"
          await github.clone_repo(repo.url, temp_dir)

          detector = APICallDetector([api.endpoint])
          calls = await detector.find_calls(temp_dir)

          if calls:
              consumers.append({
                  "repo_id": repo.id,
                  "calls": calls
              })

      return consumers
  ```

- [ ] Store dependencies in database
  ```sql
  CREATE TABLE dependencies (
      id UUID PRIMARY KEY,
      provider_api_id UUID REFERENCES apis(id),
      consumer_repo_id UUID REFERENCES repos(id),
      consumer_file_path TEXT,
      consumer_line_number INTEGER
  );
  ```

**Day 4-5: Graph Visualization Data**
- [ ] Build graph API endpoint
  ```python
  @router.get("/dashboard/dependency-graph")
  async def get_dependency_graph(user: User = Depends(get_current_user)):
      repos = await db.get_user_repos(user.id)

      nodes = [{"id": r.id, "name": r.name} for r in repos]
      edges = []

      for repo in repos:
          # Get all APIs this repo consumes
          deps = await db.get_repo_dependencies(repo.id)
          for dep in deps:
              edges.append({
                  "source": dep.provider_repo_id,
                  "target": repo.id,
                  "api": dep.api_endpoint
              })

      return {"nodes": nodes, "edges": edges}
  ```

**Deliverables**:
- ✅ Consumer detection working (70%+ accuracy)
- ✅ Dependency graph stored in database
- ✅ Graph API endpoint returning data

---

### Week 6: Context Injection

**Goal**: Inject API changes into consumer repos as context files

#### **Tasks**

**Day 1-2: Context File Generation**
- [ ] Create Markdown formatter for AI agents
  ```python
  # app/services/context_generator.py
  def generate_context_markdown(change: APIChange) -> str:
      return f"""
  # API Changes Detected

  ## {change.api.provider_repo}: {change.api.method} {change.api.endpoint}

  **Changed**: {change.detected_at.strftime("%Y-%m-%d %I:%M %p")}
  **Breaking**: {"Yes ⚠️" if change.is_breaking else "No"}

  ### What Changed
  {change.summary}

  ### Old Schema
  ```json
  {json.dumps(change.old_schema, indent=2)}
  ```

  ### New Schema
  ```json
  {json.dumps(change.new_schema, indent=2)}
  ```

  ### Affected Files in This Repo
  {"\n".join(f"- {f.file_path}:{f.line_number}" for f in change.affected_files)}

  ### Suggested Migration
  {generate_migration_hint(change)}
  """
  ```

**Day 3-4: GitHub File Creation**
- [ ] Implement context injection
  ```python
  async def inject_context(consumer_repo_id: str, change_id: str):
      change = await db.get_change(change_id)
      consumer = await db.get_repo(consumer_repo_id)

      # Generate context
      context_md = generate_context_markdown(change)

      # Detect AI agent type (look for .claude/, .cursor/, etc.)
      ai_agent = await detect_ai_agent(consumer)

      # Write to appropriate file
      context_paths = {
          "claude_code": ".claude/api-changes.md",
          "cursor": ".cursor/context.md",
          "github_copilot": ".github/copilot/context.json"
      }

      file_path = context_paths.get(ai_agent, ".ai/api-changes.md")

      await github.create_or_update_file(
          repo=consumer,
          path=file_path,
          content=context_md,
          message=f"AI Agent Mesh: API change detected in {change.api.provider_repo}"
      )
  ```

**Day 5: Testing**
- [ ] Manually verify Claude Code reads the context
  - Add a repo
  - Change an API it depends on
  - Check that .claude/api-changes.md is created
  - Open Claude Code and ask about the API
  - Verify Claude mentions the change

**Deliverables**:
- ✅ Context files created in consumer repos
- ✅ Claude Code successfully reads context (manual test)
- ✅ Context is useful (AI understands the change)

---

## Phase 3: Auto-Fix (Weeks 7-9)

### Week 7: Code Generation with Claude API

**Goal**: Generate migration code using Claude

#### **Tasks**

**Day 1-2: Claude API Integration**
- [ ] Set up Anthropic SDK
  ```python
  # app/services/claude_client.py
  from anthropic import AsyncAnthropic

  class ClaudeClient:
      def __init__(self, api_key: str):
          self.client = AsyncAnthropic(api_key=api_key)

      async def generate_migration(
          self,
          old_schema: dict,
          new_schema: dict,
          current_code: str,
          language: str
      ) -> str:
          prompt = MIGRATION_PROMPT_TEMPLATE.format(
              old_schema=json.dumps(old_schema, indent=2),
              new_schema=json.dumps(new_schema, indent=2),
              current_code=current_code,
              language=language
          )

          response = await self.client.messages.create(
              model="claude-3-5-sonnet-20241022",
              max_tokens=4000,
              system="You are an expert software engineer...",
              messages=[{"role": "user", "content": prompt}]
          )

          return response.content[0].text
  ```

**Day 3-5: Prompt Engineering**
- [ ] Craft effective prompts for migrations
  ```python
  MIGRATION_PROMPT = """
  You are an expert software engineer helping migrate code to a new API version.

  ## API Change
  **Endpoint**: {endpoint}
  **Change**: {change_summary}

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
  Generate the updated code that works with the new API schema.
  - Update function calls to match new schema
  - Update type definitions
  - Add error handling if needed
  - Preserve existing business logic

  Return only the updated code, no explanations.
  """
  ```

- [ ] Test with real examples
  ```python
  # Test: Adding required field
  old_schema = {"request": {"customer_id": "string"}}
  new_schema = {"request": {"customer_id": "string", "segment": "string"}}
  current_code = """
  result = await client.post("/api/analyze", json={"customer_id": cust_id})
  """

  new_code = await claude.generate_migration(old_schema, new_schema, current_code, "python")

  # Verify new_code includes segment field
  assert "segment" in new_code
  ```

**Deliverables**:
- ✅ Claude API integration working
- ✅ Prompts generate correct code >80% of the time
- ✅ Cost per migration: <$0.10

---

### Week 8: AST Rewriting & PR Creation

**Goal**: Apply generated code and create PRs

#### **Tasks**

**Day 1-3: AST Rewriting**
- [ ] Implement precise code replacement
  ```python
  # app/services/code_rewriter.py
  import libcst as cst

  class CodeRewriter:
      def replace_function(
          self,
          file_content: str,
          function_name: str,
          new_function_code: str
      ) -> str:
          tree = cst.parse_module(file_content)

          replacer = FunctionReplacer(function_name, new_function_code)
          new_tree = tree.visit(replacer)

          return new_tree.code

  class FunctionReplacer(cst.CSTTransformer):
      def __init__(self, target_func: str, new_code: str):
          self.target_func = target_func
          self.new_code = new_code

      def leave_FunctionDef(self, original, updated):
          if original.name.value == self.target_func:
              # Parse new code and return its AST
              new_func_node = cst.parse_statement(self.new_code)
              return new_func_node
          return updated
  ```

**Day 4-5: GitHub PR Creation**
- [ ] Implement PR creation
  ```python
  async def create_migration_pr(migration_id: str):
      migration = await db.get_migration(migration_id)
      change = await db.get_change(migration.change_id)
      consumer = await db.get_repo(migration.consumer_repo_id)

      # Create branch
      branch_name = f"ai-agent-mesh/migration-{migration.id}"
      await github.create_branch(consumer, branch_name)

      # Apply code changes
      for file_path, new_code in migration.generated_code.items():
          await github.update_file(
              repo=consumer,
              branch=branch_name,
              path=file_path,
              content=new_code,
              message=f"Update {file_path} for API change"
          )

      # Create PR
      pr = await github.create_pull_request(
          repo=consumer,
          title=f"API Migration: {change.api.endpoint}",
          body=generate_pr_description(migration),
          head=branch_name,
          base=consumer.default_branch
      )

      # Store PR info
      await db.update_migration(migration.id, pr_url=pr.html_url, pr_number=pr.number)

      return pr
  ```

**Deliverables**:
- ✅ AST rewriting preserves code formatting
- ✅ PRs created successfully
- ✅ PR descriptions are helpful

---

### Week 9: Auto-Fix Flow End-to-End

**Goal**: Complete auto-fix feature

#### **Tasks**

**Day 1-2: API Endpoint**
- [ ] POST /v1/changes/{id}/auto-fix
  ```python
  @router.post("/changes/{change_id}/auto-fix")
  async def generate_auto_fix(
      change_id: str,
      consumer_repo_id: str,
      current_user: User = Depends(get_current_user)
  ):
      # Verify permissions
      # Queue auto-fix job
      job_id = await generate_migration.delay(change_id, consumer_repo_id)

      return {
          "migration_id": job_id,
          "status": "generating",
          "estimated_duration": 60
      }
  ```

**Day 3-4: Integration Testing**
- [ ] Test full auto-fix flow
  ```python
  async def test_auto_fix_flow():
      # 1. Create test change
      change = await create_breaking_change(
          api_id="api_test",
          old_schema={"request": {"id": "string"}},
          new_schema={"request": {"id": "string", "name": "string"}}
      )

      # 2. Trigger auto-fix
      resp = await client.post(f"/v1/changes/{change.id}/auto-fix", json={
          "consumer_repo_id": "repo_consumer"
      })
      migration_id = resp.json()["migration_id"]

      # 3. Wait for completion
      await poll_until_complete(f"/v1/migrations/{migration_id}", timeout=120)

      # 4. Verify PR created
      migration = await db.get_migration(migration_id)
      assert migration.pr_url is not None

      # 5. Verify code is correct
      pr_files = await github.get_pr_files(migration.pr_url)
      assert any("name" in f.content for f in pr_files)
  ```

**Day 5: Bug Fixes & Edge Cases**
- [ ] Handle cases where Claude generates invalid code
- [ ] Handle cases where consumer repo has no write access
- [ ] Handle cases where PR already exists

**Deliverables**:
- ✅ Auto-fix working end-to-end
- ✅ At least 1 successful auto-fix on real repos
- ✅ Edge cases handled gracefully

---

## Phase 4: Polish & Launch (Weeks 10-12)

### Week 10: Dashboard UI

**Goal**: Build web dashboard (React)

#### **Tasks**

**Day 1-2: Setup React + TypeScript**
```bash
cd frontend
npx create-react-app . --template typescript
npm install @tanstack/react-query react-router-dom d3
```

**Day 3-5: Core Pages**
- [ ] Login page (GitHub OAuth)
- [ ] Dashboard overview
  - Summary stats (repos, APIs, changes)
  - Recent changes list
  - Dependency graph (D3.js)
- [ ] Repo detail page
  - List of APIs
  - Consumers/providers
- [ ] Change detail page
  - Schema diff visualization
  - Affected repos
  - "Auto-Fix" button

**Deliverables**:
- ✅ Dashboard loads in <2 seconds
- ✅ Graph is interactive (zoom, pan)
- ✅ Mobile-responsive

---

### Week 11: Testing & Bug Fixes

**Goal**: Achieve >90% reliability

#### **Tasks**

**Day 1-2: Unit Tests**
- [ ] Test coverage >80%
  ```bash
  pytest --cov=app --cov-report=html
  ```

**Day 3-4: Integration Tests**
- [ ] Test all API endpoints
- [ ] Test webhook flow
- [ ] Test auto-fix flow

**Day 5: Bug Bash**
- [ ] Fix all critical bugs
- [ ] Fix all high-priority bugs
- [ ] Document known issues (low-priority)

**Deliverables**:
- ✅ Test coverage >80%
- ✅ Zero critical bugs
- ✅ <5 high-priority bugs

---

### Week 12: Launch Prep

**Goal**: Prepare for beta launch

#### **Tasks**

**Day 1: Documentation**
- [ ] Write README
- [ ] Write Getting Started guide
- [ ] Write API docs
- [ ] Write FAQ

**Day 2: Infrastructure**
- [ ] Deploy to AWS (ECS Fargate)
- [ ] Set up domain (aigentmesh.com)
- [ ] Configure SSL (Let's Encrypt)
- [ ] Set up monitoring (Sentry, Grafana)

**Day 3: Beta User Onboarding**
- [ ] Create onboarding flow
- [ ] Create feedback form
- [ ] Set up support email

**Day 4-5: Soft Launch**
- [ ] Invite 10 friends/colleagues to test
- [ ] Fix any critical issues
- [ ] Tweet about launch
- [ ] Post on Hacker News "Show HN"

**Deliverables**:
- ✅ Production environment live
- ✅ 10+ beta users signed up
- ✅ Zero downtime during launch

---

## Success Metrics

### Week-by-Week Goals

| Week | Goal | Metric |
|------|------|--------|
| 1 | Auth working | 1 successful GitHub login |
| 2 | Discovery working | 1 repo with >5 APIs discovered |
| 3 | Pipeline working | APIs discovered within 60 seconds |
| 4 | Detection working | 1 breaking change detected |
| 5 | Graph working | Dependency graph with >2 nodes |
| 6 | Context working | Claude Code reads injected context |
| 7 | Claude working | 1 correct migration generated |
| 8 | PRs working | 1 PR created automatically |
| 9 | Auto-fix working | 1 end-to-end auto-fix |
| 10 | Dashboard working | Dashboard loads <2s |
| 11 | Tests passing | >80% test coverage |
| 12 | Beta launched | 10+ beta users |

### MVP Success Criteria (End of Week 12)

- [ ] 50+ beta users signed up
- [ ] 100+ repos connected
- [ ] 500+ APIs discovered
- [ ] 50+ breaking changes detected
- [ ] 20+ auto-fixes generated
- [ ] >80% week-1 retention
- [ ] <5% error rate
- [ ] NPS >40

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **Claude API is too expensive** | Set budget limit ($500/month), optimize prompts |
| **Detection accuracy too low** | Manual review queue, improve with ML over time |
| **GitHub rate limits** | Cache aggressively, batch requests |
| **Parsing breaks on edge cases** | Graceful fallback, manual annotation option |

### Scope Risks

| Risk | Mitigation |
|------|------------|
| **Features take longer than estimated** | Cut scope, ship MVP first |
| **Beta users don't find value** | Pivot based on feedback, validate assumptions |
| **Can't handle non-FastAPI repos** | Document limitation, add frameworks post-MVP |

---

## Post-MVP Roadmap (Weeks 13-24)

### Month 4 (Weeks 13-16)
- [ ] Support Express/NestJS (JavaScript/TypeScript)
- [ ] Support Flask (Python)
- [ ] Improve detection accuracy with ML
- [ ] Add Slack/Discord notifications

### Month 5 (Weeks 17-20)
- [ ] Support Django REST Framework
- [ ] Support Go (Chi, Gin)
- [ ] Add custom webhook support
- [ ] Improve dashboard analytics

### Month 6 (Weeks 21-24)
- [ ] Launch paid tiers
- [ ] Add team features (collaboration)
- [ ] Add contract testing (Pact-like)
- [ ] Enterprise features (SSO, on-prem)

---

## Team & Resources

### Team Structure

**Solo Founder** (Weeks 1-12):
- Full-stack engineer (you)
- Time commitment: 40 hours/week

**Optional Additions**:
- Contract designer (Week 10): $2k for dashboard UI
- Beta testers (Week 12): 10-20 users (free)

### Budget (12 weeks)

| Category | Cost |
|----------|------|
| **Infrastructure** | |
| AWS (ECS, RDS, Redis, S3) | $400/month × 3 = $1,200 |
| Domain (aigentmesh.com) | $12 |
| **APIs** | |
| Claude API (1000 migrations) | $40 |
| GitHub Enterprise (optional) | $0 (use personal) |
| **Tools** | |
| Sentry | $0 (free tier) |
| Grafana Cloud | $0 (free tier) |
| **Total** | **~$1,300** |

---

## Timeline Visualization

```
Week 1-3: Foundation
├─ Week 1: Infrastructure & Auth ████████░░
├─ Week 2: API Discovery        ░░████████
└─ Week 3: Discovery Pipeline   ░░░░██████

Week 4-6: Core Features
├─ Week 4: Change Detection     ░░░░░░████
├─ Week 5: Dependency Graph     ░░░░░░░░██
└─ Week 6: Context Injection    ░░░░░░░░░░

Week 7-9: Auto-Fix
├─ Week 7: Code Generation      ██████░░░░
├─ Week 8: AST & PR Creation    ░░████████
└─ Week 9: End-to-End           ░░░░██████

Week 10-12: Polish & Launch
├─ Week 10: Dashboard UI        ░░░░░░████
├─ Week 11: Testing             ░░░░░░░░██
└─ Week 12: Launch              ░░░░░░░░░░
```

---

**Status**: Draft
**Last Updated**: 2025-11-25
**Next Review**: Weekly standup

**Ready to start Week 1? Let's build this! 🚀**
