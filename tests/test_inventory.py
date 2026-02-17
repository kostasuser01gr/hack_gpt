"""Tests for Device Inventory & Network Ops module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from inventory.adapters.base import NormalisedClient
from inventory.adapters.manual_import import ManualImportAdapter
from inventory.config import InventoryConfig
from inventory.diff_engine import DiffEngine
from inventory.models import (
    CONSENT_VERSIONS,
    Alert,
    AuthorizedNetwork,
    Device,
    MaintenanceWindow,
    Observation,
)
from inventory.policy_engine import PolicyEngine
from inventory.privacy import hmac_device_key, mask_ip, mask_mac


# ===================================================================
# Privacy utilities
# ===================================================================
class TestPrivacy:
    def test_mask_mac(self):
        assert mask_mac("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:**:**:**"

    def test_mask_mac_dashes(self):
        assert mask_mac("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:**:**:**"

    def test_mask_mac_no_separator(self):
        assert mask_mac("AABBCCDDEEFF") == "AA:BB:CC:**:**:**"

    def test_mask_ip(self):
        assert mask_ip("192.168.1.42") == "192.168.1.***"

    def test_mask_ip_invalid(self):
        assert mask_ip("not-an-ip") == "***.***.***.***"

    def test_hmac_device_key_deterministic(self):
        k1 = hmac_device_key("AA:BB:CC:DD:EE:FF", "secret")
        k2 = hmac_device_key("AA:BB:CC:DD:EE:FF", "secret")
        assert k1 == k2
        assert len(k1) == 64  # SHA-256 hex

    def test_hmac_device_key_different_secrets(self):
        k1 = hmac_device_key("AA:BB:CC:DD:EE:FF", "secret1")
        k2 = hmac_device_key("AA:BB:CC:DD:EE:FF", "secret2")
        assert k1 != k2

    def test_hmac_normalises_mac(self):
        k1 = hmac_device_key("AA:BB:CC:DD:EE:FF", "s")
        k2 = hmac_device_key("aa-bb-cc-dd-ee-ff", "s")
        assert k1 == k2


# ===================================================================
# Config
# ===================================================================
class TestInventoryConfig:
    def test_defaults(self):
        cfg = InventoryConfig()
        assert cfg.enable_official_router_adapters is False
        assert cfg.enable_enforcement_actions is False
        assert cfg.observation_retention_days == 90

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("INVENTORY_ENABLE_ROUTER_ADAPTERS", "true")
        monkeypatch.setenv("INVENTORY_RETENTION_DAYS", "30")
        cfg = InventoryConfig.from_env()
        assert cfg.enable_official_router_adapters is True
        assert cfg.observation_retention_days == 30

    def test_from_env_defaults(self, monkeypatch):
        for key in ("INVENTORY_ENABLE_ROUTER_ADAPTERS", "INVENTORY_RETENTION_DAYS"):
            monkeypatch.delenv(key, raising=False)
        cfg = InventoryConfig.from_env()
        assert cfg.enable_official_router_adapters is False
        assert cfg.observation_retention_days == 90


# ===================================================================
# ManualImportAdapter
# ===================================================================
class TestManualImportAdapter:
    def test_capabilities(self):
        adapter = ManualImportAdapter()
        caps = adapter.capabilities()
        assert caps.supports_connected_clients is True
        assert caps.supports_block_client is False

    def test_parse_csv_basic(self):
        csv_data = b"mac,ip,hostname\nAA:BB:CC:DD:EE:FF,192.168.1.10,laptop\n11:22:33:44:55:66,10.0.0.5,phone\n"
        adapter = ManualImportAdapter()
        result = adapter.parse_file(csv_data, "devices.csv")
        assert result.success is True
        assert len(result.clients) == 2
        assert result.clients[0].mac == "AA:BB:CC:DD:EE:FF"
        assert result.clients[0].hostname == "laptop"

    def test_parse_csv_aliases(self):
        csv_data = b"mac_address,ip_address,host_name,manufacturer\nAA:BB:CC:DD:EE:FF,10.0.0.1,router,Cisco\n"
        adapter = ManualImportAdapter()
        result = adapter.parse_file(csv_data, "export.csv")
        assert result.success is True
        assert result.clients[0].vendor == "Cisco"

    def test_parse_csv_no_mac_column(self):
        csv_data = b"ip,hostname\n192.168.1.1,router\n"
        adapter = ManualImportAdapter()
        result = adapter.parse_file(csv_data, "bad.csv")
        assert result.success is False
        assert "MAC" in result.error

    def test_parse_csv_empty(self):
        adapter = ManualImportAdapter()
        result = adapter.parse_file(b"", "empty.csv")
        assert result.success is False

    def test_parse_json_array(self):
        data = json.dumps(
            [
                {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.1", "hostname": "test"},
                {"mac": "11:22:33:44:55:66"},
            ]
        ).encode()
        adapter = ManualImportAdapter()
        result = adapter.parse_file(data, "devices.json")
        assert result.success is True
        assert len(result.clients) == 2

    def test_parse_json_unifi_wrapper(self):
        data = json.dumps(
            {
                "data": [{"mac": "AA:BB:CC:DD:EE:FF", "ip": "10.0.0.1", "name": "unifi-device"}],
            }
        ).encode()
        adapter = ManualImportAdapter()
        result = adapter.parse_file(data, "unifi.json")
        assert result.success is True
        assert result.clients[0].mac == "AA:BB:CC:DD:EE:FF"

    def test_parse_json_not_array(self):
        data = json.dumps({"key": "value"}).encode()
        adapter = ManualImportAdapter()
        result = adapter.parse_file(data, "bad.json")
        assert result.success is False

    def test_parse_unsupported_extension(self):
        adapter = ManualImportAdapter()
        result = adapter.parse_file(b"data", "file.xml")
        assert result.success is False
        assert "Unsupported" in result.error

    def test_connection_type_normalisation(self):
        csv_data = b"mac,is_wired\nAA:BB:CC:DD:EE:FF,true\n11:22:33:44:55:66,wireless\n"
        adapter = ManualImportAdapter()
        result = adapter.parse_file(csv_data, "devices.csv")
        assert result.clients[0].connection_type == "ethernet"
        assert result.clients[1].connection_type == "wifi"


# ===================================================================
# DiffEngine
# ===================================================================
class TestDiffEngine:
    def _make_session(self):
        """Create an in-memory SQLAlchemy session with inventory tables."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from database.models import Base as RootBase

        engine = create_engine("sqlite:///:memory:")
        RootBase.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        return session_factory()

    def test_new_devices_created(self):
        s = self._make_session()
        cfg = InventoryConfig(hmac_secret="test-secret")
        diff = DiffEngine(cfg)

        clients = [
            NormalisedClient(mac="AA:BB:CC:DD:EE:FF", ip="192.168.1.1", hostname="laptop"),
            NormalisedClient(mac="11:22:33:44:55:66", ip="10.0.0.1"),
        ]

        stats = diff.process_clients(s, "ws1", "net1", clients, source="manual")
        s.commit()

        assert stats["devices_created"] == 2
        assert stats["observations_created"] == 2
        assert stats["alerts_created"] >= 2  # new_device + unapproved

        devices = s.query(Device).all()
        assert len(devices) == 2
        assert all(not d.approved for d in devices)

    def test_existing_device_updated(self):
        s = self._make_session()
        cfg = InventoryConfig(hmac_secret="test-secret")
        diff = DiffEngine(cfg)

        clients = [NormalisedClient(mac="AA:BB:CC:DD:EE:FF", ip="192.168.1.1")]

        # First pass
        diff.process_clients(s, "ws1", "net1", clients)
        s.commit()

        # Second pass
        stats = diff.process_clients(s, "ws1", "net1", clients)
        s.commit()

        assert stats["devices_created"] == 0
        assert stats["devices_updated"] == 1

    def test_alerts_deduped(self):
        s = self._make_session()
        cfg = InventoryConfig(hmac_secret="test-secret")
        diff = DiffEngine(cfg)

        clients = [NormalisedClient(mac="AA:BB:CC:DD:EE:FF")]

        diff.process_clients(s, "ws1", "net1", clients)
        s.commit()

        # Second import — alerts should be deduped
        stats = diff.process_clients(s, "ws1", "net1", clients)
        s.commit()

        assert stats["alerts_created"] == 0

    def test_maintenance_window_suppresses_alerts(self):
        s = self._make_session()
        cfg = InventoryConfig(hmac_secret="test-secret")
        diff = DiffEngine(cfg)

        now = datetime.now(tz=timezone.utc)
        mw = MaintenanceWindow(
            workspace_id="ws1",
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=1),
            suppress_alert_types=["new_device", "unapproved_device"],
            reason="Planned migration",
            created_by="admin",
        )
        s.add(mw)
        s.commit()

        clients = [NormalisedClient(mac="AA:BB:CC:DD:EE:FF")]
        stats = diff.process_clients(s, "ws1", "net1", clients)
        s.commit()

        assert stats["devices_created"] == 1
        assert stats["alerts_created"] == 0  # suppressed


# ===================================================================
# PolicyEngine
# ===================================================================
class TestPolicyEngine:
    def test_risk_score_unknown_unapproved(self):
        cfg = InventoryConfig()
        engine = PolicyEngine(cfg)
        dev = Device(category="unknown", approved=False, criticality="low")
        score = engine.calculate_risk_score(dev)
        assert score == cfg.risk_unknown_device_points + cfg.risk_unapproved_points

    def test_risk_score_approved_known(self):
        cfg = InventoryConfig()
        engine = PolicyEngine(cfg)
        dev = Device(category="laptop", approved=True, criticality="low")
        score = engine.calculate_risk_score(dev)
        assert score == 0

    def test_risk_level_from_score(self):
        assert PolicyEngine.risk_level_from_score(0) == "low"
        assert PolicyEngine.risk_level_from_score(29) == "low"
        assert PolicyEngine.risk_level_from_score(30) == "med"
        assert PolicyEngine.risk_level_from_score(59) == "med"
        assert PolicyEngine.risk_level_from_score(60) == "high"
        assert PolicyEngine.risk_level_from_score(100) == "high"

    def test_update_device_risk(self):
        cfg = InventoryConfig()
        engine = PolicyEngine(cfg)
        dev = Device(category="unknown", approved=False, criticality="low")
        engine.update_device_risk(dev)
        assert dev.risk_score > 0
        assert dev.risk_level in ("low", "med", "high")


# ===================================================================
# Consent
# ===================================================================
class TestConsent:
    def test_consent_text_exists(self):
        assert "1.0" in CONSENT_VERSIONS
        assert "authorization" in CONSENT_VERSIONS["1.0"].lower()


# ===================================================================
# API endpoints
# ===================================================================
class TestInventoryAPI:
    @pytest.fixture
    def client(self):
        import inventory.api as api_module

        app = Flask(__name__)
        app.config["TESTING"] = True
        api_module._config = None
        api_module._diff_engine = None
        api_module._policy_engine = None
        app.register_blueprint(api_module.inventory_bp)
        return app.test_client()

    def test_health(self, client):
        resp = client.get("/api/inventory/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["module"] == "inventory"
        assert "features" in data

    @patch("inventory.api._get_db_session")
    def test_list_networks(self, mock_session, client):
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=False)
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.all.return_value = []
        ctx.__enter__().query.return_value = mock_q
        mock_session.return_value = ctx
        resp = client.get("/api/inventory/networks?workspace_id=ws1")
        assert resp.status_code == 200

    def test_create_network_requires_admin(self, client):
        resp = client.post(
            "/api/inventory/networks",
            json={"name": "test", "consent_confirmed": True},
            headers={"X-User-ID": "u1", "X-User-Role": "viewer"},
        )
        assert resp.status_code == 403

    def test_create_network_requires_consent(self, client):
        resp = client.post(
            "/api/inventory/networks",
            json={"name": "test"},
            headers={"X-User-ID": "u1", "X-User-Role": "admin"},
        )
        assert resp.status_code == 400
        assert "consent" in resp.get_json()["error"].lower()

    def test_import_requires_admin(self, client):
        resp = client.post(
            "/api/inventory/networks/net1/import",
            headers={"X-User-ID": "u1", "X-User-Role": "viewer"},
        )
        assert resp.status_code == 403

    def test_import_requires_file(self, client):
        resp = client.post(
            "/api/inventory/networks/net1/import",
            headers={"X-User-ID": "u1", "X-User-Role": "admin"},
        )
        assert resp.status_code == 400

    def test_reveal_requires_admin(self, client):
        resp = client.post(
            "/api/inventory/devices/dev1/reveal",
            json={"reason": "incident investigation"},
            headers={"X-User-ID": "u1", "X-User-Role": "viewer"},
        )
        assert resp.status_code == 403

    def test_reveal_requires_reason(self, client):
        resp = client.post(
            "/api/inventory/devices/dev1/reveal",
            json={},
            headers={"X-User-ID": "u1", "X-User-Role": "admin"},
        )
        assert resp.status_code == 400
        assert "reason" in resp.get_json()["error"].lower()

    def test_approve_requires_admin(self, client):
        resp = client.post(
            "/api/inventory/devices/dev1/approve",
            json={"approved": True},
            headers={"X-User-ID": "u1", "X-User-Role": "viewer"},
        )
        assert resp.status_code == 403

    def test_create_policy_requires_admin(self, client):
        resp = client.post(
            "/api/inventory/policies",
            json={"name": "test rule"},
            headers={"X-User-ID": "u1", "X-User-Role": "viewer"},
        )
        assert resp.status_code == 403

    def test_audit_requires_admin(self, client):
        resp = client.get(
            "/api/inventory/audit",
            headers={"X-User-ID": "u1", "X-User-Role": "viewer"},
        )
        assert resp.status_code == 403

    def test_create_integration_bad_type(self, client):
        resp = client.post(
            "/api/inventory/integrations",
            json={"type": "carrier_pigeon"},
            headers={"X-User-ID": "u1", "X-User-Role": "admin"},
        )
        assert resp.status_code == 400

    def test_create_maintenance_missing_dates(self, client):
        resp = client.post(
            "/api/inventory/maintenance",
            json={"reason": "test"},
            headers={"X-User-ID": "u1", "X-User-Role": "admin"},
        )
        assert resp.status_code == 400


# ===================================================================
# End-to-end smoke test
# ===================================================================
class TestE2ESmoke:
    """Smoke test: manual import → devices appear → alerts generated."""

    def test_import_flow(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from database.models import Base as RootBase

        engine = create_engine("sqlite:///:memory:")
        RootBase.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        s = session_factory()

        # 1. Create network (simulating DB)
        net = AuthorizedNetwork(
            workspace_id="ws1",
            name="Office LAN",
            router_type="manual",
            consent_at=datetime.now(tz=timezone.utc),
            consent_text_version="1.0",
            consent_actor_user_id="admin1",
        )
        s.add(net)
        s.flush()

        # 2. Parse CSV import
        csv_data = b"mac,ip,hostname,vendor\nAA:BB:CC:DD:EE:FF,192.168.1.10,laptop-01,Dell\n11:22:33:44:55:66,192.168.1.20,printer-01,HP\n"
        adapter = ManualImportAdapter()
        result = adapter.parse_file(csv_data, "devices.csv")
        assert result.success
        assert len(result.clients) == 2

        # 3. Run diff engine
        cfg = InventoryConfig(hmac_secret="e2e-secret")
        diff = DiffEngine(cfg)
        diff.process_clients(s, "ws1", net.id, result.clients, source="manual")
        s.commit()

        # 4. Verify devices created
        devices = s.query(Device).filter(Device.workspace_id == "ws1").all()
        assert len(devices) == 2
        assert all(d.approved is False for d in devices)
        assert all(d.status == "active" for d in devices)

        # 5. Verify observations created
        obs = s.query(Observation).all()
        assert len(obs) == 2
        assert obs[0].mac_masked.endswith(":**:**:**")
        assert obs[0].ip_masked.endswith(".***")

        # 6. Verify alerts generated (new_device + unapproved_device per device)
        alerts = s.query(Alert).filter(Alert.workspace_id == "ws1").all()
        alert_types = {a.type for a in alerts}
        assert "new_device" in alert_types
        assert "unapproved_device" in alert_types
        assert all(a.status == "open" for a in alerts)

        # 7. Run policy engine → risk scores updated
        policy = PolicyEngine(cfg)
        policy_stats = policy.run_all_checks(s, "ws1", net.id)
        s.commit()
        assert policy_stats["risk_updated"] == 2

        for d in devices:
            s.refresh(d)
            assert d.risk_score > 0

        # 8. Approve a device → risk drops
        devices[0].approved = True
        devices[0].category = "laptop"
        policy.update_device_risk(devices[0])
        s.commit()
        assert devices[0].risk_score == 0

        s.close()
