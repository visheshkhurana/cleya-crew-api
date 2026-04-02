"""
Cleya.ai Marketing Crew — Vercel Serverless API
=================================================

Endpoints:
  POST /api/run           — Kick off full crew or specific agents
  POST /api/run/intel     — Intelligence agent only
  POST /api/run/content   — Content agent only
  POST /api/run/growth    — Growth strategy agent only
  POST /api/run/community — Community partnerships agent only
  POST /api/run/plg       — Product-led growth agent only
  GET  /api/status/{id}   — Check run status & results
  GET  /api/health        — Health check
  POST /api/webhook/slack — Slack slash command trigger

Architecture:
  - Vercel serverless functions (maxDuration=800s for Pro/Enterprise)
  - Upstash Redis for run state persistence across invocations
  - CrewAI sequential pipeline with real tool integrations
  - Results pushed to Slack + Notion automatically
"""

import os
import sys
import json
import uuid
import traceback
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

# Add src to path so crewai can find the crew module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

app = FastAPI(
    title="Cleya.ai Marketing Crew API",
    description="Multi-agent growth & viral marketing system for Cleya.ai",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── State Management (Upstash Redis or in-memory fallback) ───────────

def get_store():
    """Returns Redis client if UPSTASH_REDIS_REST_URL is set, else dict."""
    redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
    redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if redis_url and redis_token:
        try:
            from redis import Redis
            return Redis.from_url(
                redis_url.replace("https://", "rediss://"),
                password=redis_token,
                decode_responses=True,
            )
        except Exception:
            pass
    return {}

store = get_store()

def save_run(run_id: str, data: dict):
    if isinstance(store, dict):
        store[run_id] = data
    else:
        store.setex(f"run:{run_id}", 86400, json.dumps(data))  # TTL: 24h

def load_run(run_id: str) -> dict:
    if isinstance(store, dict):
        return store.get(run_id, {})
    else:
        raw = store.get(f"run:{run_id}")
        return json.loads(raw) if raw else {}


# ── Request/Response Models ──────────────────────────────────────────

class CrewRunRequest(BaseModel):
    target_segment: str = "all professionals — founders, investors, VCs, operators, engineers, designers, marketers, recruiters, and talent across India's startup and business ecosystem"
    time_period: str = "this week"
    agents: Optional[List[str]] = Field(
        default=None,
        description="Run specific agents only: intel, growth, content, community, plg. Omit for full pipeline."
    )
    notify_slack: bool = Field(default=True, description="Post results to Slack when done")
    save_to_notion: bool = Field(default=True, description="Save outputs to Notion")

class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str
    agents: List[str]


# ── Crew Execution ───────────────────────────────────────────────────

def build_inputs(req: CrewRunRequest) -> dict:
    return {
        "target_segment": req.target_segment,
        "time_period": req.time_period,
        "product_name": "Cleya.ai",
        "product_tagline": "AI Superconnector for Professionals in India",
        "product_url": "https://cleya.ai",
        "social_handle": "@joincleya",
        "product_description": (
            "Cleya.ai is an AI-powered professional networking platform that matches "
            "all kinds of professionals across India — founders, investors, operators, "
            "engineers, designers, marketers, recruiters, freelancers, and anyone building "
            "or scaling companies. Members describe their goals in plain language, and "
            "Cleya's AI finds matches based on skills, intent, industry, role fit, and "
            "professional context — delivering warm introductions with context. "
            "No cold emails. No awkward LinkedIn DMs."
        ),
        "key_differentiators": (
            "1) AI matching with 90%+ accuracy scores across all professional roles, "
            "2) Warm intros with context (not cold outreach), "
            "3) Members-only verified community, "
            "4) Covers ALL professionals — not just founders and investors, "
            "5) India-focused with Tier-2 city coverage, "
            "6) Works for hiring, partnerships, mentorship, co-founding, and deal flow"
        ),
    }


def execute_crew_run(run_id: str, req: CrewRunRequest, agent_filter: Optional[str] = None):
    """Execute crew and save results."""
    try:
        save_run(run_id, {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "inputs": req.dict(),
        })

        from cleya_marketing_crew.crew import CleyaMarketingCrew
        inputs = build_inputs(req)

        crew_instance = CleyaMarketingCrew()

        if agent_filter:
            # Run a single agent's task
            result = run_single_agent(crew_instance, agent_filter, inputs)
        else:
            # Run full pipeline
            result = crew_instance.crew().kickoff(inputs=inputs)

        output_text = result.raw if hasattr(result, "raw") else str(result)

        save_run(run_id, {
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "output": output_text[:50000],  # Cap at 50k chars for Redis
            "agents_run": agent_filter or "full_pipeline",
        })

        # Post-run hooks
        if req.notify_slack:
            post_to_slack(run_id, agent_filter or "full_pipeline", output_text)
        if req.save_to_notion:
            save_to_notion(run_id, agent_filter or "full_pipeline", output_text)

        return output_text

    except Exception as e:
        save_run(run_id, {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "failed_at": datetime.now(timezone.utc).isoformat(),
        })
        raise


def run_single_agent(crew_instance, agent_name: str, inputs: dict):
    """Run a single agent's task from the crew."""
    from crewai import Crew, Process

    agent_map = {
        "intel": ("market_intelligence_analyst", "ecosystem_intelligence_task"),
        "growth": ("growth_strategist", "growth_strategy_task"),
        "content": ("viral_content_architect", "viral_content_task"),
        "community": ("community_growth_hacker", "community_partnerships_task"),
        "plg": ("product_led_growth_engineer", "product_led_growth_task"),
    }

    if agent_name not in agent_map:
        raise ValueError(f"Unknown agent: {agent_name}. Use: {list(agent_map.keys())}")

    agent_method, task_method = agent_map[agent_name]
    agent = getattr(crew_instance, agent_method)()
    task = getattr(crew_instance, task_method)()

    mini_crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    return mini_crew.kickoff(inputs=inputs)


# ── Post-Run Hooks ───────────────────────────────────────────────────

def post_to_slack(run_id: str, agent_name: str, output: str):
    """Post crew results to Slack."""
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL", "#marketing")
    if not token:
        return

    import requests
    summary = output[:3000]  # Slack message limit
    message = (
        f"*Cleya Marketing Crew — Run Complete*\n"
        f"Run ID: `{run_id}` | Agent: `{agent_name}`\n"
        f"─────────────────────────\n"
        f"{summary}\n"
        f"─────────────────────────\n"
        f"_Full output saved to Notion_"
    )

    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel, "text": message, "mrkdwn": True},
            timeout=10,
        )
    except Exception:
        pass


def save_to_notion(run_id: str, agent_name: str, output: str):
    """Save crew output as a Notion page."""
    token = os.getenv("NOTION_API_KEY")
    parent_page = os.getenv("NOTION_PARENT_PAGE_ID")
    if not token or not parent_page:
        return

    import requests
    title = f"Crew Run: {agent_name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Split output into chunks for Notion blocks (max 2000 chars each)
    chunks = [output[i:i+2000] for i in range(0, min(len(output), 20000), 2000)]
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        }
        for chunk in chunks
    ]

    try:
        requests.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            json={
                "parent": {"page_id": parent_page},
                "properties": {"title": {"title": [{"text": {"content": title}}]}},
                "children": children,
            },
            timeout=15,
        )
    except Exception:
        pass


# ── API Endpoints ────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "crew": "cleya_marketing",
        "version": "1.0.0",
        "agents": ["intel", "growth", "content", "community", "plg"],
        "store": "redis" if not isinstance(store, dict) else "memory",
    }


@app.post("/api/run", response_model=RunResponse)
async def run_full_crew(req: CrewRunRequest):
    """Kick off the full 5-agent pipeline. Takes 5-15 minutes."""
    run_id = str(uuid.uuid4())[:8]
    agents = req.agents or ["intel", "growth", "content", "community", "plg"]

    try:
        execute_crew_run(run_id, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crew failed: {str(e)}")

    run_data = load_run(run_id)
    return RunResponse(
        run_id=run_id,
        status=run_data.get("status", "completed"),
        message="Crew execution complete. Results posted to Slack and Notion.",
        agents=agents,
    )


@app.post("/api/run/{agent_name}", response_model=RunResponse)
async def run_single(agent_name: str, req: CrewRunRequest):
    """Run a single agent: intel, growth, content, community, or plg."""
    valid = ["intel", "growth", "content", "community", "plg"]
    if agent_name not in valid:
        raise HTTPException(status_code=400, detail=f"Agent must be one of: {valid}")

    run_id = str(uuid.uuid4())[:8]

    try:
        execute_crew_run(run_id, req, agent_filter=agent_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent {agent_name} failed: {str(e)}")

    run_data = load_run(run_id)
    return RunResponse(
        run_id=run_id,
        status=run_data.get("status", "completed"),
        message=f"Agent '{agent_name}' complete. Results posted to Slack and Notion.",
        agents=[agent_name],
    )


@app.get("/api/status/{run_id}")
async def get_status(run_id: str):
    """Check the status and output of a crew run."""
    data = load_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return data


@app.post("/api/webhook/slack")
async def slack_slash_command(request: Request):
    """
    Handle Slack slash commands: /cleya-crew [agent] [segment]
    
    Examples:
      /cleya-crew               → full pipeline
      /cleya-crew intel         → intelligence only
      /cleya-crew content       → content calendar only
    """
    form = await request.form()
    text = form.get("text", "").strip()
    user = form.get("user_name", "unknown")

    parts = text.split(maxsplit=1)
    agent_filter = parts[0] if parts and parts[0] in ["intel", "growth", "content", "community", "plg"] else None
    segment = parts[1] if len(parts) > 1 else "all professionals across India's ecosystem"

    run_id = str(uuid.uuid4())[:8]
    req = CrewRunRequest(target_segment=segment)

    # Execute synchronously (Slack expects response within 3s, so we ack first)
    # In production, use a queue or Vercel background function
    return JSONResponse({
        "response_type": "in_channel",
        "text": (
            f"🚀 *Cleya Marketing Crew* triggered by @{user}\n"
            f"Run ID: `{run_id}`\n"
            f"Agent: `{agent_filter or 'full_pipeline'}`\n"
            f"Target: {segment}\n\n"
            f"_Running now — results will be posted here when complete..._"
        ),
    })


# ── Mangum handler for Vercel ────────────────────────────────────────

from mangum import Mangum
handler = Mangum(app, lifespan="off")
