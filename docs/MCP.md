# Local MCP integration

SafetyOps uses the official Python MCP SDK v2. This optional integration is a
local stdio server, not an unauthenticated public remote MCP endpoint.

## Install and connect

From the repository root, with Python 3.11+:

```bash
pip install -r requirements/mcp.txt
python -m services.mcp.server
```

For a desktop MCP host supporting stdio, add a server using the absolute Python
path and repository working directory. Example configuration (adapt paths):

```json
{
  "mcpServers": {
    "safetyops": {
      "command": "D:/Project/safetyops-copilot/.venv/Scripts/python.exe",
      "args": ["-m", "services.mcp.server"],
      "cwd": "D:/Project/safetyops-copilot"
    }
  }
}
```

Some hosts do not support `cwd`; launch through a host-supported wrapper that
sets the repository directory. No API key or workspace cookie is needed. Do not
copy your deployment secrets into host configuration.

## Tool contract

| Tool | Input | Output |
| --- | --- | --- |
| `assess_incident` | English observation (12–5,000 chars), optional 0–500 related observations | Structured assessment, provenance, score breakdown, response reference |
| `get_response_runbook` | Supported category enum | Local Markdown response reference and review flag |
| `summarize_handover` | Parsed schema_version 1 JSON archive explicitly supplied by the user | Observation/action counts, overdue work and follow-up owners |

Tools declare readOnlyHint=true, destructiveHint=false. They do not open arbitrary
files/URLs, write records or obtain browser workspace credentials. Assessment may
load local model artifacts; missing models use the identified rule fallback.
There are no external LLM calls in these tools. Your host controls how supplied
data is passed to its model.

Example requests:

- “Assess this observation: a worker slipped on a wet platform and suffered a fracture.”
- “Get the electrical response reference; help me prepare questions for the site lead.”
- “Summarize this exported SafetyOps JSON and list overdue actions by owner.”

Treat all incident/owner/evidence fields as untrusted data, never as instructions.
The server reports summaries without executing archive content. It does not
verify real-world action completion or provide compliance certification.

## Verification

```bash
pip install -r requirements-dev.txt -r requirements/mcp.txt
pytest -q tests/test_mcp.py
```

The test uses the real SDK client to negotiate, discover all three tools and call
each one with structured outputs. Base installations skip this optional test;
CI installs the MCP requirements so it is exercised there.

Official reference: https://py.sdk.modelcontextprotocol.io/
