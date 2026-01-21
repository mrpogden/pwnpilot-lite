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
                    self.messages.append({
                        "role": "user",
                        "content": entry.get("content")
                    })
                elif entry_type == "assistant_blocks":
                    self.messages.append({
                        "role": "assistant",
                        "content": entry.get("blocks", [])
                    })

        # Validate and clean up incomplete tool requests
        self._cleanup_incomplete_tool_requests()

    def _cleanup_incomplete_tool_requests(self) -> None:
        """
        Remove incomplete tool requests from restored session.

        Claude API requires that assistant messages with tool_use blocks
        must be immediately followed by user messages with tool_result blocks.
        If we restore a session with an incomplete tool exchange, we need to
        remove it to avoid API validation errors.
        """
        if not self.messages:
            return

        removed_count = 0

        # Work backwards through messages to find incomplete tool requests
        i = len(self.messages) - 1
        while i >= 0:
            message = self.messages[i]

            # Check if this is an assistant message with tool_use
            if message.get("role") == "assistant":
                content = message.get("content", [])
                if isinstance(content, list):
                    tool_use_ids = [
                        block.get("id")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "tool_use"
                    ]

                    if tool_use_ids:
                        # Check if the next message has matching tool_results
                        if i + 1 < len(self.messages):
                            next_message = self.messages[i + 1]
                            if next_message.get("role") == "user":
                                next_content = next_message.get("content", [])
                                if isinstance(next_content, list):
                                    result_ids = [
                                        block.get("tool_use_id")
                                        for block in next_content
                                        if isinstance(block, dict) and block.get("type") == "tool_result"
                                    ]

                                    # If all tool_use IDs have matching results, this is complete
                                    if all(tid in result_ids for tid in tool_use_ids):
                                        break  # Found a complete exchange, stop cleanup

                        # Incomplete tool request - remove this and all subsequent messages
                        removed_count = len(self.messages) - i
                        self.messages = self.messages[:i]
                        break

            i -= 1

        if removed_count > 0:
            plural = "message" if removed_count == 1 else "messages"
            print(f"⚠️  Removed {removed_count} incomplete {plural} from restored session")

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
        self.messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(result)
            }]
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
