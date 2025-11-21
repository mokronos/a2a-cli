from uuid import uuid4
from typing import Any

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


async def stream_task(client: Any, context_id: str, task_text: str) -> None:
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
    artifact_open_line = False
    async for event in resp:
        if isinstance(event, Message):
            if artifact_open_line:
                click.echo()
                artifact_open_line = False
            for part in event.parts:
                if isinstance(part.root, TextPart):
                    click.echo(click.style(part.root.text, fg="bright_white"))
        elif isinstance(event, tuple):
            task, update = event
            if task_id is None:
                task_id = task.id
                click.echo(
                    click.style(f"Task ID: {task_id}", fg="cyan", bold=True), err=True
                )
            if isinstance(update, TaskArtifactUpdateEvent):

                # no need to display the final output fully again
                if update.artifact.name == "final_output_total":
                    continue
                trailing_newline = False
                for part in update.artifact.parts:
                    if isinstance(part.root, TextPart):
                        text = part.root.text
                        trailing_newline = text.endswith("\n")
                        click.echo(click.style(text, fg="green"), nl=False)
                artifact_open_line = not trailing_newline
            elif isinstance(update, TaskStatusUpdateEvent):
                if artifact_open_line:
                    click.echo()
                    artifact_open_line = False
                status_line = click.style(
                    f"Status: {update.status.state}", fg="yellow", bold=True
                )
                click.echo(status_line, err=True)
                message_text = get_text(update.status.message)
                if message_text:
                    click.echo(click.style(message_text, fg="yellow"), err=True)
    if artifact_open_line:
        click.echo()
    click.echo("")  # Ensure newline at the end


@click.command()
@click.option("--agent-url", default="http://localhost:10001")
@click.option(
    "--task",
    default="what tools do you have available? Use them ONCE, just for testing, with random parameters, and report on your findings. Don't call tools multiple times, unless really necessary. You don't need to test out every possible parameter for the tools!",
)
async def main(agent_url: str, task: str) -> None:
    click.echo(click.style(f"Connecting to agent at {agent_url}", fg="cyan", bold=True))
    click.echo(click.style(f"Task: {task}", fg="magenta"))

    async with httpx.AsyncClient(timeout=30) as httpx_client:
        card_resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_url)
        agent_card: AgentCard = await card_resolver.get_agent_card()

        click.echo(click.style("Agent card:", fg="yellow", bold=True))
        click.echo(click.style(pf(agent_card), fg="bright_black"))

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
