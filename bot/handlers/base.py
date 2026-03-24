"""Base handler interface and types."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HandlerResult:
    """Result of a handler execution.

    Attributes:
        success: Whether the handler executed successfully.
        message: The response message to send to the user.
        error: Error message if success is False.
    """

    success: bool = True
    message: str = ""
    error: Optional[str] = None

    @classmethod
    def ok(cls, message: str) -> "HandlerResult":
        """Create a successful result."""
        return cls(success=True, message=message)

    @classmethod
    def fail(cls, error: str, message: str = "") -> "HandlerResult":
        """Create a failed result."""
        return cls(success=False, message=message, error=error)


@dataclass
class HandlerContext:
    """Context passed to handlers.

    Attributes:
        user_id: Telegram user ID or None for test mode.
        username: Telegram username or None for test mode.
        args: Additional arguments from the command.
    """

    user_id: Optional[int] = None
    username: Optional[str] = None
    args: Optional[str] = None
