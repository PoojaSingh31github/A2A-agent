"""A2A HTTP Server implementation using FastAPI and Uvicorn.

Exposes:
- GET /.well-known/agent-card.json (Agent Card discovery endpoint)
- POST / (A2A JSON-RPC protocol endpoint)
- GET / (Welcome / metadata endpoint)
- GET /health (Health check endpoint)
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from a2a.server.request_handlers.default_request_handler_v2 import DefaultRequestHandlerV2
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .agent import MathAgentExecutor, create_agent_card

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("math_a2a_agent")


def create_app(agent_url: str | None = None) -> FastAPI:
    """Creates and configures the FastAPI application with A2A routes."""
    resolved_url = (agent_url or os.getenv("AGENT_URL", "http://localhost:8000")).strip()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("==================================================")
        logger.info("Math A2A Agent starting up...")
        logger.info("Agent URL: %s", resolved_url)
        logger.info("Agent Card endpoint: %s/.well-known/agent-card.json", resolved_url)
        logger.info("A2A JSON-RPC endpoint: %s/", resolved_url)
        logger.info("==================================================")
        yield
        logger.info("Math A2A Agent shutting down...")

    app = FastAPI(
        title="Math A2A Agent",
        description="A clean, production-structured A2A Agent conforming to the A2A v1.0 protocol specification.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 1. Build Agent Card
    agent_card = create_agent_card(agent_url=resolved_url)

    # 2. Instantiate Agent Executor & Task Store
    agent_executor = MathAgentExecutor()
    task_store = InMemoryTaskStore()

    # 3. Create Default Request Handler (v2 standard)
    request_handler = DefaultRequestHandlerV2(
        agent_executor=agent_executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    # 4. Generate A2A Routes
    agent_card_routes = create_agent_card_routes(agent_card=agent_card)
    jsonrpc_routes = create_jsonrpc_routes(
        request_handler=request_handler,
        rpc_url="/",
    )

    # 5. Register A2A Routes with FastAPI
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=agent_card_routes,
        jsonrpc_routes=jsonrpc_routes,
    )

    # 6. Additional utility routes
    @app.get("/", summary="Agent Information")
    async def index() -> JSONResponse:
        return JSONResponse(
            {
                "name": agent_card.name,
                "description": agent_card.description,
                "version": agent_card.version,
                "status": "running",
                "agent_card_url": "/.well-known/agent-card.json",
                "a2a_endpoint": "/",
                "protocol_version": "1.0",
            }
        )

    @app.get("/health", summary="Health Check")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "healthy", "service": "math-a2a-agent"})

    return app


# Default app instance for ASGI servers like uvicorn
app = create_app()


def main() -> None:
    """CLI entrypoint to run the Math A2A Agent server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    logger.info("Starting uvicorn server on %s:%d...", host, port)
    uvicorn.run(
        "src.agent.server:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
