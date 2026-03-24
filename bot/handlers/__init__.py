"""Command handlers for the bot."""

from .start import handle_start
from .help import handle_help
from .health import handle_health, handle_health_async
from .labs import handle_labs, handle_labs_async
from .scores import handle_scores, handle_scores_async
from .intent import handle_natural_language

__all__ = [
    "handle_start",
    "handle_help",
    "handle_health",
    "handle_health_async",
    "handle_labs",
    "handle_labs_async",
    "handle_scores",
    "handle_scores_async",
    "handle_natural_language",
]
