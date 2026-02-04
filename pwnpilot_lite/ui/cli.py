"""Command-line interface for PwnPilot Lite."""

import json
from typing import Any, Dict, List, Optional

from pwnpilot_lite.core.ai_provider import AIProvider
from pwnpilot_lite.core.action_classifier import ActionClassifier
from pwnpilot_lite.core.autonomous_manager import AutonomousManager
from pwnpilot_lite.prompts.prompt_loader import PromptLoader
from pwnpilot_lite.prompts.template_engine import TemplateEngine
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
        prompt_mode: str = "basic",
        prompt_file: Optional[str] = None,
        guided_mode: bool = False,
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
            prompt_mode: Prompt mode (basic, advanced, custom)
            prompt_file: Path to custom prompt file
            guided_mode: Whether in guided mode
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
        self.prompt_mode = prompt_mode
        self.prompt_file = prompt_file
        self.guided_mode = guided_mode

        self.tools = []
        self.tool_name_set = set()
        self.system_prompt = ""

        # Autonomous mode components
        self.action_classifier = ActionClassifier()
        self.autonomous_manager = AutonomousManager()

    def initialize(self) -> None:
        """Initialize CLI with tools and system prompt."""
        if self.mcp_client:
            # Regular mode: fetch tools from MCP
            self.tools = self.mcp_client.fetch_tools(timeout=self.mcp_timeout)
            self.tool_name_set = {tool.get("name") for tool in self.tools if tool.get("name")}
        else:
            # Guided mode: no tools, just suggest commands
            self.tools = []
            self.tool_name_set = set()

        # Load system prompt using prompt loader
        prompt_loader = PromptLoader()

        # Get template variables
        target = self.session_manager.get_target()
        session_id = self.session_manager.session_id
        model_id = self.session_manager.metadata.get("model_id", "unknown")

        variables = TemplateEngine.get_default_variables(
            target=target,
            session_id=session_id,
            model_id=model_id
        )

        # Load prompt based on mode
        self.system_prompt = prompt_loader.load_prompt(
            mode=self.prompt_mode,
            guided_mode=self.guided_mode,
            custom_file=self.prompt_file,
            variables=variables
        )

        # Show prompt mode info
        if self.prompt_mode == "advanced":
            print("🧠 Advanced Mode: Full OODA loop security assessment with Knowledge Graph")
        elif self.prompt_mode == "custom":
            print(f"📝 Custom Mode: Using prompt from {self.prompt_file}")

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
            print("\nCommands: /exit | /tokens | /cache | /summarize | /sessions | /load <id> | /summary | /paste | /guided | /autonomous | /scope")
        else:
            # Guided mode
            if self.enable_caching and self.ai_provider.supports_caching():
                print("✅ Prompt caching enabled")
            if self.token_tracker and self.show_tokens:
                print("📊 Token monitoring enabled")
            if self.enable_streaming and self.ai_provider.supports_streaming():
                print("⚡ Streaming responses enabled")
            print("\nCommands: /exit | /tokens | /summarize | /sessions | /load <id> | /summary | /prompt | /tools | /scope")
            print("\n💡 In guided mode:")
            print("   - First prompt: Single-line (ask your question)")
            print("   - After AI responds: Multi-line mode (paste output, type 'END')")
            print("   - Use '/prompt' to switch to single-line input anytime")

    def run(self) -> None:
        """Run the main conversation loop."""
        while True:
            # In guided mode, first prompt is single-line, then multi-line for subsequent prompts
            if not self.mcp_client:
                # Check if this is the first interaction (no messages yet)
                if len(self.session_manager.get_messages()) == 0:
                    prompt_text = "\nuser> "
                else:
                    prompt_text = "\n[Paste output, type 'END' when done, or '/prompt' for single-line]> "
            else:
                prompt_text = "\nuser> "

            user_input = self._prompt_user(prompt_text).strip()
            if not user_input:
                continue

            # Handle /prompt command (switch to single-line for this input)
            if user_input.lower() == "/prompt":
                user_input = self._prompt_user("user> ").strip()
                if not user_input:
                    continue

            # Handle /paste command for multi-line input (useful in tool mode)
            if user_input.lower() == "/paste":
                user_input = self._read_multiline_input()
                if not user_input:
                    continue

            # In guided mode (no mcp_client), if not a command and not first prompt, treat as multi-line input
            if not self.mcp_client and not user_input.startswith("/") and len(self.session_manager.get_messages()) > 0:
                # First line already captured, get the rest until END
                lines = [user_input]
                try:
                    while True:
                        line = input()
                        if line.strip() == "END":
                            break
                        lines.append(line)
                except KeyboardInterrupt:
                    print("\n⚠️  Input cancelled")
                    continue

                user_input = "\n".join(lines)
                if user_input.strip():
                    line_count = len(lines)
                    char_count = len(user_input)
                    print(f"\n✅ Captured {line_count} lines ({char_count} characters)\n")

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

            # Handle /guided command - switch to guided mode
            if user_input.lower() == "/guided":
                self._handle_guided_command()
                continue

            # Handle /tools command - switch to tools mode
            if user_input.lower() == "/tools":
                self._handle_tools_command()
                continue

            # Handle /summary command
            if user_input.lower() == "/summary":
                self._handle_summary_command()
                continue

            # Handle /autonomous command - enter autonomous mode
            if user_input.lower().startswith("/autonomous"):
                self._handle_autonomous_command(user_input)
                continue

            # Handle /prompt command
            # In autonomous mode: exit to prompt mode
            # In guided mode after first message: switch to single-line input
            if user_input.lower() == "/prompt":
                if self.autonomous_manager.active:
                    self._handle_prompt_command()
                    continue
                else:
                    # In guided mode, this is already handled above
                    # Just continue to let normal flow handle it
                    pass

            # Handle /scope command - manage scope
            if user_input.lower().startswith("/scope"):
                self._handle_scope_command(user_input)
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

                # Reset context tracking with accurate message count
                if self.token_tracker:
                    self.token_tracker.reset_context_tracking(messages_after_compression=new_count)

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

    def _handle_summary_command(self) -> None:
        """Handle /summary command."""
        print("\n" + self.session_manager.format_summary_display() + "\n")

    def _handle_guided_command(self) -> None:
        """Handle /guided command - switch to guided mode."""
        if not self.mcp_client:
            print("\n⚠️  Already in guided mode.\n")
            return

        # Confirm switch
        print("\n🔀 Switch to Guided Mode?")
        print("   In guided mode:")
        print("   • AI suggests commands for you to run manually")
        print("   • No automatic tool execution")
        print("   • You paste command outputs back to AI")
        print("   • Use '/tools' to switch back to tools mode")
        confirm = self._prompt_user("\nSwitch to guided mode? [y/N]: ").strip().lower()

        if confirm != "y":
            print("\n⏸️  Mode switch cancelled.\n")
            return

        # Switch to guided mode
        self.guided_mode = True
        self.tools = []
        self.tool_name_set = set()

        # Reload system prompt for guided mode
        from pwnpilot_lite.prompts.prompt_loader import PromptLoader
        from pwnpilot_lite.prompts.template_engine import TemplateEngine

        prompt_loader = PromptLoader()
        template_engine = TemplateEngine()

        variables = {
            "target": self.session_manager.metadata.get("target", "[not set]"),
            "knowledge_graph": self.session_manager.metadata.get("knowledge_graph", {}),
        }

        self.system_prompt = prompt_loader.load_prompt(
            mode=self.prompt_mode,
            guided_mode=True,
            custom_file=self.prompt_file,
            variables=variables
        )

        # Log mode switch
        self.session_manager.append_log({
            "type": "mode_switch",
            "from_mode": "tools",
            "to_mode": "guided"
        })

        print("\n✅ Switched to Guided Mode")
        print("   AI will now suggest commands for you to run manually")
        print("   Use '/tools' to switch back to tools mode\n")

    def _handle_tools_command(self) -> None:
        """Handle /tools command - switch to tools mode."""
        if self.mcp_client is None:
            print("\n❌ Tools mode not available - MCP client not initialized")
            print("   Restart with MCP server enabled to use tools mode\n")
            return

        if not self.guided_mode:
            print("\n⚠️  Already in tools mode.\n")
            return

        # Confirm switch
        print("\n🔀 Switch to Tools Mode?")
        print("   In tools mode:")
        print("   • AI can execute security tools automatically")
        print("   • You approve each command before execution")
        print("   • Results are automatically sent back to AI")
        print("   • Use '/guided' to switch back to guided mode")
        confirm = self._prompt_user("\nSwitch to tools mode? [y/N]: ").strip().lower()

        if confirm != "y":
            print("\n⏸️  Mode switch cancelled.\n")
            return

        # Switch to tools mode
        self.guided_mode = False

        # Re-fetch tools from MCP
        print("\n⏳ Fetching tools from MCP server...")
        self.tools = self.mcp_client.fetch_tools(timeout=self.mcp_timeout)
        self.tool_name_set = {tool.get("name") for tool in self.tools if tool.get("name")}

        # Reload system prompt for tools mode
        from pwnpilot_lite.prompts.prompt_loader import PromptLoader
        from pwnpilot_lite.prompts.template_engine import TemplateEngine

        prompt_loader = PromptLoader()
        template_engine = TemplateEngine()

        variables = {
            "target": self.session_manager.metadata.get("target", "[not set]"),
            "knowledge_graph": self.session_manager.metadata.get("knowledge_graph", {}),
        }

        self.system_prompt = prompt_loader.load_prompt(
            mode=self.prompt_mode,
            guided_mode=False,
            custom_file=self.prompt_file,
            variables=variables
        )

        # Log mode switch
        self.session_manager.append_log({
            "type": "mode_switch",
            "from_mode": "guided",
            "to_mode": "tools"
        })

        print(f"\n✅ Switched to Tools Mode ({len(self.tools)} tools available)")
        print("   AI can now execute tools with your approval")
        print("   Use '/guided' to switch back to guided mode\n")

    def _handle_autonomous_command(self, user_input: str) -> None:
        """Handle /autonomous command - enter autonomous mode."""
        if not self.mcp_client:
            print("\n❌ Autonomous mode requires tools mode")
            print("   Start with MCP server enabled to use autonomous mode\n")
            return

        if self.autonomous_manager.active:
            print("\n⚠️  Already in autonomous mode")
            print(self.autonomous_manager.get_status())
            return

        # Parse arguments: /autonomous [--iterations N] [--tokens N] [--delay S] [objective]
        parts = user_input.split(maxsplit=1)
        args_str = parts[1] if len(parts) > 1 else ""

        max_iterations = None
        max_tokens = None
        iteration_delay = 2.0  # Default 2 seconds between iterations
        objective = ""

        # Simple argument parsing
        import re
        iter_match = re.search(r'--iterations?\s+(\d+)', args_str)
        token_match = re.search(r'--tokens?\s+(\d+)', args_str)
        delay_match = re.search(r'--delay\s+(\d+(?:\.\d+)?)', args_str)

        if iter_match:
            max_iterations = int(iter_match.group(1))
            args_str = args_str[:iter_match.start()] + args_str[iter_match.end():]

        if token_match:
            max_tokens = int(token_match.group(1))
            args_str = args_str[:token_match.start()] + args_str[token_match.end():]

        if delay_match:
            iteration_delay = float(delay_match.group(1))
            args_str = args_str[:delay_match.start()] + args_str[delay_match.end():]

        objective = args_str.strip()

        # Show warning and get confirmation
        print("\n" + "="*60)
        print("⚠️  AUTONOMOUS MODE WARNING")
        print("="*60)
        print("The agent will operate continuously until:")
        print("  • The objective is achieved")
        print("  • You type /prompt to return to normal mode")
        if max_iterations:
            print(f"  • Maximum iterations reached ({max_iterations})")
        if max_tokens:
            print(f"  • Maximum tokens spent ({max_tokens:,})")
        print()
        print("Safety Controls:")
        print("  • SAFE: Actions on in-scope targets")
        print("  • NEEDS APPROVAL: Destructive actions")
        print("  • FORBIDDEN: Out-of-scope or local filesystem destruction")
        print()
        print(self.action_classifier.get_scope_summary())
        print()

        if not objective:
            print("❌ No objective provided")
            print("Usage: /autonomous [--iterations N] [--tokens N] [--delay S] <objective>")
            print("Example: /autonomous --iterations 50 --delay 3 scan target and exploit vulnerabilities\n")
            return

        print(f"   Rate limiting: {iteration_delay}s delay between iterations")
        print()

        confirm = self._prompt_user("Start autonomous mode? [y/N]: ").strip().lower()
        if confirm != "y":
            print("\n⏸️  Autonomous mode cancelled\n")
            return

        # Initialize autonomous mode
        self.autonomous_manager = AutonomousManager(
            max_iterations=max_iterations,
            max_tokens=max_tokens,
            iteration_delay=iteration_delay
        )
        self.autonomous_manager.start()

        # Log autonomous mode start
        self.session_manager.append_log({
            "type": "autonomous_mode_start",
            "objective": objective,
            "max_iterations": max_iterations,
            "max_tokens": max_tokens,
            "scope": self.action_classifier.scope_targets
        })

        print("\n🤖 Autonomous mode activated")
        print(f"   Objective: {objective}")
        print(self.autonomous_manager.get_status())
        print()

        # Add objective as user message and start autonomous loop
        self.session_manager.add_user_message(f"[AUTONOMOUS MODE] {objective}")
        self._run_autonomous_loop()

    def _handle_prompt_command(self) -> None:
        """Handle /prompt command - exit autonomous mode."""
        if not self.autonomous_manager.active:
            print("\n⚠️  Not in autonomous mode\n")
            return

        self.autonomous_manager.pause()
        reason = self.autonomous_manager.get_stop_reason()

        print(f"\n⏸️  Autonomous mode paused: {reason}")
        print(f"   Completed {self.autonomous_manager.iterations} iterations")
        print(f"   Used {self.autonomous_manager.tokens_used:,} tokens\n")

        # Log autonomous mode stop
        self.session_manager.append_log({
            "type": "autonomous_mode_stop",
            "reason": reason,
            "iterations": self.autonomous_manager.iterations,
            "tokens_used": self.autonomous_manager.tokens_used
        })

        self.autonomous_manager.stop()
        print("✅ Returned to prompt mode\n")

    def _handle_scope_command(self, user_input: str) -> None:
        """Handle /scope command - manage scope."""
        parts = user_input.split(maxsplit=2)

        if len(parts) == 1:
            # Just /scope - show current scope
            print("\n" + self.action_classifier.get_scope_summary() + "\n")
            return

        subcommand = parts[1].lower()

        if subcommand == "add" and len(parts) == 3:
            target = parts[2]

            # Warn if target contains protocol prefix
            if target.startswith(("http://", "https://", "ftp://", "ftps://")):
                print(f"\n⚠️  Warning: Target contains protocol prefix: {target}")
                print("   Scope targets should be hostnames, IPs, or subnets WITHOUT protocols")
                print("   Examples:")
                print("     • Hostnames: example.com, testphp.vulnweb.com")
                print("     • IP addresses: 192.168.1.100, 10.10.11.50")
                print("     • Subnets: 192.168.1.0/24, 10.10.10.0/24")
                print(f"\n   Adding anyway, but consider using: {target.split('://', 1)[1] if '://' in target else target}\n")

            self.action_classifier.add_scope_target(target)
            print(f"✅ Added '{target}' to scope\n")

        elif subcommand == "remove" and len(parts) == 3:
            target = parts[2]
            self.action_classifier.remove_scope_target(target)
            print(f"\n✅ Removed '{target}' from scope\n")

        elif subcommand == "clear":
            self.action_classifier.scope_targets = []
            print("\n✅ Cleared all scope targets\n")

        else:
            print("\n⚠️  Usage:")
            print("   /scope              - Show current scope")
            print("   /scope add <target> - Add target to scope")
            print("   /scope remove <target> - Remove target from scope")
            print("   /scope clear        - Clear all scope targets")
            print("\n📋 Scope Target Examples:")
            print("   • Hostnames: example.com, testphp.vulnweb.com")
            print("   • IP addresses: 192.168.1.100, 10.10.11.50")
            print("   • Subnets: 192.168.1.0/24, 10.10.10.0/24")
            print("\n⚠️  DO NOT include protocol prefixes (http://, https://, etc.)\n")

    def _run_autonomous_loop(self) -> None:
        """Run the autonomous operation loop."""
        import time

        while self.autonomous_manager.should_continue():
            self.autonomous_manager.increment_iteration()

            print(f"\n{'='*60}")
            print(f"🤖 Autonomous Iteration {self.autonomous_manager.iterations}")
            print(f"{'='*60}\n")

            try:
                # Get AI response with exponential backoff retry
                response = self._call_ai_with_retry()

                blocks = self._extract_blocks(response)
                last_usage = response.get("usage", {})

                # Track token usage
                if self.token_tracker and last_usage:
                    self.token_tracker.update(last_usage)
                    self.autonomous_manager.add_tokens(
                        last_usage.get("input_tokens", 0) + last_usage.get("output_tokens", 0)
                    )

                # Check for tool requests
                tool_blocks = [b for b in blocks if b.get("type") == "tool_use"]

                if not tool_blocks:
                    # No tool requested, AI thinks it's done
                    print("\n✅ AI indicates objective complete or no further actions")
                    self.session_manager.add_assistant_message(blocks)
                    break

                # Add assistant message with tool request
                self.session_manager.add_assistant_message(blocks)

                # Process first tool (autonomous mode handles one at a time)
                tool_block = tool_blocks[0]
                approved = self._handle_autonomous_tool_execution(tool_block)

                if not approved:
                    print("\n⏸️  Action blocked or denied - pausing autonomous mode")
                    self.autonomous_manager.pause()
                    break

            except KeyboardInterrupt:
                print("\n\n⏸️  Keyboard interrupt - pausing autonomous mode")
                self.autonomous_manager.pause()
                break

            except KeyError as exc:
                # Handle response parsing errors
                print(f"\n❌ Response parsing error: {exc}")
                print("   Continuing to next iteration...")
                continue

            except Exception as exc:
                error_msg = str(exc)
                print(f"\n❌ Error in autonomous loop: {error_msg}")

                # Check if it's a throttling error
                if "ThrottlingException" in error_msg or "Too many requests" in error_msg:
                    print("   Rate limit exceeded - this should have been handled by retry logic")
                    print("   Increase --delay or reduce iteration speed")

                self.autonomous_manager.pause()
                break

        # Autonomous loop ended
        if not self.autonomous_manager.active:
            return

        reason = self.autonomous_manager.get_stop_reason()
        print(f"\n{'='*60}")
        print(f"⏸️  Autonomous mode stopped: {reason}")
        print(f"{'='*60}")
        print(f"   Completed {self.autonomous_manager.iterations} iterations")
        print(f"   Used {self.autonomous_manager.tokens_used:,} tokens\n")

        self.session_manager.append_log({
            "type": "autonomous_mode_stop",
            "reason": reason,
            "iterations": self.autonomous_manager.iterations,
            "tokens_used": self.autonomous_manager.tokens_used
        })

        self.autonomous_manager.stop()

    def _call_ai_with_retry(self, max_retries: int = 5) -> Dict[str, Any]:
        """
        Call AI provider with exponential backoff retry.

        Args:
            max_retries: Maximum number of retries

        Returns:
            AI response

        Raises:
            Exception: If all retries fail
        """
        import time

        for attempt in range(max_retries):
            try:
                response = self.ai_provider.chat(
                    self.system_prompt,
                    self.session_manager.get_messages(),
                    self.tools,
                    self.max_tokens,
                    self.enable_caching and self.ai_provider.supports_caching(),
                    self.enable_streaming and self.ai_provider.supports_streaming(),
                )
                return response

            except Exception as exc:
                error_msg = str(exc)

                # Check if it's a throttling error
                is_throttle = "ThrottlingException" in error_msg or "Too many requests" in error_msg

                if is_throttle and attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    print(f"\n⚠️  Rate limit hit - waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Not a throttle error, or out of retries
                    raise

        raise Exception(f"Failed after {max_retries} retries")

    def _handle_autonomous_tool_execution(self, tool_block: Dict[str, Any]) -> bool:
        """
        Handle tool execution in autonomous mode with safety classification.

        Returns:
            True if executed, False if blocked/denied
        """
        tool_name = tool_block.get("name", "")
        tool_input = tool_block.get("input", {}) or {}
        tool_id = tool_block.get("id")

        # Classify action
        classification, reason = self.action_classifier.classify_action(tool_name, tool_input)

        print(f"\n🔧 Proposed tool: {tool_name}")
        print(f"   Input: {json.dumps(tool_input, indent=2)}")
        print(f"   Classification: {classification}")
        print(f"   Reason: {reason}")

        # Handle based on classification
        if classification == "FORBIDDEN":
            print("   ❌ Action FORBIDDEN - will not execute")
            tool_result = {
                "success": False,
                "error": "Action forbidden",
                "message": f"Action blocked by safety controls: {reason}"
            }
            self.session_manager.add_tool_result(tool_id, tool_result)
            return False

        elif classification == "NEEDS_APPROVAL":
            print("   ⚠️  Action NEEDS APPROVAL")
            approval = self._prompt_user("   Approve this action? [y/N]: ").strip().lower()

            if approval != "y":
                print("   ❌ Action denied by operator")
                tool_result = {
                    "success": False,
                    "error": "User denied execution",
                    "message": "Operator denied destructive action"
                }
                self.session_manager.add_tool_result(tool_id, tool_result)
                return False

            print("   ✅ Action approved by operator")

        else:  # SAFE
            print("   ✅ Action SAFE - executing automatically")

        # Execute the tool
        tool_result, cache_hit = self.mcp_client.execute_tool(tool_name, tool_input)

        output_preview = json.dumps(tool_result, indent=2)
        if len(output_preview) > 1000:
            output_preview = output_preview[:1000] + "..."

        if cache_hit:
            print(f"\n💚 Cached result:")
        else:
            print(f"\n📄 Tool output:")

        print(f"{output_preview}\n")

        self.session_manager.append_log({
            "type": "autonomous_tool_execution",
            "tool_name": tool_name,
            "input": tool_input,
            "classification": classification,
            "result": tool_result,
            "cache_hit": cache_hit,
        })

        # Add tool result to conversation
        self.session_manager.add_tool_result(tool_id, tool_result)

        return True

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

                # Reset context tracking with accurate message count
                self.token_tracker.reset_context_tracking(messages_after_compression=new_count)

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

    def _read_multiline_input(self) -> str:
        """
        Read multi-line input from user.

        User pastes content and types 'END' on its own line to finish.
        Returns concatenated input as a single string.
        """
        print("\n📝 Multi-line input mode activated")
        print("   Paste your content (can be multiple lines)")
        print("   Type 'END' on a new line when finished\n")

        lines = []
        try:
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
        except KeyboardInterrupt:
            print("\n⚠️  Multi-line input cancelled")
            return ""

        result = "\n".join(lines)
        if result:
            line_count = len(lines)
            char_count = len(result)
            print(f"\n✅ Captured {line_count} lines ({char_count} characters)\n")
        else:
            print("\n⚠️  No input captured\n")

        return result

    @staticmethod
    def _extract_blocks(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract content blocks from AI response."""
        content = response.get("content", [])
        if isinstance(content, list):
            return content
        if isinstance(content, str):
            return [{"type": "text", "text": content}]
        return []
