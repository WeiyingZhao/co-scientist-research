"""Robust JSON parsing utilities for LLM outputs.

This module provides functions to handle malformed JSON commonly returned by LLMs,
including:
- JSON wrapped in Markdown code blocks
- Truncated JSON
- Missing quotes, trailing commas, and other common errors
"""

import json
import logging
import re
from typing import Any, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T", dict, list)


def extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON content from Markdown code blocks.

    Args:
        text: Raw text potentially containing Markdown-wrapped JSON

    Returns:
        Extracted JSON string or original text if no code block found
    """
    # Try to find JSON in code blocks (```json ... ``` or ``` ... ```)
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",  # ```json ... ```
        r"```\s*([\s\S]*?)\s*```",       # ``` ... ```
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            # Verify it looks like JSON (starts with { or [)
            if extracted and extracted[0] in "{[":
                return extracted

    return text


def repair_json(text: str) -> str:
    """
    Attempt to repair common JSON errors from LLM outputs.

    Args:
        text: Potentially malformed JSON string

    Returns:
        Repaired JSON string

    Note:
        This is a lightweight repair function. For more complex cases,
        consider using the `json_repair` library.
    """
    if not text:
        return text

    # Remove any leading/trailing whitespace and common prefixes
    text = text.strip()

    # Remove common LLM response prefixes
    prefixes_to_remove = [
        "Here is the JSON:",
        "Here's the JSON:",
        "JSON output:",
        "Output:",
    ]
    for prefix in prefixes_to_remove:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()

    # Extract from markdown if wrapped
    text = extract_json_from_markdown(text)

    # Handle truncated JSON by attempting to close brackets
    text = _attempt_close_brackets(text)

    # Fix trailing commas before closing brackets
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    # Fix single quotes to double quotes (common LLM error)
    # Be careful not to replace quotes inside strings
    text = _fix_quotes(text)

    return text


def _attempt_close_brackets(text: str) -> str:
    """Attempt to close unclosed brackets in truncated JSON."""
    if not text:
        return text

    # Count open brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    # If there are unclosed brackets, try to close them
    if open_braces > 0 or open_brackets > 0:
        # First, try to clean up any partial content at the end
        # Look for incomplete key-value pairs
        last_colon = text.rfind(":")
        last_comma = text.rfind(",")

        # If there's a colon after the last comma, we might have an incomplete value
        if last_colon > last_comma:
            # Check if there's content after the colon
            after_colon = text[last_colon + 1:].strip()
            if not after_colon or after_colon in ['"', "'", ""]:
                # Incomplete value, remove the last key-value pair attempt
                text = text[:text.rfind(",") if "," in text else text.rfind("{") + 1]

        # Close brackets in reverse order (most recent first)
        # Simple heuristic: close braces then brackets
        text = text.rstrip()
        if text and text[-1] not in "{}[]\"',0123456789nulltruefalse":
            # Might be in middle of a string or value, add quote if needed
            if text[-1] not in "\"'":
                text += '"'

        text += "}" * open_braces + "]" * open_brackets

    return text


def _fix_quotes(text: str) -> str:
    """Fix single quotes to double quotes, being careful with nested quotes."""
    result = []
    in_string = False
    string_char = None
    i = 0

    while i < len(text):
        char = text[i]

        if not in_string:
            if char == '"':
                in_string = True
                string_char = '"'
                result.append(char)
            elif char == "'":
                # Check if this looks like a string delimiter (followed by content and closing)
                # This is a heuristic - look for matching quote
                remaining = text[i + 1:]
                next_single = remaining.find("'")
                next_double = remaining.find('"')

                # If there's a matching single quote before a double quote, treat as string
                if next_single != -1 and (next_double == -1 or next_single < next_double):
                    in_string = True
                    string_char = "'"
                    result.append('"')  # Replace with double quote
                else:
                    result.append(char)
            else:
                result.append(char)
        else:
            if char == string_char and (i == 0 or text[i - 1] != "\\"):
                in_string = False
                result.append('"' if string_char == "'" else char)
                string_char = None
            elif char == "'" and string_char == "'":
                result.append(char)
            else:
                result.append(char)

        i += 1

    return "".join(result)


def parse_json_safely(
    text: str,
    expected_type: Optional[type[T]] = None,
    default: Optional[T] = None
) -> Union[dict[str, Any], list[Any], T, None]:
    """
    Safely parse JSON from LLM output with automatic repair.

    Args:
        text: Raw text containing JSON (possibly with errors)
        expected_type: Expected type (dict or list) for validation
        default: Default value to return if parsing fails

    Returns:
        Parsed JSON object, or default if parsing fails

    Example:
        >>> text = '''```json
        ... {"name": "test", "value": 42}
        ... ```'''
        >>> result = parse_json_safely(text, expected_type=dict)
        >>> result["name"]
        'test'
    """
    if not text:
        return default

    # First, try direct parsing
    try:
        result = json.loads(text)
        if expected_type and not isinstance(result, expected_type):
            logger.warning(f"Parsed JSON type {type(result)} doesn't match expected {expected_type}")
            return default
        return result
    except json.JSONDecodeError:
        pass

    # Try to repair and parse
    try:
        repaired = repair_json(text)
        result = json.loads(repaired)
        if expected_type and not isinstance(result, expected_type):
            logger.warning(f"Parsed JSON type {type(result)} doesn't match expected {expected_type}")
            return default
        logger.debug("Successfully parsed JSON after repair")
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON even after repair: {e}")

    # Last resort: try to find and extract JSON object/array
    try:
        # Find the first { or [ and last } or ]
        if expected_type == list or (not expected_type and "[" in text):
            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1
        else:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx]
            repaired = repair_json(json_str)
            result = json.loads(repaired)
            if expected_type and not isinstance(result, expected_type):
                return default
            logger.debug("Successfully parsed JSON from extracted substring")
            return result
    except json.JSONDecodeError:
        pass

    logger.warning("All JSON parsing attempts failed")
    return default


def parse_json_list(text: str, default: Optional[list] = None) -> list[Any]:
    """
    Parse JSON expecting a list result.

    Args:
        text: Raw text containing JSON array
        default: Default value if parsing fails (defaults to empty list)

    Returns:
        Parsed list or default
    """
    result = parse_json_safely(text, expected_type=list, default=default)
    return result if result is not None else (default if default is not None else [])


def parse_json_dict(text: str, default: Optional[dict] = None) -> dict[str, Any]:
    """
    Parse JSON expecting a dict result.

    Args:
        text: Raw text containing JSON object
        default: Default value if parsing fails (defaults to empty dict)

    Returns:
        Parsed dict or default
    """
    result = parse_json_safely(text, expected_type=dict, default=default)
    return result if result is not None else (default if default is not None else {})
