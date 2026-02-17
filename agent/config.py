"""Agent-specific configuration, feature flags, and per-user limits."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AgentLimits:
    """Per-user rate & budget limits to prevent surprise costs."""

    max_requests_per_minute: int = 10
    max_requests_per_day: int = 500
    max_tokens_per_request: int = 16_384
    max_tokens_per_day: int = 500_000
    max_image_generations_per_day: int = 20
    max_file_uploads_per_workspace: int = 50
    max_file_size_mb: int = 50
    max_vector_stores_per_user: int = 10


@dataclass
class AgentConfig:
    """Central configuration for Agent Mode.

    All expensive features are disabled by default and controlled via env vars.
    """

    # ── OpenAI credentials ──────────────────────────────────────────
    openai_api_key: str = ""
    default_model: str = "gpt-4o"

    # ── Feature flags (env-driven, off by default for cost control) ──
    enable_web_search: bool = False
    enable_file_search: bool = False
    enable_code_interpreter: bool = False
    enable_image_generation: bool = False
    enable_realtime_voice: bool = False
    enable_memory: bool = False

    # ── Model overrides ─────────────────────────────────────────────
    image_model: str = "gpt-image-1"
    image_quality: str = "auto"  # auto | low | medium | high
    image_size: str = "auto"  # auto | 1024x1024 | 1536x1024 | 1024x1536
    voice_model: str = "gpt-4o-mini-realtime"
    voice_name: str = "alloy"

    # ── Limits ──────────────────────────────────────────────────────
    limits: AgentLimits = field(default_factory=AgentLimits)

    # ── System prompt ───────────────────────────────────────────────
    system_prompt: str = (
        "You are HackGPT Agent, an expert AI cybersecurity assistant. "
        "You help security professionals with penetration testing, "
        "vulnerability analysis, and security research. "
        "Always provide accurate, educational information. "
        "Use available tools when they can help answer the question."
    )

    @classmethod
    def from_env(cls) -> AgentConfig:
        """Build config from environment variables with safe defaults."""

        def _bool(key: str, default: bool = False) -> bool:
            return os.getenv(key, str(default)).lower() in ("true", "1", "yes")

        def _int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            default_model=os.getenv("AGENT_MODEL", "gpt-4o"),
            enable_web_search=_bool("AGENT_ENABLE_WEB_SEARCH"),
            enable_file_search=_bool("AGENT_ENABLE_FILE_SEARCH"),
            enable_code_interpreter=_bool("AGENT_ENABLE_CODE_INTERPRETER"),
            enable_image_generation=_bool("AGENT_ENABLE_IMAGE_GENERATION"),
            enable_realtime_voice=_bool("AGENT_ENABLE_REALTIME_VOICE"),
            enable_memory=_bool("AGENT_ENABLE_MEMORY"),
            image_model=os.getenv("AGENT_IMAGE_MODEL", "gpt-image-1"),
            image_quality=os.getenv("AGENT_IMAGE_QUALITY", "auto"),
            image_size=os.getenv("AGENT_IMAGE_SIZE", "auto"),
            voice_model=os.getenv("AGENT_VOICE_MODEL", "gpt-4o-mini-realtime"),
            voice_name=os.getenv("AGENT_VOICE_NAME", "alloy"),
            system_prompt=os.getenv("AGENT_SYSTEM_PROMPT", cls.system_prompt),
            limits=AgentLimits(
                max_requests_per_minute=_int("AGENT_RATE_LIMIT_RPM", 10),
                max_requests_per_day=_int("AGENT_RATE_LIMIT_RPD", 500),
                max_tokens_per_request=_int("AGENT_MAX_TOKENS_REQUEST", 16_384),
                max_tokens_per_day=_int("AGENT_MAX_TOKENS_DAY", 500_000),
                max_image_generations_per_day=_int("AGENT_MAX_IMAGES_DAY", 20),
                max_file_uploads_per_workspace=_int("AGENT_MAX_FILES_WORKSPACE", 50),
                max_file_size_mb=_int("AGENT_MAX_FILE_SIZE_MB", 50),
                max_vector_stores_per_user=_int("AGENT_MAX_VECTOR_STORES", 10),
            ),
        )
