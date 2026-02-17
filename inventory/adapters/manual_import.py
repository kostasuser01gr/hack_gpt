"""ManualImportAdapter — parse user-provided CSV/JSON exports.

Supported formats:
- CSV with columns: mac, ip, hostname, vendor, connection_type (any subset)
- JSON array of objects with the same keys
- UniFi-style JSON export (``data`` key containing client list)
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

from inventory.adapters.base import (
    AdapterCapabilities,
    AdapterResult,
    BaseAdapter,
    NormalisedClient,
)

logger = logging.getLogger(__name__)

# Column aliases we recognise when parsing CSV/JSON
_MAC_ALIASES = {"mac", "mac_address", "macaddress", "hwaddr", "hardware_address", "mac-address"}
_IP_ALIASES = {"ip", "ip_address", "ipaddress", "ipaddr", "ip-address", "last_ip"}
_HOSTNAME_ALIASES = {"hostname", "host", "name", "device_name", "devicename", "host_name"}
_VENDOR_ALIASES = {"vendor", "manufacturer", "oui_manufacturer", "oui", "brand"}
_CONN_ALIASES = {"connection_type", "conn_type", "type", "interface", "network_type", "is_wired"}


class ManualImportAdapter(BaseAdapter):
    """Adapter that parses user-uploaded CSV/JSON device lists."""

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            supports_connected_clients=True,
            supports_dhcp_leases=False,
            supports_block_client=False,
            supports_guest_vlan=False,
        )

    def list_connected_clients(self, network_id: str) -> AdapterResult:
        """Not applicable for manual import — use ``parse_file`` instead."""
        return AdapterResult(success=False, error="Use parse_file() for manual imports")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_file(self, data: bytes, filename: str) -> AdapterResult:
        """Parse a CSV or JSON file and return normalised clients."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        try:
            if ext == "csv":
                return self._parse_csv(data)
            if ext == "json":
                return self._parse_json(data)
            return AdapterResult(success=False, error=f"Unsupported file type: .{ext}")
        except Exception as exc:
            logger.exception("Failed to parse import file %s", filename)
            return AdapterResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # CSV parser
    # ------------------------------------------------------------------

    def _parse_csv(self, data: bytes) -> AdapterResult:
        text = data.decode("utf-8-sig").strip()
        if not text:
            return AdapterResult(success=False, error="Empty CSV file")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return AdapterResult(success=False, error="CSV has no header row")

        lower_fields = {f.strip().lower(): f for f in reader.fieldnames}
        mac_col = self._find_column(lower_fields, _MAC_ALIASES)
        if not mac_col:
            return AdapterResult(
                success=False,
                error=f"CSV must contain a MAC address column. Found: {list(reader.fieldnames)}",
            )

        ip_col = self._find_column(lower_fields, _IP_ALIASES)
        host_col = self._find_column(lower_fields, _HOSTNAME_ALIASES)
        vendor_col = self._find_column(lower_fields, _VENDOR_ALIASES)
        conn_col = self._find_column(lower_fields, _CONN_ALIASES)

        clients: list[NormalisedClient] = []
        for row in reader:
            mac = (row.get(mac_col) or "").strip()
            if not mac:
                continue
            clients.append(
                NormalisedClient(
                    mac=mac,
                    ip=(row.get(ip_col) or "").strip() if ip_col else "",
                    hostname=(row.get(host_col) or "").strip() if host_col else "",
                    vendor=(row.get(vendor_col) or "").strip() if vendor_col else "",
                    connection_type=self._normalise_conn_type(
                        (row.get(conn_col) or "").strip() if conn_col else "",
                    ),
                ),
            )

        return AdapterResult(success=True, clients=clients, raw_count=len(clients))

    # ------------------------------------------------------------------
    # JSON parser
    # ------------------------------------------------------------------

    def _parse_json(self, data: bytes) -> AdapterResult:
        text = data.decode("utf-8-sig").strip()
        if not text:
            return AdapterResult(success=False, error="Empty JSON file")

        parsed = json.loads(text)

        # Handle UniFi-style wrapper: {"data": [...]}
        if isinstance(parsed, dict) and "data" in parsed and isinstance(parsed["data"], list):
            parsed = parsed["data"]

        if not isinstance(parsed, list):
            return AdapterResult(success=False, error="JSON must be an array of objects")

        clients: list[NormalisedClient] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            client = self._dict_to_client(item)
            if client:
                clients.append(client)

        return AdapterResult(success=True, clients=clients, raw_count=len(clients))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_column(lower_fields: dict[str, str], aliases: set[str]) -> str | None:
        for alias in aliases:
            if alias in lower_fields:
                return lower_fields[alias]
        return None

    @staticmethod
    def _dict_to_client(d: dict[str, Any]) -> NormalisedClient | None:
        lower = {k.strip().lower(): v for k, v in d.items()}
        mac = ""
        for alias in _MAC_ALIASES:
            if alias in lower:
                mac = str(lower[alias]).strip()
                break
        if not mac:
            return None

        ip = ""
        for alias in _IP_ALIASES:
            if alias in lower:
                ip = str(lower[alias]).strip()
                break

        hostname = ""
        for alias in _HOSTNAME_ALIASES:
            if alias in lower:
                hostname = str(lower[alias]).strip()
                break

        vendor = ""
        for alias in _VENDOR_ALIASES:
            if alias in lower:
                vendor = str(lower[alias]).strip()
                break

        conn = "unknown"
        for alias in _CONN_ALIASES:
            if alias in lower:
                raw = str(lower[alias]).strip()
                conn = ManualImportAdapter._normalise_conn_type(raw)
                break

        return NormalisedClient(mac=mac, ip=ip, hostname=hostname, vendor=vendor, connection_type=conn)

    @staticmethod
    def _normalise_conn_type(raw: str) -> str:
        low = raw.lower()
        if low in ("wifi", "wireless", "wlan", "802.11"):
            return "wifi"
        if low in ("ethernet", "wired", "lan", "eth", "true"):
            return "ethernet"
        return "unknown"
