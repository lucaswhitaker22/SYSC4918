"""
Token counting and estimation utilities for LLM context budgets.

This module provides rough token estimates for strings,
appropriate for planning LLM prompt sizes.
"""

import json
import logging

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """
    Rough token estimate based on character count (~4 chars per token).
    """
    if not text:
        return 0
    # Basic heuristic: one token per 4 characters roughly
    return max(1, len(text) // 4)

def count_tokens_in_dict(data: dict) -> int:
    """
    Estimate tokens in a dict by JSON serialization length.
    """
    try:
        text = json.dumps(data, ensure_ascii=False)
        return estimate_tokens(text)
    except Exception as e:
        logger.error(f"Error estimating tokens in dict: {e}")
        return 0
