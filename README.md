# PwnPilot Lite

AI-assisted penetration testing tool combining AWS Bedrock or local Ollama models with HexStrike MCP security tools.

**Key Features:**
- 🤖 Multiple AI providers (AWS Bedrock, local Ollama)
- 🛡️ Security-first with explicit tool approval
- 📊 Real-time token tracking and cost monitoring
- ⚡ Streaming responses and smart caching
- 🔄 Context summarization to prevent limit errors
- 📁 Per-session logging with restoration capability
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

## Notes

- This script currently supports Anthropic-compatible Bedrock models/profiles for tool use
- Use inference profiles when on-demand access is restricted
- The tool list can be capped with `MAX_MCP_TOOLS=20`
- Token tracking is only available for Bedrock models (not Ollama)
- Streaming responses are only available for Bedrock models (not Ollama)
- Pricing estimates are approximate and based on January 2025 rates
- All features (streaming, caching, token tracking) work seamlessly together
