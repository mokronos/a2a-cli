"""Persistent history management for A2A CLI."""

import os
from pathlib import Path

from prompt_toolkit.history import FileHistory, History


def get_config_dir() -> Path:
    """Get the configuration directory for a2a-cli.
    
    Uses XDG_CONFIG_HOME if set, otherwise defaults to ~/.config/a2a-cli
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_dir = Path(xdg_config) / "a2a-cli"
    else:
        config_dir = Path.home() / ".config" / "a2a-cli"
    
    # Ensure the directory exists
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_command_history() -> FileHistory:
    """Get persistent history for slash commands (used when disconnected)."""
    history_file = get_config_dir() / "command_history"
    return FileHistory(str(history_file))


def get_task_history() -> FileHistory:
    """Get persistent history for tasks sent to agents (used when connected)."""
    history_file = get_config_dir() / "task_history"
    return FileHistory(str(history_file))


class ContextAwareHistory(History):
    """A history that switches between command and task history based on connection state.
    
    When disconnected: uses command_history (for /connect, etc.)
    When connected: uses task_history (for messages sent to agents)
    """

    def __init__(self) -> None:
        super().__init__()
        self._command_history = get_command_history()
        self._task_history = get_task_history()
        self._is_connected = False

    def set_connected(self, connected: bool) -> None:
        """Update the connection state to switch history context."""
        self._is_connected = connected

    @property
    def _active_history(self) -> FileHistory:
        """Get the currently active history based on connection state."""
        return self._task_history if self._is_connected else self._command_history

    def load_history_strings(self) -> list[str]:
        """Load history strings from the active history file."""
        return list(self._active_history.load_history_strings())

    def store_string(self, string: str) -> None:
        """Store a string in the active history file."""
        self._active_history.store_string(string)
