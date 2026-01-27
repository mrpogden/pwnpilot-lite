# Changelog

All notable changes to PwnPilot Lite will be documented in this file.

## [2.1.0] - 2026-01-26

### Added
- **Legal Disclaimer**: Comprehensive disclaimer system
  - Displayed at startup requiring user acceptance
  - Complete DISCLAIMER file with all terms
  - Authorization and legal use requirements
  - Liability and warranty disclaimers
  - Ethical use and responsible disclosure guidelines
  - Professional ethics standards
  - Added to README.md for visibility
- **Multi-line Input Mode**: Enhanced multi-line input handling for guided mode
  - **First prompt is single-line**: Ask your initial question normally
  - **Subsequent prompts auto-switch to multi-line**: Perfect for pasting command output
  - Just paste your output and type 'END' on a new line - no command needed
  - Use `/prompt` command to switch back to single-line input anytime
  - **In Tool Mode**: Use `/paste` command to enter multi-line mode
  - Solves guided mode issue where line breaks interrupted input
  - Shows line and character count confirmation after capture
- **Prompt System**: Flexible prompt loading system with three modes (basic, advanced, custom)
- **Advanced Mode (Masterprompt)**: Full OODA loop security assessment methodology
  - Comprehensive OODA loop framework (Observe, Orient, Decide, Act, Validate)
  - Knowledge Graph tracking for discovered assets and relationships
  - Phased assessment approach with progressive disclosure
  - Tool rotation strategy for failure recovery
  - Recursive discovery of new assets
  - Confidence ratings for all findings (CONFIRMED, LIKELY, POSSIBLE, INCONCLUSIVE)
  - Tech-stack fingerprinting before testing
  - Context-aware vulnerability scanning
  - Ethics and legal guardrails
  - Self-check protocol for quality assurance
- **Custom Prompts**: Load custom prompt templates with variable support
- **Template Engine**: Dynamic variable replacement in prompts
  - `{{TARGET}}` - Target specification
  - `{{SESSION_ID}}` - Session identifier
  - `{{DATE}}` - Current date
  - `{{MODEL_ID}}` - Model being used
- **Target Tracking**: Store and restore target across sessions
- **Knowledge Graph Storage**: Persist and restore Knowledge Graph in sessions
- **Prompt Files**: Organized prompt templates in `prompts/` directory
- **JSON Schemas**: Schema definitions for Knowledge Graph and vulnerabilities
- **Examples**: Sample assessment report showing expected output
- **New CLI Arguments**:
  - `--prompt-mode`: Choose basic, advanced, or custom mode
  - `--prompt-file`: Path to custom prompt file
  - `--target`: Specify target for security assessment
- **Session Manager Extensions**:
  - `set_target()` and `get_target()` methods
  - `update_knowledge_graph()` and `get_knowledge_graph()` methods
  - Target and Knowledge Graph restoration from saved sessions

### Changed
- System prompts now loaded from files instead of hardcoded
- Fallback to hardcoded prompts if files are missing (backward compatibility)
- CLI initialization refactored to use PromptLoader
- Enhanced session restoration to include target and Knowledge Graph

### Documentation
- Comprehensive prompt modes documentation in README.md
- Created `prompts/README.md` with prompt usage guide
- Created `schemas/README.md` with schema documentation
- Created `examples/README.md` with example outputs
- Updated configuration table with new options

### Backward Compatibility
- Default behavior unchanged (uses basic mode)
- Existing sessions continue to work
- Fallback to hardcoded prompts if files missing
- No breaking changes to APIs

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
