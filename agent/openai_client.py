"""Unified OpenAI gateway – wraps the OpenAI Python SDK for Agent Mode.

Uses the Responses API as the primary interface for tool-calling and streaming.
"""

from __future__ import annotations

import logging
from typing import Any

import openai

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Thin wrapper around the OpenAI SDK providing helper methods for Agent Mode."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for Agent Mode")
        self.client = openai.OpenAI(api_key=config.openai_api_key)

    # ── Responses API ──────────────────────────────────────────────

    def create_response(
        self,
        *,
        input: list[dict[str, Any]],  # noqa: A002
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        store: bool = True,
        previous_response_id: str | None = None,
        stream: bool = False,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        instructions: str | None = None,
    ) -> Any:
        """Create a response using the OpenAI Responses API.

        This is the main entry point for agent interactions.
        Returns a Response object (or stream if stream=True).
        """
        kwargs: dict[str, Any] = {
            "model": model or self.config.default_model,
            "input": input,
            "store": store,
        }

        if tools:
            kwargs["tools"] = tools
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        if max_output_tokens:
            kwargs["max_output_tokens"] = max_output_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        if instructions:
            kwargs["instructions"] = instructions
        if stream:
            kwargs["stream"] = True

        logger.debug("Creating response with model=%s, tools=%d", kwargs["model"], len(tools or []))

        if stream:
            return self.client.responses.create(**kwargs)
        return self.client.responses.create(**kwargs)

    # ── Vector Stores ──────────────────────────────────────────────

    def create_vector_store(self, name: str) -> Any:
        """Create a new vector store for file_search."""
        return self.client.vector_stores.create(name=name)

    def delete_vector_store(self, vector_store_id: str) -> None:
        """Delete a vector store."""
        self.client.vector_stores.delete(vector_store_id=vector_store_id)

    def upload_file_to_vector_store(self, vector_store_id: str, file_path: str, filename: str) -> Any:
        """Upload a file to a vector store for indexing."""
        with open(file_path, "rb") as f:
            # Upload file to OpenAI
            file_obj = self.client.files.create(file=f, purpose="assistants")

        # Add to vector store
        self.client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_obj.id,
        )
        logger.info("Uploaded %s (file_id=%s) to vector store %s", filename, file_obj.id, vector_store_id)
        return file_obj

    def delete_file_from_vector_store(self, vector_store_id: str, file_id: str) -> None:
        """Remove a file from a vector store."""
        self.client.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=file_id)
        self.client.files.delete(file_id=file_id)

    def list_vector_store_files(self, vector_store_id: str) -> list[Any]:
        """List all files in a vector store."""
        result = self.client.vector_stores.files.list(vector_store_id=vector_store_id)
        return list(result.data)

    # ── Image Generation ───────────────────────────────────────────

    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
        quality: str | None = None,
        size: str | None = None,
        n: int = 1,
    ) -> list[Any]:
        """Generate images using the Images API."""
        resp = self.client.images.generate(
            model=model or self.config.image_model,
            prompt=prompt,
            quality=quality or self.config.image_quality,
            size=size or self.config.image_size,
            n=n,
        )
        return list(resp.data)

    # ── Files ──────────────────────────────────────────────────────

    def upload_file(self, file_path: str, purpose: str = "assistants") -> Any:
        """Upload a file to OpenAI."""
        with open(file_path, "rb") as f:
            return self.client.files.create(file=f, purpose=purpose)
