"""Inventory audit logger – writes to inv_audit_logs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from inventory.models import InventoryAuditLog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def log_audit(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an audit record."""
    entry = InventoryAuditLog(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
    session.add(entry)
    logger.info(
        "AUDIT | user=%s action=%s entity=%s/%s",
        actor_user_id,
        action,
        entity_type,
        entity_id,
    )
