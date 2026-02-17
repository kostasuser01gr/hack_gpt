"""
HackGPT Configuration Tests
Tests for config.ini loading, environment variable overrides,
and default value correctness.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestConfigDefaults:
    """Config should have sane defaults even without config.ini."""

    def test_default_log_level(self):
        from hackgpt import Config

        cfg = Config(config_file="/tmp/_hackgpt_test_nonexistent_cfg.ini")
        assert cfg.LOG_LEVEL == "INFO"

    def test_default_max_workers(self):
        from hackgpt import Config

        cfg = Config(config_file="/tmp/_hackgpt_test_nonexistent_cfg.ini")
        assert cfg.MAX_WORKERS == 10

    def test_default_debug_false(self):
        from hackgpt import Config

        cfg = Config(config_file="/tmp/_hackgpt_test_nonexistent_cfg.ini")
        assert cfg.DEBUG is False


class TestConfigEnvOverride:
    """Environment variables should override config file values."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-123"})
    def test_openai_key_from_env(self):
        from hackgpt import Config

        cfg = Config(config_file="/tmp/_hackgpt_test_nonexistent_cfg.ini")
        assert cfg.OPENAI_API_KEY == "sk-test-key-123"

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@db:5432/test"})
    def test_database_url_from_env(self):
        from hackgpt import Config

        cfg = Config(config_file="/tmp/_hackgpt_test_nonexistent_cfg.ini")
        assert cfg.DATABASE_URL == "postgresql://test:test@db:5432/test"

    @patch.dict(os.environ, {"SECRET_KEY": "my-secret-override"})
    def test_secret_key_from_env(self):
        from hackgpt import Config

        cfg = Config(config_file="/tmp/_hackgpt_test_nonexistent_cfg.ini")
        assert cfg.SECRET_KEY == "my-secret-override"


class TestConfigFileCreation:
    """Config should create defaults when file doesn't exist."""

    def test_creates_default_config_file(self):
        with tempfile.NamedTemporaryFile(suffix=".ini", delete=True) as f:
            path = f.name  # file is deleted, path is free

        from hackgpt import Config

        Config(config_file=path)
        assert Path(path).exists()

        # Cleanup
        Path(path).unlink(missing_ok=True)
