"""Input text pruning and normalization utilities for AI batch processing."""

import html
import re
from typing import Optional


def prune_text(text: Optional[str], max_chars: int = 1200) -> str:
    """Clean HTML markup, normalize whitespace, and truncate text on word boundary.

    Preserves semantic linebreaks from block/list tags while stripping HTML tags
    and unescaping entities to reduce input token usage without losing key specs.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    text = text.strip()
    if not text:
        return ""

    # Unescape HTML entities (&nbsp;, &amp;, &lt;, &gt;, etc.)
    text = html.unescape(text)

    # Convert structural HTML tags to linebreaks to preserve readable separation
    text = re.sub(r"<(?:br\s*/?|/p|/li|/tr|/h[1-6]|/div)>", "\n", text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Normalize horizontal whitespace (spaces, tabs, non-breaking spaces)
    text = re.sub(r"[^\S\r\n]+", " ", text)

    # Collapse multiple blank lines to at most two newlines
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = text.strip()

    # Truncate on word boundary if exceeds limit
    if len(text) > max_chars:
        truncated = text[:max_chars]
        last_space = max(truncated.rfind(" "), truncated.rfind("\n"))
        if last_space > int(max_chars * 0.7):
            text = truncated[:last_space].rstrip()
        else:
            text = truncated.rstrip()

    return text
