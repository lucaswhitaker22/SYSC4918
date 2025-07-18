"""
Token counting and estimation utilities for managing LLM context windows.

This module provides functions to count tokens, estimate content size,
and manage the 1 million token budget for Gemini 2.5 Pro integration.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Token estimation ratios for different content types
TOKEN_RATIOS = {
    'code': 0.3,        # Code is more token-dense
    'docstring': 0.25,  # Documentation is typically less dense
    'comment': 0.25,    # Comments are similar to documentation
    'text': 0.25,       # Regular text
    'json': 0.3,        # JSON structure adds overhead
    'markdown': 0.25,   # Markdown formatting
}

# Maximum token limits
MAX_TOKENS = {
    'gemini_2_5_pro': 1_000_000,
    'gemini_2_5_flash': 1_000_000,
    'gpt_4o': 128_000,
    'gpt_4o_mini': 128_000,
    'claude_sonnet': 200_000,
}

# Token budget allocation percentages
DEFAULT_BUDGET_ALLOCATION = {
    'metadata': 0.005,          # 5,000 tokens
    'dependencies': 0.01,       # 10,000 tokens
    'structure': 0.05,          # 50,000 tokens
    'api_documentation': 0.60,  # 600,000 tokens
    'examples': 0.20,           # 200,000 tokens
    'configuration': 0.035,     # 35,000 tokens
    'buffer': 0.10,             # 100,000 tokens (for LLM prompt)
}


class ContentType(Enum):
    """Types of content for token estimation."""
    CODE = "code"
    DOCSTRING = "docstring"
    COMMENT = "comment"
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class TokenBudget:
    """Token budget allocation for different content types."""
    
    total_budget: int
    metadata: int
    dependencies: int
    structure: int
    api_documentation: int
    examples: int
    configuration: int
    buffer: int
    
    def get_used_budget(self) -> int:
        """Get total allocated budget."""
        return (self.metadata + self.dependencies + self.structure + 
                self.api_documentation + self.examples + self.configuration)
    
    def get_remaining_budget(self) -> int:
        """Get remaining budget after allocations."""
        return self.total_budget - self.get_used_budget() - self.buffer


class TokenCounter:
    """Advanced token counter with content-aware estimation."""
    
    def __init__(self, model_name: str = "gemini_2_5_pro"):
        self.model_name = model_name
        self.max_tokens = MAX_TOKENS.get(model_name, 1_000_000)
        self._token_cache: Dict[str, int] = {}
        
        # Initialize tiktoken if available (for more accurate counting)
        self.tiktoken_encoder = None
        try:
            import tiktoken
            if model_name.startswith('gpt'):
                self.tiktoken_encoder = tiktoken.encoding_for_model(model_name)
            else:
                # Use cl100k_base for other models as approximation
                self.tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not available, using estimation")
        except Exception as e:
            logger.warning(f"Error initializing tiktoken: {e}")
    
    def count_tokens(self, text: str, content_type: ContentType = ContentType.TEXT) -> int:
        """
        Count tokens in text with content-type awareness.
        
        Args:
            text: Text to count tokens for
            content_type: Type of content for better estimation
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
            
        # Use cached result if available
        cache_key = f"{content_type.value}:{hash(text)}"
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]
        
        # Use tiktoken if available
        if self.tiktoken_encoder:
            try:
                token_count = len(self.tiktoken_encoder.encode(text))
                self._token_cache[cache_key] = token_count
                return token_count
            except Exception as e:
                logger.warning(f"Error with tiktoken encoding: {e}")
        
        # Fallback to estimation
        token_count = self._estimate_tokens(text, content_type)
        self._token_cache[cache_key] = token_count
        return token_count
    
    def _estimate_tokens(self, text: str, content_type: ContentType) -> int:
        """
        Estimate tokens using heuristics.
        
        Args:
            text: Text to estimate
            content_type: Type of content
            
        Returns:
            Estimated token count
        """
        # Basic character-to-token ratio
        char_count = len(text)
        base_ratio = TOKEN_RATIOS.get(content_type.value, 0.25)
        
        # Adjust for various factors
        adjustments = 0
        
        # More tokens for code due to symbols and structure
        if content_type == ContentType.CODE:
            symbol_count = len(re.findall(r'[{}()\[\],;:.]', text))
            adjustments += symbol_count * 0.5
        
        # More tokens for JSON due to structure
        elif content_type == ContentType.JSON:
            brace_count = text.count('{') + text.count('[')
            adjustments += brace_count * 2
        
        # Adjust for whitespace (whitespace is often tokenized separately)
        whitespace_count = len(re.findall(r'\s+', text))
        adjustments += whitespace_count * 0.1
        
        # Adjust for long words (often split into multiple tokens)
        long_words = len(re.findall(r'\b\w{8,}\b', text))
        adjustments += long_words * 0.5
        
        estimated_tokens = int((char_count * base_ratio) + adjustments)
        return max(1, estimated_tokens)  # Minimum 1 token
    
    def count_tokens_in_dict(self, data: Dict[str, Any], content_type: ContentType = ContentType.JSON) -> int:
        """
        Count tokens in a dictionary/JSON structure.
        
        Args:
            data: Dictionary to count tokens for
            content_type: Type of content
            
        Returns:
            Estimated token count
        """
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        return self.count_tokens(json_str, content_type)
    
    def get_budget_allocation(self, custom_allocation: Optional[Dict[str, float]] = None) -> TokenBudget:
        """
        Get token budget allocation.
        
        Args:
            custom_allocation: Custom allocation percentages
            
        Returns:
            TokenBudget object with allocations
        """
        allocation = custom_allocation or DEFAULT_BUDGET_ALLOCATION
        
        return TokenBudget(
            total_budget=self.max_tokens,
            metadata=int(self.max_tokens * allocation['metadata']),
            dependencies=int(self.max_tokens * allocation['dependencies']),
            structure=int(self.max_tokens * allocation['structure']),
            api_documentation=int(self.max_tokens * allocation['api_documentation']),
            examples=int(self.max_tokens * allocation['examples']),
            configuration=int(self.max_tokens * allocation['configuration']),
            buffer=int(self.max_tokens * allocation['buffer'])
        )


def estimate_tokens(text: str, content_type: str = "text") -> int:
    """
    Simple token estimation function.
    
    Args:
        text: Text to estimate tokens for
        content_type: Type of content (code, text, json, etc.)
        
    Returns:
        Estimated token count
    """
    counter = TokenCounter()
    try:
        content_enum = ContentType(content_type.lower())
    except ValueError:
        content_enum = ContentType.TEXT
    
    return counter.count_tokens(text, content_enum)


def count_tokens_in_text(text: str, model_name: str = "gemini_2_5_pro") -> int:
    """
    Count tokens in text for a specific model.
    
    Args:
        text: Text to count tokens for
        model_name: Name of the model
        
    Returns:
        Token count
    """
    counter = TokenCounter(model_name)
    return counter.count_tokens(text)


def get_token_budget_allocation(model_name: str = "gemini_2_5_pro") -> TokenBudget:
    """
    Get default token budget allocation.
    
    Args:
        model_name: Name of the model
        
    Returns:
        TokenBudget object
    """
    counter = TokenCounter(model_name)
    return counter.get_budget_allocation()


def optimize_content_for_tokens(content: str, max_tokens: int, content_type: str = "text") -> str:
    """
    Optimize content to fit within token limit.
    
    Args:
        content: Content to optimize
        max_tokens: Maximum allowed tokens
        content_type: Type of content
        
    Returns:
        Optimized content
    """
    counter = TokenCounter()
    try:
        content_enum = ContentType(content_type.lower())
    except ValueError:
        content_enum = ContentType.TEXT
    
    current_tokens = counter.count_tokens(content, content_enum)
    
    if current_tokens <= max_tokens:
        return content
    
    # Calculate reduction ratio
    reduction_ratio = max_tokens / current_tokens
    
    # Reduce content length
    target_length = int(len(content) * reduction_ratio * 0.9)  # 90% to be safe
    
    if content_type == "code":
        # For code, try to preserve structure
        lines = content.split('\n')
        total_chars = sum(len(line) for line in lines)
        
        result_lines = []
        current_chars = 0
        
        for line in lines:
            if current_chars + len(line) <= target_length:
                result_lines.append(line)
                current_chars += len(line)
            else:
                # Add ellipsis to indicate truncation
                result_lines.append("# ... (truncated)")
                break
        
        return '\n'.join(result_lines)
    
    else:
        # For text, simple truncation with ellipsis
        return content[:target_length] + "..." if len(content) > target_length else content


def analyze_token_distribution(data: Dict[str, Any]) -> Dict[str, int]:
    """
    Analyze token distribution across different data sections.
    
    Args:
        data: Data to analyze
        
    Returns:
        Dictionary with token counts per section
    """
    counter = TokenCounter()
    distribution = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            distribution[key] = counter.count_tokens(value, ContentType.TEXT)
        elif isinstance(value, (dict, list)):
            distribution[key] = counter.count_tokens_in_dict(value if isinstance(value, dict) else {"data": value})
        else:
            distribution[key] = counter.count_tokens(str(value), ContentType.TEXT)
    
    return distribution


def format_token_summary(token_count: int, budget: TokenBudget) -> str:
    """
    Format a human-readable token usage summary.
    
    Args:
        token_count: Current token count
        budget: Token budget
        
    Returns:
        Formatted summary string
    """
    percentage = (token_count / budget.total_budget) * 100
    remaining = budget.total_budget - token_count
    
    return f"""
Token Usage Summary:
- Used: {token_count:,} tokens ({percentage:.1f}%)
- Remaining: {remaining:,} tokens
- Budget: {budget.total_budget:,} tokens
- Status: {'✓ Within budget' if token_count <= budget.total_budget else '⚠ Over budget'}
"""
