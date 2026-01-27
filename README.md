# PwnPilot Lite

AI-assisted penetration testing tool combining AWS Bedrock or local Ollama models with HexStrike MCP security tools.

**Key Features:**
- 🤖 Multiple AI providers (AWS Bedrock, local Ollama)
- 🛡️ Security-first with explicit tool approval
- 📊 Real-time token tracking and cost monitoring
- ⚡ Streaming responses and smart caching
- 🔄 Context summarization to prevent limit errors
- 📁 Per-session logging with restoration capability
- 🧭 Guided mode for manual command execution (no MCP needed)
- 🎯 Modular architecture for easy extension

## Features

### 🚀 Token Caching (Prompt Caching)
- Automatically caches system prompts and tool definitions
- Reduces costs by up to 90% on repeated content
- Faster response times for cached content
- Can be disabled with `--disable-caching`

### ⚡ Streaming Responses
- Real-time text streaming as model generates responses
- See answers immediately without waiting for completion
- Smooth, professional user experience
- Supports tool requests during streaming
- Can be disabled with `--disable-streaming`

### 📊 Token Monitoring
- Real-time token usage tracking per request
- Running totals for input/output tokens
- Cost estimation based on model pricing
- Context window usage warnings (alerts at 80%)
- View stats anytime with `/tokens` command

### 🔄 Tool Result Caching
- Automatically caches tool execution results
- Avoids re-running identical security scans
- Configurable TTL (default: 5 minutes)
- Cache hit/miss statistics
- Manual cache management with `/cache` commands

### 🛡️ Security Features
- Tool execution requires explicit approval
- Session logging for audit trails
- Support for both Bedrock and local Ollama models

## Setup

1) Create a virtual environment (optional)
2) Install requirements:

```bash
pip install -r requirements.txt
```

3) Ensure AWS credentials are configured via AWS CLI or environment variables.

Optional: place credentials in `config/credentials.env` and they will be loaded if present.

## Run

Basic usage:

```bash
python main.py
```

With options:

```bash
python main.py --region us-east-1 --mcp-url http://localhost:8888
```

Disable caching:

```bash
python main.py --disable-caching
```

**Note:** AWS region defaults to your configured AWS CLI region (from `~/.aws/config`)

## Usage

### Commands
- `/exit` - Exit the program
- `/tokens` - Show detailed token usage and cost statistics
- `/cache` - Show tool result cache statistics
- `/cache clear` - Clear all cached tool results
- `/summarize` - Generate AI summary and compress context (prevents context limit errors)
- `/sessions` - List all saved sessions
- `/load <session_id>` - Restore a previous session
- Type your question or request normally to interact with the AI

**New in this version:** Per-session logging means each session is stored separately in `sessions/` directory for easy management and restoration.

### Example Session

```
user> scan example.com for vulnerabilities

🤖 I'll help scan example.com. Let me start with a basic reconnaissance...

🔧 Proposed tool: nmap
   Input: {
     "target": "example.com",
     "options": "-sV"
   }

Approve this command? [y/N]: y

📄 Tool output:
{...scan results...}

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

user> scan example.com again

🤖 Let me run the same scan...

🔧 Proposed tool: nmap
   Input: {
     "target": "example.com",
     "options": "-sV"
   }

Approve this command? [y/N]: y

💚 Cached result (from previous execution):
{...same scan results...}

user> /cache

🔄 Tool result cache statistics:
   Entries: 3
   Hits: 1
   Misses: 2
   Hit rate: 33.3%
   TTL: 300s
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--region` | AWS CLI config | AWS region for Bedrock (auto-detected from `~/.aws/config`) |
| `--mcp-url` | http://localhost:8888 | HexStrike MCP server URL |
| `--ollama-url` | http://localhost:11434 | Ollama server URL |
| `--max-tokens` | 4096 | Maximum tokens per response |
| `--session-log` | session.log | Path to session log file |
| `--enable-caching` | true | Enable prompt caching |
| `--disable-caching` | false | Disable prompt caching |
| `--show-tokens` | true | Show token usage stats |
| `--enable-tool-cache` | true | Enable tool result caching |
| `--disable-tool-cache` | false | Disable tool result caching |
| `--tool-cache-ttl` | 300 | Tool cache TTL in seconds |
| `--enable-streaming` | true | Enable streaming responses |
| `--disable-streaming` | false | Disable streaming responses |
| `--mcp-timeout` | 30 | MCP health check timeout in seconds (increase for many tools) |
| `--guided-mode` | false | Enable guided mode (AI suggests commands, you run them manually, no MCP needed) |
| `--prompt-mode` | basic | Prompt mode: basic (default), advanced (masterprompt), or custom |
| `--prompt-file` | None | Path to custom prompt file (required for custom mode) |
| `--target` | None | Target for security assessment (domain, IP, or organization) |

## Environment Variables

You can also configure via environment variables:

```bash
export AWS_REGION=us-east-1
export MCP_URL=http://localhost:8888
export OLLAMA_URL=http://localhost:11434
export SESSION_LOG=session.log
export MAX_MCP_TOOLS=20  # Limit number of tools loaded
```

## Token Caching Details

PwnPilot Lite uses AWS Bedrock's prompt caching feature to optimize costs:

1. **System Prompt Caching**: The security assistant instructions are cached
2. **Tool Definition Caching**: All MCP tool schemas are cached
3. **Cache Duration**: Caches last for 5 minutes of inactivity
4. **Cost Savings**:
   - Cache writes: 25% more than input tokens
   - Cache reads: 90% cheaper than input tokens
   - Typical savings: 70-90% on long conversations

## Pricing Examples (Claude 3.5 Sonnet)

Without caching:
- 10,000 input tokens: $0.030
- 1,000 output tokens: $0.015
- **Total: $0.045**

With caching (after initial request):
- 10,000 cached tokens: $0.003
- 1,000 output tokens: $0.015
- **Total: $0.018** (60% savings!)

## Streaming Responses

PwnPilot Lite uses AWS Bedrock's streaming API to show responses in real-time:

### How It Works

1. **Real-time Display**: Text appears character-by-character as the model generates it
2. **Tool Detection**: Automatically detects when model requests a tool mid-stream
3. **Seamless Integration**: Works with token tracking, caching, and all other features
4. **Professional UX**: Provides immediate feedback instead of waiting for full response

### Benefits

- **Immediate Feedback**: See responses start appearing in ~500ms instead of waiting 5-10 seconds
- **Better UX**: Users know the system is working immediately
- **Interruptible**: Can Ctrl+C during long responses (future enhancement)
- **Natural Feel**: Mimics human conversation patterns

### Example

```bash
user> explain how SQL injection works

🤖 SQL injection is a web security vulnerability that allows attackers to
interfere with database queries. It occurs when untrusted data is sent to
an interpreter as part of a command or query. Here's how it works...
[text continues streaming in real-time]
```

### When to Disable

Disable streaming if:
- You prefer seeing complete responses at once
- You're piping output to another tool
- You're debugging and want cleaner logs

```bash
python pwnpilot_lite.py --disable-streaming
```

## Tool Result Caching Details

PwnPilot Lite caches tool execution results to avoid redundant command execution:

1. **Smart Caching**: Results are cached by tool name + normalized parameters
2. **TTL Management**: Cached results expire after 5 minutes by default (configurable)
3. **Cache Key Normalization**: Same command with different argument order hits same cache
4. **Automatic Cleanup**: Expired entries are automatically removed
5. **Success-Only Caching**: Only successful tool executions are cached

### Benefits

- **Speed**: Instant results for repeated commands
- **Cost Savings**: No need to re-run expensive scans
- **Resource Efficiency**: Reduces load on security tools
- **Audit Trail**: Cache hits logged in session.log

### Use Cases

Perfect for:
- Re-checking same targets during investigation
- Demonstrating scan results to team members
- Testing different AI analysis approaches on same data
- Iterative security assessments

### Cache Management

```bash
# View cache statistics
/cache

# Clear all cached results
/cache clear

# Disable caching entirely
python pwnpilot_lite.py --disable-tool-cache

# Custom TTL (10 minutes)
python pwnpilot_lite.py --tool-cache-ttl 600
```

## Guided Mode

Guided mode allows you to use PwnPilot Lite without HexStrike MCP server. Perfect for environments where you can't run MCP or prefer manual control.

### How It Works

1. **No MCP Required**: AI suggests commands but doesn't execute them
2. **You Run Commands**: Copy suggested commands and run them in your terminal
3. **Paste Results**: Paste command output back to the AI
4. **AI Analysis**: AI analyzes results and suggests next steps

### Enable Guided Mode

```bash
python main.py --guided-mode
```

### Example Session

```
user> scan example.com for open ports

🤖 I'll help you scan example.com. Here's the command to run:

Command to run: nmap -sV -sC example.com

This will perform a service version detection scan with default scripts.
Please run this command and paste the output.

user> [paste nmap output here]

Starting Nmap 7.94...
PORT    STATE SERVICE  VERSION
80/tcp  open  http     Apache httpd 2.4.41
443/tcp open  ssl/http Apache httpd 2.4.41

🤖 Based on the scan results, I can see ports 80 and 443 are open...
Let's check for web vulnerabilities:

Command to run: nikto -h http://example.com

user> [paste nikto output here]

[conversation continues...]
```

### Benefits

- **No Infrastructure**: No need to set up HexStrike MCP server
- **Full Control**: You approve and run every command manually
- **Flexible Environment**: Run commands anywhere you have access
- **Learning Tool**: See exactly what commands are being used

### When to Use Guided Mode

- Testing PwnPilot Lite without full setup
- Environments where MCP can't be deployed
- Learning security testing techniques
- Maximum control over command execution
- Limited tool availability on target system

## Prompt Modes

PwnPilot Lite now supports three prompt modes to customize the AI's behavior and assessment approach:

### Available Modes

1. **Basic Mode** (default): Simple, concise prompts for standard security testing
2. **Advanced Mode**: Full OODA loop security assessment with Knowledge Graph tracking
3. **Custom Mode**: Load your own custom prompt template

### Basic Mode (Default)

The default mode provides straightforward security assistance with tool approval workflow:

```bash
python main.py
```

Features:
- Simple, focused prompts
- One tool at a time execution
- Operator approval required
- Works in both tool mode and guided mode

### Advanced Mode (Masterprompt)

Advanced mode uses a comprehensive OODA loop methodology with continuous Knowledge Graph updates:

```bash
python main.py --prompt-mode advanced --target example.com
```

Features:
- **OODA Loop Framework**: Observe, Orient, Decide, Act, Validate
- **Knowledge Graph**: Maintains internal graph of discovered assets and relationships
- **Phased Approach**: External reconnaissance → Active reconnaissance → Vulnerability identification → Validation
- **Progressive Disclosure**: Structured assessment with checkpoint reports
- **Tool Rotation**: Automatically switches between tools if one fails or is rate-limited
- **Recursive Discovery**: Automatically explores newly discovered assets
- **Failure Recovery**: Adapts to WAF blocks, rate limits, and errors
- **Confidence Ratings**: Each finding includes confidence level (CONFIRMED, LIKELY, POSSIBLE, INCONCLUSIVE)
- **Tech-Stack Fingerprinting**: Builds comprehensive technology profile before testing
- **Context-Aware Scanning**: Tailors vulnerability scans to detected technologies
- **Ethics & Legal Guardrails**: Built-in safety protocols and scope boundaries

#### Target Specification

Advanced mode requires a target. You can specify it via command line or you'll be prompted:

```bash
# Specify target on command line
python main.py --prompt-mode advanced --target example.com

# Or be prompted at startup
python main.py --prompt-mode advanced
# > Please specify the target for this security assessment: example.com
```

#### Knowledge Graph Tracking

In advanced mode, the AI maintains a Knowledge Graph of:
- Discovered assets (domains, IPs, services, cloud resources)
- Technologies and versions
- Vulnerabilities and their confidence levels
- Relationships between assets

You can update and retrieve the Knowledge Graph via the session manager:

```python
# In your code (for extensions):
kg = session_manager.get_knowledge_graph()
session_manager.update_knowledge_graph(updated_kg)
```

#### Example Advanced Session

```
user> Begin assessment

🤖 Beginning comprehensive security assessment of example.com

Phase 1: External Reconnaissance
- Performing DNS enumeration...
- Discovering subdomains...
- Mapping public attack surface...

[AI proposes DNS enumeration tool]

🔧 Proposed tool: subfinder
   Input: {"target": "example.com"}

Approve this command? [y/N]: y

📄 Tool output:
- example.com
- www.example.com
- api.example.com
- dev.example.com

🧠 Knowledge Graph Updated:
- Added 4 domain nodes
- Discovered 1 development environment (potential high-value target)

Proceeding to Phase 2: Active Reconnaissance...
```

### Custom Mode

Load your own custom prompt template:

```bash
python main.py --prompt-mode custom --prompt-file my-prompt.md --target example.com
```

#### Creating Custom Prompts

Custom prompts support template variables:

- `{{TARGET}}` - The target for assessment
- `{{SESSION_ID}}` - Current session identifier
- `{{DATE}}` - Current date
- `{{MODEL_ID}}` - AI model being used

Example custom prompt (`my-prompt.md`):

```markdown
You are a security assistant analyzing {{TARGET}}.
Session: {{SESSION_ID}}
Date: {{DATE}}

[Your custom instructions here]
```

See `prompts/custom-template.md` for a complete template.

### Prompt Mode Comparison

| Feature | Basic | Advanced | Custom |
|---------|-------|----------|--------|
| Tool approval required | ✅ | ✅ | ✅ |
| OODA loop methodology | ❌ | ✅ | Depends |
| Knowledge Graph | ❌ | ✅ | Depends |
| Progressive disclosure | ❌ | ✅ | Depends |
| Target tracking | ❌ | ✅ | Depends |
| Phased assessment | ❌ | ✅ | Depends |
| Confidence ratings | ❌ | ✅ | Depends |
| Tech fingerprinting | ❌ | ✅ | Depends |
| Customizable | ❌ | ❌ | ✅ |

### Configuration Table Update

| Option | Default | Description |
|--------|---------|-------------|
| `--prompt-mode` | basic | Prompt mode: basic, advanced, or custom |
| `--prompt-file` | None | Path to custom prompt file (required for custom mode) |
| `--target` | None | Target for security assessment (domain, IP, or organization) |

### Session Restoration with Advanced Mode

When you restore a session that was created in advanced mode, the target and Knowledge Graph are automatically restored:

```bash
# Original session
python main.py --prompt-mode advanced --target example.com
# [perform assessment, discover assets, exit]

# Later - restore session
/sessions
/load 20240126153045

# Target and Knowledge Graph automatically restored from session
```

### Best Practices

**Use Basic Mode When:**
- Quick, focused security tasks
- Simple reconnaissance or testing
- You want minimal AI overhead
- Learning to use the tool

**Use Advanced Mode When:**
- Comprehensive security assessments
- Bug bounty hunting
- Penetration testing engagements
- Need structured methodology
- Want detailed reports with evidence
- Tracking complex attack surfaces

**Use Custom Mode When:**
- Specialized assessment requirements
- Organization-specific methodology
- Testing new prompt approaches
- Research and development

## Notes

- This script currently supports Anthropic-compatible Bedrock models/profiles for tool use
- Use inference profiles when on-demand access is restricted
- The tool list can be capped with `MAX_MCP_TOOLS=20`
- Token tracking is only available for Bedrock models (not Ollama)
- Streaming responses are only available for Bedrock models (not Ollama)
- Pricing estimates are approximate and based on January 2025 rates
- All features (streaming, caching, token tracking) work seamlessly together
