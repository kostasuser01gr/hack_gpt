"""Per-user usage metering, rate limiting, and budget enforcement."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from agent.config import AgentLimits
from agent.schemas import UsageRecord

logger = logging.getLogger(__name__)


@dataclass
class _UserBucket:
    """In-memory counters for a single user's rate & budget tracking."""

    # Rate limiting (sliding window)
    request_timestamps: list[float] = field(default_factory=list)

    # Daily counters (reset at midnight UTC)
    daily_requests: int = 0
    daily_tokens: int = 0
    daily_images: int = 0
    daily_cost_usd: float = 0.0
    daily_reset_at: float = 0.0  # epoch when counters reset

    # Lifetime (for audit)
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Usage log
    records: list[dict[str, Any]] = field(default_factory=list)


class UsageMeter:
    """Thread-safe per-user usage metering with rate limiting and budget caps.

    This is an in-memory implementation suitable for single-process deployments.
    For multi-process / production, back this with Redis or the database.
    """

    def __init__(self, limits: AgentLimits) -> None:
        self.limits = limits
        self._buckets: dict[str, _UserBucket] = defaultdict(_UserBucket)
        self._lock = threading.Lock()

    def _get_bucket(self, user_id: str) -> _UserBucket:
        bucket = self._buckets[user_id]
        now = time.time()
        # Reset daily counters if past midnight UTC
        if now >= bucket.daily_reset_at:
            # Next midnight UTC
            import math

            day_seconds = 86400
            bucket.daily_reset_at = math.ceil(now / day_seconds) * day_seconds
            bucket.daily_requests = 0
            bucket.daily_tokens = 0
            bucket.daily_images = 0
            bucket.daily_cost_usd = 0.0
        return bucket

    # ── Pre-check: can the user make this request? ─────────────────

    def check_rate_limit(self, user_id: str) -> str | None:
        """Return an error message if rate-limited, else None."""
        with self._lock:
            bucket = self._get_bucket(user_id)
            now = time.time()

            # Sliding window (1 minute)
            cutoff = now - 60
            bucket.request_timestamps = [t for t in bucket.request_timestamps if t > cutoff]
            if len(bucket.request_timestamps) >= self.limits.max_requests_per_minute:
                return f"Rate limit exceeded: {self.limits.max_requests_per_minute} requests/minute"

            # Daily request cap
            if bucket.daily_requests >= self.limits.max_requests_per_day:
                return f"Daily request limit reached: {self.limits.max_requests_per_day}/day"

            return None

    def check_token_budget(self, user_id: str, estimated_tokens: int = 0) -> str | None:
        """Return an error message if token budget would be exceeded."""
        with self._lock:
            bucket = self._get_bucket(user_id)
            if bucket.daily_tokens + estimated_tokens > self.limits.max_tokens_per_day:
                return f"Daily token budget exceeded: {self.limits.max_tokens_per_day}/day"
            return None

    def check_image_budget(self, user_id: str) -> str | None:
        """Return error if image generation budget is exceeded."""
        with self._lock:
            bucket = self._get_bucket(user_id)
            if bucket.daily_images >= self.limits.max_image_generations_per_day:
                return f"Daily image limit reached: {self.limits.max_image_generations_per_day}/day"
            return None

    # ── Post-request: record usage ─────────────────────────────────

    def record_usage(self, record: UsageRecord) -> None:
        """Record a completed request's usage metrics."""
        with self._lock:
            bucket = self._get_bucket(record.user_id)
            now = time.time()

            bucket.request_timestamps.append(now)
            bucket.daily_requests += 1
            bucket.daily_tokens += record.total_tokens
            bucket.daily_cost_usd += record.estimated_cost_usd
            bucket.total_requests += 1
            bucket.total_tokens += record.total_tokens
            bucket.total_cost_usd += record.estimated_cost_usd
            bucket.records.append(record.to_dict())

            # Keep only last 1000 records in memory
            if len(bucket.records) > 1000:
                bucket.records = bucket.records[-500:]

        logger.info(
            "Usage: user=%s model=%s tokens=%d cost=$%.4f tools=%s",
            record.user_id,
            record.model,
            record.total_tokens,
            record.estimated_cost_usd,
            record.tools_used,
        )

    def record_image_generation(self, user_id: str, count: int = 1) -> None:
        """Record image generation usage."""
        with self._lock:
            bucket = self._get_bucket(user_id)
            bucket.daily_images += count

    # ── Query usage ────────────────────────────────────────────────

    def get_user_usage(self, user_id: str) -> dict[str, Any]:
        """Get current usage summary for a user."""
        with self._lock:
            bucket = self._get_bucket(user_id)
            return {
                "daily_requests": bucket.daily_requests,
                "daily_tokens": bucket.daily_tokens,
                "daily_images": bucket.daily_images,
                "daily_cost_usd": round(bucket.daily_cost_usd, 4),
                "total_requests": bucket.total_requests,
                "total_tokens": bucket.total_tokens,
                "total_cost_usd": round(bucket.total_cost_usd, 4),
                "limits": {
                    "max_requests_per_minute": self.limits.max_requests_per_minute,
                    "max_requests_per_day": self.limits.max_requests_per_day,
                    "max_tokens_per_day": self.limits.max_tokens_per_day,
                    "max_images_per_day": self.limits.max_image_generations_per_day,
                },
                "recent_records": bucket.records[-10:],
            }
