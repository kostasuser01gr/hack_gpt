"""Base adapter interface for network device polling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterCapabilities:
    """Declares what this adapter can do."""

    supports_connected_clients: bool = False
    supports_dhcp_leases: bool = False
    supports_block_client: bool = False
    supports_guest_vlan: bool = False


@dataclass
class NormalisedClient:
    """A single device record normalised from any adapter source."""

    mac: str  # raw (will be hashed/masked by the caller)
    ip: str = ""
    hostname: str = ""
    vendor: str = ""
    connection_type: str = "unknown"  # wifi | ethernet | unknown
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    """Return value from any adapter list operation."""

    success: bool
    clients: list[NormalisedClient] = field(default_factory=list)
    error: str = ""
    raw_count: int = 0


class BaseAdapter:
    """Abstract adapter.  Subclasses must implement at least ``capabilities`` and
    ``list_connected_clients``.
    """

    def capabilities(self) -> AdapterCapabilities:
        """Return what this adapter supports."""
        return AdapterCapabilities()

    def list_connected_clients(self, network_id: str) -> AdapterResult:
        """Fetch connected clients from the network source."""
        return AdapterResult(success=False, error="Not implemented")

    def list_dhcp_leases(self, network_id: str) -> AdapterResult:
        """Fetch DHCP leases (optional)."""
        return AdapterResult(success=False, error="Not implemented")
