"""CLI slash commands and autocompletion for A2A CLI."""

from typing import TYPE_CHECKING

import click
from devtools import PrettyFormat
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from a2a_cli.session import A2ASession

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

# URL suggestions for /connect command
URL_SUGGESTIONS = [
    {"url": "http://", "description": "HTTP protocol"},
    {"url": "https://", "description": "HTTPS protocol"},
    {"url": "http://localhost:", "description": "Local HTTP server"},
    {"url": "http://localhost:8000", "description": "Common dev port"},
    {"url": "http://localhost:3000", "description": "Common dev port"},
    {"url": "http://localhost:5000", "description": "Common dev port"},
    {"url": "http://127.0.0.1:", "description": "Local IP address"},
]


class SlashCommandCompleter(Completer):
    """Completer for slash commands with descriptions."""

    def __init__(self, session: "A2ASession") -> None:
        self.session = session

    def get_completions(self, document, complete_event):  # type: ignore
        text = document.text_before_cursor
        
        # Only complete if we're at the start of a line and typing a slash command
        if not text.startswith("/"):
            return
        
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        
        # If we're typing the URL argument for /connect
        if cmd == "/connect" and len(parts) >= 1:
            # Get what the user has typed for the URL (if anything)
            url_part = parts[1] if len(parts) > 1 else ""
            
            for suggestion in URL_SUGGESTIONS:
                url = suggestion["url"]
                if url.startswith(url_part):
                    yield Completion(
                        url,
                        start_position=-len(url_part),
                        display=HTML(f"<b>{url}</b>"),
                        display_meta=suggestion["description"],
                    )
            
            # If user has typed something, don't also show command completions
            if url_part:
                return
        
        # Get the word being typed for command completion
        word = parts[0] if parts else text
        
        for cmd_name, info in SLASH_COMMANDS.items():
            if cmd_name.startswith(word):
                # Build display text with description
                display = cmd_name
                if info["arg"]:
                    # Escape angle brackets for HTML display
                    escaped_arg = info["arg"].replace("<", "&lt;").replace(">", "&gt;")
                    display += f" {escaped_arg}"
                
                # Create the completion
                yield Completion(
                    cmd_name,
                    start_position=-len(word),
                    display=HTML(f"<b>{cmd_name}</b> <i>{escaped_arg if info['arg'] else ''}</i>"),
                    display_meta=info["description"],
                )


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


async def handle_slash_command(session: "A2ASession", command: str) -> bool:
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


def get_prompt_message(session: "A2ASession") -> list:
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
