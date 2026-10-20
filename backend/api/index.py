"""AI Skills Runner — composable skills + tool-calling agent (demo mode)."""
from __future__ import annotations
import os, re, math
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AI Skills Runner", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SKILLS = {
    "research": {"name": "research", "title": "Research Assistant", "description": "Summarize topics, compare options", "instructions": "Be structured. Use bullets.", "tools": ["web_search_mock", "summarize"]},
    "ops": {"name": "ops", "title": "Ops Helper", "description": "Status checks, time, notes", "instructions": "Be concise and action-oriented.", "tools": ["get_time", "save_note", "list_notes"]},
    "math": {"name": "math", "title": "Math Skill", "description": "Safe arithmetic", "instructions": "Show expression and result.", "tools": ["calculator"]},
    "nigeria": {"name": "nigeria", "title": "Nigeria Context", "description": "Cities and mock FX", "instructions": "Nigeria-aware, practical.", "tools": ["fx_rate", "city_info"]},
}
_NOTES: dict[str, str] = {}

def _calculator(expression: str) -> str:
    allowed = {"abs": abs, "round": round, "sqrt": math.sqrt, "pi": math.pi, "e": math.e}
    if "**" in expression:
        m = re.search(r"\*\*\s*(\d+)", expression)
        if m and int(m.group(1)) > 20:
            return "Error: exponent too large (max 20)"
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        out = f"{expression} = {result}"
        return out if len(out) < 500 else out[:200] + "… (truncated)"
    except Exception as e:
        return f"Error: {e}"

def _tool(name: str, args: dict) -> str:
    if name == "calculator":
        return _calculator(args.get("expression", "2+2"))
    if name == "get_time":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if name == "save_note":
        t, c = args.get("title", "note"), args.get("content", "")
        _NOTES[t] = c
        return f"Saved note '{t}'"
    if name == "list_notes":
        return "No notes." if not _NOTES else "\n".join(f"- {k}: {v[:60]}" for k, v in _NOTES.items())
    if name == "web_search_mock":
        q = args.get("query", "")
        return f"Mock results for '{q}': (1) Overview (2) Comparison (3) Docs"
    if name == "summarize":
        text = args.get("text", "")[:400]
        return f"Summary: {text[:120]}…" if len(text) > 120 else f"Summary: {text}"
    if name == "fx_rate":
        pair = (args.get("pair") or "USDNGN").upper()
        rates = {"USDNGN": 1600, "GBPNGN": 2050, "EURNGN": 1750}
        return f"{pair}: ~{rates.get(pair, 1500)} (mock)"
    if name == "city_info":
        city = (args.get("city") or "Abuja").title()
        info = {"Abuja": "Federal capital. Maitama, Wuse, Central Area.", "Lagos": "Commercial hub. High startup density.", "Port Harcourt": "Oil & gas hub."}
        return info.get(city, f"{city}: major Nigerian city (mock).")
    return f"Unknown tool: {name}"

class RunRequest(BaseModel):
    skill: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

class RunResponse(BaseModel):
    skill: str
    reply: str
    tool_calls: List[Dict[str, Any]]
    instructions_used: str

@app.get("/")
def root():
    return {"message": "AI Skills Runner", "skills": "/api/skills", "health": "/api/health"}

@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "skills": list(SKILLS.keys())}

@app.get("/api/skills")
@app.get("/skills")
def list_skills():
    return {"skills": [{"name": s["name"], "title": s["title"], "description": s["description"], "tools": s["tools"]} for s in SKILLS.values()]}

def _demo_run(skill_name: str, message: str) -> RunResponse:
    skill = SKILLS.get(skill_name) or SKILLS["ops"]
    lower = message.lower()
    calls: List[Dict[str, Any]] = []
    tools = set(skill["tools"])

    def call(tool: str, args: dict):
        if tool not in tools:
            return None
        result = _tool(tool, args)
        calls.append({"tool": tool, "arguments": args, "result": result})
        return result

    reply_parts = [f"[{skill['title']}] "]
    if "calculator" in tools and any(x in lower for x in ["calculate", "math", "sqrt", "+", "*"]):
        expr = message.split(":")[-1].strip() if ":" in message else "2+2"
        expr = re.sub(r"(?i)calculate", "", expr).strip()
        r = call("calculator", {"expression": expr})
        reply_parts.append(r or "")
    elif "fx_rate" in tools and any(x in lower for x in ["fx", "dollar", "naira", "exchange", "usd", "gbp", "eur"]):
        pair = "USDNGN"
        if "gbp" in lower: pair = "GBPNGN"
        if "eur" in lower: pair = "EURNGN"
        r = call("fx_rate", {"pair": pair})
        reply_parts.append(r or "")
    elif "city_info" in tools and any(x in lower for x in ["city", "lagos", "abuja", "port harcourt"]):
        city = "Abuja"
        for c in ["Port Harcourt", "Lagos", "Abuja"]:
            if c.lower() in lower:
                city = c
                break
        r = call("city_info", {"city": city})
        reply_parts.append(r or "")
    elif "get_time" in tools and "time" in lower:
        r = call("get_time", {})
        reply_parts.append(f"Current time: {r}")
    elif "save_note" in tools and ("save" in lower or "note" in lower) and "list" not in lower:
        r = call("save_note", {"title": "skill-note", "content": message})
        reply_parts.append(r or "")
    elif "list_notes" in tools and "list" in lower:
        r = call("list_notes", {})
        reply_parts.append(r or "")
    elif "web_search_mock" in tools or "summarize" in tools:
        r = call("web_search_mock", {"query": message[:80]})
        reply_parts.append(r or "")
        if "summarize" in tools:
            call("summarize", {"text": message})
            reply_parts.append(" Takeaway: clarify goals, constraints, next steps.")
    else:
        reply_parts.append(f"Skill loaded. Tools: {', '.join(skill['tools'])}. Try a prompt that needs one.")
    return RunResponse(skill=skill["name"], reply="".join(reply_parts).strip(), tool_calls=calls, instructions_used=skill["instructions"])

@app.post("/api/run")
@app.post("/run")
def run(req: RunRequest):
    return _demo_run(req.skill.strip().lower(), req.message)
