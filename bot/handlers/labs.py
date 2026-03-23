"""Handler for /labs command."""

from services.lms_client import LMSClient
from .base import HandlerContext, HandlerResult

# Static fallback labs
FALLBACK_LABS = [
    {"id": "lab-01", "name": "Introduction to Software Engineering"},
    {"id": "lab-02", "name": "Requirements Engineering"},
    {"id": "lab-03", "name": "Software Design"},
    {"id": "lab-04", "name": "Implementation and Testing"},
    {"id": "lab-05", "name": "DevOps and CI/CD"},
    {"id": "lab-06", "name": "Containerization with Docker"},
    {"id": "lab-07", "name": "Bot Development"},
]


def handle_labs(ctx: HandlerContext) -> HandlerResult:
    """Handle the /labs command.

    Args:
        ctx: Handler context with user information.

    Returns:
        HandlerResult with list of available labs.
    """
    # Use fallback labs - actual API fetch can be done by caller if needed
    labs_text = "\n".join([f"• {lab['id']}: {lab['name']}" for lab in FALLBACK_LABS])
    message = (
        f"📚 *Available Lab Assignments*\n\n"
        f"{labs_text}\n\n"
        f"Use /scores <lab_id> to check your score for a specific lab.\n"
        f"Example: /scores lab-04"
    )
    return HandlerResult.ok(message)


async def fetch_labs_from_api() -> list[dict]:
    """Fetch labs from LMS API.

    Returns:
        List of lab dicts, or empty list on error.
    """
    from config import load_config

    try:
        config = load_config(require_bot_token=False)
        if not config.lms_api_base_url or not config.lms_api_key:
            return FALLBACK_LABS

        client = LMSClient(config.lms_api_base_url, config.lms_api_key)
        labs = await client.get_labs()

        if not labs:
            return FALLBACK_LABS

        return [{"id": lab.id, "name": lab.name} for lab in labs]

    except Exception:
        return FALLBACK_LABS
