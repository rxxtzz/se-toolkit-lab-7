"""Handler for /help command."""

from .base import HandlerContext, HandlerResult


def handle_help(ctx: HandlerContext) -> HandlerResult:
    """Handle the /help command.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with help message listing available commands.
    """
    message = (
        "📖 *Available Commands*\n\n"
        "• /start - Start the bot and see welcome message\n"
        "• /help - Show this help message\n"
        "• /health - Check system health status\n"
        "• /labs - View available lab assignments\n"
        "• /scores <lab_id> - Check your score for a specific lab\n\n"
        "📝 *Examples:*\n"
        "• /scores lab-04\n"
        "• /scores lab-01\n\n"
        "💡 You can also ask questions in natural language!"
    )

    return HandlerResult.ok(message)
