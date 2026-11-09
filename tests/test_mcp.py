from __future__ import annotations

import pytest

pytest.importorskip("mcp")
from mcp import Client
from services.mcp.server import mcp


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_discovery_and_read_only_tools():
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
        assert {tool.name for tool in tools} == {
            "assess_incident",
            "get_response_runbook",
            "summarize_handover",
        }
        assert all(tool.annotations.read_only_hint for tool in tools)
        result = await client.call_tool(
            "assess_incident", {"text": "A worker was unconscious after a fall."}
        )
        assert result.structured_content["severity"] == "high"
        assert result.structured_content["review_required"] is True
        result = await client.call_tool("get_response_runbook", {"category": "electrical"})
        assert "markdown" in result.structured_content
        result = await client.call_tool(
            "summarize_handover",
            {
                "archive": {
                    "schema_version": 1,
                    "synthetic": True,
                    "observations": [],
                    "actions": [
                        {
                            "title": "Inspect platform",
                            "owner": "Lead",
                            "due_date": "2020-01-01",
                            "status": "open",
                        },
                    ],
                }
            },
        )
        assert result.structured_content["open_actions"] == 1
        assert result.structured_content["overdue_actions"] == 1
        assert result.structured_content["synthetic"] is True
