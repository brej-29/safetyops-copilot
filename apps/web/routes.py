"""Crawlable public pages and a no-index personal workspace."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response

router = APIRouter(include_in_schema=False)
WEB = Path(__file__).parent
BASE = "https://safetyops-api-a5afr3rcdq-as.a.run.app"
PAGES = {
    "/": "index.html",
    "/app": "app.html",
    "/guides/incident-triage": "triage.html",
    "/guides/shift-handover": "handover.html",
    "/privacy": "privacy.html",
}


@router.get("/assets/{filename}")
def asset(filename: str):
    if filename not in {"styles.css", "app.js", "home.js", "mark.svg", "social.png", "font.woff2"}:
        raise HTTPException(404)
    path = WEB / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return (
        "User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /api/\n"
        "Disallow: /events/\nDisallow: /docs\nDisallow: /openapi.json\n"
        f"Sitemap: {BASE}/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
def sitemap():
    urls = "".join(f"<url><loc>{BASE}{p}</loc></url>" for p in PAGES if p != "/app")
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
        media_type="application/xml",
    )


@router.get("/llms.txt", response_class=PlainTextResponse)
def llms():
    return f"""# SafetyOps Copilot

> Open-source safety observation triage and corrective-action workspace.

Record an observation, review an explainable priority assessment, assign an action,
and export a shift handover. Personal records are stored in a browser-linked
workspace backed by a database. Not an emergency service or compliance certification.

## Public documentation
- [Product]({BASE}/): Features and a clearly labeled synthetic example.
- [Incident triage]({BASE}/guides/incident-triage): Assessment and limitations.
- [Shift handover]({BASE}/guides/shift-handover): Follow-up workflow.
- [Source](https://github.com/brej-29/safetyops-copilot): Architecture, tests and model cards.

## Evidence
The checked-in MSHA evaluation covers 1,605 held-out narratives: DistilBERT macro-F1
0.7799 versus rule baseline 0.3357. Mining-domain results are not validation for
other sites. Category matching is rule-based; model_source identifies the actual
severity inference path. Priority scores are heuristics, not calibrated probabilities.

## Agent integration
Optional local MCP server: python -m services.mcp.server (see docs/MCP.md).
Read-only tools assess text, retrieve runbooks, and summarize supplied handovers.
No access to browser workspace records or credentials.
"""


@router.get("/")
@router.get("/app")
@router.get("/guides/incident-triage")
@router.get("/guides/shift-handover")
@router.get("/privacy")
def page(request: Request):
    html = (WEB / PAGES[request.url.path]).read_text(encoding="utf-8-sig")
    headers = {
        "Cache-Control": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        ),
    }
    if request.url.path == "/app":
        headers["X-Robots-Tag"] = "noindex, nofollow"
    return HTMLResponse(html, headers=headers)
