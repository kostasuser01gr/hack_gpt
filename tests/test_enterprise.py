"""
HackGPT Enterprise Module Tests
Tests for database models, cloud managers, performance subsystem,
reporting engine, and security/authentication modules.
"""

import importlib
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------


class TestDatabaseModels:
    """Verify database models can be instantiated and have correct fields."""

    def test_base_model_exists(self):
        from database.models import Base

        assert Base is not None

    def test_pentest_session_model(self):
        from database.models import PentestSession

        assert hasattr(PentestSession, "__tablename__")
        assert PentestSession.__tablename__ == "pentest_sessions"

    def test_vulnerability_model(self):
        from database.models import Vulnerability

        assert hasattr(Vulnerability, "__tablename__")
        assert Vulnerability.__tablename__ == "vulnerabilities"

    def test_user_model(self):
        from database.models import User

        assert hasattr(User, "__tablename__")
        assert User.__tablename__ == "users"

    def test_audit_log_model(self):
        from database.models import AuditLog

        assert hasattr(AuditLog, "__tablename__")
        assert AuditLog.__tablename__ == "audit_logs"

    def test_configuration_model(self):
        from database.models import Configuration

        assert hasattr(Configuration, "__tablename__")
        assert Configuration.__tablename__ == "configurations"

    def test_ai_context_model(self):
        from database.models import AIContext

        assert hasattr(AIContext, "__tablename__")
        assert AIContext.__tablename__ == "ai_contexts"

    def test_phase_result_model(self):
        from database.models import PhaseResult

        assert hasattr(PhaseResult, "__tablename__")
        assert PhaseResult.__tablename__ == "phase_results"

    def test_attack_chain_model(self):
        from database.models import AttackChain

        assert hasattr(AttackChain, "__tablename__")
        assert AttackChain.__tablename__ == "attack_chains"


class TestDatabaseInit:
    """Database __init__ should export all public models."""

    def test_all_exports_present(self):
        import database

        expected = [
            "AIContext",
            "AttackChain",
            "AuditLog",
            "Base",
            "Configuration",
            "DatabaseManager",
            "PentestSession",
            "PhaseResult",
            "User",
            "Vulnerability",
            "get_db_manager",
            "init_database",
        ]
        for name in expected:
            assert hasattr(database, name), f"database module missing export: {name}"


# ---------------------------------------------------------------------------
# Performance Module
# ---------------------------------------------------------------------------


class TestPerformanceModule:
    """Performance subsystem imports and basic instantiation."""

    def test_cache_manager_importable(self):
        from performance.cache_manager import CacheManager

        assert CacheManager is not None

    def test_cache_manager_instantiates(self):
        from performance.cache_manager import CacheManager

        cm = CacheManager()
        assert cm is not None

    def test_performance_monitor_importable(self):
        from performance.performance_monitor import PerformanceMonitor

        assert PerformanceMonitor is not None

    def test_load_balancer_importable(self):
        from performance.load_balancer import LoadBalancer

        assert LoadBalancer is not None

    def test_optimization_importable(self):
        from performance.optimization import QueryOptimizer, ResourceOptimizer

        assert QueryOptimizer is not None
        assert ResourceOptimizer is not None


class TestCacheManagerOperations:
    """CacheManager basic get/set operations."""

    def test_memory_cache_set_get(self):
        from performance.cache_manager import CacheManager

        cm = CacheManager()
        cm.set("test_key", "test_value", l1_ttl=60)
        result = cm.get("test_key")
        assert result == "test_value"

    def test_memory_cache_missing_key(self):
        from performance.cache_manager import CacheManager

        cm = CacheManager()
        result = cm.get("nonexistent_key_xyz")
        assert result is None

    def test_memory_cache_delete(self):
        from performance.cache_manager import CacheManager

        cm = CacheManager()
        cm.set("del_key", "value")
        cm.delete("del_key")
        assert cm.get("del_key") is None


# ---------------------------------------------------------------------------
# Cloud Module
# ---------------------------------------------------------------------------


class TestCloudModule:
    """Cloud subsystem module imports."""

    def test_docker_manager_importable(self):
        from cloud.docker_manager import DockerManager

        assert DockerManager is not None

    def test_kubernetes_manager_importable(self):
        from cloud.kubernetes_manager import KubernetesManager

        assert KubernetesManager is not None

    def test_service_registry_importable(self):
        from cloud.service_registry import ServiceRegistry

        assert ServiceRegistry is not None

    def test_load_balancer_importable(self):
        from cloud.load_balancer import LoadBalancer

        assert LoadBalancer is not None


class TestServiceRegistry:
    """ServiceRegistry basic operations with memory backend."""

    def test_memory_registry_instantiates(self):
        from cloud.service_registry import ServiceRegistry

        sr = ServiceRegistry(backend="memory")
        assert sr is not None

    def test_register_service(self):
        from cloud.service_registry import ServiceInstance, ServiceRegistry

        sr = ServiceRegistry(backend="memory")
        svc = ServiceInstance(
            service_name="test-svc",
            instance_id="inst-1",
            host="localhost",
            port=8080,
        )
        result = sr.register_service(svc)
        assert result is True

    def test_discover_registered_service(self):
        from cloud.service_registry import ServiceInstance, ServiceRegistry

        sr = ServiceRegistry(backend="memory")
        svc = ServiceInstance(
            service_name="my-svc",
            instance_id="inst-2",
            host="127.0.0.1",
            port=9090,
        )
        sr.register_service(svc)
        instances = sr.discover_services("my-svc", healthy_only=False)
        assert len(instances) > 0

    def test_deregister_service(self):
        from cloud.service_registry import ServiceInstance, ServiceRegistry

        sr = ServiceRegistry(backend="memory")
        svc = ServiceInstance(
            service_name="rm-svc",
            instance_id="inst-3",
            host="localhost",
            port=7070,
        )
        sr.register_service(svc)
        sr.deregister_service("rm-svc", "inst-3")
        instances = sr.discover_services("rm-svc", healthy_only=False)
        assert len(instances) == 0


# ---------------------------------------------------------------------------
# Reporting Module
# ---------------------------------------------------------------------------


class TestReportingModule:
    """Reporting module imports and instantiation."""

    def test_dynamic_reports_importable(self):
        mod = importlib.import_module("reporting.dynamic_reports")
        assert hasattr(mod, "DynamicReportGenerator")

    def test_realtime_dashboard_importable(self):
        mod = importlib.import_module("reporting.realtime_dashboard")
        assert mod is not None


# ---------------------------------------------------------------------------
# Security / Authentication Module
# ---------------------------------------------------------------------------


class TestSecurityModule:
    """Security module imports and basic auth operations."""

    def test_auth_module_importable(self):
        from security.authentication import EnterpriseAuth, LocalAuthenticator

        assert EnterpriseAuth is not None
        assert LocalAuthenticator is not None

    def test_compliance_module_importable(self):
        from security.compliance import ComplianceFrameworkMapper

        assert ComplianceFrameworkMapper is not None

    def test_local_authenticator_instantiates(self):

        from security.authentication import LocalAuthenticator

        with patch("security.authentication.get_db_manager"):
            auth = LocalAuthenticator()
            assert auth is not None
            assert hasattr(auth, "authenticate")


# ---------------------------------------------------------------------------
# Exploitation Module
# ---------------------------------------------------------------------------


class TestExploitationModule:
    """Exploitation subsystem imports."""

    def test_advanced_engine_importable(self):
        from exploitation.advanced_engine import AdvancedExploitationEngine

        assert AdvancedExploitationEngine is not None

    def test_zero_day_detector_importable(self):
        from exploitation.zero_day_detector import ZeroDayDetector

        assert ZeroDayDetector is not None


# ---------------------------------------------------------------------------
# AI Engine Module
# ---------------------------------------------------------------------------


class TestAIEngineModule:
    """AI engine advanced module."""

    def test_advanced_engine_importable(self):
        from ai_engine.advanced_engine import AdvancedAIEngine

        assert AdvancedAIEngine is not None


# ---------------------------------------------------------------------------
# HackGPT v2 Enterprise
# ---------------------------------------------------------------------------


class TestEnterpriseHackGPT:
    """Enterprise version instantiation and configuration."""

    def test_enterprise_config(self):
        from hackgpt_v2 import Config

        cfg = Config()
        assert hasattr(cfg, "DATABASE_URL")
        assert hasattr(cfg, "REDIS_URL")
        assert hasattr(cfg, "DOCKER_HOST")
        assert hasattr(cfg, "KUBERNETES_CONFIG")
        assert hasattr(cfg, "SERVICE_REGISTRY_BACKEND")

    def test_enterprise_has_all_features(self):
        """EnterpriseHackGPT should have key enterprise methods."""
        from hackgpt_v2 import EnterpriseHackGPT

        assert hasattr(EnterpriseHackGPT, "run")
        assert hasattr(EnterpriseHackGPT, "show_banner")

    def test_version_string_format(self):
        """Version should follow semver."""
        from hackgpt import __version__

        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
