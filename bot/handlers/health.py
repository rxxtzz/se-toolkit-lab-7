"""Handler for /health command."""

import asyncio
from typing import Optional

from services.lms_client import LMSClient
from .base import HandlerContext, HandlerResult


def handle_health(ctx: HandlerContext) -> HandlerResult:
    """Handle the /health command.

    This is a synchronous wrapper that returns a placeholder.
    For actual health checks, use handle_health_async.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with health status.
    """
    # This is called from sync context - return placeholder
    # Async version should be used in async contexts
    message = (
        "🏥 System Health Status\n\n"
        "Checking backend...\n\n"
        "Use test mode for detailed health check."
    )
    return HandlerResult.ok(message)


async def handle_health_async(ctx: HandlerContext) -> HandlerResult:
    """Handle the /health command with actual backend check.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with health status.
    """
    from config import load_config

    try:
        config = load_config(require_bot_token=False)

        if not config.lms_api_base_url or not config.lms_api_key:
            return HandlerResult.fail(
                error="LMS_API configuration missing",
                message="Backend configuration incomplete. Check LMS_API_BASE_URL and LMS_API_KEY."
            )

        client = LMSClient(config.lms_api_base_url, config.lms_api_key)
        is_healthy, item_count, error_msg = await client.health_check()

        if is_healthy:
            message = (
                f"✅ Backend is healthy. {item_count} items available.\n\n"
                f"API: {config.lms_api_base_url}"
            )
            return HandlerResult.ok(message)
        else:
            message = (
                f"❌ Backend error: {error_msg}\n\n"
                f"Check that the services are running."
            )
            return HandlerResult.ok(message)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        message = f"❌ Backend error: {error_msg}"
        return HandlerResult.ok(message)
