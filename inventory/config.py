"""Inventory module configuration and feature flags."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class InventoryConfig:
    """Feature flags and configuration for inventory module."""

    # Feature flags
    enable_official_router_adapters: bool = False
    enable_enforcement_actions: bool = False
    enable_ai_tools: bool = False
    enable_pdf_exports: bool = False
    data_minimization_mode: bool = False

    # Retention
    observation_retention_days: int = 90

    # Privacy
    hmac_secret: str = ""

    # Rate limits
    max_syncs_per_hour: int = 10
    max_imports_per_hour: int = 20

    # Risk engine defaults
    risk_unknown_device_points: int = 30
    risk_unapproved_points: int = 25
    risk_odd_hours_points: int = 15
    risk_new_vendor_points: int = 10
    risk_critical_network_points: int = 20

    # Odd hours window (24h format)
    odd_hours_start: int = 22  # 10 PM
    odd_hours_end: int = 6  # 6 AM

    # Absence threshold
    absent_days_threshold: int = 30

    # Default alert dedup window (seconds)
    alert_dedup_window_seconds: int = 3600

    # Allowed import file extensions
    allowed_import_extensions: list[str] = field(
        default_factory=lambda: [".csv", ".json"],
    )

    # Max import file size (bytes)
    max_import_file_size: int = 10 * 1024 * 1024  # 10 MB

    @classmethod
    def from_env(cls) -> InventoryConfig:
        """Load configuration from environment variables."""

        def _bool(key: str, default: bool = False) -> bool:
            return os.getenv(key, str(default)).lower() in ("true", "1", "yes")

        def _int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default

        return cls(
            enable_official_router_adapters=_bool("INVENTORY_ENABLE_ROUTER_ADAPTERS"),
            enable_enforcement_actions=_bool("INVENTORY_ENABLE_ENFORCEMENT"),
            enable_ai_tools=_bool("INVENTORY_ENABLE_AI_TOOLS"),
            enable_pdf_exports=_bool("INVENTORY_ENABLE_PDF_EXPORTS"),
            data_minimization_mode=_bool("INVENTORY_DATA_MINIMIZATION"),
            observation_retention_days=_int("INVENTORY_RETENTION_DAYS", 90),
            hmac_secret=os.getenv("INVENTORY_HMAC_SECRET", os.getenv("SECRET_KEY", "change-me")),
            max_syncs_per_hour=_int("INVENTORY_MAX_SYNCS_HOUR", 10),
            max_imports_per_hour=_int("INVENTORY_MAX_IMPORTS_HOUR", 20),
            odd_hours_start=_int("INVENTORY_ODD_HOURS_START", 22),
            odd_hours_end=_int("INVENTORY_ODD_HOURS_END", 6),
            absent_days_threshold=_int("INVENTORY_ABSENT_DAYS", 30),
        )
