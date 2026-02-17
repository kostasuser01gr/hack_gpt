"""Data models for Agent Mode: messages, tool traces, usage records."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Citation:
    """A single source citation from web_search."""

    title: str
    url: str
    snippet: str = ""


@dataclass
class ImageResult:
    """Generated or edited image result."""

    url: str | None = None
    b64_data: str | None = None
    revised_prompt: str = ""


@dataclass
class CodeOutput:
    """Output from code_interpreter execution."""

    code: str = ""
    stdout: str = ""
    stderr: str = ""
    files: list[dict[str, str]] = field(default_factory=list)  # [{name, url}]


@dataclass
class ToolTrace:
    """Audit record of a single tool invocation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    tool_type: str = ""  # builtin | function
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    status: ToolStatus = ToolStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "arguments": self.arguments,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AgentMessage:
    """A single message in the agent conversation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Rich content produced by tools
    citations: list[Citation] = field(default_factory=list)
    images: list[ImageResult] = field(default_factory=list)
    code_outputs: list[CodeOutput] = field(default_factory=list)

    # Tool traces for this message (audit / debugging)
    tool_traces: list[ToolTrace] = field(default_factory=list)

    # Metadata
    model: str = ""
    tokens_used: int = 0
    attachments: list[dict[str, str]] = field(default_factory=list)  # [{name, type, url}]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "citations": [{"title": c.title, "url": c.url, "snippet": c.snippet} for c in self.citations],
            "images": [{"url": i.url, "revised_prompt": i.revised_prompt} for i in self.images],
            "code_outputs": [
                {"code": co.code, "stdout": co.stdout, "stderr": co.stderr, "files": co.files}
                for co in self.code_outputs
            ],
            "tool_traces": [t.to_dict() for t in self.tool_traces],
            "model": self.model,
            "tokens_used": self.tokens_used,
            "attachments": self.attachments,
        }


@dataclass
class Conversation:
    """Full conversation state."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    workspace_id: str | None = None
    user_id: str = ""
    messages: list[AgentMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    pinned: bool = False
    archived: bool = False

    # Tool configuration overrides per conversation
    tools_enabled: dict[str, bool] = field(default_factory=dict)

    # Vector store association (for file_search)
    vector_store_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "pinned": self.pinned,
            "archived": self.archived,
            "tools_enabled": self.tools_enabled,
            "vector_store_id": self.vector_store_id,
        }


@dataclass
class UsageRecord:
    """Single usage event for metering and billing."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    conversation_id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tools_used: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tools_used": self.tools_used,
            "estimated_cost_usd": self.estimated_cost_usd,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Workspace:
    """Project workspace with its own knowledge base and settings."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default"
    user_id: str = ""
    vector_store_id: str | None = None
    files: list[dict[str, str]] = field(default_factory=list)  # [{id, name, size, status}]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "vector_store_id": self.vector_store_id,
            "files": self.files,
            "created_at": self.created_at.isoformat(),
        }


# ── Cost estimation (USD per 1K tokens, approximate) ────────────────
MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4.1": {"input": 0.002, "output": 0.008},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "gpt-4.1-nano": {"input": 0.0001, "output": 0.0004},
    "o4-mini": {"input": 0.0011, "output": 0.0044},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given model and token counts."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS.get("gpt-4o", {"input": 0.005, "output": 0.015}))
    return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])
