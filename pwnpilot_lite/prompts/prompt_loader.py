"""Prompt loading system for PwnPilot Lite."""

import os
from pathlib import Path
from typing import Optional

from pwnpilot_lite.prompts.template_engine import TemplateEngine


class PromptLoader:
    """Load and manage system prompts."""

    # Fallback prompts for when files are not available
    FALLBACK_BASIC = (
        "You are a security assistant using HexStrike MCP tools. "
        "Only request tool usage via tool_use blocks. "
        "The operator must approve every tool execution. "
        "Request only one tool at a time and wait for its output before proposing another. "
        "After each tool result, explain findings and propose the next step "
        "before waiting for the operator to proceed. "
        "When you need operator input, end your response with <USER_INPUT_NEEDED> "
        "on its own line. Do not include it when requesting a tool."
    )

    FALLBACK_BASIC_GUIDED = (
        "You are a security assistant helping with penetration testing. "
        "The operator is running commands manually, so DO NOT use tool_use blocks. "
        "When asked to perform a scan or test, suggest specific shell commands they should run. "
        "Format your command suggestions clearly, for example:\n"
        "  Command to run: nmap -sV -sC example.com\n\n"
        "After suggesting a command, the operator will run it and paste the output. "
        "Then analyze the results and suggest the next step. "
        "Be specific about command-line flags and options. "
        "Focus on security testing tools like nmap, nikto, sqlmap, nuclei, curl, etc. "
        "Suggest one command at a time and wait for the operator to provide results."
    )

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize prompt loader.

        Args:
            prompts_dir: Directory containing prompt files. If None, uses default.
        """
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            # Default to prompts/ directory in project root
            project_root = Path(__file__).parent.parent.parent
            self.prompts_dir = project_root / "prompts"

    def load_prompt(
        self,
        mode: str = "basic",
        guided_mode: bool = False,
        custom_file: Optional[str] = None,
        variables: Optional[dict] = None
    ) -> str:
        """
        Load a prompt based on mode and settings.

        Args:
            mode: Prompt mode ("basic", "advanced", or "custom")
            guided_mode: Whether in guided mode (no MCP tools)
            custom_file: Path to custom prompt file (for custom mode)
            variables: Template variables to replace

        Returns:
            Processed system prompt string
        """
        # Determine which file to load
        if mode == "custom":
            if not custom_file:
                print("⚠️  Warning: Custom mode requires --prompt-file")
                print("   Falling back to basic mode")
                mode = "basic"
            else:
                prompt_file = Path(custom_file)
        elif mode == "advanced":
            prompt_file = self.prompts_dir / "masterprompt.md"
        else:  # basic mode
            if guided_mode:
                prompt_file = self.prompts_dir / "basic-guided.md"
            else:
                prompt_file = self.prompts_dir / "basic.md"

        # Load prompt from file or use fallback
        if mode != "custom":
            prompt_text = self._load_with_fallback(prompt_file, mode, guided_mode)
        else:
            prompt_text = self._load_custom_file(prompt_file)

        # Apply template variables
        if variables:
            # Validate template before applying
            if TemplateEngine.validate_template(prompt_text):
                prompt_text = TemplateEngine.apply(prompt_text, variables)
            else:
                print("⚠️  Warning: Template validation failed, using prompt as-is")

        return prompt_text

    def _load_with_fallback(
        self,
        prompt_file: Path,
        mode: str,
        guided_mode: bool
    ) -> str:
        """
        Load prompt from file with fallback to hardcoded prompts.

        Args:
            prompt_file: Path to prompt file
            mode: Prompt mode
            guided_mode: Whether in guided mode

        Returns:
            Prompt text
        """
        if prompt_file.exists():
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"⚠️  Warning: Failed to read prompt file {prompt_file}: {e}")
                print("   Using fallback prompt")
        else:
            print(f"⚠️  Warning: Prompt file not found: {prompt_file}")
            print("   Using fallback prompt")

        # Return fallback
        if mode == "basic":
            return self.FALLBACK_BASIC_GUIDED if guided_mode else self.FALLBACK_BASIC
        else:
            # For advanced mode, fall back to basic
            print("   Advanced mode not available, using basic mode")
            return self.FALLBACK_BASIC_GUIDED if guided_mode else self.FALLBACK_BASIC

    def _load_custom_file(self, prompt_file: Path) -> str:
        """
        Load custom prompt file.

        Args:
            prompt_file: Path to custom prompt file

        Returns:
            Prompt text

        Raises:
            FileNotFoundError: If custom file doesn't exist
        """
        if not prompt_file.exists():
            raise FileNotFoundError(f"Custom prompt file not found: {prompt_file}")

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read custom prompt file {prompt_file}: {e}")

    def list_available_prompts(self) -> list:
        """
        List available prompt files.

        Returns:
            List of available prompt file names
        """
        if not self.prompts_dir.exists():
            return []

        prompts = []
        for file in self.prompts_dir.glob("*.md"):
            prompts.append(file.stem)

        return sorted(prompts)

    def get_prompt_info(self, mode: str) -> dict:
        """
        Get information about a prompt mode.

        Args:
            mode: Prompt mode name

        Returns:
            Dictionary with prompt information
        """
        info = {
            "mode": mode,
            "available": False,
            "file_path": None,
            "description": ""
        }

        if mode == "basic":
            file_path = self.prompts_dir / "basic.md"
            info["description"] = "Simple, concise prompt for tool-based mode"
        elif mode == "advanced":
            file_path = self.prompts_dir / "masterprompt.md"
            info["description"] = "Full OODA loop security assessment with Knowledge Graph"
        else:
            return info

        info["file_path"] = str(file_path)
        info["available"] = file_path.exists()

        return info
