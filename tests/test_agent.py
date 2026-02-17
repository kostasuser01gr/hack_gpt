"""HackGPT Agent Mode - Unit Tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestAgentConfig:
    def test_default_config(self):
        from agent.config import AgentConfig

        cfg = AgentConfig()
        assert cfg.default_model == "gpt-4o"
        assert cfg.enable_web_search is False
        assert cfg.enable_code_interpreter is False
        assert cfg.enable_file_search is False
        assert cfg.enable_image_generation is False

    def test_from_env(self, monkeypatch):
        from agent.config import AgentConfig

        monkeypatch.setenv("AGENT_ENABLE_WEB_SEARCH", "true")
        monkeypatch.setenv("AGENT_MODEL", "gpt-4.1-mini")
        monkeypatch.setenv("AGENT_RATE_LIMIT_RPM", "42")
        cfg = AgentConfig.from_env()
        assert cfg.enable_web_search is True
        assert cfg.default_model == "gpt-4.1-mini"
        assert cfg.limits.max_requests_per_minute == 42

    def test_from_env_defaults(self, monkeypatch):
        from agent.config import AgentConfig

        for key in (
            "AGENT_ENABLE_WEB_SEARCH",
            "AGENT_ENABLE_CODE_INTERPRETER",
            "AGENT_ENABLE_FILE_SEARCH",
            "AGENT_ENABLE_IMAGE_GENERATION",
            "AGENT_MODEL",
        ):
            monkeypatch.delenv(key, raising=False)
        cfg = AgentConfig.from_env()
        assert cfg.default_model == "gpt-4o"
        assert cfg.enable_web_search is False

    def test_limits_dataclass(self):
        from agent.config import AgentLimits

        lim = AgentLimits(max_requests_per_minute=5, max_requests_per_day=100)
        assert lim.max_requests_per_minute == 5
        assert lim.max_requests_per_day == 100
        assert lim.max_tokens_per_request == 16_384


class TestSchemas:
    def test_message_role_values(self):
        from agent.schemas import MessageRole

        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"

    def test_agent_message_defaults(self):
        from agent.schemas import AgentMessage, MessageRole

        msg = AgentMessage(role=MessageRole.USER, content="hello")
        assert msg.citations == []
        assert msg.images == []
        assert msg.tool_traces == []

    def test_conversation_creation(self):
        from agent.schemas import Conversation

        conv = Conversation(user_id="u1")
        assert conv.id
        assert conv.title == "New Chat"
        assert conv.pinned is False
        assert conv.archived is False
        assert conv.messages == []

    def test_estimate_cost(self):
        from agent.schemas import estimate_cost

        cost = estimate_cost("gpt-4o", 1000, 500)
        assert cost > 0

    def test_estimate_cost_unknown_model(self):
        from agent.schemas import estimate_cost

        cost = estimate_cost("no-such-model", 100, 50)
        assert cost > 0

    def test_workspace_creation(self):
        from agent.schemas import Workspace

        ws = Workspace(user_id="u1", name="test-ws")
        assert ws.id
        assert ws.files == []

    def test_usage_record_to_dict(self):
        from agent.schemas import UsageRecord

        rec = UsageRecord(
            user_id="u1", model="gpt-4o", input_tokens=100,
            output_tokens=50, total_tokens=150,
        )
        d = rec.to_dict()
        assert d["user_id"] == "u1"
        assert d["total_tokens"] == 150


class TestMetering:
    def test_record_and_query(self):
        from agent.config import AgentLimits
        from agent.metering import UsageMeter
        from agent.schemas import UsageRecord

        meter = UsageMeter(AgentLimits(max_requests_per_minute=100, max_requests_per_day=1000))
        rec = UsageRecord(
            user_id="u1", model="gpt-4o", input_tokens=100,
            output_tokens=50, total_tokens=150, estimated_cost_usd=0.001,
        )
        meter.record_usage(rec)
        usage = meter.get_user_usage("u1")
        assert usage["daily_requests"] == 1
        assert usage["daily_tokens"] == 150
        assert usage["daily_cost_usd"] > 0

    def test_rate_limit_check(self):
        from agent.config import AgentLimits
        from agent.metering import UsageMeter
        from agent.schemas import UsageRecord

        meter = UsageMeter(AgentLimits(max_requests_per_minute=2, max_requests_per_day=1000))
        assert meter.check_rate_limit("u1") is None
        meter.record_usage(UsageRecord(user_id="u1", model="gpt-4o", total_tokens=10))
        assert meter.check_rate_limit("u1") is None
        meter.record_usage(UsageRecord(user_id="u1", model="gpt-4o", total_tokens=10))
        result = meter.check_rate_limit("u1")
        assert result is not None
        assert "Rate limit" in result

    def test_token_budget_check(self):
        from agent.config import AgentLimits
        from agent.metering import UsageMeter
        from agent.schemas import UsageRecord

        meter = UsageMeter(AgentLimits(max_tokens_per_day=200))
        meter.record_usage(UsageRecord(user_id="u1", model="gpt-4o", total_tokens=180))
        result = meter.check_token_budget("u1", estimated_tokens=50)
        assert result is not None
        assert "token" in result.lower()

    def test_image_budget_check(self):
        from agent.config import AgentLimits
        from agent.metering import UsageMeter

        meter = UsageMeter(AgentLimits(max_image_generations_per_day=1))
        meter.record_image_generation("u1")
        result = meter.check_image_budget("u1")
        assert result is not None
        assert "image" in result.lower()

    def test_fresh_user_no_limits(self):
        from agent.config import AgentLimits
        from agent.metering import UsageMeter

        meter = UsageMeter(AgentLimits())
        usage = meter.get_user_usage("brand_new_user")
        assert usage["daily_requests"] == 0
        assert usage["total_requests"] == 0


class TestTools:
    def test_build_empty(self):
        from agent.config import AgentConfig
        from agent.tools import build_tool_list

        cfg = AgentConfig()
        tools = build_tool_list(cfg)
        assert tools == []

    def test_build_web_search(self):
        from agent.config import AgentConfig
        from agent.tools import build_tool_list

        cfg = AgentConfig(enable_web_search=True)
        tools = build_tool_list(cfg)
        assert any(t.get("type") == "web_search_preview" for t in tools)

    def test_build_code_interpreter(self):
        from agent.config import AgentConfig
        from agent.tools import build_tool_list

        cfg = AgentConfig(enable_code_interpreter=True)
        tools = build_tool_list(cfg)
        assert any(t.get("type") == "code_interpreter" for t in tools)

    def test_build_image_generation(self):
        from agent.config import AgentConfig
        from agent.tools import build_tool_list

        cfg = AgentConfig(enable_image_generation=True)
        tools = build_tool_list(cfg)
        assert any(t.get("type") == "image_generation" for t in tools)

    def test_override_disables_tool(self):
        from agent.config import AgentConfig
        from agent.tools import build_tool_list

        cfg = AgentConfig(enable_web_search=True, enable_code_interpreter=True)
        tools = build_tool_list(cfg, overrides={"web_search": False})
        types = [t.get("type") for t in tools]
        assert "web_search_preview" not in types
        assert "code_interpreter" in types

    def test_override_cannot_enable_disabled(self):
        from agent.config import AgentConfig
        from agent.tools import build_tool_list

        cfg = AgentConfig(enable_web_search=False)
        tools = build_tool_list(cfg, overrides={"web_search": True})
        assert tools == []

    def test_build_file_search_tool(self):
        from agent.tools import build_file_search_tool

        tool = build_file_search_tool(["vs_123", "vs_456"])
        assert tool["type"] == "file_search"
        assert len(tool["vector_store_ids"]) == 2

    def test_is_tool_allowed(self):
        from agent.tools import is_tool_allowed

        assert is_tool_allowed("web_search_preview") is True
        assert is_tool_allowed("code_interpreter") is True
        assert is_tool_allowed("evil_tool") is False


class TestVectorStoreManager:
    def _make_manager(self):
        from agent.config import AgentConfig
        from agent.vector_store import VectorStoreManager

        mock_client = MagicMock()
        cfg = AgentConfig()
        mgr = VectorStoreManager(cfg, mock_client)
        return mgr, mock_client

    def test_create_workspace(self):
        mgr, client = self._make_manager()
        mock_vs = MagicMock()
        mock_vs.id = "vs_abc123"
        client.create_vector_store.return_value = mock_vs
        ws = mgr.create_workspace("My Project", "u1")
        assert ws.name == "My Project"
        assert ws.vector_store_id == "vs_abc123"
        assert ws.user_id == "u1"

    def test_delete_workspace(self):
        mgr, client = self._make_manager()
        mock_vs = MagicMock()
        mock_vs.id = "vs_abc"
        client.create_vector_store.return_value = mock_vs
        ws = mgr.create_workspace("temp", "u1")
        mgr.delete_workspace(ws.id)
        client.delete_vector_store.assert_called_once_with("vs_abc")

    def test_upload_file_bad_extension(self):
        mgr, _ = self._make_manager()
        mock_vs = MagicMock()
        mock_vs.id = "vs_x"
        mgr.client.create_vector_store.return_value = mock_vs
        ws = mgr.create_workspace("ws", "u1")
        with pytest.raises(ValueError, match="not allowed"):
            mgr.upload_file(ws.id, b"data", "malware.exe")

    def test_list_workspaces_filters_by_user(self):
        mgr, client = self._make_manager()
        mock_vs = MagicMock()
        mock_vs.id = "vs_1"
        client.create_vector_store.return_value = mock_vs
        mgr.create_workspace("ws1", "u1")
        mock_vs2 = MagicMock()
        mock_vs2.id = "vs_2"
        client.create_vector_store.return_value = mock_vs2
        mgr.create_workspace("ws2", "u2")
        u1_ws = [w for w in mgr._workspaces.values() if w.user_id == "u1"]
        assert len(u1_ws) == 1

    def test_get_workspace(self):
        mgr, client = self._make_manager()
        mock_vs = MagicMock()
        mock_vs.id = "vs_1"
        client.create_vector_store.return_value = mock_vs
        ws = mgr.create_workspace("ws1", "u1")
        assert mgr.get_workspace(ws.id) is not None
        assert mgr.get_workspace("nonexistent") is None


class TestOrchestrator:
    def _make_orchestrator(self):
        from agent.config import AgentConfig
        from agent.orchestrator import AgentOrchestrator

        cfg = AgentConfig()
        with patch("agent.orchestrator.OpenAIClient"), \
             patch("agent.orchestrator.UsageMeter"):
            orch = AgentOrchestrator(cfg)
        return orch

    def test_list_conversations_empty(self):
        orch = self._make_orchestrator()
        assert orch.list_conversations("u1") == []

    def test_get_nonexistent_conversation(self):
        orch = self._make_orchestrator()
        assert orch.get_conversation("no-such-id") is None

    def test_delete_conversation(self):
        from agent.schemas import Conversation

        orch = self._make_orchestrator()
        conv = Conversation(user_id="u1")
        orch._conversations[conv.id] = conv
        assert orch.delete_conversation(conv.id) is True
        assert conv.id not in orch._conversations

    def test_delete_nonexistent(self):
        orch = self._make_orchestrator()
        assert orch.delete_conversation("nope") is False

    def test_pin_conversation(self):
        from agent.schemas import Conversation

        orch = self._make_orchestrator()
        conv = Conversation(user_id="u1")
        orch._conversations[conv.id] = conv
        orch.pin_conversation(conv.id, pinned=True)
        assert conv.pinned is True
        orch.pin_conversation(conv.id, pinned=False)
        assert conv.pinned is False

    def test_archive_conversation(self):
        from agent.schemas import Conversation

        orch = self._make_orchestrator()
        conv = Conversation(user_id="u1")
        orch._conversations[conv.id] = conv
        orch.archive_conversation(conv.id, archived=True)
        assert conv.archived is True

    def test_list_conversations_with_data(self):
        from agent.schemas import Conversation

        orch = self._make_orchestrator()
        c1 = Conversation(user_id="u1", title="Chat A")
        c2 = Conversation(user_id="u1", title="Chat B")
        c3 = Conversation(user_id="u2", title="Other")
        orch._conversations[c1.id] = c1
        orch._conversations[c2.id] = c2
        orch._conversations[c3.id] = c3
        convs = orch.list_conversations("u1")
        assert len(convs) == 2
        titles = {c["title"] for c in convs}
        assert titles == {"Chat A", "Chat B"}


class TestAgentAPI:
    @pytest.fixture()
    def client(self):
        import agent.api as api_module
        from flask import Flask
        from agent.api import agent_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        api_module._orchestrator = None
        api_module._vector_mgr = None
        api_module._config = None
        app.register_blueprint(agent_bp)
        return app.test_client()

    def test_health(self, client):
        resp = client.get("/api/agent/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "model" in data
        assert "features" in data

    @patch("agent.api._get_orchestrator")
    def test_conversations_list(self, mock_orch, client):
        mock_orch.return_value.list_conversations.return_value = []
        resp = client.get("/api/agent/conversations", headers={"X-User-ID": "u1"})
        assert resp.status_code == 200
        assert "conversations" in resp.get_json()

    @patch("agent.api._get_orchestrator")
    def test_conversation_not_found(self, mock_orch, client):
        mock_orch.return_value.get_conversation.return_value = None
        resp = client.get(
            "/api/agent/conversations/nonexistent",
            headers={"X-User-ID": "u1"},
        )
        assert resp.status_code == 404

    @patch("agent.api._get_orchestrator")
    def test_usage_endpoint(self, mock_orch, client):
        mock_orch.return_value.meter.get_user_usage.return_value = {
            "daily_requests": 5, "daily_tokens": 1000,
            "daily_cost_usd": 0.01, "total_requests": 10,
        }
        resp = client.get("/api/agent/usage", headers={"X-User-ID": "u1"})
        assert resp.status_code == 200
        assert "daily_requests" in resp.get_json()

    def test_chat_missing_message(self, client):
        resp = client.post(
            "/api/agent/chat", json={}, headers={"X-User-ID": "u1"},
        )
        assert resp.status_code == 400

    def test_chat_stream_missing_message(self, client):
        resp = client.post(
            "/api/agent/chat/stream", json={}, headers={"X-User-ID": "u1"},
        )
        assert resp.status_code == 400

    @patch("agent.api._get_vector_mgr")
    def test_workspaces_list(self, mock_mgr, client):
        mock_mgr.return_value.list_workspaces.return_value = []
        resp = client.get("/api/agent/workspaces", headers={"X-User-ID": "u1"})
        assert resp.status_code == 200

    @patch("agent.api._get_vector_mgr")
    def test_workspace_create(self, mock_mgr, client):
        from agent.schemas import Workspace

        ws = Workspace(user_id="u1", name="test-ws", vector_store_id="vs_x")
        mock_mgr.return_value.create_workspace.return_value = ws
        resp = client.post(
            "/api/agent/workspaces",
            json={"name": "test-ws"},
            headers={"X-User-ID": "u1"},
        )
        assert resp.status_code == 201

    @patch("agent.api._get_orchestrator")
    def test_delete_nonexistent_conversation(self, mock_orch, client):
        mock_orch.return_value.delete_conversation.return_value = False
        resp = client.delete(
            "/api/agent/conversations/nope",
            headers={"X-User-ID": "u1"},
        )
        assert resp.status_code == 404
