"""Vector store management – upload, index, list, delete documents per workspace."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import TYPE_CHECKING, Any

from agent.schemas import Workspace

if TYPE_CHECKING:
    from agent.config import AgentConfig
    from agent.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".txt",
        ".md",
        ".docx",
        ".csv",
        ".json",
        ".html",
        ".py",
        ".js",
        ".ts",
        ".c",
        ".cpp",
        ".java",
        ".go",
        ".rs",
        ".yaml",
        ".yml",
        ".xml",
        ".log",
    }
)


class VectorStoreManager:
    """Manages per-workspace vector stores and file uploads."""

    def __init__(self, config: AgentConfig, client: OpenAIClient) -> None:
        self.config = config
        self.client = client
        # In-memory workspace store (swap for DB in production)
        self._workspaces: dict[str, Workspace] = {}

    def create_workspace(self, name: str, user_id: str) -> Workspace:
        """Create a workspace with an associated vector store."""
        vs = self.client.create_vector_store(name=f"hackgpt-{name}")
        ws = Workspace(
            name=name,
            user_id=user_id,
            vector_store_id=vs.id,
        )
        self._workspaces[ws.id] = ws
        logger.info("Created workspace %s with vector store %s", ws.id, vs.id)
        return ws

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    def list_workspaces(self, user_id: str) -> list[dict[str, Any]]:
        return [ws.to_dict() for ws in self._workspaces.values() if ws.user_id == user_id]

    def delete_workspace(self, workspace_id: str) -> bool:
        ws = self._workspaces.pop(workspace_id, None)
        if ws and ws.vector_store_id:
            try:
                self.client.delete_vector_store(ws.vector_store_id)
            except Exception:
                logger.exception("Failed to delete vector store %s", ws.vector_store_id)
        return ws is not None

    def upload_file(
        self,
        workspace_id: str,
        file_data: bytes,
        filename: str,
    ) -> dict[str, Any]:
        """Upload a file to the workspace's vector store."""
        ws = self._workspaces.get(workspace_id)
        if not ws:
            raise ValueError(f"Workspace {workspace_id} not found")
        if not ws.vector_store_id:
            raise ValueError(f"Workspace {workspace_id} has no vector store")

        # Validate extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type {ext} not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

        # Validate size
        size_mb = len(file_data) / (1024 * 1024)
        if size_mb > self.config.limits.max_file_size_mb:
            raise ValueError(f"File too large: {size_mb:.1f}MB (max {self.config.limits.max_file_size_mb}MB)")

        # Check file count limit
        if len(ws.files) >= self.config.limits.max_file_uploads_per_workspace:
            raise ValueError(f"Workspace file limit reached: {self.config.limits.max_file_uploads_per_workspace}")

        # Write to temp file and upload
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name

        try:
            file_obj = self.client.upload_file_to_vector_store(
                vector_store_id=ws.vector_store_id,
                file_path=tmp_path,
                filename=filename,
            )
            file_record = {
                "id": file_obj.id,
                "name": filename,
                "size": f"{size_mb:.1f}MB",
                "status": "indexed",
            }
            ws.files.append(file_record)
            return file_record
        finally:
            os.unlink(tmp_path)

    def delete_file(self, workspace_id: str, file_id: str) -> bool:
        """Remove a file from the workspace's vector store."""
        ws = self._workspaces.get(workspace_id)
        if not ws or not ws.vector_store_id:
            return False

        try:
            self.client.delete_file_from_vector_store(ws.vector_store_id, file_id)
        except Exception:
            logger.exception("Failed to delete file %s from vector store", file_id)
            return False

        ws.files = [f for f in ws.files if f.get("id") != file_id]
        return True

    def list_files(self, workspace_id: str) -> list[dict[str, str]]:
        """List all files in a workspace."""
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return []
        return ws.files
