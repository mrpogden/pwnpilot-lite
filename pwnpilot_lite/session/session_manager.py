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
        self.summary_file = self.sessions_dir / f"{self.session_id}_summary.json"
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.session_summary: Dict[str, Any] = self._initialize_summary()

        if restore and self.session_file.exists():
            # Restore existing session
            self._restore_session()
            self._load_summary()
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
            self._save_summary()

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
                elif entry_type == "target_set":
                    self.metadata["target"] = entry.get("target")
                elif entry_type == "knowledge_graph_updated":
                    self.metadata["knowledge_graph"] = entry.get("knowledge_graph")

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

        # Check if restored session exceeds safe context limits
        self._check_and_truncate_restored_context()

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

    def _check_and_truncate_restored_context(self) -> None:
        """
        Check if restored session context is too large and truncate if needed.

        This prevents ValidationException when restoring very long sessions.
        Uses a heuristic of ~4 chars per token and keeps messages under a safe limit.
        """
        if not self.messages:
            return

        # Estimate token count (rough heuristic: 4 chars per token)
        # Account for system prompt + tools (~30k-50k tokens) by being conservative
        MAX_SAFE_MESSAGE_TOKENS = 100000  # Leave room for system prompt + tools

        total_chars = 0
        for msg in self.messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        # Count text blocks
                        if block.get("type") == "text":
                            total_chars += len(block.get("text", ""))
                        # Count tool content
                        elif block.get("type") in ["tool_use", "tool_result"]:
                            total_chars += len(json.dumps(block))

        estimated_tokens = total_chars // 4

        if estimated_tokens > MAX_SAFE_MESSAGE_TOKENS:
            # Context is too large - keep only recent messages
            print(f"\n⚠️  Restored session is very large (est. {estimated_tokens:,} tokens)")
            print(f"   Truncating to recent messages to prevent context overflow...")

            # Keep last 30 messages (should be well under limits)
            keep_recent = 30
            if len(self.messages) > keep_recent:
                old_count = len(self.messages)

                # Create a truncation notice
                truncation_notice = {
                    "role": "user",
                    "content": f"[SESSION RESTORED - Older messages truncated to fit context limits. Showing last {keep_recent} messages of {old_count} total. Use /summarize if you need context compression.]"
                }

                # Keep only recent messages
                self.messages = [truncation_notice] + self.messages[-keep_recent:]
                new_count = len(self.messages)

                print(f"   Truncated: {old_count} messages → {new_count} messages")
                print(f"   Kept most recent {keep_recent} messages\n")

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

    def set_target(self, target: str) -> None:
        """
        Set the target for the security assessment.

        Args:
            target: Target domain, IP, or organization name
        """
        self.metadata["target"] = target
        self.update_summary_target(target)
        self.append_log({
            "type": "target_set",
            "target": target
        })

    def get_target(self) -> Optional[str]:
        """
        Get the current target for the security assessment.

        Returns:
            Target string or None if not set
        """
        return self.metadata.get("target")

    def update_knowledge_graph(self, knowledge_graph: Dict[str, Any]) -> None:
        """
        Update the knowledge graph for the current assessment.

        Args:
            knowledge_graph: Knowledge graph data structure
        """
        self.metadata["knowledge_graph"] = knowledge_graph
        self.append_log({
            "type": "knowledge_graph_updated",
            "knowledge_graph": knowledge_graph
        })

    def get_knowledge_graph(self) -> Dict[str, Any]:
        """
        Get the current knowledge graph.

        Returns:
            Knowledge graph dictionary or empty dict if not set
        """
        return self.metadata.get("knowledge_graph", {})

    def _initialize_summary(self) -> Dict[str, Any]:
        """Initialize empty session summary structure."""
        return {
            "session_id": getattr(self, 'session_id', None),
            "target": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reconnaissance": {
                "open_ports": [],
                "services": [],
                "subdomains": [],
                "ip_addresses": [],
                "technologies": []
            },
            "credentials": [],
            "files_discovered": [],
            "vulnerabilities": [],
            "tools_attempted": [],
            "notes": []
        }

    def _load_summary(self) -> None:
        """Load session summary from file if it exists."""
        if self.summary_file.exists():
            try:
                with open(self.summary_file, "r", encoding="utf-8") as f:
                    loaded_summary = json.load(f)
                    # Merge loaded summary with initialized structure to handle schema changes
                    self.session_summary.update(loaded_summary)
            except Exception as e:
                print(f"⚠️  Could not load session summary: {e}")
                # Keep initialized empty summary

    def _save_summary(self) -> None:
        """Save session summary to file."""
        self.session_summary["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(self.session_summary, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Could not save session summary: {e}")

    def add_finding(self, category: str, item: Any, deduplicate: bool = True) -> None:
        """
        Add a finding to the session summary.

        Args:
            category: Category name (must match keys in reconnaissance dict or top-level keys)
            item: Item to add (can be string, dict, etc.)
            deduplicate: If True, avoid adding duplicates
        """
        if category in self.session_summary.get("reconnaissance", {}):
            target_list = self.session_summary["reconnaissance"][category]
        elif category in self.session_summary:
            target_list = self.session_summary[category]
        else:
            # Create new category if it doesn't exist
            self.session_summary[category] = []
            target_list = self.session_summary[category]

        # Add item if not duplicate or deduplication is disabled
        if not deduplicate or item not in target_list:
            target_list.append(item)
            self._save_summary()

    def add_note(self, note: str) -> None:
        """Add a note to the session summary."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.session_summary["notes"].append({
            "timestamp": timestamp,
            "note": note
        })
        self._save_summary()

    def add_tool_attempt(self, tool: str, command: str = "", result: str = "success", details: str = "") -> None:
        """
        Log a tool attempt in the session summary.

        Args:
            tool: Tool name
            command: Command executed (optional)
            result: Result status (success, failed, no_findings, etc.)
            details: Additional details
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.session_summary["tools_attempted"].append({
            "timestamp": timestamp,
            "tool": tool,
            "command": command,
            "result": result,
            "details": details
        })
        self._save_summary()

    def update_summary_target(self, target: str) -> None:
        """Update the target in the session summary."""
        self.session_summary["target"] = target
        self._save_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Get the current session summary."""
        return self.session_summary

    def format_summary_display(self) -> str:
        """Format session summary for display."""
        summary = self.session_summary
        lines = []

        lines.append("=" * 70)
        lines.append(f"SESSION INTELLIGENCE SUMMARY - {summary['session_id']}")
        lines.append("=" * 70)

        # Target
        if summary.get("target"):
            lines.append(f"\n🎯 Target: {summary['target']}")

        # Reconnaissance
        recon = summary.get("reconnaissance", {})
        if any(recon.values()):
            lines.append("\n📡 Reconnaissance:")
            if recon.get("ip_addresses"):
                lines.append(f"   IP Addresses: {', '.join(recon['ip_addresses'])}")
            if recon.get("open_ports"):
                lines.append(f"   Open Ports: {', '.join(map(str, recon['open_ports']))}")
            if recon.get("services"):
                lines.append(f"   Services: {', '.join(recon['services'])}")
            if recon.get("subdomains"):
                lines.append(f"   Subdomains: {', '.join(recon['subdomains'][:5])}")
                if len(recon['subdomains']) > 5:
                    lines.append(f"      ... and {len(recon['subdomains']) - 5} more")
            if recon.get("technologies"):
                lines.append(f"   Technologies: {', '.join(recon['technologies'])}")

        # Credentials
        if summary.get("credentials"):
            lines.append(f"\n🔑 Credentials Found: {len(summary['credentials'])} item(s)")
            for cred in summary['credentials'][:3]:
                if isinstance(cred, dict):
                    lines.append(f"   - {cred.get('type', 'Unknown')}: {cred.get('value', '')}")
                else:
                    lines.append(f"   - {cred}")
            if len(summary['credentials']) > 3:
                lines.append(f"   ... and {len(summary['credentials']) - 3} more")

        # Files
        if summary.get("files_discovered"):
            lines.append(f"\n📁 Files Discovered: {len(summary['files_discovered'])} item(s)")
            for file_item in summary['files_discovered'][:3]:
                if isinstance(file_item, dict):
                    lines.append(f"   - {file_item.get('path', '')}")
                else:
                    lines.append(f"   - {file_item}")
            if len(summary['files_discovered']) > 3:
                lines.append(f"   ... and {len(summary['files_discovered']) - 3} more")

        # Vulnerabilities
        if summary.get("vulnerabilities"):
            lines.append(f"\n🔓 Vulnerabilities: {len(summary['vulnerabilities'])} found")
            for vuln in summary['vulnerabilities'][:3]:
                if isinstance(vuln, dict):
                    severity = vuln.get('severity', 'unknown')
                    vuln_type = vuln.get('type', 'Unknown')
                    location = vuln.get('location', '')
                    lines.append(f"   - [{severity.upper()}] {vuln_type} at {location}")
                else:
                    lines.append(f"   - {vuln}")
            if len(summary['vulnerabilities']) > 3:
                lines.append(f"   ... and {len(summary['vulnerabilities']) - 3} more")

        # Tools attempted
        if summary.get("tools_attempted"):
            lines.append(f"\n🔧 Tools Attempted: {len(summary['tools_attempted'])}")
            recent_tools = summary['tools_attempted'][-5:]
            for tool_log in recent_tools:
                if isinstance(tool_log, dict):
                    result_icon = "✅" if tool_log.get('result') == 'success' else "❌"
                    lines.append(f"   {result_icon} {tool_log.get('tool', 'Unknown')} - {tool_log.get('result', '')}")

        # Notes
        if summary.get("notes"):
            lines.append(f"\n📝 Notes: {len(summary['notes'])}")
            for note in summary['notes'][-3:]:
                if isinstance(note, dict):
                    lines.append(f"   • {note.get('note', '')}")
                else:
                    lines.append(f"   • {note}")

        lines.append(f"\n📅 Last Updated: {summary.get('last_updated', 'Unknown')}")
        lines.append("=" * 70)

        return "\n".join(lines)

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
        Delete a session file and its summary.

        Args:
            session_id: Session ID to delete
            sessions_dir: Directory containing session files

        Returns:
            True if deleted, False otherwise
        """
        session_file = Path(sessions_dir) / f"{session_id}.jsonl"
        summary_file = Path(sessions_dir) / f"{session_id}_summary.json"

        deleted = False
        if session_file.exists():
            session_file.unlink()
            deleted = True

        # Also delete summary file if it exists
        if summary_file.exists():
            summary_file.unlink()

        return deleted

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
