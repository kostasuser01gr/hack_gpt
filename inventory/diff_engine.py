"""Diff engine — syncs adapter results into Devices/Observations and raises alerts.

Responsibilities:
1. Normalise each client record to a stable ``device_key`` (HMAC of MAC).
2. Create or update ``Device`` rows.
3. Append ``Observation`` rows (timeline).
4. Generate ``Alert`` rows for new/unapproved devices (with dedup).
5. Respect ``MaintenanceWindow`` suppression.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from inventory.models import Alert, Device, MaintenanceWindow, Observation

if TYPE_CHECKING:
    from inventory.adapters.base import NormalisedClient
from inventory.privacy import hmac_device_key, mask_ip, mask_mac, sha256_short

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from inventory.config import InventoryConfig

logger = logging.getLogger(__name__)


class DiffEngine:
    """Processes adapter results and maintains device state + alerts."""

    def __init__(self, config: InventoryConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_clients(
        self,
        session: Session,
        workspace_id: str,
        network_id: str,
        clients: list[NormalisedClient],
        source: str = "manual",
    ) -> dict[str, Any]:
        """Process a batch of normalised clients.

        Returns a summary dict with counts of created/updated devices,
        new observations, and alerts raised.
        """
        now = datetime.now(tz=timezone.utc)
        stats: dict[str, int] = {
            "devices_created": 0,
            "devices_updated": 0,
            "observations_created": 0,
            "alerts_created": 0,
        }

        # Pre-fetch existing devices for this network
        existing_devices: dict[str, Device] = {}
        for dev in session.query(Device).filter(
            Device.workspace_id == workspace_id,
            Device.network_id == network_id,
        ):
            existing_devices[dev.device_key] = dev

        # Pre-fetch active maintenance windows
        active_mw = self._active_maintenance_windows(session, workspace_id, network_id, now)
        suppressed_types = set()
        for mw in active_mw:
            suppressed_types.update(mw.suppress_alert_types or [])

        for client in clients:
            device_key = hmac_device_key(client.mac, self.config.hmac_secret)
            masked_mac = mask_mac(client.mac)
            masked_ip = mask_ip(client.ip) if client.ip else ""

            device = existing_devices.get(device_key)
            is_new = device is None

            if is_new:
                device = Device(
                    workspace_id=workspace_id,
                    network_id=network_id,
                    device_key=device_key,
                    label=client.hostname or masked_mac,
                    category="unknown",
                    approved=False,
                    status="active",
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(device)
                session.flush()  # get id
                existing_devices[device_key] = device
                stats["devices_created"] += 1
            else:
                device.last_seen_at = now
                device.status = "active"
                stats["devices_updated"] += 1

            # Append observation
            obs = Observation(
                device_id=device.id,
                network_id=network_id,
                source=source,
                connection_type=client.connection_type,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
                ip_masked=masked_ip,
                mac_masked=masked_mac,
                vendor=client.vendor or None,
                hostname=client.hostname or None,
            )
            session.add(obs)
            stats["observations_created"] += 1

            # Alerts
            if is_new:
                alert = self._maybe_create_alert(
                    session,
                    workspace_id=workspace_id,
                    network_id=network_id,
                    device_id=device.id,
                    alert_type="new_device",
                    severity="med",
                    payload={"mac_masked": masked_mac, "hostname": client.hostname},
                    suppressed_types=suppressed_types,
                    now=now,
                )
                if alert:
                    stats["alerts_created"] += 1

            if not device.approved:
                alert = self._maybe_create_alert(
                    session,
                    workspace_id=workspace_id,
                    network_id=network_id,
                    device_id=device.id,
                    alert_type="unapproved_device",
                    severity="med",
                    payload={"mac_masked": masked_mac},
                    suppressed_types=suppressed_types,
                    now=now,
                )
                if alert:
                    stats["alerts_created"] += 1

        return stats

    # ------------------------------------------------------------------
    # Alert helpers
    # ------------------------------------------------------------------

    def _maybe_create_alert(
        self,
        session: Session,
        *,
        workspace_id: str,
        network_id: str,
        device_id: str,
        alert_type: str,
        severity: str,
        payload: dict[str, Any],
        suppressed_types: set[str],
        now: datetime,
    ) -> Alert | None:
        """Create an alert unless it's suppressed or deduped."""
        if alert_type in suppressed_types:
            return None

        dedup_key = sha256_short(f"{device_id}:{alert_type}")

        # Check for recent duplicate
        existing = (
            session.query(Alert)
            .filter(
                Alert.dedup_key == dedup_key,
                Alert.status.in_(["open", "ack"]),
            )
            .first()
        )
        if existing:
            return None

        alert = Alert(
            workspace_id=workspace_id,
            network_id=network_id,
            device_id=device_id,
            type=alert_type,
            severity=severity,
            status="open",
            payload=payload,
            dedup_key=dedup_key,
            created_at=now,
        )
        session.add(alert)
        return alert

    # ------------------------------------------------------------------
    # Maintenance window query
    # ------------------------------------------------------------------

    @staticmethod
    def _active_maintenance_windows(
        session: Session,
        workspace_id: str,
        network_id: str,
        now: datetime,
    ) -> list[MaintenanceWindow]:
        return (
            session.query(MaintenanceWindow)
            .filter(
                MaintenanceWindow.workspace_id == workspace_id,
                MaintenanceWindow.start_at <= now,
                MaintenanceWindow.end_at >= now,
                (MaintenanceWindow.network_id == network_id) | (MaintenanceWindow.network_id.is_(None)),
            )
            .all()
        )
