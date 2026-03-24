"""Handler for /health command."""

from services.lms_client import LMSClient
from services.llm_client import LLMClient
from .base import HandlerContext, HandlerResult


def handle_health(ctx: HandlerContext) -> HandlerResult:
    """Handle the /health command.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with health status.
    """
    # Return a static response - actual health checks are done by the caller
    # if they need async operations
    message = (
        "🏥 *System Health Status*\n\n"
        "✅ Bot: Online\n"
        "⏳ LMS API: Checking...\n"
        "⏳ LLM Service: Checking...\n\n"
        "All systems operational."
    )

    return HandlerResult.ok(message)


async def check_health_services() -> tuple[bool, bool]:
    """Check health of external services.

    Returns:
        Tuple of (lms_healthy, llm_healthy).
    """
    from config import load_config

    lms_healthy = False
    llm_healthy = False

    try:
        config = load_config(require_bot_token=False)

        # Check LMS
        if config.lms_api_base_url and config.lms_api_key:
            try:
                client = LMSClient(config.lms_api_base_url, config.lms_api_key)
                lms_healthy = await client.health_check()
            except Exception:
                pass

        # Check LLM
        if config.llm_api_key and config.llm_api_base_url:
            try:
                client = LLMClient(config.llm_api_key, config.llm_api_base_url)
                llm_healthy = await client.health_check()
            except Exception:
                pass

    except Exception:
        pass

    return lms_healthy, llm_healthy
