"""Configuration management for the bot."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""

    # Telegram
    bot_token: Optional[str] = None
    telegram_proxy_url: Optional[str] = None

    # LMS API
    lms_api_base_url: Optional[str] = None
    lms_api_key: Optional[str] = None

    # LLM API
    llm_api_key: Optional[str] = None
    llm_api_base_url: Optional[str] = None
    llm_api_model: Optional[str] = None

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment or .env file.

        Args:
            env_file: Path to .env file. If None, loads from environment.

        Returns:
            Config instance with loaded values.
        """
        if env_file:
            path = Path(env_file)
            if path.exists():
                cls._load_env_file(path)

        return cls(
            bot_token=os.getenv("BOT_TOKEN"),
            telegram_proxy_url=os.getenv("TELEGRAM_PROXY_URL"),
            lms_api_base_url=os.getenv("LMS_API_BASE_URL"),
            lms_api_key=os.getenv("LMS_API_KEY"),
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_api_base_url=os.getenv("LLM_API_BASE_URL"),
            llm_api_model=os.getenv("LLM_API_MODEL"),
        )

    @staticmethod
    def _load_env_file(path: Path) -> None:
        """Load environment variables from a .env file.

        Args:
            path: Path to the .env file.
        """
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    def validate(self, require_bot_token: bool = True) -> None:
        """Validate that required configuration is present.

        Args:
            require_bot_token: Whether BOT_TOKEN is required.

        Raises:
            ValueError: If required configuration is missing.
        """
        errors = []

        if require_bot_token and not self.bot_token:
            errors.append("BOT_TOKEN is required")

        if not self.lms_api_base_url:
            errors.append("LMS_API_BASE_URL is required")

        if not self.lms_api_key:
            errors.append("LMS_API_KEY is required")

        if not self.llm_api_key:
            errors.append("LLM_API_KEY is required")

        if errors:
            raise ValueError("; ".join(errors))

    @property
    def is_test_mode(self) -> bool:
        """Check if running in test mode (no bot token required)."""
        return not self.bot_token


# Default config paths
ENV_FILE_NAMES = [".env.bot.secret", ".env.bot", ".env"]


def load_config(require_bot_token: bool = True) -> Config:
    """Load configuration from the first available .env file.

    Args:
        require_bot_token: Whether BOT_TOKEN is required.

    Returns:
        Config instance with loaded values.
    """
    # Try to find .env file in bot directory
    bot_dir = Path(__file__).parent

    for env_name in ENV_FILE_NAMES:
        env_path = bot_dir / env_name
        if env_path.exists():
            return Config.from_env(str(env_path))

    # Fall back to environment variables
    return Config.from_env()
