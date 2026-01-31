# Command Extractor - Audit and Replay Tool

Extract and audit commands from pwnpilot-lite session files.

## Features

- **List all sessions** with metadata
- **Extract commands** with timestamps and results
- **Multiple output formats**: text, JSON, CSV, bash script
- **Audit trail**: Track approved, denied, and failed commands
- **Replay capability**: Generate bash scripts from successful commands

## Installation

No additional dependencies needed - uses the existing pwnpilot-lite environment.

## Usage

### Basic Commands

```bash
# List all available sessions
python3 extract_commands.py --list

# Extract commands from latest session
python3 extract_commands.py

# Extract from specific session
python3 extract_commands.py -s 20240131120000

# Include command output in report
python3 extract_commands.py -s 20240131120000 --output
```

### Output Formats

#### Text Format (Default)
Human-readable audit report with status indicators:

```bash
python3 extract_commands.py -s 20240131120000
```

Output:
```
Command Audit Report - Session: 20240131120000
================================================================================
Total Commands: 5

[1] 2024-01-31T12:05:23Z
    Tool: nmap
    Command: nmap -sV 192.168.1.100
    Status: ✅ SUCCESS

[2] 2024-01-31T12:08:15Z
    Tool: sqlmap
    Command: sqlmap -u http://target.com/page?id=1 --batch
    Status: ❌ DENIED BY USER
```

#### JSON Format
Machine-readable format for integration:

```bash
python3 extract_commands.py -s 20240131120000 -f json > audit.json
```

#### CSV Format
Spreadsheet-friendly format:

```bash
python3 extract_commands.py -s 20240131120000 -f csv > commands.csv
```

#### Bash Script
Generate executable replay script:

```bash
# Only successful commands
python3 extract_commands.py -s 20240131120000 -f bash > replay.sh
chmod +x replay.sh

# Include all commands (commented)
python3 extract_commands.py -s 20240131120000 -f bash --all-commands > replay_all.sh
```

### Advanced Options

```bash
# Use custom sessions directory
python3 extract_commands.py -d /path/to/sessions --list

# Extract with full output
python3 extract_commands.py -s 20240131120000 --output

# Generate replay script with failed commands commented
python3 extract_commands.py -s 20240131120000 -f bash --all-commands
```

## Command Status Indicators

- ✅ **SUCCESS** - Command executed successfully
- ❌ **FAILED** - Command executed but returned an error
- ❌ **DENIED BY USER** - User declined to execute command
- ♻️ **CACHED** - Result retrieved from cache

## Output Format Details

### Text Format
- Human-readable audit report
- Shows command status with emoji indicators
- Optional output inclusion with truncation
- Suitable for review and documentation

### JSON Format
- Complete structured data
- Includes all metadata and results
- Suitable for programmatic processing
- Contains:
  - `session_id`: Session identifier
  - `total_commands`: Command count
  - `commands`: Array of command objects

### CSV Format
- Spreadsheet-compatible
- Columns: Timestamp, Tool, Command, Status, Success, CacheHit
- Suitable for analysis in Excel/Google Sheets

### Bash Script Format
- Executable shell script
- By default includes only successful commands
- Use `--all-commands` to include all (failed/denied as comments)
- Includes:
  - Session metadata as comments
  - Original timestamps
  - Execution status annotations

## Use Cases

### Security Audit Trail
```bash
# Generate audit report for compliance
python3 extract_commands.py -s 20240131120000 --output > audit_report.txt
```

### Command Replay
```bash
# Replay successful commands in a new environment
python3 extract_commands.py -s 20240131120000 -f bash > replay.sh
./replay.sh
```

### Data Analysis
```bash
# Export to CSV for analysis
python3 extract_commands.py -s 20240131120000 -f csv > commands.csv
# Import into spreadsheet for analysis
```

### Integration
```bash
# Export to JSON for tool integration
python3 extract_commands.py -s 20240131120000 -f json | jq '.commands[] | select(.success == true)'
```

## Module Usage

You can also import and use the extractor programmatically:

```python
from pathlib import Path
from pwnpilot_lite.session.command_extractor import CommandExtractor

# Initialize extractor
session_file = Path("sessions/20240131120000.jsonl")
extractor = CommandExtractor(session_file)

# Extract commands
commands = extractor.extract_commands()

# Format output
text_report = extractor.format_commands_text(commands, include_output=True)
json_report = extractor.format_commands_json(commands)
bash_script = extractor.format_commands_bash_script(commands)
```

## Session File Location

By default, pwnpilot-lite stores session files in:
- **Directory**: `./sessions/`
- **Format**: `{session_id}.jsonl`
- **Example**: `sessions/20240131120000.jsonl`

## Notes

- Session files are JSONL format (JSON Lines)
- Each line is a separate log entry
- Commands are logged with full input/output
- Denied commands are tracked but not executed
- Cached results are marked to avoid confusion
