"""Handler for /labs command."""

import asyncio
from typing import List

from services.lms_client import LMSClient, Lab
from .base import HandlerContext, HandlerResult

# Static fallback labs
FALLBACK_LABS = [
    {"id": "lab-01", "name": "Products, Architecture & Roles"},
    {"id": "lab-02", "name": "Run, Fix, and Deploy"},
    {"id": "lab-03", "name": "Backend API"},
    {"id": "lab-04", "name": "Testing, Front-end, and AI Agents"},
    {"id": "lab-05", "name": "Data Pipeline and Analytics"},
    {"id": "lab-06", "name": "Build Your Own Agent"},
]


def handle_labs(ctx: HandlerContext) -> HandlerResult:
    """Handle the /labs command.

    This is a synchronous wrapper that returns fallback data.
    For actual API fetch, use handle_labs_async.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with list of available labs.
    """
    labs_text = "\n".join([f"- {lab['name']}" for lab in FALLBACK_LABS])
    message = (
        f"Available labs:\n"
        f"{labs_text}\n\n"
        f"Use /scores <lab_id> to check scores for a specific lab.\n"
        f"Example: /scores lab-04"
    )
    return HandlerResult.ok(message)


async def handle_labs_async(ctx: HandlerContext) -> HandlerResult:
    """Handle the /labs command with actual API fetch.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with list of available labs.
    """
    from config import load_config

    try:
        config = load_config(require_bot_token=False)

        if not config.lms_api_base_url or not config.lms_api_key:
            return _fallback_response()

        client = LMSClient(config.lms_api_base_url, config.lms_api_key)
        labs = await client.get_labs()

        if not labs:
            return _fallback_response()

        labs_text = "\n".join([f"- {lab.name}" for lab in labs])
        message = (
            f"Available labs:\n"
            f"{labs_text}\n\n"
            f"Use /scores <lab_id> to check scores for a specific lab."
        )
        return HandlerResult.ok(message)

    except Exception as e:
        # Return fallback on error
        return _fallback_response()


def _fallback_response() -> HandlerResult:
    """Return fallback labs list."""
    labs_text = "\n".join([f"- {lab['name']}" for lab in FALLBACK_LABS])
    message = (
        f"Available labs:\n"
        f"{labs_text}\n\n"
        f"Use /scores <lab_id> to check scores for a specific lab."
    )
    return HandlerResult.ok(message)
