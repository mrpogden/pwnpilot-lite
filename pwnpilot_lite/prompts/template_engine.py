"""Template engine for prompt variable replacement."""

import re
from datetime import datetime
from typing import Dict, Optional


class TemplateEngine:
    """Handle template variable replacement in prompts."""

    # Pattern to match {{VARIABLE_NAME}}
    TEMPLATE_PATTERN = re.compile(r'\{\{([A-Z_]+)\}\}')

    @staticmethod
    def apply(
        template: str,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Apply variable replacements to a template.

        Args:
            template: Template string with {{VARIABLE}} placeholders
            variables: Dictionary of variable names to values

        Returns:
            Processed template with variables replaced
        """
        if variables is None:
            variables = {}

        # Find all template variables in the text
        found_vars = TemplateEngine.TEMPLATE_PATTERN.findall(template)

        # Track which variables were used
        used_vars = set()
        missing_vars = set()

        # Replace each variable
        result = template
        for var_name in found_vars:
            placeholder = f"{{{{{var_name}}}}}"

            if var_name in variables:
                # Replace with provided value
                result = result.replace(placeholder, variables[var_name])
                used_vars.add(var_name)
            else:
                # Variable not provided
                missing_vars.add(var_name)

        # Warn about missing variables (but don't fail)
        if missing_vars:
            print(f"⚠️  Warning: Template variables not provided: {', '.join(sorted(missing_vars))}")
            print("   These will remain as placeholders in the prompt.")

        return result

    @staticmethod
    def get_default_variables(
        target: Optional[str] = None,
        session_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get default template variables.

        Args:
            target: Target for assessment
            session_id: Session identifier
            model_id: Model identifier

        Returns:
            Dictionary of default variables
        """
        variables = {
            "DATE": datetime.now().strftime("%Y-%m-%d"),
        }

        if target:
            variables["TARGET"] = target
        if session_id:
            variables["SESSION_ID"] = session_id
        if model_id:
            variables["MODEL_ID"] = model_id

        return variables

    @staticmethod
    def validate_template(template: str) -> bool:
        """
        Validate template syntax.

        Args:
            template: Template string to validate

        Returns:
            True if template syntax is valid
        """
        # Check for mismatched braces
        open_count = template.count("{{")
        close_count = template.count("}}")

        if open_count != close_count:
            print(f"⚠️  Warning: Mismatched template braces ({{ {open_count} vs }} {close_count})")
            return False

        # Check that all variables match the pattern
        found_vars = TemplateEngine.TEMPLATE_PATTERN.findall(template)
        potential_vars = re.findall(r'\{\{([^}]+)\}\}', template)

        if len(found_vars) != len(potential_vars):
            invalid_vars = set(potential_vars) - set(found_vars)
            print(f"⚠️  Warning: Invalid template variable names: {', '.join(invalid_vars)}")
            print("   Variable names must be UPPERCASE with underscores only")
            return False

        return True

    @staticmethod
    def extract_variables(template: str) -> set:
        """
        Extract all template variable names from a template.

        Args:
            template: Template string

        Returns:
            Set of variable names found in template
        """
        return set(TemplateEngine.TEMPLATE_PATTERN.findall(template))
