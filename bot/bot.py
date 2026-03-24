#!/usr/bin/env python3
"""SE Toolkit Lab 7 Telegram Bot.

Entry point for the bot with support for:
- Telegram bot mode (production)
- Test mode via --test flag (offline testing)
- LLM-powered intent routing for natural language queries

Usage:
    uv run bot.py                  # Start Telegram bot
    uv run bot.py --test "/start"  # Test a command offline
    uv run bot.py --test "what labs are available"  # Test natural language
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import Optional

from config import Config, load_config
from handlers.base import HandlerContext
from handlers import (
    handle_start,
    handle_help,
    handle_natural_language,
)
from handlers.health import handle_health, handle_health_async
from handlers.labs import handle_labs, handle_labs_async
from handlers.scores import handle_scores, handle_scores_async

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Sync command handlers
SYNC_COMMAND_HANDLERS = {
    "start": handle_start,
    "help": handle_help,
    "health": handle_health,
    "labs": handle_labs,
    "scores": handle_scores,
}

# Async command handlers
ASYNC_COMMAND_HANDLERS = {
    "start": handle_start,
    "help": handle_help,
    "health": handle_health_async,
    "labs": handle_labs_async,
    "scores": handle_scores_async,
}

# Inline keyboard buttons for common actions
def get_main_keyboard():
    """Get inline keyboard with common actions."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("📚 Available Labs", callback_data="labs"),
            InlineKeyboardButton("🏥 System Health", callback_data="health"),
        ],
        [
            InlineKeyboardButton("📊 Lab 04 Scores", callback_data="scores_lab-04"),
            InlineKeyboardButton("📈 Lab 03 Scores", callback_data="scores_lab-03"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_callback(update, context):
    """Handle inline keyboard button callbacks."""
    from telegram import Update
    
    query = update.callback_query
    if query is None:
        return
    
    await query.answer()
    
    action = query.data
    
    if action == "labs":
        handler = handle_labs_async
    elif action == "health":
        handler = handle_health_async
    elif action == "help":
        handler = handle_help
    elif action.startswith("scores_"):
        lab_id = action.replace("scores_", "")
        handler = lambda ctx: handle_scores_async(ctx)
        # Create custom context with lab_id
        ctx = HandlerContext(
            user_id=query.from_user.id if query.from_user else None,
            username=query.from_user.username if query.from_user else None,
            args=lab_id,
        )
        result = await handler(ctx)
        await query.edit_message_text(result.message)
        return
    else:
        return
    
    ctx = HandlerContext(
        user_id=query.from_user.id if query.from_user else None,
        username=query.from_user.username if query.from_user else None,
        args=None,
    )
    result = await handler(ctx)
    await query.edit_message_text(result.message)


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


def _classify_intent_keywords(text: str) -> str:
    """Keyword-based intent classification fallback.

    Args:
        text: The user's message text.

    Returns:
        The classified intent (command name).
    """
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["start", "hello", "hi", "begin"]):
        return "start"
    elif any(kw in text_lower for kw in ["help", "command", "what can", "how to"]):
        return "help"
    elif any(kw in text_lower for kw in ["health", "status", "online", "working", "backend"]):
        return "health"
    elif any(kw in text_lower for kw in ["lab", "assignment", "available"]):
        return "labs"
    elif any(kw in text_lower for kw in ["score", "grade", "result", "mark", "pass rate"]):
        return "scores"

    return "unknown"


async def run_handler_async(command: str, args: Optional[str] = None) -> str:
    """Run an async handler for the given command.

    Args:
        command: The command name (e.g., "start", "help").
        args: Optional arguments for the command.

    Returns:
        The handler's response message.
    """
    handler = ASYNC_COMMAND_HANDLERS.get(command)

    if not handler:
        return (
            f"Unknown command: /{command}\n\n"
            f"Use /help to see available commands:\n"
            f"  /start - Welcome message\n"
            f"  /help - Available commands\n"
            f"  /health - System status\n"
            f"  /labs - View available labs\n"
            f"  /scores <lab_id> - Check your scores"
        )

    ctx = HandlerContext(user_id=None, username=None, args=args)

    try:
        result = handler(ctx)
        # Check if result is a coroutine (async handler) or HandlerResult (sync handler)
        if asyncio.iscoroutine(result):
            result = await result
        return result.message
    except Exception as e:
        logger.exception(f"Handler {command} failed")
        return f"Error: {e}"


async def run_test_mode(input_text: str) -> int:
    """Run the bot in test mode with async handlers and LLM routing.

    Args:
        input_text: The command to test (e.g., "/start" or "what labs are available").

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        text = input_text.strip()

        if text.startswith("/"):
            command, args = parse_command(text)
            response = await run_handler_async(command, args)
        else:
            # Use LLM-powered intent routing for natural language
            logger.info(f"Natural language query: {text}")
            ctx = HandlerContext(user_id=None, username=None, args=text)
            result = await handle_natural_language(ctx)
            response = result.message

        print(response)
        return 0

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
        from telegram import Update
        from telegram.ext import (
            Application,
            CallbackQueryHandler,
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

            args = " ".join(context.args) if context.args else None

            handler = ASYNC_COMMAND_HANDLERS.get(command)
            if handler:
                ctx = HandlerContext(
                    user_id=update.effective_user.id,
                    username=update.effective_user.username,
                    args=args,
                )
                result = await handler(ctx)
                
                # Add inline keyboard for /start command
                if command == "start":
                    await update.message.reply_text(
                        result.message,
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await update.message.reply_text(result.message)
            else:
                await update.message.reply_text(
                    f"Unknown command: /{command}. Use /help for available commands."
                )

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Handle natural language messages using LLM routing."""
            if update.effective_message is None:
                return

            text = update.message.text
            if not text:
                return

            logger.info(f"Natural language message: {text[:50]}...")

            ctx = HandlerContext(
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                args=text,
            )
            result = await handle_natural_language(ctx)
            await update.message.reply_text(result.message)

        request_kwargs = {}
        if config.telegram_proxy_url and config.telegram_proxy_url != "http://your-proxy:port":
            logger.info(f"Using Telegram proxy: {config.telegram_proxy_url}")
            try:
                request_kwargs["proxy"] = config.telegram_proxy_url
            except Exception as e:
                logger.warning(f"Invalid proxy URL: {e}")

        application = Application.builder()\
            .token(config.bot_token)\
            .request(HTTPXRequest(**request_kwargs) if request_kwargs else None)\
            .build()

        for command in ASYNC_COMMAND_HANDLERS.keys():
            application.add_handler(CommandHandler(command, handle_command))

        # Add callback query handler for inline buttons
        application.add_handler(CallbackQueryHandler(handle_callback))

        # Add message handler for natural language (must be last)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Starting Telegram bot with LLM routing...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

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

    if args.test:
        logger.info(f"Running in test mode with command: {args.test}")
        return asyncio.run(run_test_mode(args.test))

    logger.info("Starting in production mode")

    env_file = args.env_file
    if not env_file:
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
