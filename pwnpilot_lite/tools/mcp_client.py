"""HexStrike MCP client for tool management and execution."""

import os
from typing import Any, Dict, List, Optional, Tuple

import requests

from .tool_cache import ToolResultCache


class MCPClient:
    """Client for interacting with HexStrike MCP server."""

    def __init__(self, mcp_url: str, tool_cache: Optional[ToolResultCache] = None):
        """
        Initialize MCP client.

        Args:
            mcp_url: URL of the HexStrike MCP server
            tool_cache: Optional tool result cache
        """
        self.mcp_url = mcp_url
        self.tool_cache = tool_cache

    def check_health(self, timeout: int = 30) -> bool:
        """
        Check if MCP server is healthy.

        Args:
            timeout: Request timeout in seconds (default: 30s for environments with many tools)

        Returns:
            True if healthy, False otherwise
        """
        try:
            print(f"⏳ Checking HexStrike MCP health (timeout: {timeout}s)...")
            response = requests.get(f"{self.mcp_url}/health", timeout=timeout)
            response.raise_for_status()
            return True
        except requests.exceptions.Timeout:
            print(f"❌ HexStrike MCP health check timed out after {timeout}s")
            print(f"   The server may have many tools and needs more time to respond.")
            print(f"   Try increasing timeout or check server status.")
            return False
        except Exception as exc:
            print(f"❌ HexStrike MCP not reachable at {self.mcp_url}/health: {exc}")
            return False

    def fetch_tools(self, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch available tools from MCP server.

        Args:
            timeout: Request timeout in seconds (default: 30s for environments with many tools)

        Returns:
            List of tool definitions
        """
        try:
            print(f"⏳ Fetching tools from HexStrike MCP (timeout: {timeout}s)...")
            response = requests.get(f"{self.mcp_url}/health", timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print(f"⚠️  MCP health endpoint timed out after {timeout}s")
            print(f"   The server may have many tools. Consider increasing timeout.")
            return []
        except Exception as exc:
            print(f"⚠️  Could not reach MCP health endpoint: {exc}")
            return []

        data = response.json()
        tools_status = data.get("tools_status", {})
        available = [name for name, ok in tools_status.items() if ok]

        tools: List[Dict[str, Any]] = []
        for tool_name in available:
            tools.append({
                "name": tool_name,
                "description": f"Execute {tool_name} via HexStrike MCP",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Full command line to execute (recommended)"
                        },
                        "target": {
                            "type": "string",
                            "description": "Target URL, IP, or domain"
                        },
                        "options": {
                            "type": "string",
                            "description": "Additional command options"
                        }
                    }
                }
            })

        # Apply MAX_MCP_TOOLS limit if set
        max_tools_env = os.getenv("MAX_MCP_TOOLS", "")
        try:
            max_tools = int(max_tools_env) if max_tools_env else 0
        except ValueError:
            max_tools = 0
        if max_tools > 0 and len(tools) > max_tools:
            tools = tools[:max_tools]
            print(f"⚠️  Tool list capped to {max_tools} entries (MAX_MCP_TOOLS)")

        print(f"✅ HexStrike available: {len(tools)} tools ready")
        return tools

    def execute_tool(
        self,
        tool_name: str,
        payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Execute a tool via MCP.

        Args:
            tool_name: Name of the tool to execute
            payload: Tool input parameters

        Returns:
            Tuple of (result, cache_hit)
        """
        # Check cache first
        if self.tool_cache:
            cached_result = self.tool_cache.get(tool_name, payload)
            if cached_result is not None:
                return cached_result, True

        # Build command
        command = self._build_command(tool_name, payload)

        # Execute via MCP
        try:
            response = requests.post(
                f"{self.mcp_url}/api/command",
                json={"command": command},
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            result = {
                "success": False,
                "error": str(exc),
                "message": f"Failed to execute command: {command}"
            }

        # Store in cache if successful
        if self.tool_cache and result.get("success", False):
            self.tool_cache.set(tool_name, payload, result)

        return result, False

    def _build_command(self, tool_name: str, payload: Dict[str, Any]) -> str:
        """Build command string from tool name and payload."""
        command = payload.get("command", "").strip()
        if command:
            return command

        target = payload.get("target", "").strip()
        options = payload.get("options", "").strip()

        if tool_name.lower() == "nikto":
            host = (payload.get("host") or payload.get("url") or target).strip()
            pieces = [tool_name]
            if host and "-h" not in options and "-host" not in options:
                pieces.extend(["-h", host])
            if options:
                pieces.append(options)
            return " ".join(pieces).strip()

        if tool_name.lower() == "sqlmap":
            url = (payload.get("url") or target).strip()
            pieces = [tool_name]
            if url:
                pieces.extend(["-u", url])
            if payload.get("batch") is True and "--batch" not in options:
                pieces.append("--batch")
            if payload.get("crawl") is True:
                pieces.append("--crawl=1")
            if options:
                pieces.append(options)
            return " ".join(pieces).strip()

        if tool_name.lower() == "nuclei":
            url = (payload.get("url") or target).strip()
            templates = payload.get("templates", "").strip()
            pieces = [tool_name]
            if url:
                pieces.extend(["-u", url])
            if templates:
                pieces.extend(["-t", templates])
            if options:
                pieces.append(options)
            return " ".join(pieces).strip()

        if tool_name.lower() == "wafw00f":
            host = (payload.get("host") or payload.get("url") or target).strip()
            pieces = [tool_name]
            if host:
                pieces.append(host)
            if options:
                pieces.append(options)
            return " ".join(pieces).strip()

        # Generic fallback
        pieces = [tool_name]
        if target:
            pieces.append(target)
        if options:
            pieces.append(options)
        return " ".join(pieces).strip()
