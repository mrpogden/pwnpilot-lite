# Mode Switching Feature - Implementation Summary

## Overview

Added the ability to switch between **Tools Mode** and **Guided Mode** during an active pwnpilot-lite session.

## Changes Made

### 1. CLI Updates (`pwnpilot_lite/ui/cli.py`)

**New Commands:**
- `/guided` - Switch from Tools Mode to Guided Mode
- `/tools` - Switch from Guided Mode to Tools Mode

**New Handler Methods:**
- `_handle_guided_command()` - Handles switching to guided mode
  - Clears tools list
  - Reloads system prompt for guided mode
  - Logs mode switch to session
  - Shows confirmation and usage instructions

- `_handle_tools_command()` - Handles switching to tools mode
  - Re-fetches tools from MCP server
  - Reloads system prompt for tools mode
  - Logs mode switch to session
  - Shows confirmation and tool count

**Updated Command Lists:**
- Tools mode: Added `/guided` to command list
- Guided mode: Added `/tools` to command list

### 2. Session Logging

**New Log Entry Type:**
```json
{
  "type": "mode_switch",
  "from_mode": "tools",
  "to_mode": "guided",
  "timestamp": "2024-01-31T12:00:00Z",
  "session_id": "20240131120000"
}
```

### 3. Command Extractor Updates (`pwnpilot_lite/session/command_extractor.py`)

**Mode Switch Tracking:**
- Extracts mode switches from session logs
- Displays mode switches in audit reports
- Includes mode switches in all output formats (text, JSON, CSV, bash)

**Text Format Example:**
```
[2] 2024-01-31T12:08:15Z
    Mode Switch: tools → guided
    🔀 Operator changed session mode
```

**CSV Format:**
```csv
"2024-01-31T12:08:15Z","MODE_SWITCH","Mode: tools → guided","MODE_SWITCH",False,False
```

**Bash Script:**
Mode switches appear as comments:
```bash
# [2] 2024-01-31T12:08:15Z - Mode Switch: tools → guided
```

### 4. Documentation

**New Files:**
- `MODE_SWITCHING.md` - Comprehensive guide to mode switching
  - Overview of both modes
  - How to switch modes
  - Use cases for each mode
  - Examples and workflows
  - Troubleshooting

**Updated Files:**
- `README.md` - Added mode switching to key features and commands
- `COMMAND_EXTRACTOR.md` - Already supports mode switch tracking

## Usage Examples

### Example 1: Switch to Guided Mode

```bash
$ python3 main.py

user> /guided

🔀 Switch to Guided Mode?
   In guided mode:
   • AI suggests commands for you to run manually
   • No automatic tool execution
   • You paste command outputs back to AI
   • Use '/tools' to switch back to tools mode

Switch to guided mode? [y/N]: y

✅ Switched to Guided Mode
   AI will now suggest commands for you to run manually
   Use '/tools' to switch back to tools mode

user> scan the target
🤖 I recommend running: nmap -sV 192.168.1.100
```

### Example 2: Switch to Tools Mode

```bash
$ python3 main.py --guided-mode

user> /tools

🔀 Switch to Tools Mode?
   In tools mode:
   • AI can execute security tools automatically
   • You approve each command before execution
   • Results are automatically sent back to AI
   • Use '/guided' to switch back to guided mode

Switch to tools mode? [y/N]: y

⏳ Fetching tools from MCP server...
✅ HexStrike available: 87 tools ready

✅ Switched to Tools Mode (87 tools available)
   AI can now execute tools with your approval
   Use '/guided' to switch back to guided mode
```

### Example 3: View Mode Switches in Audit

```bash
$ python3 extract_commands.py -s 20240131120000

Command Audit Report - Session: 20240131120000
================================================================================
Total Commands: 5

[1] 2024-01-31T12:05:23Z
    Tool: nmap
    Command: nmap -sV 192.168.1.100
    Status: ✅ SUCCESS

[2] 2024-01-31T12:08:15Z
    Mode Switch: tools → guided
    🔀 Operator changed session mode

[3] 2024-01-31T12:15:42Z
    Mode Switch: guided → tools
    🔀 Operator changed session mode

[4] 2024-01-31T12:16:30Z
    Tool: nikto
    Command: nikto -h http://target.com
    Status: ✅ SUCCESS
```

## Technical Details

### Mode Switch Process

**Switching to Guided Mode:**
1. User types `/guided`
2. CLI prompts for confirmation
3. On confirmation:
   - `guided_mode` flag set to `True`
   - `tools` list cleared
   - `tool_name_set` cleared
   - System prompt reloaded with `guided_mode=True`
   - Mode switch logged to session file
   - Success message displayed

**Switching to Tools Mode:**
1. User types `/tools`
2. CLI prompts for confirmation
3. On confirmation:
   - `guided_mode` flag set to `False`
   - Tools fetched from MCP server
   - `tool_name_set` rebuilt
   - System prompt reloaded with `guided_mode=False`
   - Mode switch logged to session file
   - Success message with tool count displayed

### Limitations

- Switching to Tools Mode requires MCP server to be running
- If MCP server is unavailable, switch will fail with error message
- System prompt changes don't retroactively affect previous context
- Current conversation context is preserved during switch

## Testing Recommendations

1. **Basic Mode Switch:**
   - Start in tools mode, switch to guided
   - Start in guided mode, switch to tools
   - Verify commands work correctly in each mode

2. **MCP Server Availability:**
   - Try switching to tools mode when MCP is down
   - Verify appropriate error message
   - Confirm graceful failure

3. **Session Logging:**
   - Perform mode switches during session
   - Extract commands with `extract_commands.py`
   - Verify mode switches appear in audit

4. **Multiple Switches:**
   - Switch back and forth multiple times
   - Verify each switch logs correctly
   - Confirm tools reload properly each time

## Benefits

1. **Flexibility** - Users can adapt to changing needs mid-session
2. **Learning** - Switch to guided mode to see exact commands
3. **Remote Work** - Switch to guided for systems without MCP
4. **Audit Trail** - All mode switches are logged for compliance
5. **Seamless** - Conversation context preserved across switches
6. **Safe** - Confirmation required before switching

## Future Enhancements

Potential future improvements:
- Add `/mode` command to show current mode
- Auto-detect MCP availability and suggest mode
- Mode-specific prompt customization
- Per-tool mode switching (some auto, some manual)
- Mode switching via API/programmatic interface
