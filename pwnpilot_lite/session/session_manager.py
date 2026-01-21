"""Session management and logging."""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionManager:
    """Manages session state and logging."""

    USER_INPUT_TOKEN = "[[USER_INPUT]]"

    def __init__(
        self,
        sessions_dir: str = "sessions",
        session_id: Optional[str] = None,
        restore: bool = False
    ):
        """
        Initialize session manager.

        Args:
            sessions_dir: Directory for session files
            session_id: Session ID to restore or create (default: generate new)
            restore: Whether to restore an existing session
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)

        # Generate or use provided session ID
        if session_id:
            self.session_id = session_id
        else:
            self.session_id = time.strftime("%Y%m%d%H%M%S")

        self.session_file = self.sessions_dir / f"{self.session_id}.jsonl"
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

        if restore and self.session_file.exists():
            # Restore existing session
            self._restore_session()
            print(f"📂 Restored session: {self.session_id}")
        else:
            # Create new session
            self.metadata = {
                "session_id": self.session_id,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "model_source": None,
                "model_id": None,
            }
            self.append_log({"type": "session_start", "session_id": self.session_id})

    def _restore_session(self) -> None:
        """Restore session from existing file."""
        # Track the last assistant message with tool_use for reconstruction
        last_tool_use_ids = []
        pending_tool_results = {}

        with open(self.session_file, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line.strip())
                entry_type = entry.get("type")

                # Restore metadata
                if entry_type == "session_start":
                    self.metadata["session_id"] = entry.get("session_id")
                    self.metadata["created_at"] = entry.get("timestamp")
                elif entry_type == "model_source":
                    self.metadata["model_source"] = entry.get("value")
                elif entry_type == "model_selected":
                    self.metadata["model_id"] = entry.get("model_id")

                # Restore messages
                elif entry_type == "user_message":
                    # First, append any pending tool results
                    if pending_tool_results and last_tool_use_ids:
                        # Create tool_result message from pending results
                        tool_result_blocks = []
                        for tool_id in last_tool_use_ids:
                            if tool_id in pending_tool_results:
                                tool_result_blocks.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": json.dumps(pending_tool_results[tool_id])
                                })
                        if tool_result_blocks:
                            self.messages.append({
                                "role": "user",
                                "content": tool_result_blocks
                            })
                        pending_tool_results.clear()
                        last_tool_use_ids.clear()

                    # Now append the user message
                    self.messages.append({
                        "role": "user",
                        "content": entry.get("content")
                    })

                elif entry_type == "assistant_blocks":
                    blocks = entry.get("blocks", [])
                    self.messages.append({
                        "role": "assistant",
                        "content": blocks
                    })
                    # Track tool_use IDs for potential reconstruction
                    last_tool_use_ids = [
                        block.get("id")
                        for block in blocks
                        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id")
                    ]

                elif entry_type == "tool_result":
                    # New format: direct tool_result message
                    tool_result_block = {
                        "type": "tool_result",
                        "tool_use_id": entry.get("tool_use_id"),
                        "content": json.dumps(entry.get("result", {}))
                    }
                    self.messages.append({
                        "role": "user",
                        "content": [tool_result_block]
                    })
                    last_tool_use_ids.clear()

                elif entry_type == "tool_output":
                    # Old format: audit log, use for reconstruction if needed
                    if last_tool_use_ids:
                        # Store result for reconstruction
                        # We don't know which tool_use_id it matches, so try to match by order
                        if len(last_tool_use_ids) == 1:
                            pending_tool_results[last_tool_use_ids[0]] = entry.get("result", {})

        # Validate and clean up incomplete tool requests
        messages_before_cleanup = len(self.messages)
        self._cleanup_incomplete_tool_requests()
        messages_after_cleanup = len(self.messages)

        # Debug info
        if messages_before_cleanup != messages_after_cleanup:
            print(f"   Restored {messages_before_cleanup} messages, kept {messages_after_cleanup} after cleanup")

    def _cleanup_incomplete_tool_requests(self) -> None:
        """
        Remove incomplete tool requests from the END of restored session.

        Claude API requires that assistant messages with tool_use blocks
        must be immediately followed by user messages with tool_result blocks.
        We only clean up incomplete exchanges at the end - we trust that
        anything in the middle of the conversation was valid when saved.
        """
        if not self.messages:
            return

        # Work backwards from the end to find incomplete tool requests
        while len(self.messages) > 0:
            last_message = self.messages[-1]

            # Check if last message is an assistant with tool_use
            if last_message.get("role") == "assistant":
                content = last_message.get("content", [])
                if isinstance(content, list):
                    # Check if it has any tool_use blocks
                    has_tool_use = any(
                        isinstance(block, dict) and block.get("type") == "tool_use"
                        for block in content
                    )

                    if has_tool_use:
                        # Incomplete tool request at end - remove it
                        self.messages.pop()
                        print("⚠️  Removed incomplete tool request from end of restored session")
                        continue

            # Check if last message is user with tool_result but no preceding tool_use
            if last_message.get("role") == "user":
                content = last_message.get("content", [])
                if isinstance(content, list):
                    # Check if it has tool_result blocks
                    has_tool_result = any(
                        isinstance(block, dict) and block.get("type") == "tool_result"
                        for block in content
                    )

                    if has_tool_result:
                        # Check if previous message has matching tool_use
                        if len(self.messages) >= 2:
                            prev_message = self.messages[-2]
                            if prev_message.get("role") == "assistant":
                                prev_content = prev_message.get("content", [])
                                if isinstance(prev_content, list):
                                    has_prev_tool_use = any(
                                        isinstance(block, dict) and block.get("type") == "tool_use"
                                        for block in prev_content
                                    )
                                    if has_prev_tool_use:
                                        # Valid pair - stop cleanup
                                        break

                        # Orphaned tool_result - remove it
                        self.messages.pop()
                        print("⚠️  Removed orphaned tool result from end of restored session")
                        continue

            # Last message looks valid - stop cleanup
            break

    def append_log(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the session log."""
        entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if "session_id" not in entry:
            entry["session_id"] = self.session_id

        with open(self.session_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})
        self.append_log({"type": "user_message", "content": content})

    def add_assistant_message(self, blocks: List[Dict[str, Any]]) -> None:
        """Add an assistant message to the conversation."""
        self.messages.append({"role": "assistant", "content": blocks})
        self.append_log({"type": "assistant_blocks", "blocks": blocks})

    def add_tool_result(
        self,
        tool_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Add a tool result to the conversation."""
        tool_result_block = {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": json.dumps(result)
        }
        self.messages.append({
            "role": "user",
            "content": [tool_result_block]
        })
        # Log tool result to session file
        self.append_log({
            "type": "tool_result",
            "tool_use_id": tool_id,
            "result": result
        })

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get current conversation messages."""
        return self.messages

    def set_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Set conversation messages (e.g., after summarization)."""
        self.messages = messages

    def compress_context(self, summary: str, keep_recent: int = 6) -> None:
        """
        Compress conversation context with a summary.

        Args:
            summary: Summary text
            keep_recent: Number of recent messages to keep
        """
        if len(self.messages) <= keep_recent:
            return

        old_count = len(self.messages)

        # Create summary message
        summary_message = {
            "role": "user",
            "content": f"[CONTEXT SUMMARY - Previous session findings]\n\n{summary}\n\n[END SUMMARY - Continuing from here]"
        }

        # Keep recent messages
        recent_messages = self.messages[-keep_recent:]

        # Replace with summary + recent
        self.messages = [summary_message] + recent_messages
        new_count = len(self.messages)

        print(f"\n✅ Context compressed: {old_count} messages → {new_count} messages\n")

    def get_metadata(self) -> Dict[str, Any]:
        """Get session metadata."""
        return self.metadata

    def update_metadata(self, **kwargs) -> None:
        """Update session metadata."""
        self.metadata.update(kwargs)

    @staticmethod
    def list_sessions(sessions_dir: str = "sessions") -> List[Dict[str, Any]]:
        """
        List all available sessions.

        Returns:
            List of session metadata dictionaries
        """
        sessions_path = Path(sessions_dir)
        if not sessions_path.exists():
            return []

        sessions = []
        for session_file in sorted(sessions_path.glob("*.jsonl"), reverse=True):
            session_id = session_file.stem
            metadata = {
                "session_id": session_id,
                "file": str(session_file),
                "size": session_file.stat().st_size,
                "modified": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(session_file.stat().st_mtime)
                ),
            }

            # Read first few lines to get metadata
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        entry_type = entry.get("type")

                        if entry_type == "session_start":
                            metadata["created_at"] = entry.get("timestamp")
                        elif entry_type == "model_source":
                            metadata["model_source"] = entry.get("value")
                        elif entry_type == "model_selected":
                            metadata["model_id"] = entry.get("model_id")
                            break  # We have enough metadata

                sessions.append(metadata)
            except Exception:
                # Skip corrupted files
                continue

        return sessions

    @staticmethod
    def delete_session(session_id: str, sessions_dir: str = "sessions") -> bool:
        """
        Delete a session file.

        Args:
            session_id: Session ID to delete
            sessions_dir: Directory containing session files

        Returns:
            True if deleted, False otherwise
        """
        session_file = Path(sessions_dir) / f"{session_id}.jsonl"
        if session_file.exists():
            session_file.unlink()
            return True
        return False

    @staticmethod
    def strip_user_input_token(blocks: List[Dict[str, Any]]) -> tuple:
        """
        Strip user input token from blocks.

        Returns:
            Tuple of (cleaned_blocks, user_input_requested)
        """
        requested = False
        cleaned: List[Dict[str, Any]] = []
        for block in blocks:
            if block.get("type") == "text":
                text = block.get("text", "")
                if SessionManager.USER_INPUT_TOKEN in text:
                    requested = True
                    text = text.replace(SessionManager.USER_INPUT_TOKEN, "").strip()
                if text:
                    cleaned.append({"type": "text", "text": text})
            else:
                cleaned.append(block)
        return cleaned, requested

    @staticmethod
    def detect_tool_request_hint(text: str) -> bool:
        """Detect if text contains hints of a tool request."""
        if not text:
            return False
        lowered = text.lower()
        return "tool_use" in lowered or "\"type\": \"tool_use\"" in lowered or "'type': 'tool_use'" in lowered
