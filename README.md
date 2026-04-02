# Cleya.ai Marketing Crew — Production API

Multi-agent growth & viral marketing system deployed on Vercel, integrated with Slack, HubSpot, Notion, Lemlist, Apify, and Resend.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Full 5-agent pipeline |
| `POST` | `/api/run/intel` | Intelligence agent only |
| `POST` | `/api/run/growth` | Growth strategy agent only |
| `POST` | `/api/run/content` | Content calendar agent only |
| `POST` | `/api/run/community` | Community partnerships agent only |
| `POST` | `/api/run/plg` | Product-led growth agent only |
| `GET` | `/api/status/{run_id}` | Check run status/results |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/webhook/slack` | Slack slash command |

## Quick Start

```bash
# Clone
git clone https://github.com/visheshkhurana/cleya-crew-api.git
cd cleya-crew-api

# Configure
cp .env.example .env
# Fill in your API keys

# Deploy
npx vercel --prod
```

## Trigger a Run

```bash
# Full pipeline
curl -X POST https://your-app.vercel.app/api/run \
  -H "Content-Type: application/json" \
  -d '{"target_segment": "all professionals", "time_period": "this week"}'

# Single agent
curl -X POST https://your-app.vercel.app/api/run/content \
  -H "Content-Type: application/json" \
  -d '{"time_period": "next 7 days"}'
```

## Architecture

```
Vercel Serverless (FastAPI + Mangum)
  ├── POST /api/run → CrewAI Pipeline
  │     ├── Intel Agent    → Serper + Apify → Slack
  │     ├── Growth Agent   → Serper → Notion
  │     ├── Content Agent  → Serper → Notion + Slack
  │     ├── Community Agent → HubSpot + Lemlist + Resend
  │     └── PLG Agent      → Notion + Slack
  ├── GET /api/status → Redis/Memory state
  └── POST /api/webhook/slack → Slash command trigger
```
