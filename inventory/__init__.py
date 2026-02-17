"""Device Inventory & Authorized Network Ops module.

Provides production-grade device inventory, policy/risk engine, alerts,
and audit-logged incident response for networks you own or administer.

SAFETY CONTRACT:
- Authorized networks only (explicit consent required)
- NO scanning, wardriving, packet capture, deauth, or brute forcing
- Data sources: router official APIs (read-only) or manual CSV/JSON imports
- Sensitive identifiers masked by default; reveal requires Admin + reason + audit log
"""

from __future__ import annotations

from inventory.api import inventory_bp
from inventory.config import InventoryConfig
from inventory.diff_engine import DiffEngine
from inventory.models import (
    Alert,
    AuthorizedNetwork,
    Device,
    Integration,
    MaintenanceWindow,
    Observation,
    PolicyRule,
)
from inventory.policy_engine import PolicyEngine

__all__ = [
    "Alert",
    "AuthorizedNetwork",
    "Device",
    "DiffEngine",
    "Integration",
    "InventoryConfig",
    "MaintenanceWindow",
    "Observation",
    "PolicyEngine",
    "PolicyRule",
    "inventory_bp",
]
