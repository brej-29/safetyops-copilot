from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("SAFETYOPS_API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="SafetyOps Copilot", layout="wide")


@st.cache_resource(show_spinner=False)
def get_http_client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, timeout=5.0)


def _fetch_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    client = get_http_client()
    try:
        response = client.get("/events/recent", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        st.error(f"Failed to fetch recent events: {exc}")
        return []


def _fetch_aggregate_summary(days: int = 7) -> List[Dict[str, Any]]:
    client = get_http_client()
    try:
        response = client.get("/aggregates/summary", params={"days": days})
        response.raise_for_status()
        payload = response.json()
        return payload.get("items", [])
    except httpx.HTTPError as exc:
        st.error(f"Failed to fetch aggregate summary: {exc}")
        return []


def _produce_demo_events(n_text: int = 5, n_vision: int = 3) -> None:
    client = get_http_client()
    text_examples = [
        "Worker slipped on wet floor near loading bay.",
        "Minor electrical shock when handling exposed wire.",
        "Small fire in storage area; extinguished quickly.",
        "Chemical spill in lab; area evacuated.",
        "Routine safety inspection with no incidents.",
    ]

    for i in range(n_text):
        payload = {
            "text": text_examples[i % len(text_examples)],
            "metadata": {"source": "ui-demo"},
        }
        try:
            client.post("/events/text", json=payload)
        except httpx.HTTPError as exc:
            st.error(f"Failed to publish demo text event: {exc}")
            break

    for i in range(n_vision):
        payload = {
            "image_path": "data/sample/sample_ppe_image.jpg",  # placeholder path
            "metadata": {"source": "ui-demo"},
        }
        try:
            # Use form encoding so it matches the API definition
            client.post("/events/vision", data=payload)
        except httpx.HTTPError as exc:
            st.error(f"Failed to publish demo vision event: {exc}")
            break


def _render_live_feed_tab() -> None:
    st.subheader("Live Feed")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### Demo Controls")
        n_text = st.slider("Number of demo text events", min_value=1, max_value=20, value=5)
        n_vision = st.slider("Number of demo vision events", min_value=1, max_value=10, value=3)
        if st.button("Produce demo events"):
            _produce_demo_events(n_text=n_text, n_vision=n_vision)
            st.success("Demo events submitted")

        if st.button("Refresh feed"):
            st.experimental_rerun()

    with col2:
        st.markdown("### Recent Enriched Events")
        events = _fetch_recent_events(limit=100)
        if events:
            df = pd.DataFrame(events)
            # Flatten enrichment for display if present
            if "enrichment" in df.columns:
                enrichment_cols = df["enrichment"].apply(lambda x: x or {})
                enrichment_df = pd.json_normalize(enrichment_cols)
                enrichment_df.columns = [f"enrich.{c}" for c in enrichment_df.columns]
                df = pd.concat([df.drop(columns=["enrichment"]), enrichment_df], axis=1)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No enriched events available yet. Produce some demo events to get started.")


def _render_incident_triage_tab() -> None:
    st.subheader("Incident Triage")

    with st.form("incident_triage_form"):
        text = st.text_area(
            "Incident description",
            placeholder="Describe what happened...",
            height=150,
        )
        submitted = st.form_submit_button("Submit for triage")

    if submitted:
        if not text.strip():
            st.warning("Please provide an incident description.")
            return

        client = get_http_client()
        try:
            response = client.post("/events/text", json={"text": text, "metadata": {"source": "ui-triage"}})
            response.raise_for_status()
            st.success("Incident submitted for triage")
        except httpx.HTTPError as exc:
            st.error(f"Failed to submit incident: {exc}")
            return

    st.markdown("### Recent Triaged Incidents")
    events = _fetch_recent_events(limit=20)
    text_events = [e for e in events if e.get("event_type") == "text_event"]
    if text_events:
        df = pd.DataFrame(text_events)
        enrichment_cols = df["enrichment"].apply(lambda x: x or {})
        enrichment_df = pd.json_normalize(enrichment_cols)
        enrichment_df.columns = [f"enrich.{c}" for c in enrichment_df.columns]
        df = pd.concat([df.drop(columns=["enrichment"]), enrichment_df], axis=1)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No triaged incidents yet. Submit one above to see it here.")


def _render_ops_dashboard_tab() -> None:
    st.subheader("Ops Dashboard")

    days = st.slider("Aggregation window (days)", min_value=1, max_value=30, value=7)
    summary_items = _fetch_aggregate_summary(days=days)

    if not summary_items:
        st.info("No aggregates available yet. Process more events via the worker.")
        return

    df = pd.DataFrame(summary_items)
    st.markdown("### Counts by event type and severity")

    pivot = df.pivot_table(index="event_type", columns="severity", values="count", aggfunc="sum", fill_value=0)
    st.bar_chart(pivot)

    st.markdown("### Raw aggregate data")
    st.dataframe(df, use_container_width=True)

    st.markdown("### Monitoring and Drift (Placeholders)")
    st.write(
        "In later prompts, this section will link to more detailed monitoring views "
        " (e.g., Grafana dashboards, drift reports, and model performance summaries)."
    )


def main() -> None:
    st.title("SafetyOps Copilot")
    st.caption("PPE and incident triage assistant (v1)")

    tab_live, tab_triage, tab_ops = st.tabs(["Live Feed", "Incident Triage", "Ops Dashboard"])

    with tab_live:
        _render_live_feed_tab()

    with tab_triage:
        _render_incident_triage_tab()

    with tab_ops:
        _render_ops_dashboard_tab()


if __name__ == "__main__":
    main()