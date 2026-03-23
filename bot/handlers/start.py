"""Handler for /start command."""

from .base import HandlerContext, HandlerResult


def handle_start(ctx: HandlerContext) -> HandlerResult:
    """Handle the /start command.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with welcome message.
    """
    username = ctx.username or "Student"

    message = (
        f"👋 Welcome, {username}!\n\n"
        f"I'm your SE Toolkit Lab Assistant. I can help you with:\n\n"
        f"• 📚 View available labs\n"
        f"• 📊 Check your scores\n"
        f"• ❓ Get help with commands\n"
        f"• 🏥 Check system health\n\n"
        f"Use /help to see all available commands."
    )

    return HandlerResult.ok(message)
