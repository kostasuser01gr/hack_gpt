"""Agent tool registry – declares which tools are available and builds tool specs."""

from __future__ import annotations

from typing import Any

from agent.config import AgentConfig


def build_tool_list(config: AgentConfig, *, overrides: dict[str, bool] | None = None) -> list[dict[str, Any]]:
    """Build the tool list for the OpenAI Responses API based on config flags.

    Each tool is either a *built-in* tool (web_search, file_search, code_interpreter,
    image_generation) or a *function* tool (custom pentest tools).

    Args:
        config: Agent configuration with feature flags.
        overrides: Per-conversation overrides (e.g. {"web_search": False}).

    Returns:
        List of tool specifications suitable for the Responses API ``tools`` param.
    """
    tools: list[dict[str, Any]] = []
    flags = _resolve_flags(config, overrides)

    if flags.get("web_search"):
        tools.append({"type": "web_search_preview"})

    if flags.get("code_interpreter"):
        tools.append(
            {
                "type": "code_interpreter",
                "container": {"type": "auto"},
            }
        )

    if flags.get("image_generation"):
        tools.append(
            {
                "type": "image_generation",
                "quality": config.image_quality,
                "size": config.image_size,
            }
        )

    # file_search is added dynamically when a vector_store_id is present
    # (see orchestrator.py – it appends file_search with the store ID)

    return tools


def build_file_search_tool(vector_store_ids: list[str]) -> dict[str, Any]:
    """Build a file_search tool spec with specific vector store IDs."""
    return {
        "type": "file_search",
        "vector_store_ids": vector_store_ids,
    }


# ── Allowed tools (security allowlist) ─────────────────────────────

ALLOWED_BUILTIN_TOOLS = frozenset(
    {
        "web_search_preview",
        "file_search",
        "code_interpreter",
        "image_generation",
    }
)


def is_tool_allowed(tool_type: str) -> bool:
    """Check if a tool type is in the security allowlist."""
    return tool_type in ALLOWED_BUILTIN_TOOLS


# ── Internal helpers ───────────────────────────────────────────────


def _resolve_flags(config: AgentConfig, overrides: dict[str, bool] | None) -> dict[str, bool]:
    """Merge config flags with per-conversation overrides."""
    flags = {
        "web_search": config.enable_web_search,
        "file_search": config.enable_file_search,
        "code_interpreter": config.enable_code_interpreter,
        "image_generation": config.enable_image_generation,
    }
    if overrides:
        for key, value in overrides.items():
            if key in flags:
                # Override can only *disable*, never enable a globally-disabled tool
                if not flags[key]:
                    continue
                flags[key] = value
    return flags
