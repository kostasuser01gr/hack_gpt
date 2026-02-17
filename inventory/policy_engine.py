"""Policy & risk engine — evaluates rules and calculates device risk scores."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from inventory.models import Alert, Device
from inventory.privacy import sha256_short

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from inventory.config import InventoryConfig

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluates policy rules against device inventory and generates alerts."""

    def __init__(self, config: InventoryConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Risk score
    # ------------------------------------------------------------------

    def calculate_risk_score(self, device: Device) -> int:
        """Calculate a 0-100 risk score based on device attributes."""
        score = 0
        if device.category == "unknown":
            score += self.config.risk_unknown_device_points
        if not device.approved:
            score += self.config.risk_unapproved_points
        if device.criticality == "high":
            score += self.config.risk_critical_network_points
        return min(score, 100)

    @staticmethod
    def risk_level_from_score(score: int) -> str:
        if score >= 60:
            return "high"
        if score >= 30:
            return "med"
        return "low"

    def update_device_risk(self, device: Device) -> None:
        """Recalculate and set risk_score + risk_level on a device."""
        device.risk_score = self.calculate_risk_score(device)
        device.risk_level = self.risk_level_from_score(device.risk_score)

    # ------------------------------------------------------------------
    # Built-in policy checks
    # ------------------------------------------------------------------

    def check_odd_hours(
        self,
        session: Session,
        device: Device,
        *,
        workspace_id: str,
        network_id: str,
        now: datetime | None = None,
    ) -> Alert | None:
        """Alert if device is seen during odd hours."""
        now = now or datetime.now(tz=timezone.utc)
        hour = now.hour
        start = self.config.odd_hours_start
        end = self.config.odd_hours_end

        in_odd = (start > end and (hour >= start or hour < end)) or (start <= end and start <= hour < end)
        if not in_odd:
            return None

        dedup_key = sha256_short(f"{device.id}:odd_hours:{now.date().isoformat()}")
        existing = session.query(Alert).filter(Alert.dedup_key == dedup_key, Alert.status.in_(["open", "ack"])).first()
        if existing:
            return None

        alert = Alert(
            workspace_id=workspace_id,
            network_id=network_id,
            device_id=device.id,
            type="odd_hours",
            severity="low",
            payload={"hour": hour, "device_label": device.label},
            dedup_key=dedup_key,
            created_at=now,
        )
        session.add(alert)
        return alert

    def check_long_absent(
        self,
        session: Session,
        device: Device,
        *,
        workspace_id: str,
        network_id: str,
        now: datetime | None = None,
    ) -> Alert | None:
        """Mark device inactive and alert if not seen for threshold days."""
        now = now or datetime.now(tz=timezone.utc)
        if not device.last_seen_at:
            return None

        last_seen = device.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        days_absent = (now - last_seen).days
        if days_absent < self.config.absent_days_threshold:
            return None

        device.status = "inactive"

        dedup_key = sha256_short(f"{device.id}:long_absent")
        existing = session.query(Alert).filter(Alert.dedup_key == dedup_key, Alert.status.in_(["open", "ack"])).first()
        if existing:
            return None

        alert = Alert(
            workspace_id=workspace_id,
            network_id=network_id,
            device_id=device.id,
            type="long_absent",
            severity="info",
            payload={"days_absent": days_absent, "device_label": device.label},
            dedup_key=dedup_key,
            created_at=now,
        )
        session.add(alert)
        return alert

    def run_all_checks(
        self,
        session: Session,
        workspace_id: str,
        network_id: str,
        devices: list[Device] | None = None,
    ) -> dict[str, Any]:
        """Run all built-in policy checks for a network's devices."""
        now = datetime.now(tz=timezone.utc)
        if devices is None:
            devices = (
                session.query(Device).filter(Device.workspace_id == workspace_id, Device.network_id == network_id).all()
            )

        stats = {"risk_updated": 0, "alerts_created": 0}

        for dev in devices:
            self.update_device_risk(dev)
            stats["risk_updated"] += 1

            if self.check_odd_hours(session, dev, workspace_id=workspace_id, network_id=network_id, now=now):
                stats["alerts_created"] += 1

            if self.check_long_absent(session, dev, workspace_id=workspace_id, network_id=network_id, now=now):
                stats["alerts_created"] += 1

        return stats
