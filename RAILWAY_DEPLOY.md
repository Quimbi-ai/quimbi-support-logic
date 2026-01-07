# Deploying Backend to Railway

## Prerequisites

1. PostgreSQL database provisioned in Railway (already done)
2. Database environment variables available

## Railway Setup

### 1. Create Backend Service

In Railway dashboard:
1. Click "New Service"
2. Select "GitHub Repo"
3. Choose this repository
4. Set root directory to `/backend`

### 2. Configure Environment Variables

Add these environment variables to the backend service:

**Required:**
- `DATABASE_URL` - Railway will auto-provide this from PostgreSQL service
- `API_KEY` - Your API key for authentication
- `ENVIRONMENT` - Set to `production`

**CORS (Important!):**
- `CORS_ORIGINS` - Set to your frontend URL (e.g., `https://front-endalphaecommerce-production.up.railway.app`)

**Optional (AI Features):**
- `ANTHROPIC_API_KEY` - For AI draft generation
- `OPENAI_API_KEY` - Alternative AI provider

**Optional (Advanced):**
- `REDIS_URL` - For caching (if you add Redis service)
- `SCORING_CHURN_WEIGHT` - Default: 3.0
- `SCORING_VALUE_WEIGHT` - Default: 2.0
- `SCORING_URGENCY_WEIGHT` - Default: 1.5
- `TOPIC_ALERT_BOOST` - Default: 5.0

### 3. Link PostgreSQL Database

In Railway dashboard:
1. Go to backend service settings
2. Under "Service Variables", ensure `DATABASE_URL` references the PostgreSQL service
3. Railway should auto-configure this

### 4. Deploy

Railway will automatically:
1. Build the Docker image
2. Start the FastAPI server
3. Create database tables on first startup (via lifespan event)

## Post-Deployment: Seed Database

After first deployment, seed the database with sample data:

```bash
# Using Railway CLI
railway run python -m app.db_init
```

Or manually via the Railway dashboard shell.

## API Endpoints

After deployment, your API will be available at:
- Health check: `https://your-backend-url.railway.app/health`
- API docs: `https://your-backend-url.railway.app/docs`
- Tickets list: `https://your-backend-url.railway.app/api/tickets`

## Connecting Frontend

Update frontend environment variable:
- `VITE_API_BASE_URL` = `https://your-backend-url.railway.app`

## Troubleshooting

**Database connection errors:**
- Check `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host:port/db`
- Ensure PostgreSQL service is running

**CORS errors:**
- Verify `CORS_ORIGINS` includes your frontend URL
- Check for trailing slashes

**Empty ticket list:**
- Run database seed script: `python -m app.db_init`
