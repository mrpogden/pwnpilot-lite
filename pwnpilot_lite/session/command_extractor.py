#!/usr/bin/env python3
"""Command extraction and audit reporting from pwnpilot-lite session files."""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class CommandExtractor:
    """Extract and format executed commands from session logs."""

    def __init__(self, session_file: Path):
        """
        Initialize command extractor.

        Args:
            session_file: Path to session JSONL file
        """
        self.session_file = session_file
        self.session_id = session_file.stem.replace("_summary", "")

    def extract_commands(self) -> List[Dict[str, Any]]:
        """
        Extract all executed commands from session log.

        Returns:
            List of command execution records with metadata
        """
        commands = []

        with open(self.session_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_type = entry.get("type")

                    # Look for tool_output entries (approved and executed commands)
                    if entry_type == "tool_output":
                        command_record = {
                            "timestamp": entry.get("timestamp"),
                            "tool_name": entry.get("tool_name"),
                            "input": entry.get("input", {}),
                            "result": entry.get("result", {}),
                            "cache_hit": entry.get("cache_hit", False),
                        }

                        # Extract the actual command executed
                        result = entry.get("result", {})
                        input_data = entry.get("input", {})

                        # Command can be in result.command_executed or input.command
                        command_record["command"] = (
                            result.get("command_executed") or
                            input_data.get("command") or
                            self._extract_command_from_input(entry.get("tool_name"), input_data)
                        )

                        command_record["success"] = result.get("success", False)

                        # Output can be in result.output or result.stdout
                        command_record["output"] = (
                            result.get("output") or
                            result.get("stdout", "")
                        )

                        # Error can be in result.error or result.stderr
                        command_record["error"] = (
                            result.get("error") or
                            result.get("stderr", "")
                        )

                        commands.append(command_record)

                    # Also capture denied commands for audit trail
                    elif entry_type == "tool_denied":
                        command_record = {
                            "timestamp": entry.get("timestamp"),
                            "tool_name": entry.get("tool_name"),
                            "input": entry.get("input", {}),
                            "status": "DENIED",
                            "command": self._extract_command_from_input(
                                entry.get("tool_name"),
                                entry.get("input", {})
                            ),
                        }
                        commands.append(command_record)

                    # Capture mode switches for audit trail
                    elif entry_type == "mode_switch":
                        command_record = {
                            "timestamp": entry.get("timestamp"),
                            "status": "MODE_SWITCH",
                            "from_mode": entry.get("from_mode"),
                            "to_mode": entry.get("to_mode"),
                        }
                        commands.append(command_record)

                except json.JSONDecodeError:
                    continue

        return commands

    def _extract_command_from_input(self, tool_name: str, input_data: Dict[str, Any]) -> str:
        """
        Build command string from tool input.

        Args:
            tool_name: Name of the tool
            input_data: Tool input parameters

        Returns:
            Command string
        """
        # Check if command is directly provided
        if "command" in input_data:
            return input_data["command"]

        # Build from components
        target = input_data.get("target", "")
        options = input_data.get("options", "")

        if target:
            return f"{tool_name} {target} {options}".strip()
        return tool_name

    def format_commands_text(self, commands: List[Dict[str, Any]], include_output: bool = False) -> str:
        """
        Format commands as readable text.

        Args:
            commands: List of command records
            include_output: Whether to include command output

        Returns:
            Formatted text output
        """
        lines = []
        lines.append(f"Command Audit Report - Session: {self.session_id}")
        lines.append("=" * 80)
        lines.append(f"Total Commands: {len(commands)}")
        lines.append("")

        for idx, cmd in enumerate(commands, 1):
            timestamp = cmd.get("timestamp", "Unknown")

            lines.append(f"[{idx}] {timestamp}")

            # Handle mode switches
            if cmd.get("status") == "MODE_SWITCH":
                from_mode = cmd.get("from_mode", "unknown")
                to_mode = cmd.get("to_mode", "unknown")
                lines.append(f"    Mode Switch: {from_mode} → {to_mode}")
                lines.append("    🔀 Operator changed session mode")
                lines.append("")
                continue

            # Handle regular commands
            tool_name = cmd.get("tool_name", "unknown")
            command = cmd.get("command", "")

            lines.append(f"    Tool: {tool_name}")
            lines.append(f"    Command: {command}")

            # Show status
            if cmd.get("status") == "DENIED":
                lines.append("    Status: ❌ DENIED BY USER")
            elif cmd.get("cache_hit"):
                lines.append("    Status: ♻️  CACHED")
            elif cmd.get("success"):
                lines.append("    Status: ✅ SUCCESS")
            else:
                lines.append("    Status: ❌ FAILED")
                if cmd.get("error"):
                    lines.append(f"    Error: {cmd.get('error')}")

            # Include output if requested
            if include_output and "output" in cmd:
                output = cmd.get("output", "")
                if output:
                    lines.append("    Output:")
                    # Truncate long outputs
                    if len(output) > 500:
                        lines.append(f"    {output[:500]}...")
                        lines.append(f"    [Output truncated - {len(output)} chars total]")
                    else:
                        for line in output.split("\n")[:20]:  # Max 20 lines
                            lines.append(f"    {line}")

            lines.append("")

        return "\n".join(lines)

    def format_commands_json(self, commands: List[Dict[str, Any]]) -> str:
        """
        Format commands as JSON.

        Args:
            commands: List of command records

        Returns:
            JSON string
        """
        report = {
            "session_id": self.session_id,
            "total_commands": len(commands),
            "commands": commands
        }
        return json.dumps(report, indent=2)

    def format_commands_csv(self, commands: List[Dict[str, Any]]) -> str:
        """
        Format commands as CSV.

        Args:
            commands: List of command records

        Returns:
            CSV string
        """
        lines = []
        lines.append("Timestamp,Tool,Command,Status,Success,CacheHit")

        for cmd in commands:
            timestamp = cmd.get("timestamp", "")

            # Handle mode switches
            if cmd.get("status") == "MODE_SWITCH":
                from_mode = cmd.get("from_mode", "")
                to_mode = cmd.get("to_mode", "")
                lines.append(f'"{timestamp}","MODE_SWITCH","Mode: {from_mode} → {to_mode}","MODE_SWITCH",False,False')
                continue

            # Handle regular commands
            tool_name = cmd.get("tool_name", "")
            command = cmd.get("command", "").replace('"', '""')  # Escape quotes
            status = "DENIED" if cmd.get("status") == "DENIED" else "EXECUTED"
            success = cmd.get("success", False)
            cache_hit = cmd.get("cache_hit", False)

            lines.append(f'"{timestamp}","{tool_name}","{command}","{status}",{success},{cache_hit}')

        return "\n".join(lines)

    def format_commands_bash_script(self, commands: List[Dict[str, Any]], only_successful: bool = True) -> str:
        """
        Format commands as executable bash script.

        Args:
            commands: List of command records
            only_successful: Only include successful commands

        Returns:
            Bash script string
        """
        lines = []
        lines.append("#!/bin/bash")
        lines.append(f"# Command replay script - Session: {self.session_id}")
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append("")

        for idx, cmd in enumerate(commands, 1):
            # Handle mode switches
            if cmd.get("status") == "MODE_SWITCH":
                timestamp = cmd.get("timestamp", "")
                from_mode = cmd.get("from_mode", "")
                to_mode = cmd.get("to_mode", "")
                lines.append(f"# [{idx}] {timestamp} - Mode Switch: {from_mode} → {to_mode}")
                lines.append("")
                continue

            # Skip denied or failed commands if only_successful
            if only_successful:
                if cmd.get("status") == "DENIED" or not cmd.get("success"):
                    continue

            timestamp = cmd.get("timestamp", "")
            command = cmd.get("command", "")

            if command:
                lines.append(f"# [{idx}] {timestamp}")
                if cmd.get("status") == "DENIED":
                    lines.append(f"# DENIED: {command}")
                elif not cmd.get("success"):
                    lines.append(f"# FAILED: {command}")
                else:
                    lines.append(command)
                lines.append("")

        return "\n".join(lines)


def list_sessions(sessions_dir: Path) -> List[Path]:
    """
    List all available session files.

    Args:
        sessions_dir: Path to sessions directory

    Returns:
        List of session file paths
    """
    if not sessions_dir.exists():
        return []

    # Get all .jsonl files, excluding summary files
    sessions = [
        f for f in sessions_dir.glob("*.jsonl")
        if not f.name.endswith("_summary.jsonl")
    ]

    # Sort by modification time (newest first)
    sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return sessions


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract and audit commands from pwnpilot-lite session files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all sessions
  python -m pwnpilot_lite.session.command_extractor --list

  # Extract commands from latest session
  python -m pwnpilot_lite.session.command_extractor

  # Extract from specific session with output
  python -m pwnpilot_lite.session.command_extractor -s 20240131120000 --output

  # Export as JSON
  python -m pwnpilot_lite.session.command_extractor -s 20240131120000 -f json > audit.json

  # Generate bash replay script (successful commands only)
  python -m pwnpilot_lite.session.command_extractor -s 20240131120000 -f bash > replay.sh
        """
    )

    parser.add_argument(
        "-d", "--sessions-dir",
        default="sessions",
        help="Path to sessions directory (default: sessions)"
    )

    parser.add_argument(
        "-s", "--session-id",
        help="Session ID to extract commands from (default: latest)"
    )

    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all available sessions"
    )

    parser.add_argument(
        "-f", "--format",
        choices=["text", "json", "csv", "bash"],
        default="text",
        help="Output format (default: text)"
    )

    parser.add_argument(
        "-o", "--output",
        action="store_true",
        help="Include command output in text format"
    )

    parser.add_argument(
        "--all-commands",
        action="store_true",
        help="Include failed/denied commands in bash script output"
    )

    args = parser.parse_args()

    sessions_dir = Path(args.sessions_dir)

    # List sessions mode
    if args.list:
        sessions = list_sessions(sessions_dir)
        if not sessions:
            print(f"No sessions found in {sessions_dir}")
            return

        print(f"\nAvailable sessions ({len(sessions)} total):\n")
        print(f"{'Session ID':<18} {'Date':<20} {'Size':<10}")
        print("-" * 50)

        for session_file in sessions[:20]:  # Show latest 20
            session_id = session_file.stem
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            size = session_file.stat().st_size
            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"

            print(f"{session_id:<18} {mtime.strftime('%Y-%m-%d %H:%M:%S'):<20} {size_str:<10}")

        if len(sessions) > 20:
            print(f"\n... and {len(sessions) - 20} more sessions")
        print()
        return

    # Extract commands mode
    if args.session_id:
        session_file = sessions_dir / f"{args.session_id}.jsonl"
    else:
        # Use latest session
        sessions = list_sessions(sessions_dir)
        if not sessions:
            print(f"No sessions found in {sessions_dir}")
            return
        session_file = sessions[0]

    if not session_file.exists():
        print(f"Session file not found: {session_file}")
        return

    # Extract commands
    extractor = CommandExtractor(session_file)
    commands = extractor.extract_commands()

    if not commands:
        print(f"No commands found in session: {extractor.session_id}")
        return

    # Format output
    if args.format == "text":
        output = extractor.format_commands_text(commands, include_output=args.output)
    elif args.format == "json":
        output = extractor.format_commands_json(commands)
    elif args.format == "csv":
        output = extractor.format_commands_csv(commands)
    elif args.format == "bash":
        output = extractor.format_commands_bash_script(commands, only_successful=not args.all_commands)

    print(output)


if __name__ == "__main__":
    main()
