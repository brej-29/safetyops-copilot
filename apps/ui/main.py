from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("SAFETYOPS_API_BASE_URL", "http://localhost:8000")
# Forwarded to the API's write endpoints when it is deployed with
# SAFETYOPS_API_KEY protection enabled.
API_KEY = os.getenv("SAFETYOPS_API_KEY")
DEPLOY_MODE = os.getenv("DEPLOY_MODE", os.getenv("SAFETYOPS_DEPLOY_MODE", "local"))

st.set_page_config(page_title="SafetyOps Copilot", layout="wide")


@st.cache_resource(show_spinner=False)
def get_http_client() -> httpx.Client:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    return httpx.Client(base_url=API_BASE_URL, timeout=5.0, headers=headers)


def _fetch_system_status() -> Dict[str, Any]:
    client = get_http_client()
    try:
        resp = client.get("/system/status")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        st.error(
            "System status check failed. Ensure the API is running and reachable. "
            f"Details: {exc}"
        )
        return {}


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

    col_status, col_controls, col_table = st.columns([1, 1, 2])

    with col_status:
        st.markdown("### System Status")
        status = _fetch_system_status()
        if not status:
            st.info(
                "System status is unavailable. Make sure the API is running at "
                f"{API_BASE_URL} and Docker services are up."
            )
        else:
            api_icon = "✅" if status.get("api_ok") else "❌"
            db_icon = "✅" if status.get("database_ok") else "❌"
            redis_icon = "✅" if status.get("redis_ok") else "❌"

            st.markdown(f"{api_icon} API")
            st.markdown(f"{db_icon} Database")
            st.markdown(f"{redis_icon} Redis")

            hb = status.get("worker_last_heartbeat")
            hb_age = status.get("worker_seconds_since_heartbeat")
            if hb:
                st.caption(
                    f"Worker heartbeat: {hb} (age: {hb_age:.0f}s)"
                    if isinstance(hb_age, (int, float))
                    else f"Worker heartbeat: {hb}"
                )
            else:
                st.caption(
                    "Worker heartbeat not available. Ensure the worker process is running."
                )

    with col_controls:
        st.markdown("### Demo Controls")
        n_text = st.slider("Number of demo text events", min_value=1, max_value=20, value=5)
        n_vision = st.slider("Number of demo vision events", min_value=1, max_value=10, value=3)
        if st.button("Produce demo events"):
            _produce_demo_events(n_text=n_text, n_vision=n_vision)
            st.success("Demo events submitted")

        if st.button("Refresh feed"):
            st.rerun()

    with col_table:
        st.markdown("### Recent Enriched Events")
        st.caption("Auto-refreshing every 5 seconds")
        _render_recent_events_table()


@st.fragment(run_every="5s")
def _render_recent_events_table() -> None:
    """Auto-refreshing fragment showing the latest enriched events."""
    events = _fetch_recent_events(limit=100)
    if events:
        df = pd.DataFrame(events)
        # Flatten enrichment for display if present
        if "enrichment" in df.columns:
            enrichment_cols = df["enrichment"].apply(lambda x: x or {})
            enrichment_df = pd.json_normalize(enrichment_cols)
            enrichment_df.columns = [f"enrich.{c}" for c in enrichment_df.columns]
            df = pd.concat([df.drop(columns=["enrichment"]), enrichment_df], axis=1)
        st.dataframe(df, width="stretch")
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
        submitted = st.form_submit_button("Submit incident")

    if submitted:
        if not text.strip():
            st.warning("Please enter an incident description.")
        else:
            client = get_http_client()
            try:
                payload = {"text": text, "metadata": {"source": "ui-incident"}}
                resp = client.post("/events/text", json=payload)
                resp.raise_for_status()
                st.success(
                    "Incident submitted for triage. "
                    "It will appear below once processed by the worker."
                )
            except httpx.HTTPError as exc:
                st.error(f"Failed to submit incident: {exc}")

    st.markdown("### Latest triaged incidents")
    events = _fetch_recent_events(limit=50)
    if not events:
        st.info("No triaged incidents yet. Submit one above to see it here.")
        return

    text_events = [event for event in events if event.get("event_type") == "text_event"]
    if not text_events:
        st.info("No text incidents have been triaged yet.")
        return

    df = pd.DataFrame(text_events)
    if "enrichment" in df.columns:
        enrichment_cols = df["enrichment"].apply(lambda value: value or {})
        enrichment_df = pd.json_normalize(enrichment_cols)
        enrichment_df.columns = [f"enrich.{column}" for column in enrichment_df.columns]
        df = pd.concat([df.drop(columns=["enrichment"]), enrichment_df], axis=1)
    st.dataframe(df, width="stretch")


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
        # Triage runs DB queries plus an optional LLM call; allow extra time.
        resp = client.post("/copilot/triage", json={"text": text}, timeout=30.0)
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

    summary = _fetch_metrics_summary()
    col_metrics, col_drift = st.columns([1, 2])

    with col_metrics:
        st.markdown("### Metrics Summary")
        if not summary:
            st.info(
                "Metrics are not available. Ensure the API is running and Prometheus is "
                "scraping /metrics."
            )
        else:
            st.metric(
                "Events ingested (total)",
                f"{summary['events_ingested_total']:.0f}",
            )
            st.metric(
                "Events processed (success)",
                f"{summary['events_processed_success']:.0f}",
            )
            st.metric(
                "Events processed (DLQ)",
                f"{summary['events_processed_dlq']:.0f}",
            )
            st.metric(
                "DLQ messages (total)",
                f"{summary['dlq_messages_total']:.0f}",
            )

    with col_drift:
        st.markdown("### Drift Report")
        client = get_http_client()

        if st.button("Run drift analysis"):
            try:
                resp = client.post("/monitoring/drift/run")
                resp.raise_for_status()
                st.success("Drift analysis triggered.")
            except httpx.HTTPError as exc:
                st.error(f"Failed to run drift analysis: {exc}")

        try:
            latest = client.get("/monitoring/drift/latest")
            latest.raise_for_status()
            latest_path = latest.json().get("report_path")
        except httpx.HTTPError:
            latest_path = None

        if latest_path and os.path.exists(latest_path):
            st.iframe(Path(latest_path), height=600)
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
        st.info(
            "No aggregates available yet. Ensure the worker is running and events "
            "are being ingested."
        )
        return

    df = pd.DataFrame(summary_items)
    st.markdown("### Counts by event type and severity")

    pivot = df.pivot_table(
        index="event_type",
        columns="severity",
        values="count",
        aggfunc="sum",
        fill_value=0,
    )
    st.bar_chart(pivot)

    st.markdown("### Raw aggregate data")
    st.dataframe(df, width="stretch")


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