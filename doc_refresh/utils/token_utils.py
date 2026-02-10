"""
Token Utilities for Document Refresh Pipeline.

Provides token counting and truncation for text inputs to LLMs. Uses tiktoken
when available for accurate token counts, falling back to character-based
estimation (4 chars per token) when tiktoken is not installed.

Functions:
    count_tokens: Count tokens in a text string
    truncate_to_tokens: Truncate text to a maximum token count
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.debug("tiktoken not available, using character-based estimation")

CHARS_PER_TOKEN = 4
DEFAULT_ENCODING = "cl100k_base"

_encoder: Optional["tiktoken.Encoding"] = None


def _get_encoder() -> Optional["tiktoken.Encoding"]:
    """Get or initialize the tiktoken encoder."""
    global _encoder
    if not _TIKTOKEN_AVAILABLE:
        return None
    if _encoder is None:
        _encoder = tiktoken.get_encoding(DEFAULT_ENCODING)
    return _encoder


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string.

    Args:
        text: Input text to count tokens for.

    Returns:
        Token count (estimated from characters if tiktoken unavailable).
    """
    if not text:
        return 0

    encoder = _get_encoder()
    if encoder:
        return len(encoder.encode(text))

    return len(text) // CHARS_PER_TOKEN


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate text to a maximum number of tokens.

    Args:
        text: Input text to truncate.
        max_tokens: Maximum number of tokens allowed.

    Returns:
        Truncated text that fits within the token limit.
    """
    if not text or max_tokens <= 0:
        return ""

    encoder = _get_encoder()
    if encoder:
        tokens = encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return encoder.decode(tokens[:max_tokens])

    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
