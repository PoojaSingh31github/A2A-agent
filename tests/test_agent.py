"""Unit and integration tests for Math A2A Agent."""

import pytest
import httpx
from a2a.client import A2ACardResolver, create_client, ClientConfig
from a2a.helpers import get_message_text, new_text_message
from a2a.types import Role, SendMessageConfiguration, SendMessageRequest

from src.agent.agent import create_agent_card, evaluate_math_expression
from src.agent.server import create_app


# ---------------------------------------------------------------------------
# Unit Tests: Math Evaluator
# ---------------------------------------------------------------------------

def test_evaluate_basic_multiplication():
    assert evaluate_math_expression("Calculate 25 * 4") == "100"
    assert evaluate_math_expression("25 * 4") == "100"


def test_evaluate_addition_and_subtraction():
    assert evaluate_math_expression("What is 12 + 15?") == "27"
    assert evaluate_math_expression("Compute 50 - 18") == "32"


def test_evaluate_division_and_floats():
    assert evaluate_math_expression("Compute 100 / 5") == "20"
    assert evaluate_math_expression("7 / 2") == "3.5"


def test_evaluate_advanced_operations():
    assert evaluate_math_expression("2 ** 8") == "256"
    assert evaluate_math_expression("2 ^ 3") == "8"
    assert evaluate_math_expression("sqrt(144) + 6") == "18"
    assert evaluate_math_expression("abs(-42)") == "42"
    assert evaluate_math_expression("(10 + 5) * 2") == "30"


def test_evaluate_errors():
    with pytest.raises(ValueError, match="Division by zero"):
        evaluate_math_expression("10 / 0")

    with pytest.raises(ValueError, match="Invalid mathematical expression"):
        evaluate_math_expression("25 * +")

    with pytest.raises(ValueError, match="Empty request"):
        evaluate_math_expression("   ")

    with pytest.raises(ValueError, match="not allowed"):
        evaluate_math_expression("__import__('os').system('ls')")


# ---------------------------------------------------------------------------
# Unit Tests: Agent Card
# ---------------------------------------------------------------------------

def test_agent_card_structure():
    card = create_agent_card("http://localhost:8000")
    assert card.name == "Math A2A Agent"
    assert card.version == "1.0.0"
    assert len(card.supported_interfaces) == 1
    assert card.supported_interfaces[0].url == "http://localhost:8000"
    assert card.supported_interfaces[0].protocol_version == "1.0"
    assert len(card.skills) == 1
    assert card.skills[0].id == "calculate"
    assert card.skills[0].name == "Calculate"


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI Endpoints & A2A Client
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_card_endpoint():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        resp = await client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Math A2A Agent"
        assert data["version"] == "1.0.0"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["id"] == "calculate"


@pytest.mark.asyncio
async def test_health_and_index_endpoints():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        index_resp = await client.get("/")
        assert index_resp.status_code == 200
        assert index_resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_a2a_client_calculation_flow():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url="http://localhost:8000")
        card = await resolver.get_agent_card()
        assert card.name == "Math A2A Agent"

        client = await create_client(card, client_config=ClientConfig(httpx_client=http_client))

        # Test valid calculation
        msg = new_text_message("Calculate 25 * 4", role=Role.ROLE_USER)
        req = SendMessageRequest(
            message=msg,
            configuration=SendMessageConfiguration(
                accepted_output_modes=["text/plain", "application/json"],
                return_immediately=False,
                history_length=0,
            ),
        )

        response_texts = []
        async for event in client.send_message(req):
            if event.HasField("message"):
                response_texts.append(get_message_text(event.message))

        assert len(response_texts) == 1
        assert response_texts[0] == "100"


@pytest.mark.asyncio
async def test_a2a_client_error_handling():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url="http://localhost:8000")
        card = await resolver.get_agent_card()
        client = await create_client(card, client_config=ClientConfig(httpx_client=http_client))

        # Test division by zero
        msg = new_text_message("Calculate 10 / 0", role=Role.ROLE_USER)
        req = SendMessageRequest(
            message=msg,
            configuration=SendMessageConfiguration(
                accepted_output_modes=["text/plain", "application/json"],
                return_immediately=False,
                history_length=0,
            ),
        )

        response_texts = []
        async for event in client.send_message(req):
            if event.HasField("message"):
                response_texts.append(get_message_text(event.message))

        assert len(response_texts) == 1
        assert "Division by zero" in response_texts[0]
