from time import sleep
from uuid import uuid4

import asyncclick as click
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    GetTaskRequest,
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendStreamingMessageRequest,
    TaskQueryParams,
    TextPart,
)
from devtools import PrettyFormat

pf = PrettyFormat()


@click.command()
@click.option("--agent-url", default="http://localhost:8000")
@click.option(
    "--task",
    default="what tools do you have available? Use one, just for testing, with random parameters, and report on your findings.",
)
async def main(agent_url: str, task: str):
    click.echo(f"Connecting to agent at {agent_url}")

    async with httpx.AsyncClient(timeout=30) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_url)
        agent_card: AgentCard = await card_resolver.get_agent_card()

        click.echo(pf(agent_card))

        client_config = ClientConfig(
                streaming=agent_card.capabilities.streaming,
                polling=not agent_card.capabilities.streaming,
                httpx_client=httpx_client,
        )
        client_factory = ClientFactory(client_config)
        client = client_factory.create(card=agent_card)
        context_id = str(uuid4())

        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=task))],
            message_id=str(uuid4()),
        )

        payload = MessageSendParams(
            message=message,
            configuration=MessageSendConfiguration(
                accepted_output_modes=["text"],
            ),
        )

        resp = client.send_message(
            request=message,
        )

        print(resp)

        # responses = [x async for x in resp]

        # print(len(responses))



        async for event in resp:
            click.echo(pf(event[1]))
        exit()
