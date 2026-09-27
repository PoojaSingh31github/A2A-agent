"""A2A Client Demo script.

Demonstrates how an external client:
1. Discovers an agent using A2ACardResolver
2. Inspects its Agent Card and declared skills
3. Creates a client session with create_client
4. Sends mathematical calculation requests and receives responses
5. Demonstrates raw JSON-RPC wire format handling
"""

import asyncio
import sys
import uuid
import httpx
from a2a.client import A2ACardResolver, create_client, ClientConfig
from a2a.helpers import get_message_text, new_text_message
from a2a.types import Role, SendMessageConfiguration, SendMessageRequest


async def run_demo(base_url: str = "http://localhost:8000") -> None:
    print("=" * 60)
    print(f"Connecting to A2A Agent at {base_url}...")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        # Step 1: Discover Agent Card
        resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
        try:
            agent_card = await resolver.get_agent_card()
            print("\n[+] Agent Card Discovered:")
            print(f"    Name:        {agent_card.name}")
            print(f"    Description: {agent_card.description}")
            print(f"    Version:     {agent_card.version}")
            print(f"    Skills ({len(agent_card.skills)}):")
            for skill in agent_card.skills:
                print(f"      - ID: {skill.id}, Name: {skill.name}")
                print(f"        Description: {skill.description}")
                print(f"        Examples:    {list(skill.examples)}")
        except Exception as exc:
            print(f"[-] Failed to fetch Agent Card from {base_url}: {exc}")
            print("    Please ensure the A2A Agent server is running.")
            return

        # Step 2: Create A2A Client
        client = await create_client(
            agent_card,
            client_config=ClientConfig(httpx_client=http_client),
        )

        test_queries = [
            "Calculate 25 * 4",
            "What is 12 + 15?",
            "Compute 100 / 5",
            "Evaluate sqrt(144) * 3",
            "Calculate 2 ** 8",
            "Calculate 10 / 0",          # Division by zero test
            "Calculate 25 * +",          # Syntax error test
        ]

        print("\n" + "=" * 60)
        print("Sending A2A Calculation Requests (via A2A SDK Client):")
        print("=" * 60)

        for query in test_queries:
            print(f"\n>> Request:  '{query}'")
            user_msg = new_text_message(query, role=Role.ROLE_USER)
            req = SendMessageRequest(
                message=user_msg,
                configuration=SendMessageConfiguration(
                    accepted_output_modes=["text/plain", "application/json"],
                    return_immediately=False,
                    history_length=0,
                ),
            )

            try:
                async for event in client.send_message(req):
                    if event.HasField("message"):
                        resp_text = get_message_text(event.message)
                        print(f"<< Response: '{resp_text}'")
            except Exception as exc:
                print(f"[-] Request failed: {exc}")

        # Step 3: Raw JSON-RPC Demonstration
        print("\n" + "=" * 60)
        print("Raw JSON-RPC Protocol Request (via HTTP POST):")
        print("=" * 60)

        raw_rpc_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "SendMessage",
            "params": {
                "message": {
                    "message_id": str(uuid.uuid4()),
                    "role": 1,  # ROLE_USER
                    "parts": [{"text": "Calculate (50 * 2) + 15"}],
                },
                "configuration": {
                    "acceptedOutputModes": ["text/plain", "application/json"],
                    "returnImmediately": False,
                },
            },
        }

        resp = await http_client.post(
            f"{base_url}/",
            json=raw_rpc_payload,
            headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
        )
        print("Raw JSON-RPC Response:")
        print(resp.json())


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(run_demo(url))
