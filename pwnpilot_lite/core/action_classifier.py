"""Action classifier for autonomous mode safety."""

import re
from typing import Dict, Any, List, Tuple


class ActionClassifier:
    """Classifies actions as SAFE, NEEDS_APPROVAL, or FORBIDDEN."""

    # Destructive command patterns
    DESTRUCTIVE_PATTERNS = [
        r'\brm\b.*(-rf|-r|-f)',  # rm with dangerous flags
        r'\b(mkfs|dd)\b',  # Filesystem destructive
        r'\b(shutdown|reboot|halt)\b',  # System control
        r'\b(kill|pkill|killall)\b.*-9',  # Force kill
        r'>\s*/dev/',  # Writing to devices
        r'\bformat\b',  # Format commands
        r'\b(fdisk|parted)\b',  # Disk partitioning
    ]

    # Local filesystem patterns
    LOCAL_FS_PATTERNS = [
        r'/home/',
        r'/Users/',
        r'/root/',
        r'/etc/',
        r'/var/',
        r'/usr/',
        r'\$HOME',
        r'~/',
        r'\.\.',  # Parent directory traversal
    ]

    def __init__(self, scope_targets: List[str] = None, scope_description: str = ""):
        """
        Initialize action classifier.

        Args:
            scope_targets: List of in-scope targets (IPs, domains, etc.)
            scope_description: Human-readable scope description
        """
        self.scope_targets = scope_targets or []
        self.scope_description = scope_description

    def classify_action(self, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[str, str]:
        """
        Classify an action as SAFE, NEEDS_APPROVAL, or FORBIDDEN.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Tuple of (classification, reason)
        """
        # Extract command from input
        command = tool_input.get("command", "")
        target = tool_input.get("target", "")
        url = tool_input.get("url", "")

        # Combine all target-like fields
        all_targets = f"{command} {target} {url}".lower()

        # Check for local filesystem destructive actions (ALWAYS FORBIDDEN)
        if self._is_local_destructive(command):
            return "FORBIDDEN", "Destructive action on local filesystem"

        # Check if target is out of scope (FORBIDDEN)
        if not self._is_in_scope(all_targets):
            return "FORBIDDEN", "Target is out of scope"

        # Check if action is destructive (NEEDS APPROVAL)
        if self._is_destructive(command):
            return "NEEDS_APPROVAL", "Destructive action requires approval"

        # Otherwise it's safe
        return "SAFE", "Action is in scope and non-destructive"

    def _is_local_destructive(self, command: str) -> bool:
        """Check if command is destructive to local filesystem."""
        if not command:
            return False

        # Check for destructive patterns on local filesystem
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                # Check if it targets local filesystem
                for fs_pattern in self.LOCAL_FS_PATTERNS:
                    if re.search(fs_pattern, command):
                        return True

        return False

    def _is_destructive(self, command: str) -> bool:
        """Check if command is potentially destructive."""
        if not command:
            return False

        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        # Check for other risky operations
        risky_keywords = [
            'drop table', 'drop database', 'truncate',
            'delete from', '--dump-all',
            'exploit', 'payload',
            'reverse shell', 'bind shell',
        ]

        command_lower = command.lower()
        for keyword in risky_keywords:
            if keyword in command_lower:
                return True

        return False

    def _is_in_scope(self, target_string: str) -> bool:
        """Check if target is in scope."""
        if not self.scope_targets:
            # No scope defined, everything is considered in scope
            # (User should define scope when using autonomous mode)
            return True

        target_lower = target_string.lower()

        # Check if any scope target appears in the command/target
        for scope_target in self.scope_targets:
            if scope_target.lower() in target_lower:
                return True

        return False

    def add_scope_target(self, target: str) -> None:
        """Add a target to the scope."""
        if target and target not in self.scope_targets:
            self.scope_targets.append(target)

    def remove_scope_target(self, target: str) -> None:
        """Remove a target from the scope."""
        if target in self.scope_targets:
            self.scope_targets.remove(target)

    def get_scope_summary(self) -> str:
        """Get a summary of current scope."""
        if not self.scope_targets:
            return "⚠️  No scope defined - all targets considered in scope"

        lines = ["📋 Current Scope:"]
        if self.scope_description:
            lines.append(f"   Description: {self.scope_description}")
        lines.append(f"   Targets: {', '.join(self.scope_targets)}")

        return "\n".join(lines)
