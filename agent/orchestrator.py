"""Agent orchestrator – runs the tool-calling loop until a final assistant message.

Uses the OpenAI Responses API. The loop:
1. Send user message + tools → get response
2. If response contains tool calls → execute them, feed results back
3. Repeat until the model produces a final text output
4. Collect citations, images, code outputs, and tool traces
"""

from __future__ import annotations

import logging
import time
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from agent.config import AgentConfig
from agent.metering import UsageMeter
from agent.openai_client import OpenAIClient
from agent.schemas import (
    AgentMessage,
    Citation,
    CodeOutput,
    Conversation,
    ImageResult,
    MessageRole,
    ToolStatus,
    ToolTrace,
    UsageRecord,
    estimate_cost,
)
from agent.tools import build_file_search_tool, build_tool_list

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Runs agent conversations with tool-calling support.

    Typical usage::

        config = AgentConfig.from_env()
        agent = AgentOrchestrator(config)
        response = agent.run("What vulnerabilities exist in log4j?", user_id="u1")
    """

    MAX_TOOL_ROUNDS = 10  # Safety limit to prevent infinite loops

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.client = OpenAIClient(config)
        self.meter = UsageMeter(config.limits)

        # In-memory conversation store (swap for DB in production)
        self._conversations: dict[str, Conversation] = {}

    # ── Public API ─────────────────────────────────────────────────

    def run(
        self,
        user_message: str,
        *,
        user_id: str = "anonymous",
        conversation_id: str | None = None,
        workspace_id: str | None = None,
        tool_overrides: dict[str, bool] | None = None,
        attachments: list[dict[str, str]] | None = None,
    ) -> AgentMessage:
        """Run a full agent turn (blocking). Returns the assistant message."""

        # Rate-limit check
        rate_err = self.meter.check_rate_limit(user_id)
        if rate_err:
            return self._error_message(rate_err)

        token_err = self.meter.check_token_budget(user_id)
        if token_err:
            return self._error_message(token_err)

        # Get or create conversation
        conv = self._get_or_create_conversation(conversation_id, user_id, workspace_id)

        # Record user message
        user_msg = AgentMessage(
            role=MessageRole.USER,
            content=user_message,
            attachments=attachments or [],
        )
        conv.messages.append(user_msg)

        # Build tools
        tools = build_tool_list(self.config, overrides=tool_overrides or conv.tools_enabled)

        # Add file_search if workspace has a vector store
        vector_store_id = conv.vector_store_id
        if vector_store_id and self.config.enable_file_search:
            tools.append(build_file_search_tool([vector_store_id]))

        # Build input for Responses API
        api_input = self._build_input(conv)

        # Run the agent loop
        assistant_msg = self._agent_loop(
            api_input=api_input,
            tools=tools,
            conv=conv,
            user_id=user_id,
        )

        # Record in conversation
        conv.messages.append(assistant_msg)
        conv.updated_at = datetime.now(timezone.utc)

        # Auto-title from first exchange
        if len(conv.messages) <= 3 and conv.title == "New Chat":
            conv.title = user_message[:60] + ("..." if len(user_message) > 60 else "")

        return assistant_msg

    def run_stream(
        self,
        user_message: str,
        *,
        user_id: str = "anonymous",
        conversation_id: str | None = None,
        workspace_id: str | None = None,
        tool_overrides: dict[str, bool] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Stream an agent turn via SSE-friendly chunks.

        Yields dicts like:
            {"type": "text_delta", "content": "..."}
            {"type": "tool_start", "tool": "web_search_preview"}
            {"type": "tool_done", "tool": "web_search_preview", "duration_ms": 1234}
            {"type": "citation", "title": "...", "url": "..."}
            {"type": "image", "url": "..."}
            {"type": "code_output", "code": "...", "stdout": "..."}
            {"type": "done", "message": {...}}
            {"type": "error", "message": "..."}
        """
        # Rate-limit check
        rate_err = self.meter.check_rate_limit(user_id)
        if rate_err:
            yield {"type": "error", "message": rate_err}
            return

        conv = self._get_or_create_conversation(conversation_id, user_id, workspace_id)

        user_msg = AgentMessage(role=MessageRole.USER, content=user_message)
        conv.messages.append(user_msg)

        tools = build_tool_list(self.config, overrides=tool_overrides or conv.tools_enabled)
        if conv.vector_store_id and self.config.enable_file_search:
            tools.append(build_file_search_tool([conv.vector_store_id]))

        api_input = self._build_input(conv)

        try:
            yield from self._agent_loop_streaming(
                api_input=api_input,
                tools=tools,
                conv=conv,
                user_id=user_id,
            )
        except Exception as exc:
            logger.exception("Streaming error")
            yield {"type": "error", "message": str(exc)}

    # ── Conversation management ────────────────────────────────────

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def list_conversations(self, user_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": c.id,
                "title": c.title,
                "updated_at": c.updated_at.isoformat(),
                "pinned": c.pinned,
                "archived": c.archived,
            }
            for c in sorted(
                self._conversations.values(),
                key=lambda c: c.updated_at,
                reverse=True,
            )
            if c.user_id == user_id
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        return self._conversations.pop(conversation_id, None) is not None

    def pin_conversation(self, conversation_id: str, pinned: bool = True) -> bool:
        conv = self._conversations.get(conversation_id)
        if conv:
            conv.pinned = pinned
            return True
        return False

    def archive_conversation(self, conversation_id: str, archived: bool = True) -> bool:
        conv = self._conversations.get(conversation_id)
        if conv:
            conv.archived = archived
            return True
        return False

    # ── Internal: agent loop (blocking) ────────────────────────────

    def _agent_loop(
        self,
        *,
        api_input: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        conv: Conversation,
        user_id: str,
    ) -> AgentMessage:
        """Run tool-calling loop until a final text response."""

        assistant_msg = AgentMessage(role=MessageRole.ASSISTANT, model=self.config.default_model)
        total_input_tokens = 0
        total_output_tokens = 0

        previous_response_id = None

        for _round in range(self.MAX_TOOL_ROUNDS):
            response = self.client.create_response(
                input=api_input,
                tools=tools or None,
                previous_response_id=previous_response_id,
                instructions=self.config.system_prompt,
                max_output_tokens=self.config.limits.max_tokens_per_request,
            )

            previous_response_id = response.id

            # Track tokens
            if hasattr(response, "usage") and response.usage:
                total_input_tokens += getattr(response.usage, "input_tokens", 0)
                total_output_tokens += getattr(response.usage, "output_tokens", 0)

            # Process output items
            has_tool_calls = False
            for item in response.output:
                item_type = getattr(item, "type", "")

                if item_type == "message":
                    # Final text content
                    for content in getattr(item, "content", []):
                        if getattr(content, "type", "") == "output_text":
                            assistant_msg.content += getattr(content, "text", "")
                            # Extract annotations (citations)
                            for ann in getattr(content, "annotations", []):
                                if getattr(ann, "type", "") == "url_citation":
                                    assistant_msg.citations.append(
                                        Citation(
                                            title=getattr(ann, "title", ""),
                                            url=getattr(ann, "url", ""),
                                        )
                                    )

                elif item_type == "web_search_call":
                    trace = ToolTrace(
                        tool_name="web_search_preview",
                        tool_type="builtin",
                        status=ToolStatus.COMPLETED,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                    )
                    assistant_msg.tool_traces.append(trace)
                    has_tool_calls = True

                elif item_type == "file_search_call":
                    trace = ToolTrace(
                        tool_name="file_search",
                        tool_type="builtin",
                        arguments={"query": getattr(item, "queries", [])},
                        status=ToolStatus.COMPLETED,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                    )
                    assistant_msg.tool_traces.append(trace)
                    has_tool_calls = True

                elif item_type == "code_interpreter_call":
                    code = getattr(item, "input", "")
                    outputs = getattr(item, "outputs", [])
                    stdout_parts = []
                    files = []
                    for out in outputs:
                        if getattr(out, "type", "") == "logs":
                            stdout_parts.append(getattr(out, "logs", ""))
                        elif getattr(out, "type", "") == "files":
                            for f in getattr(out, "files", []):
                                files.append({"name": getattr(f, "name", ""), "url": getattr(f, "url", "")})

                    code_output = CodeOutput(code=code, stdout="\n".join(stdout_parts), files=files)
                    assistant_msg.code_outputs.append(code_output)

                    trace = ToolTrace(
                        tool_name="code_interpreter",
                        tool_type="builtin",
                        arguments={"code": code[:200]},
                        status=ToolStatus.COMPLETED,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                    )
                    assistant_msg.tool_traces.append(trace)
                    has_tool_calls = True

                elif item_type == "image_generation_call":
                    result_data = getattr(item, "result", None)
                    if result_data:
                        img = ImageResult(
                            url=getattr(result_data, "url", None),
                            b64_data=getattr(result_data, "b64_json", None),
                            revised_prompt=getattr(result_data, "revised_prompt", ""),
                        )
                        assistant_msg.images.append(img)

                    trace = ToolTrace(
                        tool_name="image_generation",
                        tool_type="builtin",
                        arguments={"prompt": getattr(item, "prompt", "")[:200]},
                        status=ToolStatus.COMPLETED,
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                    )
                    assistant_msg.tool_traces.append(trace)
                    has_tool_calls = True

            # If no tool calls were made, we have the final answer
            if not has_tool_calls:
                break

            # For built-in tools, the API handles execution internally
            # so we just continue with the same response chain
            # The API auto-continues for built-in tools, so we break
            break

        # Record usage
        assistant_msg.tokens_used = total_input_tokens + total_output_tokens
        cost = estimate_cost(self.config.default_model, total_input_tokens, total_output_tokens)

        tools_used = list({t.tool_name for t in assistant_msg.tool_traces})
        usage = UsageRecord(
            user_id=user_id,
            conversation_id=conv.id,
            model=self.config.default_model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            tools_used=tools_used,
            estimated_cost_usd=cost,
        )
        self.meter.record_usage(usage)

        return assistant_msg

    # ── Internal: agent loop (streaming) ───────────────────────────

    def _agent_loop_streaming(
        self,
        *,
        api_input: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        conv: Conversation,
        user_id: str,
    ) -> Generator[dict[str, Any], None, None]:
        """Streaming version of the agent loop."""

        assistant_msg = AgentMessage(role=MessageRole.ASSISTANT, model=self.config.default_model)
        total_input_tokens = 0
        total_output_tokens = 0

        stream = self.client.create_response(
            input=api_input,
            tools=tools or None,
            instructions=self.config.system_prompt,
            max_output_tokens=self.config.limits.max_tokens_per_request,
            stream=True,
        )

        tool_start_time: float | None = None

        for event in stream:
            event_type = getattr(event, "type", "")

            # Text deltas
            if event_type == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                assistant_msg.content += delta
                yield {"type": "text_delta", "content": delta}

            # Tool starts
            elif event_type in (
                "response.web_search_call.in_progress",
                "response.file_search_call.in_progress",
                "response.code_interpreter_call.in_progress",
                "response.image_generation_call.in_progress",
            ):
                tool_name = event_type.split(".")[1].replace("_call", "")
                if tool_name == "web_search":
                    tool_name = "web_search_preview"
                tool_start_time = time.time()
                yield {"type": "tool_start", "tool": tool_name}

            # Tool completions
            elif event_type in (
                "response.web_search_call.completed",
                "response.file_search_call.completed",
                "response.code_interpreter_call.completed",
                "response.image_generation_call.completed",
            ):
                tool_name = event_type.split(".")[1].replace("_call", "")
                if tool_name == "web_search":
                    tool_name = "web_search_preview"
                duration = (time.time() - tool_start_time) * 1000 if tool_start_time else 0
                trace = ToolTrace(
                    tool_name=tool_name,
                    tool_type="builtin",
                    status=ToolStatus.COMPLETED,
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    duration_ms=duration,
                )
                assistant_msg.tool_traces.append(trace)
                yield {"type": "tool_done", "tool": tool_name, "duration_ms": round(duration)}
                tool_start_time = None

            # Code interpreter output
            elif event_type == "response.code_interpreter_call.interpreting":
                code_input = getattr(event, "input", "")
                if code_input:
                    yield {"type": "code_input", "code": code_input}

            # Response completed – extract final data
            elif event_type == "response.completed":
                response = getattr(event, "response", None)
                if response:
                    usage = getattr(response, "usage", None)
                    if usage:
                        total_input_tokens = getattr(usage, "input_tokens", 0)
                        total_output_tokens = getattr(usage, "output_tokens", 0)

                    # Extract citations, images, code outputs from final response
                    for item in getattr(response, "output", []):
                        item_type = getattr(item, "type", "")
                        if item_type == "message":
                            for content in getattr(item, "content", []):
                                for ann in getattr(content, "annotations", []):
                                    if getattr(ann, "type", "") == "url_citation":
                                        cit = Citation(
                                            title=getattr(ann, "title", ""),
                                            url=getattr(ann, "url", ""),
                                        )
                                        assistant_msg.citations.append(cit)
                                        yield {"type": "citation", "title": cit.title, "url": cit.url}

                        elif item_type == "image_generation_call":
                            result_data = getattr(item, "result", None)
                            if result_data:
                                img = ImageResult(
                                    url=getattr(result_data, "url", None),
                                    revised_prompt=getattr(result_data, "revised_prompt", ""),
                                )
                                assistant_msg.images.append(img)
                                yield {"type": "image", "url": img.url, "revised_prompt": img.revised_prompt}

                        elif item_type == "code_interpreter_call":
                            code = getattr(item, "input", "")
                            outputs = getattr(item, "outputs", [])
                            stdout_parts = []
                            files = []
                            for out in outputs:
                                if getattr(out, "type", "") == "logs":
                                    stdout_parts.append(getattr(out, "logs", ""))
                                elif getattr(out, "type", "") == "files":
                                    for f in getattr(out, "files", []):
                                        files.append({"name": getattr(f, "name", ""), "url": getattr(f, "url", "")})
                            co = CodeOutput(code=code, stdout="\n".join(stdout_parts), files=files)
                            assistant_msg.code_outputs.append(co)
                            yield {"type": "code_output", "code": code, "stdout": co.stdout, "files": files}

        # Finalize
        assistant_msg.tokens_used = total_input_tokens + total_output_tokens
        cost = estimate_cost(self.config.default_model, total_input_tokens, total_output_tokens)

        tools_used = list({t.tool_name for t in assistant_msg.tool_traces})
        usage_record = UsageRecord(
            user_id=user_id,
            conversation_id=conv.id,
            model=self.config.default_model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            tools_used=tools_used,
            estimated_cost_usd=cost,
        )
        self.meter.record_usage(usage_record)

        conv.messages.append(assistant_msg)
        conv.updated_at = datetime.now(timezone.utc)

        if len(conv.messages) <= 3 and conv.title == "New Chat":
            conv.title = assistant_msg.content[:60] + ("..." if len(assistant_msg.content) > 60 else "")

        yield {"type": "done", "message": assistant_msg.to_dict()}

    # ── Helpers ────────────────────────────────────────────────────

    def _build_input(self, conv: Conversation) -> list[dict[str, Any]]:
        """Convert conversation history to Responses API input format."""
        items: list[dict[str, Any]] = []
        for msg in conv.messages:
            items.append(
                {
                    "role": msg.role.value,
                    "content": msg.content,
                }
            )
        return items

    def _get_or_create_conversation(
        self,
        conversation_id: str | None,
        user_id: str,
        workspace_id: str | None,
    ) -> Conversation:
        if conversation_id and conversation_id in self._conversations:
            return self._conversations[conversation_id]

        conv = Conversation(user_id=user_id, workspace_id=workspace_id)
        if conversation_id:
            conv.id = conversation_id
        self._conversations[conv.id] = conv
        return conv

    def _error_message(self, error: str) -> AgentMessage:
        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=f"⚠️ {error}",
        )
