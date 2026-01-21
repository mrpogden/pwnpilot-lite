# Changelog

All notable changes to PwnPilot Lite will be documented in this file.

## [2.0.0] - 2026-01-19

### Added
- **Modular Architecture**: Refactored to clean modular structure
- **Per-Session Logging**: Each session in separate `.jsonl` file in `sessions/` directory
- **Session Restoration**: `/sessions` and `/load <id>` commands to restore previous sessions
- **Progressive Context Warnings**: 70%, 80%, 90% warnings with automatic summarization at 85%
- **Context Summarization**: `/summarize` command with AI-powered compression
- **AWS Region Auto-Detection**: Reads default region from AWS CLI config
- **Regional API Compatibility**: Fixed pagination issues in regions like `eu-north-1`
- **Guided Mode**: `--guided-mode` flag for manual command execution (no MCP server needed)
- **Configurable MCP Timeout**: `--mcp-timeout` flag for large tool deployments (default: 30s)
- **Comprehensive Documentation**: Added `HELP.md` with complete user guide

### Changed
- Entry point: `pwnpilot_lite.py` → `main.py`
- Session storage: `session.log` → `sessions/*.jsonl`

### Fixed
- "Cannot be paginated" error in certain AWS regions
- Context overflow issues with warnings and auto-summarization
- MCP health check timeouts in environments with many tools (100+)

## [1.0.0] - 2026-01-14

### Initial Release
- AWS Bedrock and Ollama support
- Tool execution with approval workflow
- Token tracking and prompt caching (Bedrock)
- Tool result caching
- HexStrike MCP integration
