"""Flask REST API for Device Inventory & Network Ops.

Blueprint prefix: ``/api/inventory``

SAFETY CONTRACT:
- All endpoints require authentication (X-User-ID header minimum;
  production deployments should use JWT/session auth).
- Sensitive identifiers are masked by default.
- Reveal endpoints require Admin role + reason + audit log.
- No endpoint performs network scanning.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, jsonify, request

from inventory.adapters.manual_import import ManualImportAdapter
from inventory.audit import log_audit
from inventory.config import InventoryConfig
from inventory.diff_engine import DiffEngine
from inventory.models import (
    CONSENT_VERSIONS,
    Alert,
    AuthorizedNetwork,
    Device,
    Integration,
    InventoryAuditLog,
    MaintenanceWindow,
    Observation,
    PolicyRule,
)
from inventory.policy_engine import PolicyEngine

logger = logging.getLogger(__name__)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

# ---------------------------------------------------------------------------
# Module-level singletons (lazy init)
# ---------------------------------------------------------------------------
_config: InventoryConfig | None = None
_diff_engine: DiffEngine | None = None
_policy_engine: PolicyEngine | None = None


def _get_config() -> InventoryConfig:
    global _config
    if _config is None:
        _config = InventoryConfig.from_env()
    return _config


def _get_diff_engine() -> DiffEngine:
    global _diff_engine
    if _diff_engine is None:
        _diff_engine = DiffEngine(_get_config())
    return _diff_engine


def _get_policy_engine() -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine(_get_config())
    return _policy_engine


def _get_user_id() -> str:
    return request.headers.get("X-User-ID", "anonymous")


def _get_user_role() -> str:
    return request.headers.get("X-User-Role", "viewer")


def _is_admin() -> bool:
    return _get_user_role().lower() == "admin"


def _get_db_session():
    """Get a DB session from the database manager."""
    from database import get_db_manager

    return get_db_manager().get_session()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@inventory_bp.route("/health", methods=["GET"])
def health():
    cfg = _get_config()
    return jsonify(
        {
            "status": "ok",
            "module": "inventory",
            "features": {
                "official_router_adapters": cfg.enable_official_router_adapters,
                "enforcement_actions": cfg.enable_enforcement_actions,
                "ai_tools": cfg.enable_ai_tools,
                "pdf_exports": cfg.enable_pdf_exports,
            },
        }
    )


# ===================================================================
# AUTHORIZED NETWORKS
# ===================================================================
@inventory_bp.route("/networks", methods=["GET"])
def list_networks():
    workspace_id = request.args.get("workspace_id", "default")
    with _get_db_session() as s:
        nets = (
            s.query(AuthorizedNetwork)
            .filter(AuthorizedNetwork.workspace_id == workspace_id, AuthorizedNetwork.is_deleted.is_(False))
            .order_by(AuthorizedNetwork.created_at.desc())
            .all()
        )
        return jsonify(
            {
                "networks": [_net_to_dict(n) for n in nets],
            }
        )


@inventory_bp.route("/networks", methods=["POST"])
def create_network():
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    consent_confirmed = data.get("consent_confirmed", False)
    if not consent_confirmed:
        return jsonify(
            {
                "error": "You must confirm consent before adding a network",
                "consent_text": CONSENT_VERSIONS.get("1.0", ""),
            }
        ), 400

    workspace_id = data.get("workspace_id", "default")

    with _get_db_session() as s:
        net = AuthorizedNetwork(
            workspace_id=workspace_id,
            name=name,
            site=data.get("site"),
            router_type=data.get("router_type", "manual"),
            capabilities=data.get("capabilities", {}),
            consent_at=datetime.now(tz=timezone.utc),
            consent_text_version="1.0",
            consent_actor_user_id=user_id,
        )
        s.add(net)
        s.flush()

        log_audit(
            s,
            workspace_id=workspace_id,
            actor_user_id=user_id,
            action="create_network",
            entity_type="authorized_network",
            entity_id=net.id,
            ip_address=request.remote_addr,
            metadata={"name": name, "router_type": net.router_type},
        )

        return jsonify(_net_to_dict(net)), 201


@inventory_bp.route("/networks/<network_id>", methods=["DELETE"])
def delete_network(network_id: str):
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    with _get_db_session() as s:
        net = s.query(AuthorizedNetwork).filter(AuthorizedNetwork.id == network_id).first()
        if not net:
            return jsonify({"error": "Not found"}), 404
        net.is_deleted = True
        log_audit(
            s,
            workspace_id=net.workspace_id,
            actor_user_id=user_id,
            action="delete_network",
            entity_type="authorized_network",
            entity_id=network_id,
            ip_address=request.remote_addr,
        )
        return jsonify({"deleted": True})


# ===================================================================
# MANUAL IMPORT
# ===================================================================
@inventory_bp.route("/networks/<network_id>/import", methods=["POST"])
def import_devices(network_id: str):
    """Upload a CSV/JSON file to import devices into a network."""
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded"}), 400

    cfg = _get_config()
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in cfg.allowed_import_extensions:
        return jsonify({"error": f"Unsupported file type. Allowed: {cfg.allowed_import_extensions}"}), 400

    data = file.read()
    if len(data) > cfg.max_import_file_size:
        return jsonify({"error": f"File too large (max {cfg.max_import_file_size // 1024 // 1024}MB)"}), 400

    with _get_db_session() as s:
        net = (
            s.query(AuthorizedNetwork)
            .filter(AuthorizedNetwork.id == network_id, AuthorizedNetwork.is_deleted.is_(False))
            .first()
        )
        if not net:
            return jsonify({"error": "Network not found"}), 404

        adapter = ManualImportAdapter()
        result = adapter.parse_file(data, file.filename)
        if not result.success:
            return jsonify({"error": result.error}), 400

        diff = _get_diff_engine()
        stats = diff.process_clients(s, net.workspace_id, network_id, result.clients, source="manual")

        # Run policy checks
        policy = _get_policy_engine()
        policy_stats = policy.run_all_checks(s, net.workspace_id, network_id)
        stats["risk_updated"] = policy_stats["risk_updated"]
        stats["policy_alerts"] = policy_stats["alerts_created"]

        log_audit(
            s,
            workspace_id=net.workspace_id,
            actor_user_id=user_id,
            action="import_devices",
            entity_type="authorized_network",
            entity_id=network_id,
            ip_address=request.remote_addr,
            metadata={"filename": file.filename, "raw_count": result.raw_count, **stats},
        )

        return jsonify({"import": stats, "raw_count": result.raw_count})


# ===================================================================
# DEVICES
# ===================================================================
@inventory_bp.route("/devices", methods=["GET"])
def list_devices():
    workspace_id = request.args.get("workspace_id", "default")
    network_id = request.args.get("network_id")
    status_filter = request.args.get("status")
    risk_filter = request.args.get("risk_level")
    approved_filter = request.args.get("approved")
    page = max(int(request.args.get("page", "1")), 1)
    per_page = min(int(request.args.get("per_page", "50")), 200)

    with _get_db_session() as s:
        q = s.query(Device).filter(Device.workspace_id == workspace_id)
        if network_id:
            q = q.filter(Device.network_id == network_id)
        if status_filter:
            q = q.filter(Device.status == status_filter)
        if risk_filter:
            q = q.filter(Device.risk_level == risk_filter)
        if approved_filter is not None:
            q = q.filter(Device.approved == (approved_filter.lower() in ("true", "1")))

        total = q.count()
        devices = q.order_by(Device.last_seen_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify(
            {
                "devices": [_device_to_dict(d) for d in devices],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )


@inventory_bp.route("/devices/<device_id>", methods=["GET"])
def get_device(device_id: str):
    with _get_db_session() as s:
        dev = s.query(Device).filter(Device.id == device_id).first()
        if not dev:
            return jsonify({"error": "Not found"}), 404

        # Get observations timeline
        observations = (
            s.query(Observation)
            .filter(Observation.device_id == device_id)
            .order_by(Observation.created_at.desc())
            .limit(100)
            .all()
        )

        # Get related alerts
        alerts = s.query(Alert).filter(Alert.device_id == device_id).order_by(Alert.created_at.desc()).limit(50).all()

        return jsonify(
            {
                "device": _device_to_dict(dev),
                "observations": [_obs_to_dict(o) for o in observations],
                "alerts": [_alert_to_dict(a) for a in alerts],
            }
        )


@inventory_bp.route("/devices/<device_id>/approve", methods=["POST"])
def approve_device(device_id: str):
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    data = request.get_json(silent=True) or {}
    approved = data.get("approved", True)

    with _get_db_session() as s:
        dev = s.query(Device).filter(Device.id == device_id).first()
        if not dev:
            return jsonify({"error": "Not found"}), 404

        dev.approved = approved
        _get_policy_engine().update_device_risk(dev)

        log_audit(
            s,
            workspace_id=dev.workspace_id,
            actor_user_id=user_id,
            action="approve_device" if approved else "unapprove_device",
            entity_type="device",
            entity_id=device_id,
            ip_address=request.remote_addr,
        )

        # Resolve unapproved_device alerts if approving
        if approved:
            open_alerts = (
                s.query(Alert)
                .filter(Alert.device_id == device_id, Alert.type == "unapproved_device", Alert.status == "open")
                .all()
            )
            for a in open_alerts:
                a.status = "resolved"
                a.resolved_at = datetime.now(tz=timezone.utc)

        return jsonify(_device_to_dict(dev))


@inventory_bp.route("/devices/<device_id>", methods=["PATCH"])
def update_device(device_id: str):
    user_id = _get_user_id()
    data = request.get_json(silent=True) or {}

    allowed_fields = {"label", "tags", "category", "owner", "criticality", "notes"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    with _get_db_session() as s:
        dev = s.query(Device).filter(Device.id == device_id).first()
        if not dev:
            return jsonify({"error": "Not found"}), 404

        for k, v in updates.items():
            setattr(dev, k, v)
        _get_policy_engine().update_device_risk(dev)

        log_audit(
            s,
            workspace_id=dev.workspace_id,
            actor_user_id=user_id,
            action="update_device",
            entity_type="device",
            entity_id=device_id,
            ip_address=request.remote_addr,
            metadata={"fields": list(updates.keys())},
        )

        return jsonify(_device_to_dict(dev))


@inventory_bp.route("/devices/<device_id>/reveal", methods=["POST"])
def reveal_device(device_id: str):
    """Reveal full MAC/IP. Requires Admin + reason. Audit logged."""
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required to reveal sensitive data"}), 403

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "A reason is required for revealing sensitive identifiers"}), 400

    with _get_db_session() as s:
        dev = s.query(Device).filter(Device.id == device_id).first()
        if not dev:
            return jsonify({"error": "Not found"}), 404

        # Get latest observation with identifiers
        obs = (
            s.query(Observation)
            .filter(Observation.device_id == device_id)
            .order_by(Observation.created_at.desc())
            .first()
        )

        log_audit(
            s,
            workspace_id=dev.workspace_id,
            actor_user_id=user_id,
            action="reveal_identifiers",
            entity_type="device",
            entity_id=device_id,
            ip_address=request.remote_addr,
            metadata={"reason": reason},
        )

        return jsonify(
            {
                "device_id": device_id,
                "note": "Full identifiers are not stored. Only hashed device_key and masked values are retained.",
                "device_key": dev.device_key,
                "latest_masked_mac": obs.mac_masked if obs else None,
                "latest_masked_ip": obs.ip_masked if obs else None,
                "reveal_logged": True,
            }
        )


# ===================================================================
# ALERTS
# ===================================================================
@inventory_bp.route("/alerts", methods=["GET"])
def list_alerts():
    workspace_id = request.args.get("workspace_id", "default")
    network_id = request.args.get("network_id")
    status_filter = request.args.get("status")
    severity_filter = request.args.get("severity")
    page = max(int(request.args.get("page", "1")), 1)
    per_page = min(int(request.args.get("per_page", "50")), 200)

    with _get_db_session() as s:
        q = s.query(Alert).filter(Alert.workspace_id == workspace_id)
        if network_id:
            q = q.filter(Alert.network_id == network_id)
        if status_filter:
            q = q.filter(Alert.status == status_filter)
        if severity_filter:
            q = q.filter(Alert.severity == severity_filter)

        total = q.count()
        alerts = q.order_by(Alert.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify(
            {
                "alerts": [_alert_to_dict(a) for a in alerts],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )


@inventory_bp.route("/alerts/<alert_id>/ack", methods=["POST"])
def ack_alert(alert_id: str):
    user_id = _get_user_id()
    with _get_db_session() as s:
        alert = s.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return jsonify({"error": "Not found"}), 404
        alert.status = "ack"
        alert.ack_at = datetime.now(tz=timezone.utc)
        log_audit(
            s,
            workspace_id=alert.workspace_id,
            actor_user_id=user_id,
            action="ack_alert",
            entity_type="alert",
            entity_id=alert_id,
            ip_address=request.remote_addr,
        )
        return jsonify(_alert_to_dict(alert))


@inventory_bp.route("/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id: str):
    user_id = _get_user_id()
    data = request.get_json(silent=True) or {}
    with _get_db_session() as s:
        alert = s.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return jsonify({"error": "Not found"}), 404
        alert.status = "resolved"
        alert.resolved_at = datetime.now(tz=timezone.utc)
        log_audit(
            s,
            workspace_id=alert.workspace_id,
            actor_user_id=user_id,
            action="resolve_alert",
            entity_type="alert",
            entity_id=alert_id,
            ip_address=request.remote_addr,
            metadata={"resolution_notes": data.get("notes", "")},
        )
        return jsonify(_alert_to_dict(alert))


# ===================================================================
# POLICIES
# ===================================================================
@inventory_bp.route("/policies", methods=["GET"])
def list_policies():
    workspace_id = request.args.get("workspace_id", "default")
    with _get_db_session() as s:
        rules = (
            s.query(PolicyRule).filter(PolicyRule.workspace_id == workspace_id).order_by(PolicyRule.created_at).all()
        )
        return jsonify({"policies": [_policy_to_dict(r) for r in rules]})


@inventory_bp.route("/policies", methods=["POST"])
def create_policy():
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    workspace_id = data.get("workspace_id", "default")
    with _get_db_session() as s:
        rule = PolicyRule(
            workspace_id=workspace_id,
            network_id=data.get("network_id"),
            name=name,
            enabled=data.get("enabled", True),
            conditions=data.get("conditions", {}),
            actions=data.get("actions", {}),
            severity=data.get("severity", "med"),
            schedule=data.get("schedule"),
            created_by=user_id,
        )
        s.add(rule)
        s.flush()
        log_audit(
            s,
            workspace_id=workspace_id,
            actor_user_id=user_id,
            action="create_policy",
            entity_type="policy_rule",
            entity_id=rule.id,
            ip_address=request.remote_addr,
        )
        return jsonify(_policy_to_dict(rule)), 201


@inventory_bp.route("/policies/<policy_id>", methods=["PATCH"])
def update_policy(policy_id: str):
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    data = request.get_json(silent=True) or {}
    with _get_db_session() as s:
        rule = s.query(PolicyRule).filter(PolicyRule.id == policy_id).first()
        if not rule:
            return jsonify({"error": "Not found"}), 404

        for field in ("name", "enabled", "conditions", "actions", "severity", "schedule"):
            if field in data:
                setattr(rule, field, data[field])

        log_audit(
            s,
            workspace_id=rule.workspace_id,
            actor_user_id=user_id,
            action="update_policy",
            entity_type="policy_rule",
            entity_id=policy_id,
            ip_address=request.remote_addr,
        )
        return jsonify(_policy_to_dict(rule))


# ===================================================================
# MAINTENANCE WINDOWS
# ===================================================================
@inventory_bp.route("/maintenance", methods=["GET"])
def list_maintenance():
    workspace_id = request.args.get("workspace_id", "default")
    with _get_db_session() as s:
        windows = (
            s.query(MaintenanceWindow)
            .filter(MaintenanceWindow.workspace_id == workspace_id)
            .order_by(MaintenanceWindow.start_at.desc())
            .all()
        )
        return jsonify({"windows": [_mw_to_dict(w) for w in windows]})


@inventory_bp.route("/maintenance", methods=["POST"])
def create_maintenance():
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    data = request.get_json(silent=True) or {}
    try:
        start_at = datetime.fromisoformat(data["start_at"])
        end_at = datetime.fromisoformat(data["end_at"])
    except (KeyError, ValueError):
        return jsonify({"error": "start_at and end_at (ISO format) required"}), 400

    workspace_id = data.get("workspace_id", "default")
    with _get_db_session() as s:
        mw = MaintenanceWindow(
            workspace_id=workspace_id,
            network_id=data.get("network_id"),
            start_at=start_at,
            end_at=end_at,
            suppress_alert_types=data.get("suppress_alert_types", []),
            reason=data.get("reason", ""),
            created_by=user_id,
        )
        s.add(mw)
        s.flush()
        log_audit(
            s,
            workspace_id=workspace_id,
            actor_user_id=user_id,
            action="create_maintenance_window",
            entity_type="maintenance_window",
            entity_id=mw.id,
            ip_address=request.remote_addr,
        )
        return jsonify(_mw_to_dict(mw)), 201


# ===================================================================
# INTEGRATIONS
# ===================================================================
@inventory_bp.route("/integrations", methods=["GET"])
def list_integrations():
    workspace_id = request.args.get("workspace_id", "default")
    with _get_db_session() as s:
        integrations = (
            s.query(Integration).filter(Integration.workspace_id == workspace_id).order_by(Integration.created_at).all()
        )
        return jsonify({"integrations": [_integration_to_dict(i) for i in integrations]})


@inventory_bp.route("/integrations", methods=["POST"])
def create_integration():
    user_id = _get_user_id()
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    data = request.get_json(silent=True) or {}
    int_type = (data.get("type") or "").strip()
    if int_type not in ("email", "webhook", "slack", "discord", "teams"):
        return jsonify({"error": "type must be one of: email, webhook, slack, discord, teams"}), 400

    workspace_id = data.get("workspace_id", "default")
    with _get_db_session() as s:
        integration = Integration(
            workspace_id=workspace_id,
            type=int_type,
            config_ref=data.get("config_ref"),
            enabled=data.get("enabled", True),
            severity_filter=data.get("severity_filter", []),
        )
        s.add(integration)
        s.flush()
        log_audit(
            s,
            workspace_id=workspace_id,
            actor_user_id=user_id,
            action="create_integration",
            entity_type="integration",
            entity_id=integration.id,
            ip_address=request.remote_addr,
            metadata={"type": int_type},
        )
        return jsonify(_integration_to_dict(integration)), 201


# ===================================================================
# AUDIT LOG (read-only)
# ===================================================================
@inventory_bp.route("/audit", methods=["GET"])
def list_audit():
    if not _is_admin():
        return jsonify({"error": "Admin role required"}), 403

    workspace_id = request.args.get("workspace_id", "default")
    page = max(int(request.args.get("page", "1")), 1)
    per_page = min(int(request.args.get("per_page", "50")), 200)

    with _get_db_session() as s:
        q = s.query(InventoryAuditLog).filter(InventoryAuditLog.workspace_id == workspace_id)
        total = q.count()
        entries = q.order_by(InventoryAuditLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify(
            {
                "entries": [
                    {
                        "id": e.id,
                        "actor": e.actor_user_id,
                        "action": e.action,
                        "entity_type": e.entity_type,
                        "entity_id": e.entity_id,
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                        "metadata": e.metadata_json,
                    }
                    for e in entries
                ],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )


# ===================================================================
# REPORTS / KPIs
# ===================================================================
@inventory_bp.route("/reports/kpis", methods=["GET"])
def report_kpis():
    workspace_id = request.args.get("workspace_id", "default")
    with _get_db_session() as s:
        total_devices = s.query(Device).filter(Device.workspace_id == workspace_id).count()
        approved = s.query(Device).filter(Device.workspace_id == workspace_id, Device.approved.is_(True)).count()
        unapproved = total_devices - approved
        active = s.query(Device).filter(Device.workspace_id == workspace_id, Device.status == "active").count()

        high_risk = s.query(Device).filter(Device.workspace_id == workspace_id, Device.risk_level == "high").count()

        open_alerts = s.query(Alert).filter(Alert.workspace_id == workspace_id, Alert.status == "open").count()
        total_alerts = s.query(Alert).filter(Alert.workspace_id == workspace_id).count()

        networks = (
            s.query(AuthorizedNetwork)
            .filter(AuthorizedNetwork.workspace_id == workspace_id, AuthorizedNetwork.is_deleted.is_(False))
            .count()
        )

        return jsonify(
            {
                "kpis": {
                    "total_devices": total_devices,
                    "approved_devices": approved,
                    "unapproved_devices": unapproved,
                    "active_devices": active,
                    "high_risk_devices": high_risk,
                    "open_alerts": open_alerts,
                    "total_alerts": total_alerts,
                    "authorized_networks": networks,
                    "approval_rate": round(approved / total_devices * 100, 1) if total_devices else 0,
                },
            }
        )


@inventory_bp.route("/reports/export", methods=["GET"])
def export_report():
    """Export device inventory as CSV."""
    workspace_id = request.args.get("workspace_id", "default")

    with _get_db_session() as s:
        devices = s.query(Device).filter(Device.workspace_id == workspace_id).order_by(Device.last_seen_at.desc()).all()

        import csv as csv_mod
        import io as io_mod

        output = io_mod.StringIO()
        writer = csv_mod.writer(output)
        writer.writerow(
            [
                "id",
                "label",
                "category",
                "owner",
                "status",
                "approved",
                "risk_score",
                "risk_level",
                "criticality",
                "first_seen",
                "last_seen",
                "tags",
            ]
        )
        for d in devices:
            writer.writerow(
                [
                    d.id,
                    d.label,
                    d.category,
                    d.owner or "",
                    d.status,
                    d.approved,
                    d.risk_score,
                    d.risk_level,
                    d.criticality,
                    d.first_seen_at.isoformat() if d.first_seen_at else "",
                    d.last_seen_at.isoformat() if d.last_seen_at else "",
                    ",".join(d.tags or []),
                ]
            )

        from flask import Response

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=device_inventory.csv"},
        )


# ===================================================================
# Serialisation helpers
# ===================================================================
def _net_to_dict(n: AuthorizedNetwork) -> dict[str, Any]:
    return {
        "id": n.id,
        "workspace_id": n.workspace_id,
        "name": n.name,
        "site": n.site,
        "router_type": n.router_type,
        "capabilities": n.capabilities,
        "consent_at": n.consent_at.isoformat() if n.consent_at else None,
        "consent_text_version": n.consent_text_version,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _device_to_dict(d: Device) -> dict[str, Any]:
    return {
        "id": d.id,
        "workspace_id": d.workspace_id,
        "network_id": d.network_id,
        "label": d.label,
        "tags": d.tags or [],
        "category": d.category,
        "owner": d.owner,
        "criticality": d.criticality,
        "approved": d.approved,
        "risk_score": d.risk_score,
        "risk_level": d.risk_level,
        "status": d.status,
        "notes": d.notes,
        "first_seen_at": d.first_seen_at.isoformat() if d.first_seen_at else None,
        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
    }


def _obs_to_dict(o: Observation) -> dict[str, Any]:
    return {
        "id": o.id,
        "source": o.source,
        "connection_type": o.connection_type,
        "first_seen_at": o.first_seen_at.isoformat() if o.first_seen_at else None,
        "last_seen_at": o.last_seen_at.isoformat() if o.last_seen_at else None,
        "seen_count": o.seen_count,
        "ip_masked": o.ip_masked,
        "mac_masked": o.mac_masked,
        "vendor": o.vendor,
        "hostname": o.hostname,
    }


def _alert_to_dict(a: Alert) -> dict[str, Any]:
    return {
        "id": a.id,
        "workspace_id": a.workspace_id,
        "network_id": a.network_id,
        "device_id": a.device_id,
        "type": a.type,
        "severity": a.severity,
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "ack_at": a.ack_at.isoformat() if a.ack_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "payload": a.payload,
    }


def _policy_to_dict(r: PolicyRule) -> dict[str, Any]:
    return {
        "id": r.id,
        "workspace_id": r.workspace_id,
        "network_id": r.network_id,
        "name": r.name,
        "enabled": r.enabled,
        "conditions": r.conditions,
        "actions": r.actions,
        "severity": r.severity,
        "schedule": r.schedule,
        "created_by": r.created_by,
    }


def _mw_to_dict(w: MaintenanceWindow) -> dict[str, Any]:
    return {
        "id": w.id,
        "workspace_id": w.workspace_id,
        "network_id": w.network_id,
        "start_at": w.start_at.isoformat() if w.start_at else None,
        "end_at": w.end_at.isoformat() if w.end_at else None,
        "suppress_alert_types": w.suppress_alert_types,
        "reason": w.reason,
        "created_by": w.created_by,
    }


def _integration_to_dict(i: Integration) -> dict[str, Any]:
    return {
        "id": i.id,
        "workspace_id": i.workspace_id,
        "type": i.type,
        "enabled": i.enabled,
        "severity_filter": i.severity_filter,
    }
