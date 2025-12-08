"""A2A streaming functionality for handling task responses."""

from typing import Any
from uuid import uuid4

import click
import httpx
from a2a.client.errors import A2AClientError
from a2a.types import (
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
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
    try:
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
                print(update)
                if task_id is None:
                    task_id = task.id
                    click.echo(click.style(f"Task ID: {task_id}", fg="cyan", bold=True), err=True)
                if isinstance(update, TaskArtifactUpdateEvent):
                    # no need to display the final output fully again
                    if update.artifact.name == "final_output_total":
                        continue

                    # Determine color based on artifact name
                    artifact_name = update.artifact.name
                    if artifact_name == "tool_result":
                        color = "cyan"
                        force_newline = True  # Always add newline after tool results
                    else:
                        color = "green"
                        force_newline = False

                    trailing_newline = False
                    for part in update.artifact.parts:
                        if isinstance(part.root, TextPart):
                            text = part.root.text
                            trailing_newline = text.endswith("\n")
                            click.echo(click.style(text, fg=color), nl=False)

                    # Force newline for tool_result or track if we need one
                    if force_newline and not trailing_newline:
                        click.echo()
                        artifact_open_line = False
                    else:
                        artifact_open_line = not trailing_newline
                elif isinstance(update, TaskStatusUpdateEvent):
                    if artifact_open_line:
                        click.echo()
                        artifact_open_line = False
                    status_line = click.style(f"Status: {update.status.state}", fg="yellow", bold=True)
                    click.echo(status_line, err=True)
                    message_text = get_text(update.status.message)
                    if message_text:
                        click.echo(click.style(message_text, fg="yellow"), err=True)
    except (A2AClientError, httpx.HTTPError, httpx.StreamError) as e:
        # Handle connection errors gracefully
        if artifact_open_line:
            click.echo()  # Close any open artifact line
        click.echo()
        click.echo(click.style("⚠ Connection lost", fg="red", bold=True), err=True)
        click.echo(click.style(f"  Server disconnected: {e}", fg="red"), err=True)
        click.echo(click.style("  The agent may have crashed or restarted.", fg="bright_black"), err=True)
        return
    if artifact_open_line:
        click.echo()
    click.echo("")  # Ensure newline at the end
