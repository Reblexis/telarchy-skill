"""Push a heartbeat and a trace to /admin so the workspace operator sees this
agent in `/admin → Bot agents` with full reasoning per market.

Requires:
  TELARCHY_MASTER_KEY  (X-API-Key for the platform operator)
  TELARCHY_WORKSPACE_ID
  AGENT_ID  (whatever you want the operator to see)
"""

import os
import datetime
import urllib.request
import json

BASE = os.environ.get("TELARCHY_URL", "https://telarchy.com")
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": os.environ["TELARCHY_MASTER_KEY"],
    "X-Workspace-Id": os.environ["TELARCHY_WORKSPACE_ID"],
}
AGENT_ID = os.environ.get("AGENT_ID", "skill-example-bot")
NOW = datetime.datetime.utcnow().isoformat() + "Z"
NEXT = (datetime.datetime.utcnow() + datetime.timedelta(minutes=5)).isoformat() + "Z"


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        method="POST",
        headers=HEADERS,
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req) as r:
        body = r.read().decode("utf-8") or "{}"
        print(f"  {path} -> {r.status}: {body[:200]}")


print(f"==> heartbeat for {AGENT_ID}")
post("/api/admin/agent-heartbeat", {
    "agentId": AGENT_ID,
    "status": "idle",
    "workspaceId": os.environ["TELARCHY_WORKSPACE_ID"],
    "strategy": "skill-example",
    "lastCycleStartedAt": NOW,
    "lastCycleEndedAt": NOW,
    "nextCycleAt": NEXT,
    "pollIntervalSeconds": 300,
    "lastTraded": 0,
    "lastSkipped": 1,
    "lastErrors": 0,
    "balance": 1000,
})

print(f"==> trace for {AGENT_ID}")
post("/api/admin/agent-traces", {
    "workspaceId": os.environ["TELARCHY_WORKSPACE_ID"],
    "agentId": AGENT_ID,
    "strategy": "skill-example",
    "startedAt": NOW,
    "endedAt": NOW,
    "candidates": 1,
    "traded": 0,
    "skipped": 1,
    "errors": 0,
    "entries": [
        {
            "marketId": "demo-market",
            "metric": "Demo Metric",
            "targetDate": "2026-12-31",
            "rangeMin": 0,
            "rangeMax": 1000,
            "consensus": 500,
            "estimate": 510,
            "confidence": 0.5,
            "distance": 10,
            "threshold": 80,
            "outcome": "skip-under-threshold",
            "reasoning": "Skill example: distance 10 below threshold 80, no edge to trade.",
        }
    ],
})

print("==> open https://telarchy.com/admin to see this agent in the Bot agents panel")
