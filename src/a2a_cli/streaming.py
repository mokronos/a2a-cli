"""A2A streaming functionality for handling task responses."""

from typing import Any
from uuid import uuid4

import click
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

from a2a_cli.utils import get_text


async def stream_task(client: Any, context_id: str, task_text: str) -> None:
    """Stream a task to the A2A agent and display the response."""
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
