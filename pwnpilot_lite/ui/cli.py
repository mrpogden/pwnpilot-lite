"""Command-line interface for PwnPilot Lite."""

import json
from typing import Any, Dict, List, Optional

from pwnpilot_lite.core.ai_provider import AIProvider
from pwnpilot_lite.session.session_manager import SessionManager
from pwnpilot_lite.session.token_tracker import TokenTracker
from pwnpilot_lite.tools.mcp_client import MCPClient
from pwnpilot_lite.tools.tool_cache import ToolResultCache


class CLI:
    """Command-line interface for PwnPilot Lite."""

    def __init__(
        self,
        ai_provider: AIProvider,
        mcp_client: MCPClient,
        session_manager: SessionManager,
        token_tracker: Optional[TokenTracker] = None,
        tool_cache: Optional[ToolResultCache] = None,
        max_tokens: int = 4096,
        enable_caching: bool = True,
        enable_streaming: bool = True,
        show_tokens: bool = True,
        mcp_timeout: int = 30,
    ):
        """
        Initialize CLI.

        Args:
            ai_provider: AI provider instance
            mcp_client: MCP client instance
            session_manager: Session manager instance
            token_tracker: Optional token tracker
            tool_cache: Optional tool cache
            max_tokens: Maximum tokens per response
            enable_caching: Enable prompt caching
            enable_streaming: Enable streaming responses
            show_tokens: Show token usage stats
            mcp_timeout: MCP health check timeout in seconds
        """
        self.ai_provider = ai_provider
        self.mcp_client = mcp_client
        self.session_manager = session_manager
        self.token_tracker = token_tracker
        self.tool_cache = tool_cache
        self.max_tokens = max_tokens
        self.enable_caching = enable_caching
        self.enable_streaming = enable_streaming
        self.show_tokens = show_tokens
        self.mcp_timeout = mcp_timeout

        self.tools = []
        self.tool_name_set = set()
        self.system_prompt = ""

    def initialize(self) -> None:
        """Initialize CLI with tools and system prompt."""
        if self.mcp_client:
            # Regular mode: fetch tools from MCP
            self.tools = self.mcp_client.fetch_tools(timeout=self.mcp_timeout)
            self.tool_name_set = {tool.get("name") for tool in self.tools if tool.get("name")}

            # Build system prompt for tool-based mode
            self.system_prompt = (
                "You are a security assistant using HexStrike MCP tools. "
                "Only request tool usage via tool_use blocks. "
                "The operator must approve every tool execution. "
                "Request only one tool at a time and wait for its output before proposing another. "
                "After each tool result, explain findings and propose the next step "
                "before waiting for the operator to proceed. "
                f"When you need operator input, end your response with {SessionManager.USER_INPUT_TOKEN} "
                "on its own line. Do not include it when requesting a tool."
            )
        else:
            # Guided mode: no tools, just suggest commands
            self.tools = []
            self.tool_name_set = set()

            # Build system prompt for guided mode
            self.system_prompt = (
                "You are a security assistant helping with penetration testing. "
                "The operator is running commands manually, so DO NOT use tool_use blocks. "
                "When asked to perform a scan or test, suggest specific shell commands they should run. "
                "Format your command suggestions clearly, for example:\n"
                "  Command to run: nmap -sV -sC example.com\n\n"
                "After suggesting a command, the operator will run it and paste the output. "
                "Then analyze the results and suggest the next step. "
                "Be specific about command-line flags and options. "
                "Focus on security testing tools like nmap, nikto, sqlmap, nuclei, curl, etc. "
                "Suggest one command at a time and wait for the operator to provide results."
            )

        # Display configuration
        if self.mcp_client:
            # Regular mode with MCP tools
            if self.enable_caching and self.ai_provider.supports_caching():
                print("✅ Prompt caching enabled (system + tools cached)")
            if self.token_tracker and self.show_tokens:
                print("📊 Token monitoring enabled")
            if self.tool_cache and self.tool_cache.enabled:
                print(f"🔄 Tool result caching enabled (TTL: {self.tool_cache.ttl_seconds}s)")
            if self.enable_streaming and self.ai_provider.supports_streaming():
                print("⚡ Streaming responses enabled")
            print("\nCommands: /exit | /tokens | /cache | /summarize | /sessions | /load <id>")
        else:
            # Guided mode
            if self.enable_caching and self.ai_provider.supports_caching():
                print("✅ Prompt caching enabled")
            if self.token_tracker and self.show_tokens:
                print("📊 Token monitoring enabled")
            if self.enable_streaming and self.ai_provider.supports_streaming():
                print("⚡ Streaming responses enabled")
            print("\nCommands: /exit | /tokens | /summarize | /sessions | /load <id>")
            print("\n💡 In guided mode: AI suggests commands, you run them and paste results back")

    def run(self) -> None:
        """Run the main conversation loop."""
        while True:
            user_input = self._prompt_user("\nuser> ").strip()
            if not user_input:
                continue

            # Handle exit command
            if user_input.lower() in {"/exit", "quit", "exit"}:
                break

            # Handle /tokens command
            if user_input.lower() == "/tokens":
                self._handle_tokens_command()
                continue

            # Handle /cache command
            if user_input.lower() in {"/cache", "/cache stats"}:
                self._handle_cache_stats_command()
                continue

            # Handle /cache clear command
            if user_input.lower() == "/cache clear":
                self._handle_cache_clear_command()
                continue

            # Handle /summarize command
            if user_input.lower() == "/summarize":
                self._handle_summarize_command()
                continue

            # Handle /sessions command
            if user_input.lower() == "/sessions":
                self._handle_sessions_command()
                continue

            # Handle /load command
            if user_input.lower().startswith("/load"):
                self._handle_load_command(user_input)
                continue

            # Add user message to conversation
            self.session_manager.add_user_message(user_input)

            # Inner loop for handling tool requests
            while True:
                # Get AI response
                try:
                    response = self.ai_provider.chat(
                        self.system_prompt,
                        self.session_manager.get_messages(),
                        self.tools,
                        self.max_tokens,
                        self.enable_caching and self.ai_provider.supports_caching(),
                        self.enable_streaming and self.ai_provider.supports_streaming(),
                    )

                    blocks = self._extract_blocks(response)
                    last_usage = response.get("usage", {})

                    # Track token usage
                    if self.token_tracker and last_usage:
                        self.token_tracker.update(last_usage)
                        self.session_manager.append_log({
                            "type": "token_usage",
                            "usage": last_usage,
                            "total_cost": self.token_tracker.calculate_cost(),
                        })

                except Exception as exc:
                    print(f"\n❌ Model invoke failed: {exc}")
                    break

                # Strip user input token
                blocks, user_input_requested = SessionManager.strip_user_input_token(blocks)

                # Show token usage if enabled
                if self.token_tracker and self.show_tokens and last_usage:
                    print(f"\n{self.token_tracker.format_summary(last_usage)}\n")
                    self._show_progressive_warnings()
                    self._check_auto_summarization()

                # Check for tool requests
                tool_blocks = [b for b in blocks if b.get("type") == "tool_use"]
                if not tool_blocks:
                    # In guided mode, always assume user needs to provide input
                    if not self.mcp_client:
                        self.session_manager.add_assistant_message(blocks)
                        break
                    # In tool mode, check if user input was requested
                    if not user_input_requested:
                        print("\n⚠️  Model did not request user input; returning to prompt.\n")
                    break

                # Add assistant message with tool request
                self.session_manager.add_assistant_message(blocks)

                # Handle multiple tools warning
                if len(tool_blocks) > 1:
                    print("\n⚠️  Multiple tools requested. Executing the first one only.\n")
                    self.session_manager.append_log({
                        "type": "tool_multi_requested",
                        "count": len(tool_blocks),
                    })

                # Execute first tool
                tool_block = tool_blocks[0]
                approved = self._handle_tool_execution(tool_block)

                if not approved:
                    print("\n⏸️  Tool execution denied. Waiting for your next instruction.\n")
                    break

                print("\n⏳ Processing tool output...\n")

        print("\nGoodbye.")
        self.session_manager.append_log({"type": "session_end"})

    def _handle_tokens_command(self) -> None:
        """Handle /tokens command."""
        if self.token_tracker:
            print(f"\n{self.token_tracker.format_summary()}\n")
        else:
            print("\n⚠️  Token tracking not available for this model source.\n")

    def _handle_cache_stats_command(self) -> None:
        """Handle /cache stats command."""
        if self.tool_cache:
            print(f"\n{self.tool_cache.format_stats()}\n")
        else:
            print("\n⚠️  Tool result caching is disabled.\n")

    def _handle_cache_clear_command(self) -> None:
        """Handle /cache clear command."""
        if self.tool_cache:
            num_entries = len(self.tool_cache.cache)
            self.tool_cache.clear()
            print(f"\n🗑️  Cache cleared ({num_entries} entries removed)\n")
        else:
            print("\n⚠️  Tool result caching is disabled.\n")

    def _handle_summarize_command(self) -> None:
        """Handle /summarize command."""
        if not self.ai_provider.supports_token_tracking():
            print("\n⚠️  Summarization only available for providers with token tracking.\n")
            return

        messages = self.session_manager.get_messages()
        if len(messages) < 4:
            print("\n⚠️  Not enough conversation history to summarize.\n")
            return

        print("\n🔄 Generating conversation summary...\n")
        summary = self.ai_provider.summarize(messages, max_tokens=2048)

        if summary:
            print("📝 Summary generated:")
            print("-" * 60)
            print(summary)
            print("-" * 60)

            # Ask user if they want to compress
            compress = self._prompt_user("\nCompress conversation context with this summary? [y/N]: ").strip().lower()
            if compress == "y":
                old_count = len(messages)
                self.session_manager.compress_context(summary, keep_recent=6)
                new_count = len(self.session_manager.get_messages())

                # Reset context tracking
                if self.token_tracker:
                    self.token_tracker.reset_context_tracking()

                # Log the summarization
                self.session_manager.append_log({
                    "type": "context_summarized",
                    "summary": summary,
                    "messages_before": old_count,
                    "messages_after": new_count,
                })

                print(f"\n✅ Context compressed: {old_count} messages → {new_count} messages")
                if self.token_tracker:
                    usage = self.token_tracker.get_context_usage()
                    print(f"   Context usage reset to ~{usage:.1f}%\n")
            else:
                print("\n⏸️  Context compression cancelled.\n")
        else:
            print("\n❌ Failed to generate summary.\n")

    def _handle_sessions_command(self) -> None:
        """Handle /sessions command."""
        sessions = SessionManager.list_sessions(str(self.session_manager.sessions_dir))

        if not sessions:
            print("\n📂 No saved sessions found.\n")
            return

        print(f"\n📂 Available sessions ({len(sessions)} total):\n")
        print(f"{'Session ID':<16} {'Created':<20} {'Model':<25} {'Size':<10}")
        print("-" * 80)

        for session in sessions[:20]:  # Show latest 20
            session_id = session.get("session_id", "")
            created = session.get("created_at", "Unknown")[:19].replace("T", " ")
            model = session.get("model_id", "Unknown")
            if len(model) > 24:
                model = model[:21] + "..."
            size = session.get("size", 0)
            size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"

            # Highlight current session
            marker = "→" if session_id == self.session_manager.session_id else " "
            print(f"{marker} {session_id:<14} {created:<20} {model:<25} {size_str:<10}")

        if len(sessions) > 20:
            print(f"\n... and {len(sessions) - 20} more sessions")

        print(f"\nCurrent session: {self.session_manager.session_id}")
        print("Use '/load <session_id>' to restore a previous session\n")

    def _handle_load_command(self, user_input: str) -> None:
        """Handle /load command."""
        parts = user_input.split(maxsplit=1)
        if len(parts) < 2:
            print("\n⚠️  Usage: /load <session_id>\n")
            return

        session_id = parts[1].strip()

        # Check if session exists
        session_file = self.session_manager.sessions_dir / f"{session_id}.jsonl"
        if not session_file.exists():
            print(f"\n❌ Session '{session_id}' not found.\n")
            return

        # Confirm load
        print(f"\n⚠️  Loading session '{session_id}' will end the current session.")
        confirm = self._prompt_user("Continue? [y/N]: ").strip().lower()
        if confirm != "y":
            print("\n⏸️  Load cancelled.\n")
            return

        # Close current session
        self.session_manager.append_log({"type": "session_end"})

        # Create new session manager with restoration
        from pwnpilot_lite.session.session_manager import SessionManager
        self.session_manager = SessionManager(
            sessions_dir=str(self.session_manager.sessions_dir),
            session_id=session_id,
            restore=True
        )

        # Reset token tracker if using Bedrock
        if self.token_tracker:
            from pwnpilot_lite.session.token_tracker import TokenTracker
            model_id = self.session_manager.metadata.get("model_id", "")
            self.token_tracker = TokenTracker(model_id)

        print(f"\n✅ Session '{session_id}' loaded with {len(self.session_manager.get_messages())} messages.\n")

    def _show_progressive_warnings(self) -> None:
        """Show progressive context warnings."""
        if not self.token_tracker:
            return

        if self.token_tracker.should_show_warning():
            usage = self.token_tracker.get_context_usage()
            level = self.token_tracker.get_warning_level()

            if level == "critical":
                print("🚨 " + "="*60)
                print("  CRITICAL: Context window nearly exhausted!")
                print(f"  Current usage: {usage:.1f}%")
                print("  Automatic summarization will trigger at next exchange.")
                print("  Alternative: Start a new session to avoid context limits.")
                print("="*60 + "\n")
            elif level == "high":
                print("⚠️  " + "-"*60)
                print("  WARNING: Context usage is high!")
                print(f"  Current usage: {usage:.1f}%")
                print("  Consider using context summarization soon.")
                print("  Type '/summarize' to compress context now.")
                print("-"*60 + "\n")
            elif level == "medium":
                print(f"ℹ️  Context usage: {usage:.1f}% - Monitoring recommended.\n")

    def _check_auto_summarization(self) -> None:
        """Check and perform automatic summarization if needed."""
        if not self.token_tracker:
            return

        messages = self.session_manager.get_messages()
        if self.token_tracker.should_summarize() and len(messages) >= 4:
            print("\n🔄 Context limit approaching - automatic summarization triggered...\n")

            summary = self.ai_provider.summarize(messages, max_tokens=2048)

            if summary:
                print("📝 Summary generated:")
                print("-" * 60)
                print(summary)
                print("-" * 60)

                # Automatically compress context
                old_count = len(messages)
                self.session_manager.compress_context(summary, keep_recent=6)
                new_count = len(self.session_manager.get_messages())

                # Reset context tracking
                self.token_tracker.reset_context_tracking()

                print(f"\n✅ Context auto-compressed: {old_count} messages → {new_count} messages")
                usage = self.token_tracker.get_context_usage()
                print(f"   Context usage reset to ~{usage:.1f}%")
                print("   This helps prevent context limit errors.\n")

                # Log the summarization
                self.session_manager.append_log({
                    "type": "context_auto_summarized",
                    "summary": summary,
                    "messages_before": old_count,
                    "messages_after": new_count,
                })
            else:
                print("\n⚠️  Automatic summarization failed. Consider starting a new session.\n")

    def _handle_tool_execution(self, tool_block: Dict[str, Any]) -> bool:
        """
        Handle tool execution with user approval.

        Returns:
            True if approved, False otherwise
        """
        tool_name = tool_block.get("name", "")
        tool_input = tool_block.get("input", {}) or {}
        tool_id = tool_block.get("id")

        print(f"\n🔧 Proposed tool: {tool_name}")
        print(f"   Input: {json.dumps(tool_input, indent=2)}")

        # Check if tool is known
        if tool_name not in self.tool_name_set:
            print(f"⚠️  Unknown tool requested: {tool_name}")
            tool_result = {
                "success": False,
                "error": "Unknown tool",
                "message": f"Tool '{tool_name}' is not available"
            }
            self.session_manager.append_log({
                "type": "tool_invalid",
                "tool_name": tool_name,
                "input": tool_input,
            })
            self.session_manager.add_tool_result(tool_id, tool_result)
            print("\n⏳ Processing tool output...\n")
            return False

        # Get user approval
        approval = self._prompt_user("Approve this command? [y/N]: ").strip().lower()
        if approval != "y":
            tool_result = {
                "success": False,
                "error": "User denied execution",
                "message": "Operator denied tool execution"
            }
            self.session_manager.append_log({
                "type": "tool_denied",
                "tool_name": tool_name,
                "input": tool_input,
            })
            cache_hit = False
        else:
            # Execute tool
            tool_result, cache_hit = self.mcp_client.execute_tool(tool_name, tool_input)

            output_preview = json.dumps(tool_result, indent=2)
            if len(output_preview) > 2000:
                output_preview = output_preview[:2000] + "..."

            if cache_hit:
                print(f"\n💚 Cached result (from previous execution):")
            else:
                print(f"\n📄 Tool output:")

            print(f"{output_preview}\n")

            self.session_manager.append_log({
                "type": "tool_output",
                "tool_name": tool_name,
                "input": tool_input,
                "result": tool_result,
                "cache_hit": cache_hit,
            })

        # Add tool result to conversation
        self.session_manager.add_tool_result(tool_id, tool_result)

        return approval == "y"

    @staticmethod
    def _prompt_user(prompt: str) -> str:
        """Prompt user for input with keyboard interrupt handling."""
        try:
            return input(prompt)
        except KeyboardInterrupt:
            return "/exit"

    @staticmethod
    def _extract_blocks(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract content blocks from AI response."""
        content = response.get("content", [])
        if isinstance(content, list):
            return content
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        return []
