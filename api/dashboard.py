"""
Cleya Marketing Crew — Vercel Dashboard & Proxy
=================================================

Lightweight Vercel function that serves a dashboard UI and proxies 
crew run requests to the Railway-hosted crew API.

This stays under Vercel's 500MB limit because it has no heavy 
ML/AI dependencies — just requests + FastAPI.
"""

import os
import json
import requests as http_requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

app = FastAPI(title="Cleya Marketing Crew Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The Railway-hosted crew API URL
CREW_API_URL = os.getenv("CREW_API_URL", "http://localhost:8000")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the crew dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/api/health")
async def health():
    """Health check + crew API status."""
    try:
        resp = http_requests.get(f"{CREW_API_URL}/api/health", timeout=5)
        crew_status = resp.json() if resp.ok else {"status": "unreachable"}
    except Exception:
        crew_status = {"status": "unreachable"}
    
    return {
        "dashboard": "ok",
        "crew_api": crew_status,
        "crew_api_url": CREW_API_URL,
    }


@app.post("/api/run/{path:path}")
async def proxy_run(path: str, request: Request):
    """Proxy run requests to the crew API."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    try:
        resp = http_requests.post(
            f"{CREW_API_URL}/api/run/{path}" if path else f"{CREW_API_URL}/api/run",
            json=body,
            timeout=900,  # 15 min timeout for crew runs
        )
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Crew API error: {str(e)}")


@app.post("/api/run")
async def proxy_run_full(request: Request):
    """Proxy full pipeline run to crew API."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    try:
        resp = http_requests.post(
            f"{CREW_API_URL}/api/run",
            json=body,
            timeout=900,
        )
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Crew API error: {str(e)}")


@app.get("/api/status/{run_id}")
async def proxy_status(run_id: str):
    """Proxy status requests to the crew API."""
    try:
        resp = http_requests.get(f"{CREW_API_URL}/api/status/{run_id}", timeout=10)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Crew API error: {str(e)}")


# ── Dashboard HTML ───────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cleya.ai Marketing Crew</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a; color: #e5e5e5; min-height: 100vh;
            padding: 2rem;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { 
            font-size: 1.8rem; font-weight: 600; margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #737373; margin-bottom: 2rem; font-size: 0.9rem; }
        .status-bar {
            display: flex; gap: 1rem; margin-bottom: 2rem;
            padding: 1rem; background: #171717; border-radius: 12px;
            border: 1px solid #262626;
        }
        .status-item { 
            display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem;
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .dot.green { background: #22c55e; }
        .dot.red { background: #ef4444; }
        .dot.yellow { background: #eab308; }
        .agents-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 1rem; margin-bottom: 2rem;
        }
        .agent-card {
            background: #171717; border: 1px solid #262626; border-radius: 12px;
            padding: 1.25rem; cursor: pointer; transition: all 0.2s;
        }
        .agent-card:hover { border-color: #60a5fa; transform: translateY(-2px); }
        .agent-card.running { border-color: #eab308; }
        .agent-card h3 { font-size: 0.95rem; margin-bottom: 0.25rem; }
        .agent-card p { font-size: 0.8rem; color: #737373; line-height: 1.4; }
        .agent-card .tag { 
            display: inline-block; font-size: 0.7rem; padding: 2px 8px;
            background: #1e3a5f; color: #60a5fa; border-radius: 4px;
            margin-top: 0.5rem;
        }
        .run-panel {
            background: #171717; border: 1px solid #262626; border-radius: 12px;
            padding: 1.5rem; margin-bottom: 2rem;
        }
        .run-panel h2 { font-size: 1.1rem; margin-bottom: 1rem; }
        .input-group { margin-bottom: 1rem; }
        .input-group label { font-size: 0.8rem; color: #a3a3a3; display: block; margin-bottom: 0.25rem; }
        .input-group input, .input-group select {
            width: 100%; padding: 0.6rem 0.8rem; background: #0a0a0a;
            border: 1px solid #262626; border-radius: 8px; color: #e5e5e5;
            font-size: 0.85rem;
        }
        .btn {
            padding: 0.6rem 1.5rem; border: none; border-radius: 8px;
            font-size: 0.85rem; font-weight: 500; cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            color: white;
        }
        .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-secondary { background: #262626; color: #e5e5e5; }
        .btn-secondary:hover { background: #363636; }
        .output-panel {
            background: #0f0f0f; border: 1px solid #262626; border-radius: 12px;
            padding: 1.25rem; margin-top: 1rem; display: none;
            max-height: 500px; overflow-y: auto;
        }
        .output-panel pre { 
            font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
            white-space: pre-wrap; line-height: 1.5; color: #a3a3a3;
        }
        .actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cleya.ai Marketing Crew</h1>
        <p class="subtitle">Multi-agent growth & viral marketing system</p>

        <div class="status-bar">
            <div class="status-item">
                <div class="dot" id="apiDot"></div>
                <span id="apiStatus">Checking API...</span>
            </div>
            <div class="status-item">
                <div class="dot" id="storeDot"></div>
                <span id="storeStatus">Store: —</span>
            </div>
        </div>

        <div class="agents-grid">
            <div class="agent-card" onclick="runAgent('intel')">
                <h3>Intelligence Analyst</h3>
                <p>Ecosystem intel, funding trends, competitor monitoring, Tier-2 signals</p>
                <span class="tag">Serper + Apify + Slack</span>
            </div>
            <div class="agent-card" onclick="runAgent('growth')">
                <h3>Growth Strategist</h3>
                <p>Acquisition funnels, growth loops, channel strategy, metrics</p>
                <span class="tag">Serper + Notion + Slack</span>
            </div>
            <div class="agent-card" onclick="runAgent('content')">
                <h3>Content Architect</h3>
                <p>LinkedIn/X content calendar, hooks, memes, viral mechanics</p>
                <span class="tag">Serper + Notion + Slack</span>
            </div>
            <div class="agent-card" onclick="runAgent('community')">
                <h3>Community Hacker</h3>
                <p>Partnerships, ambassadors, events, WhatsApp flows</p>
                <span class="tag">HubSpot + Lemlist + Resend</span>
            </div>
            <div class="agent-card" onclick="runAgent('plg')">
                <h3>PLG Engineer</h3>
                <p>Referral systems, match cards, waitlist gamification</p>
                <span class="tag">Notion + Slack</span>
            </div>
        </div>

        <div class="run-panel">
            <h2>Run Crew</h2>
            <div class="input-group">
                <label>Target Segment</label>
                <input type="text" id="segment" value="all professionals across India's ecosystem" />
            </div>
            <div class="input-group">
                <label>Time Period</label>
                <input type="text" id="period" value="this week" />
            </div>
            <div class="actions">
                <button class="btn btn-primary" onclick="runAgent('')">Run Full Pipeline</button>
                <button class="btn btn-secondary" onclick="runAgent('intel')">Intel Only</button>
                <button class="btn btn-secondary" onclick="runAgent('content')">Content Only</button>
                <button class="btn btn-secondary" onclick="runAgent('growth')">Growth Only</button>
            </div>
        </div>

        <div class="output-panel" id="output">
            <pre id="outputText"></pre>
        </div>
    </div>

    <script>
        async function checkHealth() {
            try {
                const resp = await fetch('/api/health');
                const data = await resp.json();
                const apiDot = document.getElementById('apiDot');
                const apiStatus = document.getElementById('apiStatus');
                const storeDot = document.getElementById('storeDot');
                const storeStatus = document.getElementById('storeStatus');

                if (data.crew_api?.status === 'ok') {
                    apiDot.className = 'dot green';
                    apiStatus.textContent = 'Crew API: Online';
                    storeDot.className = 'dot green';
                    storeStatus.textContent = 'Store: ' + (data.crew_api.store || 'memory');
                } else {
                    apiDot.className = 'dot red';
                    apiStatus.textContent = 'Crew API: Offline';
                    storeDot.className = 'dot red';
                    storeStatus.textContent = 'Store: unavailable';
                }
            } catch (e) {
                document.getElementById('apiDot').className = 'dot red';
                document.getElementById('apiStatus').textContent = 'Crew API: Error';
            }
        }

        async function runAgent(agent) {
            const segment = document.getElementById('segment').value;
            const period = document.getElementById('period').value;
            const output = document.getElementById('output');
            const outputText = document.getElementById('outputText');

            output.style.display = 'block';
            outputText.textContent = `Running ${agent || 'full pipeline'}...\\nTarget: ${segment}\\nPeriod: ${period}\\n\\nThis may take 5-15 minutes. Results will be posted to Slack and Notion.\\n`;

            try {
                const url = agent ? `/api/run/${agent}` : '/api/run';
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_segment: segment,
                        time_period: period,
                    }),
                });
                const data = await resp.json();
                outputText.textContent += `\\n${JSON.stringify(data, null, 2)}`;
            } catch (e) {
                outputText.textContent += `\\nError: ${e.message}`;
            }
        }

        checkHealth();
        setInterval(checkHealth, 30000);
    </script>
</body>
</html>
"""

handler = Mangum(app, lifespan="off")
