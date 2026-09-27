# Math A2A Agent

A complete, production-structured **Agent-to-Agent (A2A)** Agent in Python adhering to the current **A2A v1.0 protocol specification** and SDK conventions.

---

## 📌 Overview

This project provides a standalone mathematical calculation agent that communicates with other agents and platforms via the standard A2A protocol.

- **Python Runtime:** Python 3.13+
- **SDK:** `a2a-sdk >= 1.0.0`
- **Framework:** FastAPI + Uvicorn
- **Default Port:** `8000`
- **Agent Card URL:** `http://localhost:8000/.well-known/agent-card.json`
- **JSON-RPC Endpoint:** `http://localhost:8000/`

---

## 📂 Project Structure

```
math-a2a-agent/
├── src/
│   └── agent/
│       ├── __init__.py       # Package exports
│       ├── agent.py          # MathAgentExecutor, AST evaluator, Agent Card definition
│       └── server.py         # FastAPI app factory, routes, and CLI entrypoint
├── tests/
│   ├── __init__.py
│   └── test_agent.py         # Unit & A2A integration tests
├── client_demo.py            # Standalone A2A client test script
├── pyproject.toml            # Project dependencies and packaging metadata
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration
└── README.md                 # Complete documentation and quickstart guide
```

---

## 📖 Key Concepts

### 1. What is an Agent Card?
An **Agent Card** is a JSON metadata document served at the standard well-known endpoint (`/.well-known/agent-card.json`). It acts as a machine-readable ID card for the agent, advertising:
- **Agent Identity:** Name, description, and version.
- **Supported Interfaces:** Endpoint URL, protocol binding (`JSONRPC`, `HTTP+JSON`, `GRPC`), and protocol version (`1.0`).
- **Skills & Capabilities:** List of skills the agent supports (e.g. `calculate`), example prompts, input/output MIME types, streaming, and push notification support.

Other agents or orchestrators (like Agent Nexus) query this endpoint to dynamically discover how to interact with the agent.

### 2. How A2A Request/Response Works
1. **Discovery:** The caller (A2A client/orchestrator) queries `GET /.well-known/agent-card.json` to verify agent capabilities and retrieve the communication endpoint.
2. **Message Dispatch:** The caller sends a JSON-RPC 2.0 `POST` request to `/` containing a `SendMessage` method, specifying:
   - `message`: contains `message_id`, `role` (`ROLE_USER` = 1), and `parts` (`[{"text": "Calculate 25 * 4"}]`).
   - `configuration`: output mode preferences and execution settings.
3. **Execution & Event Streaming:** The `MathAgentExecutor` receives the `RequestContext`, extracts the user input, performs the safe AST evaluation, and emits a `ROLE_AGENT` response event back to the `EventQueue`.
4. **JSON-RPC Response:** The server serializes the response message and returns it to the caller.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.13+** installed
- **uv** package manager installed

### 2. Installation
From the project root directory (`try-projects/agent/`):

```bash
uv sync
```

### 3. Running the Agent
Run the agent using Uvicorn:

```bash
uv run uvicorn src.agent.server:app --host 0.0.0.0 --port 8000 --reload
```

Or using the CLI entrypoint:

```bash
uv run math-a2a-agent
```

---

## 🧪 Testing the Agent

### A. Verify the Agent Card in Browser or cURL
Open in your browser:
[http://localhost:8000/.well-known/agent-card.json](http://localhost:8000/.well-known/agent-card.json)

Or using `curl`:
```bash
curl http://localhost:8000/.well-known/agent-card.json
```

### B. Run the Automated Tests
Run the comprehensive unit and integration test suite:

```bash
uv run pytest
```

### C. Run the A2A Client Demo
In a separate terminal (while the server is running), execute:

```bash
uv run python client_demo.py
```

### D. Direct JSON-RPC `curl` Test
You can send a direct JSON-RPC `SendMessage` request to the agent:

```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-001",
    "method": "SendMessage",
    "params": {
      "message": {
        "message_id": "msg-001",
        "role": 1,
        "parts": [{"text": "Calculate 25 * 4"}]
      }
    }
  }'
```

Expected output:
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "message": {
      "messageId": "...",
      "contextId": "...",
      "taskId": "...",
      "role": "ROLE_AGENT",
      "parts": [{"text": "100"}]
    }
  }
}
```

---

## 🛡️ Mathematical Evaluator & Error Handling

The math engine evaluates expressions via Python's Abstract Syntax Tree (`ast`), ensuring safe execution without arbitrary code injection:

- **Supported Operations:** Addition (`+`), subtraction (`-`), multiplication (`*`), division (`/`), floor division (`//`), modulo (`%`), exponentiation (`**` / `^`), unary negative (`-`).
- **Supported Functions:** `sqrt`, `abs`, `round`, `pow`, `sin`, `cos`, `tan`, `log`, `log10`, `exp`, `pi`, `e`.
- **Natural Language Stripping:** Automatically parses prefixes like *"Calculate 25 * 4"*, *"What is 12 + 15?"*, *"Compute 100 / 5"*.
- **Error Handling:** Returns clear, friendly error messages on zero division (`"Error: Division by zero is undefined."`) and syntax errors (`"Error: Invalid mathematical expression syntax"`).

---

## 🌐 Connecting from another A2A Client (Python)

```python
import asyncio
import httpx
from a2a.client import A2ACardResolver, create_client, ClientConfig
from a2a.helpers import new_text_message, get_message_text
from a2a.types import Role, SendMessageRequest, SendMessageConfiguration

async def main():
    async with httpx.AsyncClient() as http_client:
        # 1. Discover the agent card
        resolver = A2ACardResolver(httpx_client=http_client, base_url="http://localhost:8000")
        card = await resolver.get_agent_card()

        # 2. Create client session
        client = await create_client(card, client_config=ClientConfig(httpx_client=http_client))

        # 3. Send message
        msg = new_text_message("Calculate 25 * 4", role=Role.ROLE_USER)
        req = SendMessageRequest(
            message=msg,
            configuration=SendMessageConfiguration(
                accepted_output_modes=["text/plain", "application/json"],
                return_immediately=False,
            ),
        )

        async for event in client.send_message(req):
            if event.HasField("message"):
                print("Result:", get_message_text(event.message))

asyncio.run(main())
```
