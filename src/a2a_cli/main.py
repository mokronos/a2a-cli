from uuid import uuid4

import asyncclick as click
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    TextPart,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from devtools import PrettyFormat
from a2a_cli.utils import get_text

pf = PrettyFormat()


async def stream_task(client, context_id: str, task_text: str) -> None:
    message = Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=task_text))],
        message_id=str(uuid4()),
        context_id=context_id,
    )

    resp = client.send_message(
        request=message,
    )

    task_id = None
    async for event in resp:
        if isinstance(event, Message):
            for part in event.parts:
                if isinstance(part.root, TextPart):
                    click.echo(part.root.text)
        elif isinstance(event, tuple):
            task, update = event
            if task_id is None:
                task_id = task.id
                click.echo(f"Task ID: {task_id}", err=True)
            if isinstance(update, TaskArtifactUpdateEvent):
                for part in update.artifact.parts:
                    if isinstance(part.root, TextPart):
                        click.echo(part.root.text, nl=False)
            elif isinstance(update, TaskStatusUpdateEvent):
                click.echo(
                    f"Status: \n{update.status.state} | {get_text(update.status.message)}",
                    err=True,
                )
    click.echo("")  # Ensure newline at the end


@click.command()
@click.option("--agent-url", default="http://localhost:10001")
@click.option(
    "--task",
    default="what tools do you have available? Use one, just for testing, with random parameters, and report on your findings.",
)
async def main(agent_url: str, task: str):
    click.echo(f"Connecting to agent at {agent_url}")
    click.echo(f"Task: {task}")

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

        await stream_task(client, context_id, task)

        while True:
            followup = (
                await click.prompt(
                    "Ask a follow-up (leave blank to exit)",
                    default="",
                    show_default=False,
                )
            ).strip()
            if not followup:
                break
            await stream_task(client, context_id, followup)



if __name__ == "__main__":
    main()
