# PwnPilot Lite - User Guide

Complete guide to using PwnPilot Lite for AI-assisted penetration testing.

---

## Table of Contents
- [Quick Start](#quick-start)
- [Commands Reference](#commands-reference)
- [Session Management](#session-management)
- [Context Management](#context-management)
- [Tool Execution](#tool-execution)
- [Cost Optimization](#cost-optimization)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Installation

```bash
# Clone or download the repository
cd pwnpilot-lite

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials (for Bedrock)
aws configure
```

### 2. Start a Session

```bash
python main.py
```

### 3. Select Provider
```
Select a model source:
  1. AWS Bedrock
  2. Local (Ollama)

Choose a source by number: 1
```

### 4. Select Model
```
Available models:
  1. PROFILE: us.anthropic.claude-3-5-sonnet-v2
  2. MODEL: anthropic.claude-3-5-haiku-20241022-v1:0 (Anthropic)

Select a model/profile by number: 1
```

### 5. Start Testing
```
user> scan example.com for open ports
```

---

## Commands Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/exit` | End session and exit | `/exit` |
| `/tokens` | Show token usage and costs (Bedrock only) | `/tokens` |
| `/cache` | Show tool result cache statistics | `/cache` |
| `/cache clear` | Clear all cached tool results | `/cache clear` |
| `/summarize` | AI-generate summary and compress context | `/summarize` |
| `/sessions` | List all available sessions | `/sessions` |
| `/load <id>` | Restore a previous session | `/load 20260119160543` |

### Usage Examples

**View token statistics:**
```
user> /tokens

📊 Last request:
   Input: 1,234 tokens
   Output: 567 tokens
   💚 Cache read: 8,945 tokens (90% savings!)

📈 Session totals (3 requests):
   Input: 3,456 tokens
   Output: 1,234 tokens
   💰 Est. cost: $0.0234
   🧠 Context: 15.2% used
```

**List available sessions:**
```
user> /sessions

📂 Available sessions (5 total):

Session ID       Created              Model                     Size
--------------------------------------------------------------------------------
→ 20260119160543 2026-01-19 16:05:43 claude-3-5-sonnet-v2      8KB
  20260119154200 2026-01-19 15:42:00 claude-3-5-sonnet-v2      15KB
  20260118141230 2026-01-18 14:12:30 qwen3-coder:latest        4KB

Current session: 20260119160543
Use '/load <session_id>' to restore a previous session
```

**Load previous session:**
```
user> /load 20260119154200

⚠️  Loading session '20260119154200' will end the current session.
Continue? [y/N]: y

📂 Restored session: 20260119154200
✅ Session '20260119154200' loaded with 12 messages.

user> continue scanning the web application
```

---

## Session Management

### Per-Session Files

PwnPilot Lite stores each session in a separate file:

```
sessions/
├── 20260119160543.jsonl  (current session)
├── 20260119154200.jsonl  (previous session)
└── 20260118141230.jsonl  (older session)
```

**Benefits:**
- ✅ Clean separation between engagements
- ✅ Easy to archive or delete specific sessions
- ✅ Restore any previous session
- ✅ No more giant ever-expanding log file

### Creating New Sessions

Every time you start PwnPilot Lite, a new session is created automatically:

```bash
python main.py

# Output:
📁 Session: 20260119160543
```

The session ID is a timestamp: `YYYYMMDDHHMMSS`

### Restoring Sessions

To continue a previous penetration test:

1. List available sessions:
   ```
   user> /sessions
   ```

2. Load the desired session:
   ```
   user> /load 20260119154200
   ```

3. Continue your work:
   ```
   user> continue the vulnerability scan
   ```

**All conversation history is restored**, allowing the AI to remember:
- Previous scan results
- Identified vulnerabilities
- Testing methodology
- Targets and scope

### Managing Sessions

**Archive completed engagements:**
```bash
# Create archive
tar -czf client-pentest-2024.tar.gz sessions/20260119*.jsonl

# Move to archive directory
mkdir archive
mv sessions/202601*.jsonl archive/
```

**Delete old test sessions:**
```bash
# Delete sessions older than 30 days
find sessions/ -name "*.jsonl" -mtime +30 -delete

# Delete specific session
rm sessions/20260119160543.jsonl
```

**View session content:**
```bash
# Sessions are JSON Lines format
cat sessions/20260119160543.jsonl | jq .

# Count messages in session
grep '"type": "user_message"' sessions/20260119160543.jsonl | wc -l
```

---

## Context Management

### Progressive Context Warnings

PwnPilot Lite monitors context usage and provides warnings at three levels:

**70% - Medium Warning:**
```
ℹ️  Context usage: 71.2% - Monitoring recommended.
```

**80% - High Warning:**
```
⚠️  ------------------------------------------------------------
  WARNING: Context usage is high!
  Current usage: 82.3%
  Consider using context summarization soon.
  Type '/summarize' to compress context now.
------------------------------------------------------------
```

**90% - Critical Warning:**
```
🚨 ============================================================
  CRITICAL: Context window nearly exhausted!
  Current usage: 92.1%
  Automatic summarization will trigger at next exchange.
  Alternative: Start a new session to avoid context limits.
============================================================
```

### Context Summarization

When context gets too large, use AI-powered summarization:

```
user> /summarize

🔄 Generating conversation summary...

📝 Summary generated:
------------------------------------------------------------
Target: example.com
Tools Used: nmap, nikto, sqlmap
Key Findings:
- Port 80/443 open (Apache 2.4.41)
- SQL injection in /search.php?id= parameter
- XSS in comment field
- Outdated jQuery library (CVE-2020-11023)

Next Steps: Validate SQL injection with manual queries
------------------------------------------------------------

Compress conversation context with this summary? [y/N]: y

✅ Context compressed: 24 messages → 7 messages
```

**What happens:**
1. AI generates concise summary of findings
2. Old messages are replaced with summary
3. Recent 6 messages kept for continuity
4. Context usage drops significantly

### Automatic Summarization

At **85% context usage**, summarization triggers automatically:

```
🔄 Context limit approaching - automatic summarization triggered...

📝 Summary generated:
[... summary content ...]

✅ Context auto-compressed: 28 messages → 7 messages
   This helps prevent context limit errors.
```

This prevents the conversation from hitting the 100% limit and failing.

---

## Tool Execution

### Approval Workflow

Every tool execution requires explicit approval:

```
user> scan example.com with nmap

🤖 I'll scan example.com using nmap...

🔧 Proposed tool: nmap
   Input: {
     "target": "example.com",
     "options": "-sV -sC"
   }

Approve this command? [y/N]: y

📄 Tool output:
{
  "success": true,
  "stdout": "Starting Nmap 7.94...\n..."
}
```

**Denial:**
```
Approve this command? [y/N]: n

⏸️  Tool execution denied. Waiting for your next instruction.
```

### Tool Result Caching

Identical tool executions are cached for 5 minutes (configurable):

```
user> scan example.com again

🔧 Proposed tool: nmap
   Input: { "target": "example.com", "options": "-sV -sC" }

Approve this command? [y/N]: y

💚 Cached result (from previous execution):
{... same results as before ...}
```

**Benefits:**
- ⚡ Instant results (no re-execution)
- 💰 Saves API costs
- 🔋 Reduces load on security tools

**Cache management:**
```
# View cache stats
user> /cache

🔄 Tool result cache statistics:
   Entries: 3
   Hits: 2
   Misses: 4
   Hit rate: 33.3%
   TTL: 300s

# Clear cache
user> /cache clear

🗑️  Cache cleared (3 entries removed)
```

**Disable caching:**
```bash
python main.py --disable-tool-cache

# Or custom TTL (10 minutes)
python main.py --tool-cache-ttl 600
```

### Available Tools

Tools are provided by HexStrike MCP server. Common tools:
- `nmap` - Network scanning
- `nikto` - Web server scanning
- `sqlmap` - SQL injection testing
- `nuclei` - Template-based vulnerability scanning
- `wafw00f` - WAF detection
- `zaproxy` - OWASP ZAP scanning

View available tools at startup:
```
✅ HexStrike available: 12 tools ready
```

---

## Cost Optimization

### Token Usage Tracking

**View anytime:**
```
user> /tokens
```

**Automatic display after each request:**
```
📊 Last request:
   Input: 1,234 tokens
   Output: 567 tokens
   💚 Cache read: 8,945 tokens (90% savings!)

📈 Session totals (3 requests):
   Input: 3,456 tokens
   Output: 1,234 tokens
   💚 Cache reads: 26,835 tokens
   💰 Est. cost: $0.0234
   🧠 Context: 15.2% used
```

### Prompt Caching

PwnPilot Lite automatically caches:
- System prompt (security instructions)
- Tool definitions (all MCP tools)

**First request:**
```
📝 Cache created: 12,500 tokens
(costs 25% more than regular input)
```

**Subsequent requests:**
```
💚 Cache read: 12,500 tokens (90% savings!)
(costs 90% less than regular input)
```

**Cost comparison (Claude 3.5 Sonnet):**

Without caching:
- 10 requests × 10,000 tokens = 100,000 tokens
- Cost: 100,000 × $0.003/1K = **$0.30**

With caching:
- 1st request: 10,000 tokens cached (write: $0.0375)
- 9 requests: 9 × 10,000 cached (read: 9 × $0.003 = $0.027)
- Total: **$0.0645** (78% savings!)

**Disable caching:**
```bash
python main.py --disable-caching
```

### Tool Result Caching

Avoid re-running expensive scans:

```
# First scan: executed
user> scan target.com with nmap
Approve? y
[... scan runs for 30 seconds ...]

# Same scan: cached
user> run that scan again
Approve? y
💚 Cached result (instant!)
```

**Savings:**
- Time: 30s → instant
- Cost: Repeated API calls → cached
- Resources: No duplicate tool execution

---

## Advanced Usage

### Command-Line Options

```bash
python main.py \
  --region eu-north-1 \
  --mcp-url http://hexstrike-server:8888 \
  --max-tokens 8192 \
  --disable-streaming \
  --tool-cache-ttl 600
```

**Full options:**
```bash
python main.py --help
```

### Environment Variables

Create `config/credentials.env`:
```bash
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
MCP_URL=http://localhost:8888
OLLAMA_URL=http://localhost:11434
MAX_MCP_TOOLS=20
```

### Custom Ollama Models

Create a custom pentesting model:

```bash
cat > Modelfile <<'EOF'
FROM qwen2.5-coder:32b

PARAMETER num_ctx 8192
PARAMETER temperature 0.2

SYSTEM """
You are a security testing assistant for authorized CTF and web/API testing.
Focus on safe, test-friendly steps with minimal-impact payloads.
"""
EOF

ollama create qwen32b-pentest -f Modelfile
```

Then select it when using Ollama provider.

### Multi-Engagement Workflow

**Engagement A - Web App:**
```bash
python main.py
# Session: 20260119140000
user> scan webapp.target.com
# ... perform testing ...
user> /exit
```

**Engagement B - Network:**
```bash
python main.py
# Session: 20260119150000
user> scan 192.168.1.0/24
# ... perform testing ...
user> /exit
```

**Resume Engagement A:**
```bash
python main.py
user> /load 20260119140000
user> continue web app testing
```

### Batch Session Export

Export all sessions to reports:

```python
#!/usr/bin/env python3
import json
from pathlib import Path

sessions_dir = Path("sessions")
for session_file in sessions_dir.glob("*.jsonl"):
    print(f"Session: {session_file.stem}")

    with open(session_file) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("type") == "tool_output":
                tool = entry.get("tool_name")
                result = entry.get("result", {})
                print(f"  - {tool}: {result.get('success')}")
```

---

## Troubleshooting

### Common Issues

**1. "Could not list foundation models: Operation cannot be paginated"**

Some AWS regions (like `eu-north-1`) don't support pagination.

**Fixed in latest version** - automatic fallback to non-paginated API call.

**2. "Context window nearly exhausted"**

Use context summarization:
```
user> /summarize
```

Or start a new session:
```
user> /exit
python main.py
```

**3. "Session not found"**

Check available sessions:
```
user> /sessions
```

Verify session ID format: `YYYYMMDDHHMMSS`

**4. "MCP server not reachable"**

Check HexStrike MCP is running:
```bash
curl http://localhost:8888/health
```

Specify custom URL:
```bash
python main.py --mcp-url http://custom-host:8888
```

**5. "MCP health check timed out" or "Fetching tools timed out"**

Environments with many tools (100+) can take longer to respond.

**Solution:** Increase MCP timeout (default: 30s):
```bash
# For environments with 100+ tools, try 60 seconds
python main.py --mcp-timeout 60

# For very large deployments, try 120 seconds
python main.py --mcp-timeout 120
```

The timeout applies to:
- Initial health check
- Tool list fetching

**6. "Token tracking not available"**

Token tracking only works with Bedrock models, not Ollama.

Use Bedrock for cost monitoring features.

**7. High costs**

Enable prompt caching (default):
```bash
python main.py  # caching enabled by default
```

Check token usage:
```
user> /tokens
```

Use context summarization to reduce tokens:
```
user> /summarize
```

### Debug Mode

View detailed session logs:

```bash
# Pretty-print session
cat sessions/20260119160543.jsonl | jq .

# Find all tool executions
grep '"type": "tool_output"' sessions/*.jsonl

# Count requests per session
grep '"type": "user_message"' sessions/20260119160543.jsonl | wc -l
```

### Getting Help

1. Check this documentation
2. Review README.md for feature overview
3. Check session logs for errors
4. Verify AWS credentials and region
5. Test MCP server connectivity

### Performance Tips

**Faster responses:**
- Enable streaming (default): `python main.py`
- Use prompt caching (default)
- Use tool result caching (default)

**Lower costs:**
- Enable all caching features (default)
- Use `/summarize` to compress context
- Use Ollama for free local inference (no token tracking)

**Better results:**
- Use specific, detailed prompts
- Approve tools selectively
- Review tool outputs before next step
- Use context summarization to keep AI focused

---

## Best Practices

### 1. Session Organization

- **One session per target/engagement**
- Name sessions descriptively (requires code modification)
- Archive completed engagements
- Delete test sessions regularly

### 2. Context Management

- Monitor context usage with `/tokens`
- Use `/summarize` when reaching 80%
- Start new session for different targets
- Keep sessions focused on specific objectives

### 3. Tool Execution

- Review tool proposals before approving
- Check cached results for efficiency
- Clear cache between engagements
- Use appropriate tools for each task

### 4. Cost Control

- Monitor costs with `/tokens` regularly
- Enable all caching features (default)
- Compress context before long conversations
- Use Ollama for testing/development

### 5. Security

- Review all tool commands before approval
- Keep session logs secure (contain scan results)
- Archive sensitive sessions separately
- Delete logs after engagement completion

---

## Summary

**Essential commands:**
- `/sessions` - List all sessions
- `/load <id>` - Restore session
- `/tokens` - Check costs
- `/summarize` - Compress context
- `/cache` - View tool cache
- `/exit` - End session

**Key features:**
- Per-session logging
- Context summarization
- Progressive warnings
- Tool result caching
- Prompt caching
- Streaming responses

**Tips:**
- One session per engagement
- Summarize at 80% context
- Review tools before approval
- Monitor costs regularly
- Archive completed work

---

For more details, see:
- `README.md` - Feature overview and setup
- `requirements.txt` - Dependencies
- `sessions/` - Your session files
- `pwnpilot_lite/` - Modular source code
