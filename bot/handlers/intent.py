"""Handler for natural language intent routing with LLM tool calling."""

import logging
from typing import Dict, List

from services.llm_client import LLMClient, SYSTEM_PROMPT
from .base import HandlerContext, HandlerResult

logger = logging.getLogger(__name__)


async def handle_natural_language(ctx: HandlerContext) -> HandlerResult:
    """Handle natural language queries using LLM with tool calling.

    This is the main entry point for intent-based routing. The LLM receives
    the user's message along with tool definitions, decides which tools to call,
    and produces a final answer based on the tool results.

    Args:
        ctx: Handler context with user information and message.

    Returns:
        HandlerResult with the LLM's response.
    """
    from config import load_config

    user_message = ctx.args or ""

    if not user_message:
        return HandlerResult.ok(
            "I'm here to help! You can ask me about:\n"
            "- Available labs and assignments\n"
            "- Pass rates and scores\n"
            "- Student performance and rankings\n"
            "- Group comparisons\n\n"
            "Try asking: 'what labs are available?' or 'show me scores for lab 4'"
        )

    try:
        config = load_config(require_bot_token=False)

        # Check if LLM is configured
        if not config.llm_api_key or not config.llm_api_base_url:
            return _fallback_response(user_message)

        # Initialize LLM client
        model = config.llm_api_model or "qwen-coder"
        llm = LLMClient(config.llm_api_key, config.llm_api_base_url, model)

        # Check if LLM is healthy
        if not await llm.health_check():
            logger.warning("LLM health check failed, using fallback")
            return _fallback_response(user_message)

        # Prepare messages for the LLM
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Call LLM with tool support
        response = await llm.chat_with_tools(messages)

        if not response or len(response.strip()) < 10:
            return _fallback_response(user_message)

        return HandlerResult.ok(response)

    except Exception as e:
        logger.exception(f"LLM routing failed for: {user_message[:50]}...")
        return _fallback_response(user_message)


def _fallback_response(message: str) -> HandlerResult:
    """Return a helpful fallback response when LLM is unavailable.

    Args:
        message: The user's original message.

    Returns:
        HandlerResult with a helpful fallback message.
    """
    message_lower = message.lower()

    # Check for greetings
    if any(kw in message_lower for kw in ["hello", "hi", "hey", "greetings"]):
        return HandlerResult.ok(
            "👋 Hello! I'm your SE Toolkit Lab Assistant.\n\n"
            "I can help you with:\n"
            "• Viewing available labs\n"
            "• Checking pass rates and scores\n"
            "• Finding top learners\n"
            "• Comparing group performance\n\n"
            "Try asking: 'what labs are available?'"
        )

    # Check for gibberish or very short messages
    if len(message) < 3 or message_lower in ["asdf", "test", "abc"]:
        return HandlerResult.ok(
            "I'm not sure I understood that. Here's what I can help with:\n\n"
            "• 'what labs are available?' - List all labs\n"
            "• 'show me scores for lab 4' - View pass rates\n"
            "• 'who are the top students?' - See leaderboard\n"
            "• 'which group is best in lab 3?' - Compare groups\n\n"
            "Or use commands like /help, /labs, /scores"
        )

    # Check for lab mentions without clear intent
    if "lab" in message_lower:
        return HandlerResult.ok(
            f"I see you mentioned '{message}'. What would you like to know?\n\n"
            "Try:\n"
            "• 'show me scores for this lab'\n"
            "• 'what's the pass rate?'\n"
            "• 'who are the top students?'\n"
            "• 'how many students completed it?'"
        )

    # Generic fallback
    return HandlerResult.ok(
        "I'm having trouble understanding. Here's what I can help with:\n\n"
        "• 'what labs are available?' - List all labs\n"
        "• 'show me scores for lab 4' - View pass rates\n"
        "• 'who are the top 5 students?' - See leaderboard\n"
        "• 'which group is best?' - Compare groups\n"
        "• 'when are submissions due?' - Check timeline\n\n"
        "Or use commands: /start, /help, /labs, /scores <lab_id>"
    )
