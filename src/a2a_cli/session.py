"""A2A session management for connection state and context."""

from typing import Any
from uuid import uuid4

import click
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import AgentCard


class A2ASession:
    """Manages the connection state and context for an A2A agent session."""

    def __init__(self) -> None:
        self.agent_url: str | None = None
        self.agent_card: AgentCard | None = None
        self.httpx_client: httpx.AsyncClient | None = None
        self.client: Any = None
        self.context_id: str | None = None

    def is_connected(self) -> bool:
        return self.client is not None

    async def connect(self, agent_url: str) -> bool:
        """Connect to an A2A agent at the specified URL."""
        try:
            # Disconnect from any existing connection
            await self.disconnect()

            self.httpx_client = httpx.AsyncClient(timeout=30)
            card_resolver = A2ACardResolver(
                httpx_client=self.httpx_client, base_url=agent_url
            )
            self.agent_card = await card_resolver.get_agent_card()

            client_config = ClientConfig(
                streaming=self.agent_card.capabilities.streaming,
                polling=not self.agent_card.capabilities.streaming,
                httpx_client=self.httpx_client,
            )
            client_factory = ClientFactory(client_config)
            self.client = client_factory.create(card=self.agent_card)
            self.agent_url = agent_url
            self.context_id = str(uuid4())
            return True
        except Exception as e:
            click.echo(click.style(f"Failed to connect: {e}", fg="red", bold=True))
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from the current agent."""
        if self.httpx_client:
            await self.httpx_client.aclose()
        self.httpx_client = None
        self.client = None
        self.agent_card = None
        self.agent_url = None
        self.context_id = None

    def reset_context(self) -> str:
        """Reset the conversation context and return the new context_id."""
        self.context_id = str(uuid4())
        return self.context_id
