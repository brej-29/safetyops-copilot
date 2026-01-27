from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

API_BASE_URL = os.getenv("SAFETYOPS_API_BASE_URL", "http://localhost:8000")
DEPLOY_MODE = os.getenv("DEPLOY_MODE", os.getenv("SAFETYOPS_DEPLOY_MODE", "local"))

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
        st.caption("Auto-refreshing every 5 seconds")
        st.experimental_autorefresh(interval=5000, key="live_feed_refresh")

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


def _fetch_metrics_summary() -> Dict[str, Any]:
    client = get_http_client()
    try:
        resp = client.get("/metrics")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        st.error(f"Failed to fetch metrics: {exc}")
        return {}

    lines = resp.text.splitlines()
    summary: Dict[str, Any] = {
        "events_ingested_total": 0,
        "events_processed_success": 0,
        "events_processed_dlq": 0,
        "dlq_messages_total": 0,
    }
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        if "events_ingested_total" in line:
            try:
                summary["events_ingested_total"] += float(line.rsplit(" ", 1)[-1])
            except ValueError:
                continue
        if 'events_processed_total' in line and 'status="success"' in line:
            try:
                summary["events_processed_success"] += float(line.rsplit(" ", 1)[-1])
            except ValueError:
                continue
        if 'events_processed_total' in line and 'status="dlq"' in line:
            try:
                summary["events_processed_dlq"] += float(line.rsplit(" ", 1)[-1])
            except ValueError:
                continue
        if "dlq_messages_total" in line and "{" not in line:
            try:
                summary["dlq_messages_total"] += float(line.rsplit(" ", 1)[-1])
            except ValueError:
                continue
    return summary


def _render_copilot_chat_tab() -> None:
    st.subheader("Copilot Chat")

    if DEPLOY_MODE != "local":
        st.info(
            "Copilot Chat is available in local/full deployments. "
            "In cloud-only mode, consider pointing this UI at a deployed API."
        )

    with st.form("copilot_chat_form"):
        text = st.text_area(
            "Describe the incident",
            placeholder="Enter an incident description...",
            height=150,
        )
        submitted = st.form_submit_button("Ask Copilot")

    if not submitted:
        return

    if not text.strip():
        st.warning("Please enter an incident description.")
        return

    client = get_http_client()
    try:
        resp = client.post("/copilot/triage", json={"text": text})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        st.error(f"Failed to call Copilot triage: {exc}")
        return

    payload = resp.json()
    st.markdown("### Structured Triage")
    st.json(payload, expanded=False)

    report_md = payload.get("report_markdown") or ""
    st.markdown("### Copilot Report")
    st.markdown(report_md)


def _render_monitoring_tab() -> None:
    st.subheader("Monitoring")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Drift Analysis")
        if st.button("Run drift report"):
            client = get_http_client()
            try:
                resp = client.post("/monitoring/drift/run")
                resp.raise_for_status()
                st.success("Drift report generated")
            except httpx.HTTPError as exc:
                st.error(f"Failed to run drift analysis: {exc}")

        client = get_http_client()
        try:
            latest = client.get("/monitoring/drift/latest")
            latest.raise_for_status()
            latest_path = latest.json().get("report_path")
        except httpx.HTTPError as exc:
            latest_path = None
            st.error(f"Failed to fetch latest drift report: {exc}")

        if latest_path:
            st.caption(f"Latest drift report: {latest_path}")
        else:
            st.info("No drift report available yet.")

        st.markdown("### Metrics Summary")
        metrics_summary = _fetch_metrics_summary()
        if metrics_summary:
            st.metric("Events ingested", metrics_summary.get("events_ingested_total", 0))
            st.metric("Events processed (success)", metrics_summary.get("events_processed_success", 0))
            st.metric("Events processed to DLQ", metrics_summary.get("events_processed_dlq", 0))
            st.metric("DLQ messages total", metrics_summary.get("dlq_messages_total", 0))

    with col2:
        st.markdown("### Drift Report Preview")
        client = get_http_client()
        try:
            latest = client.get("/monitoring/drift/latest")
            latest.raise_for_status()
            latest_path = latest.json().get("report_path")
        except httpx.HTTPError:
            latest_path = None

        if latest_path and os.path.exists(latest_path):
            with open(latest_path, "r", encoding="utf-8") as f:
                html = f.read()
            components.html(html, height=600, scrolling=True)
        else:
            st.info(
                "Generate a drift report to see an HTML preview here. "
                "In some deployments, direct file access may not be available."
            )


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


def main() -> None:
    st.title("SafetyOps Copilot")
    st.caption("PPE and incident triage assistant (v1)")

    tab_live, tab_triage, tab_copilot, tab_ops, tab_monitor = st.tabs(
        ["Live Feed", "Incident Triage", "Copilot Chat", "Ops Dashboard", "Monitoring"]
    )

    with tab_live:
        _render_live_feed_tab()

    with tab_triage:
        _render_incident_triage_tab()

    with tab_copilot:
        _render_copilot_chat_tab()

    with tab_ops:
        _render_ops_dashboard_tab()

    with tab_monitor:
        _render_monitoring_tab()


if __name__ == "__main__":
    main()