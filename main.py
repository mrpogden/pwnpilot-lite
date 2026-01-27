#!/usr/bin/env python3
"""
PwnPilot Lite: AI-assisted penetration testing tool.

Main entry point for the application.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from pwnpilot_lite.core.bedrock_provider import BedrockProvider
from pwnpilot_lite.core.ollama_provider import OllamaProvider
from pwnpilot_lite.session.session_manager import SessionManager
from pwnpilot_lite.session.token_tracker import TokenTracker
from pwnpilot_lite.tools.mcp_client import MCPClient
from pwnpilot_lite.tools.tool_cache import ToolResultCache
from pwnpilot_lite.ui.cli import CLI


def load_env() -> None:
    """Load environment variables from config file."""
    config_path = os.path.join(os.path.dirname(__file__), "config", "credentials.env")
    if os.path.exists(config_path):
        load_dotenv(config_path, override=True)


def get_default_aws_region() -> str:
    """Get default AWS region from boto3 session config or fallback to us-east-1."""
    try:
        import boto3
        session = boto3.Session()
        region = session.region_name
        if region:
            return region
    except Exception:
        pass

    # Fallback to environment variable or us-east-1
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"


def setup_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    default_region = get_default_aws_region()

    parser = argparse.ArgumentParser(
        description="PwnPilot Lite - AI-assisted penetration testing tool"
    )
    parser.add_argument("--region", default=default_region,
                       help=f"AWS region (default: {default_region} from AWS config)")
    parser.add_argument("--mcp-url", default=os.getenv("MCP_URL", "http://localhost:8888"),
                       help="HexStrike MCP server URL")
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                       help="Ollama server URL")
    parser.add_argument("--max-tokens", type=int, default=4096,
                       help="Maximum tokens per response")
    parser.add_argument("--session-log", default=os.getenv("SESSION_LOG", "session.log"),
                       help="Session log file path")
    parser.add_argument("--enable-caching", action="store_true", default=True,
                       help="Enable prompt caching (default: enabled)")
    parser.add_argument("--disable-caching", action="store_true",
                       help="Disable prompt caching")
    parser.add_argument("--show-tokens", action="store_true", default=True,
                       help="Show token usage stats (default: enabled)")
    parser.add_argument("--enable-tool-cache", action="store_true", default=True,
                       help="Enable tool result caching (default: enabled)")
    parser.add_argument("--disable-tool-cache", action="store_true",
                       help="Disable tool result caching")
    parser.add_argument("--tool-cache-ttl", type=int, default=300,
                       help="Tool cache TTL in seconds (default: 300)")
    parser.add_argument("--enable-streaming", action="store_true", default=True,
                       help="Enable streaming responses (default: enabled)")
    parser.add_argument("--disable-streaming", action="store_true",
                       help="Disable streaming responses")
    parser.add_argument("--mcp-timeout", type=int, default=30,
                       help="MCP health check timeout in seconds (default: 30, increase for many tools)")
    parser.add_argument("--guided-mode", action="store_true",
                       help="Enable guided mode (AI suggests commands, you run them manually, no MCP needed)")
    parser.add_argument("--prompt-mode", choices=["basic", "advanced", "custom"], default="basic",
                       help="Prompt mode: basic (default), advanced (masterprompt), or custom")
    parser.add_argument("--prompt-file", type=str,
                       help="Path to custom prompt file (required for custom mode)")
    parser.add_argument("--target", type=str,
                       help="Target for security assessment (domain, IP, or organization)")
    return parser.parse_args()


def select_provider_type() -> str:
    """Prompt user to select AI provider type."""
    options = [
        ("AWS Bedrock", "bedrock"),
        ("Local (Ollama)", "ollama")
    ]
    print("\nSelect a model source:")
    for idx, (label, _) in enumerate(options, 1):
        print(f"{idx:>3}. {label}")

    while True:
        raw = input("\nChoose a source by number: ").strip()
        if raw.isdigit():
            choice_idx = int(raw)
            if 1 <= choice_idx <= len(options):
                return options[choice_idx - 1][1]
        print(f"Invalid selection. Enter a number between 1 and {len(options)}.")


def select_model(provider_type: str, region: str, ollama_url: str) -> tuple:
    """
    Select a model from available options.

    Returns:
        Tuple of (model_id, provider_instance)
    """
    if provider_type == "bedrock":
        print(f"\nRegion: {region}")
        models = BedrockProvider.list_available_models(region)

        if not models:
            print("No models available.")
            sys.exit(1)

        print("\nAvailable models:")
        for idx, model in enumerate(models, 1):
            print(f"{idx:>3}. {model['display']}")

        while True:
            raw = input("\nSelect a model/profile by number: ").strip()
            if raw.isdigit():
                choice_idx = int(raw)
                if 1 <= choice_idx <= len(models):
                    selected = models[choice_idx - 1]
                    model_id = selected['id']
                    provider = BedrockProvider(model_id, region)
                    return model_id, provider
            print(f"Invalid selection. Enter a number between 1 and {len(models)}.")

    else:  # ollama
        models = OllamaProvider.list_available_models(ollama_url)

        if not models:
            print("No models available.")
            sys.exit(1)

        print("\nAvailable models:")
        for idx, model in enumerate(models, 1):
            print(f"{idx:>3}. {model['display']}")

        while True:
            raw = input("\nSelect a model by number: ").strip()
            if raw.isdigit():
                choice_idx = int(raw)
                if 1 <= choice_idx <= len(models):
                    selected = models[choice_idx - 1]
                    model_id = selected['id']
                    provider = OllamaProvider(model_id, ollama_url)
                    return model_id, provider
            print(f"Invalid selection. Enter a number between 1 and {len(models)}.")


def show_disclaimer() -> None:
    """Display legal disclaimer and require acceptance."""
    print("\n" + "=" * 78)
    print("PWNPILOT LITE - LEGAL DISCLAIMER")
    print("=" * 78)
    print("""
⚠️  AUTHORIZED USE ONLY ⚠️

This tool is for AUTHORIZED security testing only. By using this software:

• You have EXPLICIT WRITTEN AUTHORIZATION to test target systems
• You will comply with ALL applicable laws and regulations
• You accept FULL RESPONSIBILITY for your actions
• You understand UNAUTHORIZED ACCESS is ILLEGAL

This software is provided "AS IS" with NO WARRANTY. The authors are NOT LIABLE
for any damages or legal consequences resulting from use or misuse.

See DISCLAIMER file for complete terms.
""")
    print("=" * 78)

    try:
        response = input("\nDo you accept these terms? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n❌ Disclaimer not accepted. Exiting.")
            sys.exit(0)
        print("✅ Disclaimer accepted. Starting PwnPilot Lite...\n")
    except KeyboardInterrupt:
        print("\n\n❌ Disclaimer not accepted. Exiting.")
        sys.exit(0)


def main() -> None:
    """Main entry point."""
    # Show disclaimer and require acceptance
    show_disclaimer()

    # Load environment
    load_env()

    # Parse arguments
    args = setup_arguments()

    # Initialize MCP client (skip in guided mode)
    mcp_client = None
    if not args.guided_mode:
        mcp_client = MCPClient(args.mcp_url)
        # Check MCP health (with configurable timeout for environments with many tools)
        if not mcp_client.check_health(timeout=args.mcp_timeout):
            sys.exit(1)
    else:
        print("\n🧭 Guided Mode: AI will suggest commands for you to run manually")
        print("   No HexStrike MCP server needed")
        print("   You run commands and paste results back\n")

    # Initialize session manager (uses per-session files in sessions/ directory)
    session_manager = SessionManager(sessions_dir="sessions")

    # Select AI provider
    provider_type = select_provider_type()
    session_manager.append_log({"type": "model_source", "value": provider_type})
    session_manager.update_metadata(model_source=provider_type)

    # Select model and create provider
    model_id, ai_provider = select_model(provider_type, args.region, args.ollama_url)
    session_manager.append_log({"type": "model_selected", "model_id": model_id})
    session_manager.update_metadata(model_id=model_id)

    print(f"\n📁 Session: {session_manager.session_id}")

    print(f"\nMCP URL: {args.mcp_url}")
    print(f"🔍 Model: {model_id}")

    # Initialize token tracker (for Bedrock only)
    token_tracker = None
    if ai_provider.supports_token_tracking():
        token_tracker = TokenTracker(model_id)
        if token_tracker.model_family:
            pricing = TokenTracker.PRICING.get(token_tracker.model_family, {})
            if pricing:
                input_price = pricing.get("input", 0)
                output_price = pricing.get("output", 0)
                cache_read_price = pricing.get("cache_read", 0)
                print(f"💰 Pricing: ${input_price}/1K in, ${output_price}/1K out (${cache_read_price}/1K cached)")
        else:
            print("⚠️  Pricing not available for this model")

    # Initialize tool cache
    tool_cache_enabled = not args.disable_tool_cache and args.enable_tool_cache
    tool_cache = ToolResultCache(
        ttl_seconds=args.tool_cache_ttl,
        enabled=tool_cache_enabled
    )

    # Set tool cache on MCP client (skip in guided mode)
    if mcp_client:
        mcp_client.tool_cache = tool_cache

    # Determine caching and streaming settings
    enable_caching = not args.disable_caching and args.enable_caching
    enable_streaming = not args.disable_streaming and args.enable_streaming

    # Handle target for advanced mode
    target = args.target
    if args.prompt_mode == "advanced" and not target:
        # Prompt for target if not provided
        print("\n🎯 Advanced mode requires a target specification")
        target = input("Please specify the target for this security assessment (domain, IP, or organization name): ").strip()
        if not target:
            print("⚠️  Target is required for advanced mode. Falling back to basic mode.")
            args.prompt_mode = "basic"

    # Store target in session if provided
    if target:
        session_manager.set_target(target)
        print(f"🎯 Target: {target}")

    # Initialize CLI
    cli = CLI(
        ai_provider=ai_provider,
        mcp_client=mcp_client,
        session_manager=session_manager,
        token_tracker=token_tracker,
        tool_cache=tool_cache,
        max_tokens=args.max_tokens,
        enable_caching=enable_caching,
        enable_streaming=enable_streaming,
        show_tokens=args.show_tokens,
        mcp_timeout=args.mcp_timeout,
        prompt_mode=args.prompt_mode,
        prompt_file=args.prompt_file,
        guided_mode=args.guided_mode,
    )

    # Initialize and run
    cli.initialize()
    cli.run()


if __name__ == "__main__":
    main()
