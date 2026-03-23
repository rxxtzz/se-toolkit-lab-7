# SE Toolkit Lab 7 Bot

Telegram bot for SE Toolkit Lab 7.

## Usage

### Test Mode

```bash
uv run bot.py --test "/start"
uv run bot.py --test "/help"
uv run bot.py --test "/health"
uv run bot.py --test "/labs"
uv run bot.py --test "/scores lab-04"
```

### Production Mode

```bash
# Copy and configure environment
cp .env.bot.example .env.bot.secret
# Edit .env.bot.secret with real values

# Run the bot
uv run bot.py
```

## Configuration

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `LMS_API_BASE_URL` | LMS API base URL |
| `LMS_API_KEY` | LMS API authentication key |
| `LLM_API_KEY` | LLM API authentication key |
| `LLM_API_BASE_URL` | LLM API endpoint |
