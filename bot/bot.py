#!/usr/bin/env python3
"""SE Toolkit Lab 7 Telegram Bot.

Entry point for the bot with support for:
- Telegram bot mode (production)
- Test mode via --test flag (offline testing)

Usage:
    uv run bot.py                  # Start Telegram bot
    uv run bot.py --test "/start"  # Test a command offline
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from config import Config, load_config
from handlers.base import HandlerContext
from handlers import (
    handle_start,
    handle_help,
    handle_health,
    handle_labs,
    handle_scores,
)
from services.llm_client import LLMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Command router: maps command names to handler functions
COMMAND_HANDLERS = {
    "start": handle_start,
    "help": handle_help,
    "health": handle_health,
    "labs": handle_labs,
    "scores": handle_scores,
}


def parse_command(input_text: str) -> tuple[str, Optional[str]]:
    """Parse a command from input text.

    Args:
        input_text: The input text (e.g., "/start" or "/scores lab-04").

    Returns:
        Tuple of (command_name, args).
    """
    text = input_text.strip()

    # Remove leading slash if present
    if text.startswith("/"):
        text = text[1:]

    # Split command and arguments
    parts = text.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else None

    return command, args


async def classify_intent(text: str) -> str:
    """Classify the intent of a natural language query.

    Args:
        text: The user's message text.

    Returns:
        The classified intent (command name).
    """
    try:
        config = load_config(require_bot_token=False)
        if not config.llm_api_key or not config.llm_api_base_url:
            # Fall back to keyword-based classification
            return _classify_intent_keywords(text)

        client = LLMClient(config.llm_api_key, config.llm_api_base_url)
        intent = await client.classify_intent(text)
        logger.info(f"LLM classified intent: {intent}")
        return intent if intent in COMMAND_HANDLERS else "unknown"

    except Exception as e:
        logger.warning(f"Intent classification failed: {e}, using keyword fallback")
        return _classify_intent_keywords(text)


def _classify_intent_keywords(text: str) -> str:
    """Keyword-based intent classification fallback.

    Args:
        text: The user's message text.

    Returns:
        The classified intent (command name).
    """
    text_lower = text.lower()

    # Check for specific patterns
    if any(kw in text_lower for kw in ["start", "hello", "hi", "begin"]):
        return "start"
    elif any(kw in text_lower for kw in ["help", "command", "what can", "how to"]):
        return "help"
    elif any(kw in text_lower for kw in ["health", "status", "online", "working"]):
        return "health"
    elif any(kw in text_lower for kw in ["lab", "assignment", "available"]):
        return "labs"
    elif any(kw in text_lower for kw in ["score", "grade", "result", "mark"]):
        return "scores"

    return "unknown"


def run_handler(command: str, args: Optional[str] = None) -> str:
    """Run a handler for the given command.

    Args:
        command: The command name (e.g., "start", "help").
        args: Optional arguments for the command.

    Returns:
        The handler's response message.

    Raises:
        ValueError: If the command is not found.
    """
    handler = COMMAND_HANDLERS.get(command)

    if not handler:
        raise ValueError(f"Unknown command: /{command}. Use /help for available commands.")

    # Create context (no user info in test mode)
    ctx = HandlerContext(user_id=None, username=None, args=args)

    # Run the handler
    result = handler(ctx)

    if not result.success:
        logger.error(f"Handler failed: {result.error}")
        return f"Error: {result.error}"

    return result.message


async def run_test_mode(input_text: str) -> int:
    """Run the bot in test mode.

    Args:
        input_text: The command to test (e.g., "/start" or "what labs are available").

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        text = input_text.strip()

        # Check if it's a command (starts with /)
        if text.startswith("/"):
            command, args = parse_command(text)
            
            # Check if command exists
            if command not in COMMAND_HANDLERS:
                print(
                    f"Unknown command: /{command}\n\n"
                    f"Use /help to see available commands:\n"
                    f"  /start - Welcome message\n"
                    f"  /help - Available commands\n"
                    f"  /health - System status\n"
                    f"  /labs - View available labs\n"
                    f"  /scores <lab_id> - Check your scores"
                )
                return 0
            
            response = run_handler(command, args)
        else:
            # Natural language query - classify intent first
            intent = await classify_intent(text)
            logger.info(f"Classified intent: {intent} for: {text}")

            if intent == "unknown":
                print(
                    "I'm not sure what you're asking. Try using commands like:\n"
                    "  /start - Welcome message\n"
                    "  /help - Available commands\n"
                    "  /labs - View available labs\n"
                    "  /scores <lab_id> - Check your scores\n"
                    "  /health - System status"
                )
                return 0

            # Extract lab_id if intent is scores
            args = None
            if intent == "scores":
                # Try to extract lab_id from text
                import re
                match = re.search(r'lab-?\d+', text.lower())
                if match:
                    args = match.group().replace('-', '')
                    args = f"lab-{args.split('lab')[1]}" if 'lab' in args else args

            response = run_handler(intent, args)

        print(response)
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unexpected error in test mode")
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def run_telegram_bot(config: Config) -> None:
    """Run the Telegram bot.

    Args:
        config: Bot configuration.
    """
    try:
        # Import telegram libraries only when needed
        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            filters,
        )
        from telegram.request import HTTPXRequest

        async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Handle Telegram commands."""
            if update.effective_message is None or update.effective_user is None:
                return

            command = update.message.command if update.message else None
            if not command:
                return

            # Get command arguments
            args = " ".join(context.args) if context.args else None

            # Run the handler
            ctx = HandlerContext(
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                args=args,
            )

            handler = COMMAND_HANDLERS.get(command)
            if handler:
                result = handler(ctx)
                await update.message.reply_text(result.message)
            else:
                await update.message.reply_text(
                    f"Unknown command: /{command}. Use /help for available commands."
                )

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Handle natural language messages (intent routing)."""
            if update.effective_message is None:
                return

            text = update.message.text
            if not text:
                return

            # Classify intent and route to appropriate handler
            intent = await classify_intent(text)
            logger.info(f"Classified intent: {intent} for: {text}")

            if intent == "unknown":
                await update.message.reply_text(
                    "I'm not sure what you're asking. Try using commands like:\n"
                    "/start - Welcome message\n"
                    "/help - Available commands\n"
                    "/labs - View available labs\n"
                    "/scores <lab_id> - Check your scores\n"
                    "/health - System status"
                )
                return

            # Create context and run handler
            ctx = HandlerContext(
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                args=None,
            )
            handler = COMMAND_HANDLERS.get(intent)
            if handler:
                result = handler(ctx)
                await update.message.reply_text(result.message)

        # Build request with proxy support if configured
        request_kwargs = {}
        if config.telegram_proxy_url:
            logger.info(f"Using Telegram proxy: {config.telegram_proxy_url}")
            request_kwargs["proxy_url"] = config.telegram_proxy_url

        # Create the application with proxy support
        application = Application.builder()\
            .token(config.bot_token)\
            .request(HTTPXRequest(**request_kwargs) if request_kwargs else None)\
            .build()

        # Add command handlers
        for command in COMMAND_HANDLERS.keys():
            application.add_handler(CommandHandler(command, handle_command))

        # Add message handler for natural language
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start the bot
        logger.info("Starting Telegram bot...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        # Keep running
        while True:
            await asyncio.sleep(1)

    except ImportError:
        logger.error(
            "Telegram libraries not installed. "
            "Run: uv add python-telegram-bot python-telegram-bot[job-queue]"
        )
        sys.exit(1)
    except Exception as e:
        logger.exception("Error running Telegram bot")
        raise


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(description="SE Toolkit Lab 7 Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Run in test mode with the given command (e.g., '/start')",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to .env file (default: .env.bot.secret)",
    )

    args = parser.parse_args()

    # Test mode
    if args.test:
        logger.info(f"Running in test mode with command: {args.test}")
        return asyncio.run(run_test_mode(args.test))

    # Production mode (Telegram bot)
    logger.info("Starting in production mode")

    # Load configuration
    env_file = args.env_file
    if not env_file:
        # Default to bot directory
        bot_dir = Path(__file__).parent
        for name in [".env.bot.secret", ".env.bot", ".env"]:
            if (bot_dir / name).exists():
                env_file = str(bot_dir / name)
                break

    try:
        config = load_config(require_bot_token=True)
        config.validate(require_bot_token=True)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Run the Telegram bot
    try:
        asyncio.run(run_telegram_bot(config))
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return 0
    except Exception as e:
        logger.exception("Bot crashed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
