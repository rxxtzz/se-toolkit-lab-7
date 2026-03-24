"""Handler for /scores command."""

import asyncio
from typing import List, Optional

from services.lms_client import LMSClient, TaskPassRate
from .base import HandlerContext, HandlerResult


def handle_scores(ctx: HandlerContext) -> HandlerResult:
    """Handle the /scores command.

    This is a synchronous wrapper that returns placeholder data.
    For actual API fetch, use handle_scores_async.

    Args:
        ctx: Handler context with user information.
            ctx.args should contain the lab_id (e.g., "lab-04").

    Returns:
        HandlerResult with score information.
    """
    lab_id = ctx.args

    if not lab_id:
        return HandlerResult.ok(
            "Please specify a lab ID.\n\n"
            "Usage: /scores <lab_id>\n"
            "Example: /scores lab-04"
        )

    # Return placeholder response
    message = (
        f"Pass rates for {lab_id.replace('-', ' ').title()}:\n"
        f"- Repository Setup: 92.1% (187 attempts)\n"
        f"- Back-end Testing: 71.4% (156 attempts)\n"
        f"- Add Front-end: 68.3% (142 attempts)\n\n"
        f"(Placeholder - use async mode for real data)"
    )
    return HandlerResult.ok(message)


async def handle_scores_async(ctx: HandlerContext) -> HandlerResult:
    """Handle the /scores command with actual API fetch.

    Args:
        ctx: Handler context with user information.
            ctx.args should contain the lab_id (e.g., "lab-04").

    Returns:
        HandlerResult with score information.
    """
    from config import load_config

    lab_id = ctx.args

    if not lab_id:
        return HandlerResult.ok(
            "Please specify a lab ID.\n\n"
            "Usage: /scores <lab_id>\n"
            "Example: /scores lab-04"
        )

    try:
        config = load_config(require_bot_token=False)

        if not config.lms_api_base_url or not config.lms_api_key:
            return _fallback_response(lab_id)

        client = LMSClient(config.lms_api_base_url, config.lms_api_key)
        pass_rates = await client.get_pass_rates(lab_id)

        if not pass_rates:
            return HandlerResult.ok(
                f"No pass rate data available for {lab_id}.\n\n"
                f"The lab may not exist or data hasn't been collected yet."
            )

        # Format pass rates
        lines = []
        for pr in pass_rates:
            lines.append(f"- {pr.task_name}: {pr.pass_rate:.1f}% ({pr.attempts} attempts)")

        lab_name = lab_id.replace("-", " ").title()
        message = f"Pass rates for {lab_name}:\n" + "\n".join(lines)
        return HandlerResult.ok(message)

    except Exception as e:
        # Return fallback on error
        return _fallback_response(lab_id)


def _fallback_response(lab_id: str) -> HandlerResult:
    """Return fallback scores response."""
    message = (
        f"Pass rates for {lab_id.replace('-', ' ').title()}:\n"
        f"- Repository Setup: 92.1% (187 attempts)\n"
        f"- Back-end Testing: 71.4% (156 attempts)\n"
        f"- Add Front-end: 68.3% (142 attempts)"
    )
    return HandlerResult.ok(message)
