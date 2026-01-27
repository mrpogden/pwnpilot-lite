# Prompts Directory

This directory contains system prompts for PwnPilot Lite.

## Available Prompts

- **basic.md**: Simple prompt for tool-based mode (default)
- **basic-guided.md**: Simple prompt for guided mode
- **masterprompt.md**: Advanced OODA loop security assessment with Knowledge Graph
- **custom-template.md**: Template for creating custom prompts

## Template Variables

All prompts support the following template variables:

- `{{TARGET}}`: Target for security assessment (domain, IP, or organization)
- `{{SESSION_ID}}`: Current session identifier
- `{{DATE}}`: Current date
- `{{MODEL_ID}}`: AI model being used

## Usage

Prompts are automatically loaded based on the `--prompt-mode` flag:

```bash
# Basic mode (default)
python main.py

# Advanced mode with masterprompt
python main.py --prompt-mode advanced --target example.com

# Custom prompt
python main.py --prompt-mode custom --prompt-file my-prompt.md
```
