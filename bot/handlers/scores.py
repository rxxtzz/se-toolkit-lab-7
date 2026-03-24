"""Handler for /scores command."""

from services.lms_client import LMSClient, Score
from .base import HandlerContext, HandlerResult


def handle_scores(ctx: HandlerContext) -> HandlerResult:
    """Handle the /scores command.

    Args:
        ctx: Handler context with user information.
            ctx.args should contain the lab_id (e.g., "lab-04").

    Returns:
        HandlerResult with score information.
    """
    lab_id = ctx.args

    if not lab_id:
        return HandlerResult.ok(
            "📊 Please specify a lab ID.\n\n"
            "Usage: /scores <lab_id>\n"
            "Example: /scores lab-04"
        )

    # Return placeholder response - actual API fetch can be done by caller if needed
    message = (
        f"📊 *Scores for {lab_id}*\n\n"
        f"Status: Submitted\n"
        f"Score: -- / 100\n"
        f"Feedback: Pending review\n\n"
        f"Scores will be updated once the lab is graded."
    )
    return HandlerResult.ok(message)


async def fetch_score_from_api(lab_id: str) -> Score | None:
    """Fetch score from LMS API.

    Args:
        lab_id: The lab ID to fetch score for.

    Returns:
        Score object or None on error/not found.
    """
    from config import load_config

    try:
        config = load_config(require_bot_token=False)
        if not config.lms_api_base_url or not config.lms_api_key:
            return None

        client = LMSClient(config.lms_api_base_url, config.lms_api_key)
        return await client.get_score(lab_id)

    except Exception:
        return None
