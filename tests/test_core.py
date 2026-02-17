"""
HackGPT Core Unit Tests
Tests for import integrity, class instantiation, configuration,
input validation, rate limiting, and AI engine error handling.
"""

import importlib
import os
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------


class TestImports:
    """Verify that all core modules can be imported."""

    def test_hackgpt_v1_imports(self):
        """hackgpt.py exports HackGPT, AIEngine, ToolManager."""
        from hackgpt import AIEngine, HackGPT, ToolManager

        assert HackGPT is not None
        assert AIEngine is not None
        assert ToolManager is not None

    def test_hackgpt_v2_imports(self):
        """hackgpt_v2.py exports EnterpriseHackGPT."""
        from hackgpt_v2 import EnterpriseHackGPT

        assert EnterpriseHackGPT is not None

    @pytest.mark.parametrize(
        "module_name",
        [
            "database",
            "ai_engine",
            "security",
            "exploitation",
            "reporting",
            "cloud",
            "performance",
        ],
    )
    def test_submodule_importable(self, module_name):
        """Each sub-package should import without error."""
        mod = importlib.import_module(module_name)
        assert mod is not None

    def test_version_attribute(self):
        """hackgpt.py should expose __version__."""
        import hackgpt

        assert hasattr(hackgpt, "__version__")
        assert isinstance(hackgpt.__version__, str)
        assert hackgpt.__version__  # non-empty


# ---------------------------------------------------------------------------
# Configuration Tests
# ---------------------------------------------------------------------------


class TestConfigLoading:
    """Configuration should load safely with or without config.ini."""

    def test_config_class_instantiates(self):
        from hackgpt_v2 import Config

        cfg = Config()
        assert cfg is not None
        assert hasattr(cfg, "DATABASE_URL")
        assert hasattr(cfg, "SECRET_KEY")

    def test_config_debug_default(self):
        from hackgpt_v2 import Config

        cfg = Config()
        # Production default should be False
        assert cfg.DEBUG is False

    def test_config_log_level_default(self):
        from hackgpt_v2 import Config

        cfg = Config()
        assert cfg.LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


class TestInputValidator:
    """InputValidator should reject malicious / oversized input."""

    def test_valid_domain(self):
        from hackgpt import InputValidator

        ok, result = InputValidator.validate_target("example.com")
        assert ok is True
        assert result == "example.com"

    def test_valid_ip(self):
        from hackgpt import InputValidator

        ok, _result = InputValidator.validate_target("192.168.1.1")
        assert ok is True

    def test_valid_cidr(self):
        from hackgpt import InputValidator

        ok, _result = InputValidator.validate_target("10.0.0.0/24")
        assert ok is True

    def test_empty_target(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target("")
        assert ok is False

    def test_whitespace_target(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target("   ")
        assert ok is False

    def test_too_long_target(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target("a" * 300)
        assert ok is False

    def test_invalid_chars_target(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target("example.com; rm -rf /")
        assert ok is False

    def test_sql_injection_target(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target("' OR 1=1 --")
        assert ok is False

    def test_valid_scope(self):
        from hackgpt import InputValidator

        ok, result = InputValidator.validate_scope("Web application testing")
        assert ok is True
        assert result == "Web application testing"

    def test_empty_scope(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_scope("")
        assert ok is False

    def test_too_long_scope(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_scope("x" * 501)
        assert ok is False


# ---------------------------------------------------------------------------
# Rate Limiter Tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """RateLimiter should enforce request budgets."""

    def test_allows_within_limit(self):
        from hackgpt import RateLimiter

        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.allow("test") is True

    def test_blocks_over_limit(self):
        from hackgpt import RateLimiter

        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            rl.allow("test")
        assert rl.allow("test") is False

    def test_independent_keys(self):
        from hackgpt import RateLimiter

        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.allow("a")
        rl.allow("a")
        assert rl.allow("a") is False
        assert rl.allow("b") is True  # different key


# ---------------------------------------------------------------------------
# AI Engine Tests
# ---------------------------------------------------------------------------


class TestAIEngine:
    """AIEngine should instantiate without crashing."""

    @patch("hackgpt.subprocess.run")
    def test_ai_engine_local_mode(self, mock_run):
        """Without OPENAI_API_KEY, AIEngine falls back to local mode."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            from hackgpt import AIEngine

            ai = AIEngine()
            assert ai.local_mode is True
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key

    @patch("hackgpt.subprocess.run")
    def test_ai_engine_creates_prompt(self, mock_run):
        """Prompt creation should return a non-empty string."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from hackgpt import AIEngine

        ai = AIEngine()
        prompt = ai._create_prompt("test context", "test data", "recon")
        assert isinstance(prompt, str)
        assert "test context" in prompt
        assert "test data" in prompt

    @patch("hackgpt.subprocess.run")
    def test_ai_engine_rate_limited(self, mock_run):
        """analyze() should respect the rate limiter."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        from hackgpt import AIEngine, _rate_limiter

        ai = AIEngine()
        # Exhaust rate limit
        _rate_limiter._timestamps["ai_analyze"] = [time.monotonic() for _ in range(30)]
        result = ai.analyze("ctx", "data", "test")
        assert "Rate limit" in result
        # Cleanup
        _rate_limiter._timestamps.pop("ai_analyze", None)


# ---------------------------------------------------------------------------
# Tool Manager Tests
# ---------------------------------------------------------------------------


class TestToolManager:
    """ToolManager should instantiate and report tool status."""

    def test_tool_manager_instantiates(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        assert tm is not None
        assert isinstance(tm.installed_tools, set)

    def test_check_tool_returns_bool(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        # 'python3' should be available in the test environment
        result = tm.check_tool("python3")
        assert isinstance(result, bool)

    def test_run_command_returns_dict(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        result = tm.run_command("echo hello")
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "hello" in result["stdout"]

    def test_run_command_timeout(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        result = tm.run_command("sleep 10", timeout=1)
        assert result["success"] is False
        assert "timed out" in result["stderr"].lower()

    def test_run_command_with_pipe(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        result = tm.run_command("echo hello | tr a-z A-Z")
        assert result["success"] is True
        assert "HELLO" in result["stdout"]


# ---------------------------------------------------------------------------
# HackGPT Main Class Tests
# ---------------------------------------------------------------------------


class TestHackGPTClass:
    """Top-level HackGPT class instantiation."""

    @patch("hackgpt.subprocess.run")
    def test_hackgpt_instantiates(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from hackgpt import HackGPT

        hgpt = HackGPT()
        assert hgpt is not None
        assert hasattr(hgpt, "ai_engine")
        assert hasattr(hgpt, "tool_manager")

    @patch("hackgpt.subprocess.run")
    def test_hackgpt_has_show_banner(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from hackgpt import HackGPT

        hgpt = HackGPT()
        assert callable(getattr(hgpt, "show_banner", None))

    @patch("hackgpt.subprocess.run")
    def test_hackgpt_has_show_menu(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from hackgpt import HackGPT

        hgpt = HackGPT()
        assert callable(getattr(hgpt, "show_menu", None))
