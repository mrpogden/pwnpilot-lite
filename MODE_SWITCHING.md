# Mode Switching in PwnPilot-Lite

Switch between Tools Mode and Guided Mode during a session.

## Overview

PwnPilot-Lite supports two operational modes that you can switch between during an active session:

### Tools Mode (Default)
- AI can execute security tools automatically
- You approve each command before execution
- Results are automatically fed back to AI
- Full automation with human-in-the-loop approval

### Guided Mode
- AI suggests commands for you to run manually
- No automatic tool execution
- You paste command outputs back to AI
- Useful for:
  - Running commands on systems without MCP access
  - Complex multi-step workflows requiring manual intervention
  - Learning command syntax and tool usage
  - Situations where automation is not desired

## Switching Modes

### During Session Launch

Start in Tools Mode (default):
```bash
python3 main.py
```

Start in Guided Mode:
```bash
python3 main.py --guided-mode
```

### During Active Session

Switch from Tools Mode to Guided Mode:
```
user> /guided
```

Switch from Guided Mode to Tools Mode:
```
user> /tools
```

## Commands

### Tools Mode Commands
```
/exit          - Exit the session
/tokens        - Show token usage statistics
/cache         - Show tool cache statistics
/cache clear   - Clear tool result cache
/summarize     - Manually trigger context summarization
/sessions      - List all saved sessions
/load <id>     - Load a previous session
/summary       - Show session summary
/paste         - Enter multi-line input mode
/guided        - Switch to guided mode
```

### Guided Mode Commands
```
/exit          - Exit the session
/tokens        - Show token usage statistics
/summarize     - Manually trigger context summarization
/sessions      - List all saved sessions
/load <id>     - Load a previous session
/summary       - Show session summary
/prompt        - Switch to single-line input
/tools         - Switch to tools mode (if MCP available)
```

## Mode Switch Workflow

### Switching to Guided Mode

1. Type `/guided` in the conversation
2. Confirm the switch when prompted
3. AI will now suggest commands instead of executing them
4. You manually run the commands and paste results back

Example:
```
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

user> scan the target for open ports

🤖 I recommend running this command:

nmap -sV -p- 192.168.1.100

Please run this command and paste the output below (type 'END' when done).

[Paste output, type 'END' when done, or '/prompt' for single-line]>
```

### Switching to Tools Mode

1. Type `/tools` in the conversation
2. Confirm the switch when prompted
3. AI will re-fetch available tools from MCP server
4. Normal tool execution workflow resumes

Example:
```
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

## Use Cases

### Use Guided Mode When:

**Remote Systems**
- You need to run commands on a system without MCP access
- Working through SSH/RDP on a remote pentest target
- Testing environments where installing MCP is not possible

**Manual Workflows**
- Commands require interactive input
- Multi-step processes that need manual checkpoints
- Workflows involving GUI tools or browser interaction

**Learning and Documentation**
- You want to learn exact command syntax
- Building documentation of manual procedures
- Training scenarios where automation should be disabled

**Compliance and Control**
- Security policies require manual command execution
- Need more granular control over what runs
- Situations requiring command review before execution

### Use Tools Mode When:

**Automation**
- Standard security assessments
- Routine vulnerability scanning
- Automated enumeration and reconnaissance

**Efficiency**
- Large-scale testing requiring many tool executions
- Time-sensitive engagements
- Situations where manual execution is impractical

**Integration**
- Working within the local environment with MCP
- Tools are available and properly configured
- Full automation is desired

## Session Audit Trail

Mode switches are logged in the session file for audit purposes:

```bash
# View session including mode switches
python3 extract_commands.py -s 20240131120000
```

Example output:
```
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

### What Happens When Switching

**Switching to Guided Mode:**
1. Tools list is cleared
2. System prompt is reloaded for guided mode
3. AI behavior changes to suggest rather than execute
4. Input mode switches to multi-line after first prompt
5. Mode switch is logged in session file

**Switching to Tools Mode:**
1. Tools are re-fetched from MCP server
2. System prompt is reloaded for tools mode
3. AI behavior changes to request tool execution
4. Tool approval workflow is re-enabled
5. Mode switch is logged in session file

### Limitations

- Switching to Tools Mode requires MCP server to be running
- If MCP server is unavailable, you'll remain in Guided Mode
- System prompt changes don't affect previous conversation context
- Some advanced features (caching, etc.) behave differently in each mode

## Best Practices

1. **Start in the right mode** - Choose Tools or Guided at launch if you know your needs
2. **Switch when needed** - Don't hesitate to switch modes mid-engagement
3. **Document switches** - Session logs automatically track mode changes for audit
4. **Test connectivity** - Ensure MCP server is running before switching to Tools Mode
5. **Clear communication** - Tell AI when you're pasting results in Guided Mode

## Examples

### Example 1: Start Tools, Switch to Guided for Manual Work

```bash
# Start in tools mode
python3 main.py

user> enumerate the target
🔧 Proposed tool: nmap
Approve this command? [y/N]: y
[AI executes nmap and analyzes results]

user> /guided
[Switch to guided mode]

user> now use metasploit to exploit the vulnerability
🤖 I recommend using this Metasploit command:
msfconsole -x "use exploit/..."

[You manually run the command and paste results]
```

### Example 2: Start Guided, Switch to Tools for Automation

```bash
# Start in guided mode
python3 main.py --guided-mode

user> what should I scan first?
🤖 Start with a basic nmap scan: nmap -sV target.com
[Paste output, type 'END' when done, or '/prompt' for single-line]>
[You paste output]

user> /tools
[Switch to tools mode]

user> continue the assessment with automated tools
🔧 Proposed tool: nikto
[AI executes remaining tools automatically]
```

## Troubleshooting

**Can't switch to Tools Mode:**
- Verify MCP server is running: `curl http://localhost:8888/health`
- Check MCP URL configuration
- Restart MCP server if needed

**Commands not executing in Tools Mode:**
- Confirm you approved the command
- Check MCP server logs for errors
- Verify tools are installed on the system

**AI not suggesting commands in Guided Mode:**
- Ensure prompt is clear about what you want to do
- Ask AI to "suggest a command for..."
- Try switching to Tools mode if automation is desired
