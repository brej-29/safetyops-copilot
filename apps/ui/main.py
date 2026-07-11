from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("SAFETYOPS_API_BASE_URL", "http://localhost:8000")
# Forwarded to the API's write endpoints when it is deployed with
# SAFETYOPS_API_KEY protection enabled.
API_KEY = os.getenv("SAFETYOPS_API_KEY")
DEPLOY_MODE = os.getenv("DEPLOY_MODE", os.getenv("SAFETYOPS_DEPLOY_MODE", "local"))
GITHUB_URL = "https://github.com/brej-29/safetyops-copilot"

SEVERITY_BADGES = {
    "low": "🟢 Low",
    "medium": "🟡 Medium",
    "high": "🔴 High",
}

SAMPLE_INCIDENTS = {
    "🩹 Slip near loading bay": "Worker slipped on a wet floor near the loading bay and was taken to hospital.",
    "🚜 Forklift collision": "Forklift backed into shelving; falling boxes struck a worker on the shoulder.",
    "🔥 Electrical fire": "Small electrical fire in the control panel; extinguished, no injuries.",
    "🧪 Chemical splash": "Chemical splash on a technician's arm in the lab; first aid given on site.",
    "✅ Routine inspection": "Routine walkthrough completed; guard rail bolts found loose, no incident.",
}

SAMPLE_IMAGES = {
    "👷 Construction site": "data/sample/sample_construction_site.jpg",
    "🏗️ Crane crew": "data/sample/sample_crane_site.jpg",
    "🧱 Stonemason team": "data/sample/sample_workers_group.jpg",
    "🥽 Helmet close-up": "data/sample/sample_worker_helmet_visor.jpg",
    "👤 Worker portrait": "data/sample/sample_worker_portrait.jpg",
    "🚶 Street scene": "data/sample/sample_ppe_image.jpg",
}

st.set_page_config(
    page_title="SafetyOps Copilot",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(100deg, #111827 0%, #1f2937 55%, #78350f 130%);
        border-radius: 14px;
        padding: 1.6rem 2rem 1.4rem 2rem;
        margin-bottom: 0.4rem;
    }
    .hero h1 { color: #ffffff; margin: 0 0 0.35rem 0; font-size: 2rem; }
    .hero p { color: #fcd34d; margin: 0; font-size: 1.05rem; }
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 12px;
        padding: 0.8rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_http_client() -> httpx.Client:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    return httpx.Client(base_url=API_BASE_URL, timeout=30.0, headers=headers)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=20, show_spinner=False)
def _fetch_system_status() -> Dict[str, Any]:
    try:
        resp = get_http_client().get("/system/status")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return {}


def _fetch_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        response = get_http_client().get("/events/recent", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        st.error(f"Could not reach the SafetyOps API: {exc}")
        return []


def _fetch_aggregate_summary(days: int = 7) -> List[Dict[str, Any]]:
    try:
        response = get_http_client().get("/aggregates/summary", params={"days": days})
        response.raise_for_status()
        return response.json().get("items", [])
    except httpx.HTTPError as exc:
        st.error(f"Could not load summary data: {exc}")
        return []


def _wait_for_enriched_event(event_id: str, timeout_s: float = 30.0) -> Optional[Dict[str, Any]]:
    """Poll the API until the background worker has analyzed the event."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for event in _fetch_recent_events(limit=50):
            if event.get("id") == event_id:
                return event
        time.sleep(2.0)
    return None


def _severity_badge(severity: Optional[str]) -> str:
    return SEVERITY_BADGES.get((severity or "").lower(), "⚪ Unknown")


def _flatten_events(events: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(events)
    if "enrichment" in df.columns:
        enrichment = pd.json_normalize(df["enrichment"].apply(lambda x: x or {}))
        enrichment.columns = [f"ai.{c}" for c in enrichment.columns]
        df = pd.concat([df.drop(columns=["enrichment"]), enrichment], axis=1)
    return df


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🦺 SafetyOps Copilot")
        st.caption("AI triage for workplace safety — reads reports, checks photos, plans the response.")

        st.divider()
        st.markdown("**System status**")
        status = _fetch_system_status()
        if not status:
            st.info("⏳ Waking the free-tier backend (~1 min)...")
        else:
            rows = [
                ("Web API", status.get("api_ok")),
                ("Database", status.get("database_ok")),
                ("Event queue", status.get("redis_ok")),
            ]
            for name, ok in rows:
                st.markdown(f"{'🟢' if ok else '🔴'} {name}")
            hb_age = status.get("worker_seconds_since_heartbeat")
            if isinstance(hb_age, (int, float)) and hb_age < 60:
                st.markdown("🟢 AI worker")
            else:
                st.markdown("💤 AI worker (wakes with traffic)")

        st.divider()
        st.markdown(f"[⭐ Source code on GitHub]({GITHUB_URL})")
        st.caption(
            "Runs on free-tier cloud infrastructure — the first request after a quiet "
            "period takes about a minute while the server wakes up."
        )


# ---------------------------------------------------------------------------
# Overview tab
# ---------------------------------------------------------------------------


def _render_overview_tab() -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Severity prediction accuracy",
        "78%",
        "+38 pts vs keyword rules",
        help="DistilBERT fine-tuned on real accident narratives, measured on a held-out test set of 1,605 reports.",
    )
    col2.metric(
        "High-severity incidents caught",
        "88%",
        "recall on fatal/disabling events",
        help="Of the truly high-severity incidents in the test set, the model flags 88%.",
    )
    col3.metric(
        "Real training reports",
        "273k",
        "public MSHA safety data",
        help="Labels derived from officially reported injury outcomes — no synthetic data.",
    )

    st.markdown("#### From incident to action plan in four steps")
    steps = [
        ("📨", "Ingest", "Reports and photos arrive via API and join an event queue — nothing gets lost."),
        ("🧠", "Analyze", "AI models judge severity of text and spot missing hard hats in photos."),
        ("🗄️", "Score", "Each event gets a 0–100 risk score and lands in the database."),
        ("📋", "Advise", "The Copilot writes an incident brief with concrete next steps."),
    ]
    cols = st.columns(4)
    for col, (icon, title, desc) in zip(cols, steps):
        with col, st.container(border=True):
            st.markdown(f"### {icon} {title}")
            st.caption(desc)

    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        st.markdown("##### 🎯 Try it in 30 seconds")
        st.markdown(
            "1. **🚨 Report an Incident** — watch the AI classify it and write an action plan\n"
            "2. **📷 PPE Photo Check** — run a photo through the vision model\n"
            "3. **📊 Safety Dashboard** — see events become trends"
        )
    with right, st.container(border=True):
        st.markdown("##### 🤔 Why does this matter?")
        st.caption(
            "Safety teams receive endless incident reports and site photos. Triaging them "
            "by hand is slow — and the serious ones need attention *now*. This copilot "
            "reads everything instantly and puts the riskiest items on top."
        )

    st.caption(
        f"Built with FastAPI · Redis Streams · Postgres · Hugging Face · YOLOv8 · LangGraph · "
        f"Prometheus — [source on GitHub]({GITHUB_URL})"
    )


# ---------------------------------------------------------------------------
# Incident reporting tab
# ---------------------------------------------------------------------------


def _render_incident_tab() -> None:
    st.markdown("#### 🚨 Describe what happened — the Copilot does the rest")
    st.caption(
        "Type an incident like a supervisor would radio it in, or tap a sample. "
        "The AI judges severity, estimates risk, and writes an action plan."
    )

    sample_label = st.pills("Samples", list(SAMPLE_INCIDENTS.keys()), selection_mode="single")
    default_text = SAMPLE_INCIDENTS.get(sample_label, "")

    with st.form("incident_form", border=False):
        text = st.text_area(
            "Incident description",
            value=default_text,
            placeholder="e.g. Worker slipped on a wet floor near the loading bay...",
            height=110,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("🚨 Analyze incident", type="primary")

    if not submitted:
        return
    if not text.strip():
        st.warning("Please describe the incident first.")
        return

    client = get_http_client()
    with st.spinner("Reading the report, checking history, writing the brief… (~10 s)"):
        try:
            resp = client.post("/copilot/triage", json={"text": text}, timeout=150.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            st.error(f"The Copilot could not be reached: {exc}")
            return
        # Also feed it into the live event pipeline so it shows up in the dashboard.
        try:
            client.post("/events/text", json={"text": text, "metadata": {"source": "ui-incident"}})
        except httpx.HTTPError:
            pass

    result = resp.json()
    risk = result.get("risk_score") or 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Severity", _severity_badge(result.get("severity")))
    col2.metric("Category", (result.get("category") or "other").replace("_", " ").title())
    col3.metric("Risk score", f"{risk} / 100")
    st.progress(min(max(risk, 0), 100) / 100.0)

    with st.container(border=True):
        st.markdown("##### 📋 Incident brief — written by the AI")
        st.markdown(result.get("report_markdown") or "_No report generated._")

    with st.expander("🔍 What just happened behind the scenes?"):
        st.markdown(
            "1. Your text hit the **FastAPI** backend and a **DistilBERT** model predicted severity.\n"
            "2. The **LangGraph workflow** pulled related events, scored the risk, and picked a playbook.\n"
            "3. An **LLM** (Groq) rewrote the draft into the brief above.\n"
            "4. In parallel the incident entered the **event queue** — it's on the Safety Dashboard now."
        )


# ---------------------------------------------------------------------------
# Vision tab
# ---------------------------------------------------------------------------


def _render_vision_tab() -> None:
    st.markdown("#### 📷 Can the AI spot missing safety gear?")
    st.caption(
        "The vision model counts people and checks who is wearing a hard hat — the same "
        "signal a site camera would feed into this system automatically."
    )

    choice = st.pills("Choose a photo", list(SAMPLE_IMAGES.keys()), selection_mode="single", default=list(SAMPLE_IMAGES.keys())[0])
    image_path = SAMPLE_IMAGES[choice or list(SAMPLE_IMAGES.keys())[0]]

    col_img, col_result = st.columns([1, 1])
    with col_img:
        if Path(image_path).exists():
            st.image(image_path, width="stretch")

    with col_result:
        run = st.button("📷 Run PPE check", type="primary")
        if run:
            client = get_http_client()
            try:
                resp = client.post("/events/vision", data={"image_path": image_path})
                resp.raise_for_status()
                event_id = resp.json()["event_id"]
            except httpx.HTTPError as exc:
                st.error(f"Could not submit the photo: {exc}")
                return

            with st.spinner("The vision model is scanning the photo…"):
                event = _wait_for_enriched_event(event_id)

            if event is None:
                st.warning("Taking longer than expected (server may be waking up) — check the dashboard in a minute.")
                return

            ai = event.get("enrichment") or {}
            persons = ai.get("num_persons", 0)
            with_ppe = ai.get("num_persons_with_ppe", 0)
            compliance = ai.get("compliance_score", 0.0)

            m1, m2 = st.columns(2)
            m1.metric("People detected", persons)
            m2.metric("Wearing hard hats", with_ppe)
            st.metric("PPE compliance", f"{compliance:.0%}")
            st.progress(min(max(compliance, 0.0), 1.0))

            if compliance >= 0.8:
                st.success("Good compliance — no action needed.", icon="✅")
            elif compliance >= 0.5:
                st.warning("Partial compliance — a supervisor should check this area.", icon="⚠️")
            else:
                st.error("Low compliance — immediate attention recommended.", icon="🚨")
        else:
            st.info("Pick a photo and press **Run PPE check**.", icon="👈")

    with st.expander("🔍 What happens behind the scenes?"):
        st.markdown(
            "The photo reference goes onto the **event queue**, the **background worker** runs "
            "**YOLOv8 hard-hat detection**, computes the compliance ratio, assigns severity, and "
            "stores it all in **Postgres** — the same path a real CCTV snapshot would take."
        )


# ---------------------------------------------------------------------------
# Dashboard tab
# ---------------------------------------------------------------------------


def _render_dashboard_tab() -> None:
    st.markdown("#### 📊 The safety manager's view")
    st.caption(
        "Every analyzed report and photo lands here — what happened, how severe, and where "
        "the trends are heading."
    )

    days = st.slider("Look back (days)", min_value=1, max_value=30, value=7)
    summary_items = _fetch_aggregate_summary(days=days)

    if summary_items:
        df = pd.DataFrame(summary_items)
        col_chart, col_table = st.columns([2, 1])
        with col_chart, st.container(border=True):
            st.markdown("**Events by type and severity**")
            pivot = df.pivot_table(
                index="event_type", columns="severity", values="count",
                aggfunc="sum", fill_value=0,
            )
            pivot.index = [i.replace("_event", " reports").title() for i in pivot.index]
            st.bar_chart(pivot, color=["#dc2626", "#16a34a", "#eab308"][: pivot.shape[1]])
        with col_table, st.container(border=True):
            st.markdown("**Totals by severity**")
            totals = df.groupby("severity")["count"].sum().reset_index()
            totals["severity"] = totals["severity"].map(_severity_badge)
            totals.columns = ["Severity", "Events"]
            st.dataframe(totals, hide_index=True, width="stretch")
    else:
        st.info("No data yet — analyze an incident or photo first, then come back.", icon="📭")

    st.markdown("**Latest analyzed events** — auto-refreshes every 5 seconds")
    _render_recent_events_table()


@st.fragment(run_every="5s")
def _render_recent_events_table() -> None:
    events = _fetch_recent_events(limit=50)
    if not events:
        st.info("Nothing here yet — the feed fills up as events are analyzed.")
        return
    df = _flatten_events(events)
    display_cols = [
        c for c in ("created_at", "event_type", "category", "severity",
                    "ai.risk_score", "ai.compliance_score", "ai.text")
        if c in df.columns
    ]
    df = df[display_cols].rename(columns={
        "created_at": "When",
        "event_type": "Type",
        "category": "Category",
        "severity": "Severity",
        "ai.risk_score": "Risk",
        "ai.compliance_score": "PPE compliance",
        "ai.text": "Description",
    })
    if "Type" in df.columns:
        df["Type"] = df["Type"].map({"text_event": "📝 Report", "vision_event": "📷 Photo"}).fillna(df["Type"])
    if "Severity" in df.columns:
        df["Severity"] = df["Severity"].map(_severity_badge)
    if "When" in df.columns:
        df["When"] = pd.to_datetime(df["When"], format="mixed").dt.strftime("%b %d, %H:%M")
    st.dataframe(df, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Behind the scenes tab
# ---------------------------------------------------------------------------


def _render_behind_the_scenes_tab() -> None:
    st.markdown("#### ⚙️ For the technically curious")
    st.caption("This demo is not a mock-up — it's a distributed system running live on free-tier cloud infrastructure.")

    st.markdown(
        """
        | Component | Technology | What it does |
        |---|---|---|
        | Web API | **FastAPI** · Google Cloud Run | Ingestion + queries, API-key auth, rate limiting |
        | Event queue | **Redis Streams** · Upstash | Buffers events; failed ones go to a dead-letter queue for replay |
        | Background worker | **Python** consumer | Runs the ML models with retries and idempotent processing |
        | Database | **Postgres** · Neon | Raw events, AI enrichments, hourly/daily aggregates |
        | Text AI | **DistilBERT** · Hugging Face | Severity prediction — 78% accuracy vs 40% keyword baseline |
        | Vision AI | **YOLOv8** · Ultralytics | Hard-hat detection → PPE compliance scoring |
        | Copilot | **LangGraph** + Groq LLM | Context → risk → playbook → written brief |
        | Observability | **Prometheus** + Evidently | Metrics and text-drift reports |
        """
    )

    with st.expander("⚠️ Honest limitations — every ML system has them"):
        st.markdown(
            "- The severity model is trained on **mining-industry** narratives; transfer to other industries is plausible but unvalidated.\n"
            "- The vision model detects **hard hats only** — vests and goggles are future work.\n"
            "- Free-tier hosting sleeps when idle, so the first request can take a minute.\n"
            "- AI outputs are **advisory**: a real deployment keeps a human in the loop."
        )

    st.caption(f"Model cards, evaluation results, and architecture decision records: [GitHub]({GITHUB_URL})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _render_sidebar()

    st.markdown(
        """
        <div class="hero">
          <h1>🦺 SafetyOps Copilot</h1>
          <p>AI that reads incident reports, spots missing safety gear in photos,
          and tells safety teams what to do next.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_overview, tab_incident, tab_vision, tab_dash, tab_tech = st.tabs(
        [
            "🏠 Overview",
            "🚨 Report an Incident",
            "📷 PPE Photo Check",
            "📊 Safety Dashboard",
            "⚙️ Behind the Scenes",
        ]
    )

    with tab_overview:
        _render_overview_tab()
    with tab_incident:
        _render_incident_tab()
    with tab_vision:
        _render_vision_tab()
    with tab_dash:
        _render_dashboard_tab()
    with tab_tech:
        _render_behind_the_scenes_tab()


if __name__ == "__main__":
    main()
