"""Configuration management for Custom FDTD plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv not available, use environment variables directly
    pass


@dataclass
class CustomFDTDConfig:
    """Configuration for Custom FDTD API client."""

    api_endpoint: str
    api_key: Optional[str] = None
    timeout: int = 300  # 5 minutes default
    retry_attempts: int = 3
    retry_delay: float = 1.0

    @classmethod
    def from_environment(cls) -> CustomFDTDConfig:
        """Create config from environment variables."""
        api_key = os.getenv("CUSTOM_FDTD_API_KEY")
        if not api_key:
            raise ValueError(
                "CUSTOM_FDTD_API_KEY environment variable is required. "
                "Set your API key to connect to the Custom FDTD backend."
            )

        return cls(
            api_endpoint=os.getenv(
                "CUSTOM_FDTD_API_ENDPOINT", "https://api.custom-fdtd.example.com"
            ),
            api_key=api_key,
            timeout=int(os.getenv("CUSTOM_FDTD_TIMEOUT", "300")),
            retry_attempts=int(os.getenv("CUSTOM_FDTD_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("CUSTOM_FDTD_RETRY_DELAY", "1.0")),
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.api_key:
            raise ValueError("API key is required")

        if not self.api_endpoint:
            raise ValueError("API endpoint cannot be empty")

        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if self.retry_attempts < 0:
            raise ValueError("Retry attempts must be non-negative")


# Global config instance
_config: Optional[CustomFDTDConfig] = None


def get_config() -> CustomFDTDConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CustomFDTDConfig.from_environment()
        _config.validate()
    return _config


def set_config(config: CustomFDTDConfig) -> None:
    """Set a custom configuration instance."""
    global _config
    config.validate()
    _config = config


def reset_config() -> None:
    """Reset configuration to reload from environment."""
    global _config
    _config = None
