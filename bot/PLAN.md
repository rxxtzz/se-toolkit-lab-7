# Bot Development Plan

## Overview

This document outlines the development plan for the SE Toolkit Lab 7 Telegram bot. The bot serves as an interface between students and the learning management system (LMS), providing access to lab assignments, scores, and AI-powered assistance.

## Architecture Principles

### 1. Testable Handler Architecture (P0.1)

The core design principle is **separation of concerns**: command handlers are pure functions that take input and return responses without any knowledge of Telegram. This enables:

- **Offline testing**: Handlers can be tested via CLI without Telegram API calls
- **Reusability**: Same handlers work for Telegram, web UI, or future interfaces
- **Maintainability**: Business logic is isolated from transport layer

The architecture follows this flow:
```
Telegram Message → bot.py (entry point) → Router → Handler → Service Layer → Response
CLI --test       → bot.py (entry point) → Router → Handler → Service Layer → Response
```

### 2. CLI Test Mode (P0.2)

The `--test` flag allows direct invocation of handlers:
- `uv run bot.py --test "/start"` → prints welcome message to stdout
- `uv run bot.py --test "/scores lab-04"` → prints lab scores
- No Telegram connection required
- Exit code 0 on success, non-zero on error

## Implementation Phases

### Phase 1: Scaffold (Current Task)

Create the project skeleton with:
- `bot.py` entry point with `--test` mode support
- `handlers/` directory for command handlers
- `services/` directory for API clients
- `config.py` for environment variable loading
- `pyproject.toml` for dependency management
- `.env.bot.example` template

Handlers return placeholder text. Focus is on architecture verification.

### Phase 2: Backend Integration

Implement real handler logic:
- `/start` - Welcome message with bot capabilities
- `/help` - List of available commands
- `/health` - Backend service health check via API call
- `/labs` - Fetch available labs from LMS API
- `/scores <lab_id>` - Fetch student scores for specific lab

Services layer implements:
- `LMSClient`: HTTP client for LMS API with authentication
- `LLMClient`: Client for AI-powered queries

### Phase 3: Intent Routing (Task 3)

Implement natural language understanding:
- Integrate LLM for intent classification
- Route queries like "what labs are available" to `/labs` handler
- Handle follow-up questions contextually
- Fallback to help for unrecognized intents

### Phase 4: Deployment

Docker containerization:
- Add bot service to `docker-compose.yml`
- Environment-based configuration
- Health checks and restart policies
- Logging configuration

## File Structure

```
bot/
├── bot.py              # Entry point, Telegram bot setup, --test mode
├── config.py           # Environment variable loading and validation
├── pyproject.toml      # Python dependencies
├── PLAN.md             # This file
├── .env.bot.example    # Environment template
├── handlers/
│   ├── __init__.py
│   ├── base.py         # Base handler interface
│   ├── start.py        # /start command
│   ├── help.py         # /help command
│   ├── health.py       # /health command
│   ├── labs.py         # /labs command
│   └── scores.py       # /scores command
└── services/
    ├── __init__.py
    ├── lms_client.py   # LMS API client
    └── llm_client.py   # LLM/AI client
```

## Testing Strategy

1. **Unit tests**: Test handlers in isolation with mocked services
2. **Integration tests**: Test handler + service combinations
3. **E2E tests**: Test via Telegram bot in staging environment

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token | Yes (production) |
| `LMS_API_BASE_URL` | LMS API base URL | Yes |
| `LMS_API_KEY` | LMS API authentication key | Yes |
| `LLM_API_KEY` | LLM API authentication key | Yes |
| `LLM_API_BASE_URL` | LLM API endpoint | Yes |

## Risk Mitigation

- **API rate limits**: Implement retry logic with exponential backoff
- **Service downtime**: Health checks and graceful degradation
- **Secret management**: Use `.env.bot.secret` (gitignored) for production
- **Handler errors**: Try-catch with user-friendly error messages
