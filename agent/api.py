"""Flask Blueprint for Agent Mode API endpoints.

All endpoints are prefixed with /api/agent/.
Provides: chat, streaming, conversations, workspaces, file uploads, usage.
"""

from __future__ import annotations

import json
import logging

from flask import Blueprint, Response, jsonify, request, stream_with_context

from agent.config import AgentConfig
from agent.openai_client import OpenAIClient
from agent.orchestrator import AgentOrchestrator
from agent.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")

# ── Module-level singletons (initialized on first request) ─────────
_orchestrator: AgentOrchestrator | None = None
_vector_mgr: VectorStoreManager | None = None
_config: AgentConfig | None = None


def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator, _config
    if _orchestrator is None:
        _config = AgentConfig.from_env()
        _orchestrator = AgentOrchestrator(_config)
    return _orchestrator


def _get_vector_mgr() -> VectorStoreManager:
    global _vector_mgr, _config
    if _vector_mgr is None:
        if _config is None:
            _config = AgentConfig.from_env()
        client = OpenAIClient(_config)
        _vector_mgr = VectorStoreManager(_config, client)
    return _vector_mgr


def _get_user_id() -> str:
    """Extract user ID from request (header, JWT, or default)."""
    return request.headers.get("X-User-ID", "anonymous")


# ── Health / Config ────────────────────────────────────────────────


@agent_bp.route("/health", methods=["GET"])
def agent_health() -> tuple[Response, int]:
    cfg = AgentConfig.from_env()
    return jsonify(
        {
            "status": "ok",
            "agent_mode": True,
            "features": {
                "web_search": cfg.enable_web_search,
                "file_search": cfg.enable_file_search,
                "code_interpreter": cfg.enable_code_interpreter,
                "image_generation": cfg.enable_image_generation,
                "realtime_voice": cfg.enable_realtime_voice,
                "memory": cfg.enable_memory,
            },
            "model": cfg.default_model,
        }
    ), 200


# ── Chat (blocking) ───────────────────────────────────────────────


@agent_bp.route("/chat", methods=["POST"])
def agent_chat() -> tuple[Response, int]:
    """Send a message and get a complete response (non-streaming)."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    orch = _get_orchestrator()
    user_id = _get_user_id()

    result = orch.run(
        message,
        user_id=user_id,
        conversation_id=data.get("conversation_id"),
        workspace_id=data.get("workspace_id"),
        tool_overrides=data.get("tools"),
    )

    return jsonify(
        {
            "message": result.to_dict(),
            "conversation_id": data.get("conversation_id") or result.id,
        }
    ), 200


# ── Chat (streaming via SSE) ──────────────────────────────────────


@agent_bp.route("/chat/stream", methods=["POST"])
def agent_chat_stream() -> Response:
    """Stream a response via Server-Sent Events (SSE)."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': 'message is required'})}\n\n",
            mimetype="text/event-stream",
            status=400,
        )

    orch = _get_orchestrator()
    user_id = _get_user_id()

    def generate():
        for chunk in orch.run_stream(
            message,
            user_id=user_id,
            conversation_id=data.get("conversation_id"),
            workspace_id=data.get("workspace_id"),
            tool_overrides=data.get("tools"),
        ):
            yield f"data: {json.dumps(chunk, default=str)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Conversations ──────────────────────────────────────────────────


@agent_bp.route("/conversations", methods=["GET"])
def list_conversations() -> tuple[Response, int]:
    user_id = _get_user_id()
    orch = _get_orchestrator()
    return jsonify({"conversations": orch.list_conversations(user_id)}), 200


@agent_bp.route("/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id: str) -> tuple[Response, int]:
    orch = _get_orchestrator()
    conv = orch.get_conversation(conv_id)
    if not conv:
        return jsonify({"error": "not found"}), 404
    return jsonify(conv.to_dict()), 200


@agent_bp.route("/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id: str) -> tuple[Response, int]:
    orch = _get_orchestrator()
    if orch.delete_conversation(conv_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


@agent_bp.route("/conversations/<conv_id>/pin", methods=["POST"])
def pin_conversation(conv_id: str) -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    orch = _get_orchestrator()
    if orch.pin_conversation(conv_id, data.get("pinned", True)):
        return jsonify({"ok": True}), 200
    return jsonify({"error": "not found"}), 404


@agent_bp.route("/conversations/<conv_id>/archive", methods=["POST"])
def archive_conversation(conv_id: str) -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    orch = _get_orchestrator()
    if orch.archive_conversation(conv_id, data.get("archived", True)):
        return jsonify({"ok": True}), 200
    return jsonify({"error": "not found"}), 404


# ── Workspaces ─────────────────────────────────────────────────────


@agent_bp.route("/workspaces", methods=["GET"])
def list_workspaces() -> tuple[Response, int]:
    user_id = _get_user_id()
    mgr = _get_vector_mgr()
    return jsonify({"workspaces": mgr.list_workspaces(user_id)}), 200


@agent_bp.route("/workspaces", methods=["POST"])
def create_workspace() -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    user_id = _get_user_id()
    mgr = _get_vector_mgr()

    try:
        ws = mgr.create_workspace(name, user_id)
        return jsonify(ws.to_dict()), 201
    except Exception as exc:
        logger.exception("Failed to create workspace")
        return jsonify({"error": str(exc)}), 500


@agent_bp.route("/workspaces/<ws_id>", methods=["DELETE"])
def delete_workspace(ws_id: str) -> tuple[Response, int]:
    mgr = _get_vector_mgr()
    if mgr.delete_workspace(ws_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


# ── File Uploads ───────────────────────────────────────────────────


@agent_bp.route("/workspaces/<ws_id>/files", methods=["GET"])
def list_files(ws_id: str) -> tuple[Response, int]:
    mgr = _get_vector_mgr()
    return jsonify({"files": mgr.list_files(ws_id)}), 200


@agent_bp.route("/workspaces/<ws_id>/files", methods=["POST"])
def upload_file(ws_id: str) -> tuple[Response, int]:
    if "file" not in request.files:
        return jsonify({"error": "file is required (multipart form)"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "filename is required"}), 400

    mgr = _get_vector_mgr()
    try:
        result = mgr.upload_file(ws_id, file.read(), file.filename)
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("File upload failed")
        return jsonify({"error": str(exc)}), 500


@agent_bp.route("/workspaces/<ws_id>/files/<file_id>", methods=["DELETE"])
def delete_file(ws_id: str, file_id: str) -> tuple[Response, int]:
    mgr = _get_vector_mgr()
    if mgr.delete_file(ws_id, file_id):
        return jsonify({"deleted": True}), 200
    return jsonify({"error": "not found"}), 404


# ── Usage / Metering ──────────────────────────────────────────────


@agent_bp.route("/usage", methods=["GET"])
def get_usage() -> tuple[Response, int]:
    user_id = _get_user_id()
    orch = _get_orchestrator()
    return jsonify(orch.meter.get_user_usage(user_id)), 200
