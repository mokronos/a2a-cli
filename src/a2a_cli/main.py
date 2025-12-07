"""A2A CLI - Interactive client for A2A agents."""

import asyncclick as click
from devtools import PrettyFormat
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from a2a_cli.commands import (
    SlashCommandCompleter,
    get_prompt_message,
    handle_slash_command,
)
from a2a_cli.history import ContextAwareHistory
from a2a_cli.session import A2ASession
from a2a_cli.streaming import stream_task

pf = PrettyFormat()

# Define prompt_toolkit style
PROMPT_STYLE = Style.from_dict({
    "bracket": "#888888",
    "agent-name": "#00aa00 bold",
    "disconnected": "#aa0000",
    "prompt": "#ffffff",
    "command": "#00aaff bold",
})


@click.command()
@click.option("--agent-url", default=None, help="URL of the A2A agent to connect to")
@click.option("--task", default=None, help="Initial task to send to the agent")
async def main(agent_url: str | None, task: str | None) -> None:
    """A2A CLI - Interactive client for A2A agents.

    Start without arguments for interactive mode, or use --agent-url and --task
    for quick one-shot usage.
    """
    session = A2ASession()
    
    # Create context-aware history that persists across sessions
    history = ContextAwareHistory()

    # Create prompt session with autocompletion and persistent history
    prompt_session: PromptSession = PromptSession(
        completer=SlashCommandCompleter(session),
        history=history,
        style=PROMPT_STYLE,
        complete_while_typing=True,
    )

    # Display welcome message
    click.echo(click.style("""
╭───────────────────────────────────────╮
│           A2A CLI Client              │
│   Type /help for available commands   │
│   Use Tab for autocompletion          │
│   Use ↑/↓ for history navigation      │
╰───────────────────────────────────────╯
""", fg="cyan", bold=True))

    # If agent-url is provided, connect immediately
    if agent_url:
        click.echo(click.style(f"Connecting to {agent_url}...", fg="cyan"))
        if await session.connect(agent_url):
            click.echo(click.style(f"✓ Connected to {agent_url}", fg="green", bold=True))
            click.echo(click.style("Agent card:", fg="yellow", bold=True))
            click.echo(click.style(pf(session.agent_card), fg="bright_black"))
            # Update history context to task mode
            history.set_connected(True)

            # If a task was also provided, execute it
            if task:
                click.echo(click.style(f"\nTask: {task}", fg="magenta"))
                await stream_task(session.client, session.context_id, task)
        else:
            click.echo(click.style("Failed to connect. Use /connect <url> to try again.", fg="red"))

    # Main interactive loop
    try:
        while True:
            try:
                user_input = await prompt_session.prompt_async(
                    get_prompt_message(session),
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    # Track connection state before command
                    was_connected = session.is_connected()
                    
                    should_continue = await handle_slash_command(session, user_input)
                    
                    # Update history context if connection state changed
                    is_connected = session.is_connected()
                    if was_connected != is_connected:
                        history.set_connected(is_connected)
                    
                    if not should_continue:
                        break
                    continue

                # Handle regular input (send as task)
                if not session.is_connected():
                    click.echo(click.style("Not connected to any agent.", fg="red"))
                    click.echo(click.style("Use /connect <url> to connect first.", fg="bright_black"))
                    continue

                # Send the task
                await stream_task(session.client, session.context_id, user_input)

            except KeyboardInterrupt:
                # Handle Ctrl+C - exit the program
                click.echo()
                break

    except EOFError:
        # Handle Ctrl+D
        click.echo()
    finally:
        if session.is_connected():
            await session.disconnect()
        click.echo(click.style("Goodbye!", fg="cyan"))


if __name__ == "__main__":
    main()
