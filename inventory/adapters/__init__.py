"""Adapter interface and ManualImportAdapter for device inventory.

SAFETY CONTRACT:
- Adapters NEVER scan networks, discover routers, or guess IPs.
- Adapters ONLY read data from official router APIs (when explicitly
  configured by the user) or from user-provided CSV/JSON exports.
- ManualImportAdapter is the default and always available.
"""

from __future__ import annotations

from inventory.adapters.base import AdapterCapabilities, AdapterResult, BaseAdapter
from inventory.adapters.manual_import import ManualImportAdapter

__all__ = [
    "AdapterCapabilities",
    "AdapterResult",
    "BaseAdapter",
    "ManualImportAdapter",
]
