"""Export ChatGPT conversations as JSON files and Markdown files."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def export_conversation_json(conversation: dict[str, Any], output_dir: Path) -> Path:
    """Write a single conversation's raw API response as a JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    conv_id = conversation.get("conversation_id", conversation.get("id", "unknown"))
    title = conversation.get("title", "Untitled")
    filename = _safe_filename(title, conv_id) + ".json"
    filepath = output_dir / filename

    filepath.write_text(
        json.dumps(conversation, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return filepath


def export_conversation_markdown(conversation: dict[str, Any], output_dir: Path) -> Path:
    """Convert a conversation to Markdown and write it to a file.

    Traverses the conversation's mapping tree to produce a linear sequence of
    messages, then formats them as a readable Markdown document.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    conv_id = conversation.get("conversation_id", conversation.get("id", "unknown"))
    title = conversation.get("title", "Untitled")
    create_time = conversation.get("create_time", 0)
    messages = linearize_conversation(conversation)

    lines: list[str] = []
    lines.append(f"# {title}\n")

    if create_time:
        dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
        lines.append(f"*Created: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

    lines.append("---\n")

    for msg in messages:
        role = msg["role"]
        text = msg["text"]

        if role == "user":
            lines.append(f"## User\n")
            lines.append(f"{text}\n")
        elif role == "assistant":
            lines.append(f"## Assistant\n")
            lines.append(f"{text}\n")
        elif role == "tool":
            lines.append(f"## Tool\n")
            lines.append(f"```\n{text}\n```\n")

    filename = _safe_filename(title, conv_id) + ".md"
    filepath = output_dir / filename
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def linearize_conversation(conversation: dict[str, Any]) -> list[dict[str, str]]:
    """Traverse the mapping tree and produce a linear list of messages.

    ChatGPT stores messages in a tree (mapping dict). Each node has:
    - id, parent, children, message (with .author.role and .content.parts)

    Strategy: Start from root (no parent), follow the last child at each
    branch to get the most recent response thread.
    """
    mapping = conversation.get("mapping", {})
    if not mapping:
        return []

    # Find the root node (no parent)
    root_id = None
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            root_id = node_id
            break

    if root_id is None:
        return []

    # Walk the tree following the last child at each branch
    messages: list[dict[str, str]] = []
    current_id = root_id

    while current_id is not None:
        node = mapping.get(current_id)
        if node is None:
            break

        message = node.get("message")
        if message is not None:
            role = message.get("author", {}).get("role", "unknown")
            text = _extract_message_text(message)

            if text.strip() and role in ("user", "assistant", "tool"):
                messages.append({"role": role, "text": text})

        children = node.get("children", [])
        current_id = children[-1] if children else None

    return messages


def export_all(
    conversations: list[dict[str, Any]],
    output_dir: Path,
) -> tuple[list[Path], list[Path]]:
    """Export a list of conversations to both JSON and Markdown.

    Creates 'json/' and 'markdown/' subdirs under output_dir.
    """
    json_dir = output_dir / "json"
    markdown_dir = output_dir / "markdown"

    json_paths: list[Path] = []
    markdown_paths: list[Path] = []

    for conv in conversations:
        title = conv.get("title", "Untitled")
        try:
            jp = export_conversation_json(conv, json_dir)
            json_paths.append(jp)
        except Exception as e:
            logger.warning("Failed to export JSON for '%s': %s", title, e)

        try:
            mp = export_conversation_markdown(conv, markdown_dir)
            markdown_paths.append(mp)
        except Exception as e:
            logger.warning("Failed to export Markdown for '%s': %s", title, e)

    return json_paths, markdown_paths


def _extract_message_text(message: dict[str, Any]) -> str:
    """Extract readable text from a message's content.parts list."""
    content = message.get("content", {})
    parts = content.get("parts", [])
    text_pieces: list[str] = []

    for part in parts:
        if isinstance(part, str):
            text_pieces.append(part)
        elif isinstance(part, dict):
            if "text" in part:
                text_pieces.append(part["text"])
            elif part.get("content_type") == "image_asset_pointer":
                text_pieces.append("[Image]")

    return "\n".join(text_pieces)


def _safe_filename(title: str, conv_id: str, max_length: int = 80) -> str:
    """Create a filesystem-safe filename from a conversation title and ID."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title)
    safe = safe.strip().strip('.')

    if not safe:
        safe = "Untitled"

    if len(safe) > max_length:
        safe = safe[:max_length].rstrip()

    short_id = conv_id[:8] if len(conv_id) >= 8 else conv_id
    return f"{safe}_{short_id}"
