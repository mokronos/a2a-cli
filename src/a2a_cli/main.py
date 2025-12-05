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
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from a2a_cli.utils import get_text

pf = PrettyFormat()

# Define slash commands with their descriptions and argument hints
SLASH_COMMANDS = {
    "/connect": {"description": "Connect to an A2A agent", "arg": "<url>"},
    "/disconnect": {"description": "Disconnect from the current agent", "arg": None},
    "/status": {"description": "Show current connection status", "arg": None},
    "/card": {"description": "Display the current agent's card", "arg": None},
    "/reset": {"description": "Reset conversation (new context)", "arg": None},
    "/new": {"description": "Reset conversation (new context)", "arg": None},
    "/help": {"description": "Show available commands", "arg": None},
    "/?": {"description": "Show available commands", "arg": None},
    "/quit": {"description": "Exit the CLI", "arg": None},
    "/exit": {"description": "Exit the CLI", "arg": None},
}


class SlashCommandCompleter(Completer):
    """Completer for slash commands with descriptions."""

    def __init__(self, session: "A2ASession") -> None:
        self.session = session

    def get_completions(self, document, complete_event):  # type: ignore
        text = document.text_before_cursor
        
        # Only complete if we're at the start of a line and typing a slash command
        if not text.startswith("/"):
            return
        
        # Get the word being typed
        word = text.split()[0] if text.split() else text
        
        for cmd, info in SLASH_COMMANDS.items():
            if cmd.startswith(word):
                # Build display text with description
                display = cmd
                if info["arg"]:
                    # Escape angle brackets for HTML display
                    escaped_arg = info["arg"].replace("<", "&lt;").replace(">", "&gt;")
                    display += f" {escaped_arg}"
                
                # Create the completion
                yield Completion(
                    cmd,
                    start_position=-len(word),
                    display=HTML(f"<b>{cmd}</b> <i>{escaped_arg if info['arg'] else ''}</i>"),
                    display_meta=info["description"],
                )


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


def show_help() -> None:
    """Display available slash commands."""
    help_text = """
╭──────────────────────────────────────────────────────────╮
│                  Available Commands                       │
├──────────────────────────────────────────────────────────┤
│  /connect <url>   Connect to an A2A agent at <url>       │
│  /disconnect      Disconnect from the current agent       │
│  /status          Show current connection status          │
│  /card            Display the current agent's card        │
│  /reset, /new     Reset conversation (new context)        │
│  /help, /?        Show this help message                  │
│  /quit, /exit     Exit the CLI                            │
├──────────────────────────────────────────────────────────┤
│  TIP: Use Tab for command autocompletion                  │
╰──────────────────────────────────────────────────────────╯
"""
    click.echo(click.style(help_text, fg="cyan"))


async def handle_slash_command(session: A2ASession, command: str) -> bool:
    """
    Handle slash commands.
    Returns True if the CLI should continue, False if it should exit.
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None

    if cmd in ("/help", "/?"):
        show_help()

    elif cmd == "/connect":
        if not arg:
            click.echo(click.style("Usage: /connect <url>", fg="red"))
            return True
        click.echo(click.style(f"Connecting to {arg}...", fg="cyan"))
        if await session.connect(arg):
            click.echo(click.style(f"✓ Connected to {arg}", fg="green", bold=True))
            click.echo(click.style("Agent card:", fg="yellow", bold=True))
            click.echo(click.style(pf(session.agent_card), fg="bright_black"))

    elif cmd == "/disconnect":
        if session.is_connected():
            url = session.agent_url
            await session.disconnect()
            click.echo(click.style(f"✓ Disconnected from {url}", fg="green"))
        else:
            click.echo(click.style("Not connected to any agent.", fg="yellow"))

    elif cmd == "/status":
        if session.is_connected():
            click.echo(click.style("Connection Status:", fg="cyan", bold=True))
            click.echo(f"  Agent URL: {click.style(session.agent_url, fg='green')}")
            click.echo(f"  Agent Name: {click.style(session.agent_card.name, fg='green')}")
            click.echo(f"  Context ID: {click.style(session.context_id, fg='bright_black')}")
            if session.agent_card.capabilities.streaming:
                click.echo(f"  Streaming: {click.style('enabled', fg='green')}")
            else:
                click.echo(f"  Streaming: {click.style('disabled (polling)', fg='yellow')}")
        else:
            click.echo(click.style("Not connected to any agent.", fg="yellow"))
            click.echo(click.style("Use /connect <url> to connect.", fg="bright_black"))

    elif cmd == "/card":
        if session.is_connected():
            click.echo(click.style("Agent card:", fg="yellow", bold=True))
            click.echo(click.style(pf(session.agent_card), fg="bright_black"))
        else:
            click.echo(click.style("Not connected to any agent.", fg="yellow"))

    elif cmd in ("/reset", "/new"):
        if session.is_connected():
            new_context = session.reset_context()
            click.echo(click.style("✓ Conversation reset.", fg="green", bold=True))
            click.echo(click.style(f"New context ID: {new_context}", fg="bright_black"))
        else:
            click.echo(click.style("Not connected to any agent.", fg="yellow"))

    elif cmd in ("/quit", "/exit"):
        if session.is_connected():
            await session.disconnect()
        click.echo(click.style("Goodbye!", fg="cyan"))
        return False

    else:
        click.echo(click.style(f"Unknown command: {cmd}", fg="red"))
        click.echo(click.style("Type /help for available commands.", fg="bright_black"))

    return True


def get_prompt_message(session: A2ASession) -> list:
    """Generate the prompt message for prompt_toolkit based on connection status."""
    if session.is_connected():
        agent_name = session.agent_card.name if session.agent_card else "agent"
        return [
            ("class:bracket", "["),
            ("class:agent-name", agent_name),
            ("class:bracket", "]"),
            ("class:prompt", " > "),
        ]
    else:
        return [
            ("class:bracket", "["),
            ("class:disconnected", "not connected"),
            ("class:bracket", "]"),
            ("class:prompt", " > "),
        ]


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

    # Create prompt session with autocompletion
    prompt_session: PromptSession = PromptSession(
        completer=SlashCommandCompleter(session),
        history=InMemoryHistory(),
        style=PROMPT_STYLE,
        complete_while_typing=True,
    )

    # Display welcome message
    click.echo(click.style("""
╭───────────────────────────────────────╮
│           A2A CLI Client              │
│   Type /help for available commands   │
│   Use Tab for autocompletion          │
╰───────────────────────────────────────╯
""", fg="cyan", bold=True))

    # If agent-url is provided, connect immediately
    if agent_url:
        click.echo(click.style(f"Connecting to {agent_url}...", fg="cyan"))
        if await session.connect(agent_url):
            click.echo(click.style(f"✓ Connected to {agent_url}", fg="green", bold=True))
            click.echo(click.style("Agent card:", fg="yellow", bold=True))
            click.echo(click.style(pf(session.agent_card), fg="bright_black"))

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
                    should_continue = await handle_slash_command(session, user_input)
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
