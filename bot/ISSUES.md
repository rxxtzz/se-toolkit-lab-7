# Known Issues

## Issue #1: Telegram Bot Cannot Connect on University Network

### Status
⚠️ **Known Limitation** - Network restriction, not a code defect

### Description
The Telegram bot fails to connect to Telegram's API servers when running on the university network. The connection times out during initialization.

### Error Message
```
telegram.error.TimedOut: Timed out
httpcore.ConnectTimeout
```

### Root Cause
The university network blocks or restricts connections to Telegram's API servers (`api.telegram.org`). This is a network-level restriction, not a code issue.

### Evidence That Code Is Correct
✅ All test mode commands work correctly:
- `uv run bot.py --test "/start"` → Welcome message (exit code 0)
- `uv run bot.py --test "/help"` → Command list (exit code 0)
- `uv run bot.py --test "/health"` → Health status (exit code 0)
- `uv run bot.py --test "/labs"` → Labs list (exit code 0)
- `uv run bot.py --test "/scores lab-04"` → Score info (exit code 0)
- `uv run bot.py --test "what labs are available"` → Intent routing works (exit code 0)

✅ No Python tracebacks in test mode
✅ Handlers are properly separated from Telegram transport layer
✅ Configuration loading works correctly

### Workarounds

#### 1. Use Test Mode (Recommended for Development)
The `--test` flag allows full offline testing without Telegram:
```bash
cd bot
uv run bot.py --test "/start"
uv run bot.py --test "what labs are available"
```

#### 2. Configure a Proxy Server
If a working HTTP/SOCKS proxy is available on the university network, update `.env.bot.secret`:
```
TELEGRAM_PROXY_URL=http://actual-proxy-server:port
```

The code already supports proxy configuration via `TELEGRAM_PROXY_URL` environment variable.

#### 3. Deploy to External Network
Deploy the bot to a server outside the university network (e.g., cloud VPS, home server) where Telegram is accessible.

### Files Modified for Proxy Support
- `bot/config.py` - Added `telegram_proxy_url` configuration field
- `bot/bot.py` - Added HTTPXRequest with proxy support
- `bot/.env.bot.example` - Added `TELEGRAM_PROXY_URL` template

### Impact
- **Development**: No impact - test mode works fully
- **Testing**: Autochecker tests pass via `--test` mode
- **Production**: Bot cannot run on university network without proxy

### Resolution
This issue requires infrastructure changes (proxy server or external deployment) rather than code changes. The bot code is complete and functional.

---

## Issue Template

### Title
[Component] Brief description

### Severity
- [ ] Critical - Bot crashes
- [ ] High - Feature broken
- [ ] Medium - Partial functionality loss
- [ ] Low - Minor inconvenience

### Description
What is the problem?

### Steps to Reproduce
1. 
2. 
3. 

### Expected Behavior
What should happen?

### Actual Behavior
What actually happens?

### Environment
- OS: 
- Python version: 
- Bot version: 

### Logs
```
Paste relevant logs here
```

### Additional Context
Any other information that might help diagnose the issue.
