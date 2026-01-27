# Custom Prompt Template

You can use this template to create your own custom system prompts for PwnPilot Lite.

## Template Variables

The following variables will be automatically replaced when the prompt is loaded:

- `{{TARGET}}` - The target for the security assessment
- `{{SESSION_ID}}` - The current session identifier
- `{{DATE}}` - The current date
- `{{MODEL_ID}}` - The AI model being used

## Example Custom Prompt

You are a security assistant helping with security assessment of {{TARGET}}. Today's date is {{DATE}}.

[Add your custom instructions here]

## Tips for Creating Custom Prompts

1. Be specific about the role and capabilities
2. Clearly define the interaction pattern (tool-based or guided mode)
3. Set expectations for output format
4. Include safety and ethical guidelines
5. Use template variables to make the prompt dynamic

## Usage

Save this file with your custom content and use it with:

```bash
python main.py --prompt-mode custom --prompt-file your-prompt.md --target example.com
```
