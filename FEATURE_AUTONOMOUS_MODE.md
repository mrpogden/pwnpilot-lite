# Feature: Autonomous Mode Implementation

## Overview

Implemented autonomous mode for pwnpilot-lite, enabling AI-driven continuous operation toward a defined objective with comprehensive safety controls.

## Components Added

### 1. Action Classifier (`pwnpilot_lite/core/action_classifier.py`)

**Purpose:** Classifies every action as SAFE, NEEDS_APPROVAL, or FORBIDDEN

**Features:**
- Pattern matching for destructive commands
- Local filesystem protection
- Scope enforcement
- Configurable target scope

**Classifications:**
- **SAFE**: In-scope, non-destructive actions → Execute automatically
- **NEEDS_APPROVAL**: Destructive actions → Require user confirmation
- **FORBIDDEN**: Out-of-scope or local destruction → Always blocked

**Protected Patterns:**
- `rm -rf`, `mkfs`, `dd` - Filesystem destruction
- `/home/`, `/etc/`, `~/` - Local filesystem paths
- `shutdown`, `reboot` - System control
- Out-of-scope targets

### 2. Autonomous Manager (`pwnpilot_lite/core/autonomous_manager.py`)

**Purpose:** Manages autonomous mode state and limits

**Features:**
- Iteration counting and limits
- Token usage tracking and limits
- Pause/stop control
- Status reporting

**Limits:**
- `max_iterations`: Stop after N AI response cycles
- `max_tokens`: Stop after N tokens consumed
- Manual pause via `/prompt` command

### 3. CLI Integration (`pwnpilot_lite/ui/cli.py`)

**New Methods:**
- `_handle_autonomous_command()` - Enter autonomous mode
- `_handle_prompt_command()` - Exit autonomous mode
- `_handle_scope_command()` - Manage scope
- `_run_autonomous_loop()` - Main autonomous operation loop
- `_handle_autonomous_tool_execution()` - Execute tools with safety checks

**New Commands:**
- `/autonomous [--iterations N] [--tokens N] <objective>` - Start autonomous mode
- `/prompt` - Exit autonomous mode (also works in guided mode)
- `/scope` - Show current scope
- `/scope add <target>` - Add target to scope
- `/scope remove <target>` - Remove target from scope
- `/scope clear` - Clear all scope targets

## Usage

### Basic Workflow

1. **Define Scope:**
   ```bash
   /scope add target.htb
   /scope add 192.168.1.100
   ```

2. **Start Autonomous Mode:**
   ```bash
   /autonomous --iterations 50 scan and exploit target.htb
   ```

3. **Agent Operates:**
   - SAFE actions execute automatically
   - NEEDS_APPROVAL actions require confirmation
   - FORBIDDEN actions are blocked

4. **Exit When Done:**
   ```bash
   /prompt  # or agent completes objective
   ```

### Example Session

```bash
user> /scope add target.htb
✅ Added 'target.htb' to scope

user> /autonomous --iterations 30 scan target.htb for vulnerabilities

⚠️  AUTONOMOUS MODE WARNING
[... warning and safety info ...]

Start autonomous mode? [y/N]: y

============================================================
🤖 Autonomous Iteration 1
============================================================

🔧 Proposed tool: nmap
   Classification: SAFE
   ✅ Action SAFE - executing automatically

[... tool output ...]

============================================================
🤖 Autonomous Iteration 2
============================================================

🔧 Proposed tool: sqlmap
   Classification: NEEDS_APPROVAL
   ⚠️  Action NEEDS APPROVAL
   Approve this action? [y/N]: y
   ✅ Action approved by operator

[... continues until objective complete or limits reached ...]
```

## Safety Controls

### Three-Tier Classification

1. **SAFE (Auto-execute):**
   - Target in scope
   - Non-destructive operations
   - Reconnaissance, enumeration
   - Read-only queries

2. **NEEDS APPROVAL (User confirmation):**
   - Exploitation attempts
   - Credential attacks
   - Database modifications
   - System changes

3. **FORBIDDEN (Always blocked):**
   - Out-of-scope targets
   - Local filesystem destruction
   - System shutdown/reboot
   - Device writes

### Scope Enforcement

All targets must be explicitly added to scope:
```bash
/scope add target.com
/scope add 10.10.11.50
```

Actions on targets NOT in scope are FORBIDDEN.

### Local Filesystem Protection

Destructive actions on local filesystem are ALWAYS forbidden:
- `rm -rf /home/...`
- `format /dev/...`
- `dd if=/dev/zero of=/...`
- Any destructive operation on `/home/`, `/etc/`, etc.

## Configuration Options

### Iteration Limit

```bash
/autonomous --iterations 50 <objective>
```

Stops after 50 AI response cycles. Useful for:
- Preventing infinite loops
- Budget control
- Phased operations

### Token Limit

```bash
/autonomous --tokens 100000 <objective>
```

Stops after consuming 100K tokens. Useful for:
- Cost control
- Resource management
- Long-running tasks

### Combined Limits

```bash
/autonomous --iterations 30 --tokens 50000 <objective>
```

Stops when EITHER limit is reached.

## Session Logging

All autonomous operations are logged:

```json
{
  "type": "autonomous_mode_start",
  "objective": "scan and exploit target",
  "max_iterations": 50,
  "max_tokens": 100000,
  "scope": ["target.htb"]
}

{
  "type": "autonomous_tool_execution",
  "tool_name": "nmap",
  "classification": "SAFE",
  "result": {...}
}

{
  "type": "autonomous_mode_stop",
  "reason": "Maximum iterations reached",
  "iterations": 50,
  "tokens_used": 87234
}
```

Extract audit trail:
```bash
python3 extract_commands.py -s <session_id>
```

## Integration

### Works With

- ✅ Token tracking and cost monitoring
- ✅ Tool result caching
- ✅ Context auto-summarization
- ✅ Session restoration
- ✅ All MCP tools

### Requires

- ✅ Tools mode (MCP server)
- ✅ Token tracker (for limits)

### Does Not Work With

- ❌ Guided mode (requires tools)

## Use Cases

### 1. CTF/HackTheBox

```bash
/scope add machine.htb
/autonomous --iterations 50 pwn machine.htb and capture flags
```

### 2. Vulnerability Assessment

```bash
/scope add app.client.com
/autonomous --iterations 100 perform OWASP Top 10 assessment
```

### 3. Penetration Testing

```bash
/scope add 192.168.1.0/24
/autonomous --iterations 200 enumerate and identify exploitation opportunities
```

### 4. Bug Bounty

```bash
/scope add *.target.com
/autonomous --iterations 75 enumerate subdomains and find vulnerabilities
```

## Technical Details

### Loop Structure

```python
while autonomous_manager.should_continue():
    # Get AI response
    # Check for tool requests
    # Classify action (SAFE/NEEDS_APPROVAL/FORBIDDEN)
    # Execute or block based on classification
    # Track iterations and tokens
    # Check for pause/limits
```

### Action Classification

```python
classification, reason = action_classifier.classify_action(tool_name, tool_input)

if classification == "FORBIDDEN":
    # Block and return error
elif classification == "NEEDS_APPROVAL":
    # Prompt user for approval
else:  # SAFE
    # Execute automatically
```

### Limit Checking

```python
def should_continue():
    if not active: return False
    if pause_requested: return False
    if max_iterations and iterations >= max_iterations: return False
    if max_tokens and tokens_used >= max_tokens: return False
    return True
```

## Files Modified

1. **New Files:**
   - `pwnpilot_lite/core/action_classifier.py`
   - `pwnpilot_lite/core/autonomous_manager.py`
   - `AUTONOMOUS_MODE.md`
   - `FEATURE_AUTONOMOUS_MODE.md`

2. **Modified Files:**
   - `pwnpilot_lite/ui/cli.py` - Added autonomous mode handlers and loop
   - `README.md` - Updated with autonomous mode info

## Testing Recommendations

1. **Scope Testing:**
   - Verify in-scope actions are SAFE
   - Verify out-of-scope actions are FORBIDDEN
   - Test scope add/remove/clear

2. **Classification Testing:**
   - Test destructive commands → NEEDS_APPROVAL
   - Test local filesystem destruction → FORBIDDEN
   - Test safe reconnaissance → SAFE

3. **Limit Testing:**
   - Verify iteration limit stops correctly
   - Verify token limit stops correctly
   - Verify manual `/prompt` works

4. **Safety Testing:**
   - Attempt out-of-scope attack → Should be blocked
   - Attempt `rm -rf /home/` → Should be blocked
   - Verify approval required for exploits

## Future Enhancements

Potential improvements:
1. **Custom classification rules** - User-defined patterns
2. **Action whitelisting** - Pre-approve specific commands
3. **Multi-target support** - Parallel operations on multiple targets
4. **Progress reporting** - Structured progress updates
5. **Checkpoint/resume** - Save state and resume autonomous session
6. **Learning mode** - Train classifier based on user decisions
7. **Risk scoring** - Numerical risk assessment per action

## Security Considerations

1. **Authorization Required**: Only use on authorized systems
2. **Scope = Authorization Boundary**: Scope should match legal authorization
3. **Human in the Loop**: User must approve destructive actions
4. **Audit Trail**: All actions logged for accountability
5. **Fail-Safe Design**: Default to blocking unknown patterns

## Conclusion

Autonomous mode enables powerful hands-off operation while maintaining safety through:
- Multi-tier action classification
- Scope enforcement
- User approval for risky actions
- Hard limits on iterations and tokens
- Complete audit trail

Use responsibly and only on authorized targets!
