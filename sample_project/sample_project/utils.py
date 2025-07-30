"""
Utility functions and decorators for the Sample Project.

This module provides common utilities, helper functions, decorators,
and validation tools used throughout the project.
"""

import functools
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Constants
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
URL_PATTERN = re.compile(r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?$')
PHONE_PATTERN = re.compile(r'^\+?1?-?\s?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$')

# Type aliases
ValidatorFunction = Callable[[Any], bool]
FormatterFunction = Callable[[Any], str]


def timing_decorator(func: Callable) -> Callable:
    """
    Decorator to measure and log function execution time.
    
    Args:
        func: Function to be timed
        
    Returns:
        Wrapped function that logs execution time
        
    Example:
        >>> @timing_decorator
        ... def slow_function():
        ...     time.sleep(0.1)
        ...     return "done"
        >>> result = slow_function()  # Logs execution time
        >>> result
        'done'
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.4f} seconds: {e}")
            raise
    return wrapper


def retry_decorator(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying function calls with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each attempt
        
    Returns:
        Decorator function
        
    Example:
        >>> @retry_decorator(max_attempts=3, delay=0.1)
        ... def flaky_function():
        ...     import random
        ...     if random.random() < 0.7:
        ...         raise ValueError("Random failure")
        ...     return "success"
        >>> result = flaky_function()  # Will retry up to 3 times
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts - 1:  # Last attempt
                        break
                    
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            logger.error(f"{func.__name__} failed after {max_attempts} attempts")
            raise last_exception
        return wrapper
    return decorator


def cache_decorator(ttl_seconds: int = 300):
    """
    Simple caching decorator with TTL (Time To Live).
    
    Args:
        ttl_seconds: Cache TTL in seconds
        
    Returns:
        Decorator function
        
    Example:
        >>> @cache_decorator(ttl_seconds=60)
        ... def expensive_function(x):
        ...     time.sleep(1)  # Simulate expensive operation
        ...     return x * 2
        >>> result1 = expensive_function(5)  # Takes ~1 second
        >>> result2 = expensive_function(5)  # Returns immediately from cache
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            # Check if cached result is still valid
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                else:
                    del cache[key]  # Remove expired entry
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            return result
        
        # Add cache management methods
        wrapper.clear_cache = lambda: cache.clear()
        wrapper.cache_info = lambda: {"size": len(cache), "ttl": ttl_seconds}
        return wrapper
    return decorator


def validate_input(data: Any, validators: Optional[List[ValidatorFunction]] = None) -> bool:
    """
    Validate input data using a list of validator functions.
    
    Args:
        data: Data to validate
        validators: List of validator functions
        
    Returns:
        True if all validations pass, False otherwise
        
    Example:
        >>> def is_string(x): return isinstance(x, str)
        >>> def min_length(x): return len(x) >= 3
        >>> validate_input("hello", [is_string, min_length])
        True
        >>> validate_input("hi", [is_string, min_length])
        False
    """
    if validators is None:
        return True
    
    for validator in validators:
        try:
            if not validator(data):
                return False
        except Exception as e:
            logger.warning(f"Validator {validator.__name__} raised exception: {e}")
            return False
    
    return True


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address string
        
    Returns:
        True if valid email format
        
    Example:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    return bool(EMAIL_PATTERN.match(email)) if isinstance(email, str) else False


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL string
        
    Returns:
        True if valid URL format
        
    Example:
        >>> validate_url("https://example.com")
        True
        >>> validate_url("not-a-url")
        False
    """
    return bool(URL_PATTERN.match(url)) if isinstance(url, str) else False


def validate_phone(phone: str) -> bool:
    """
    Validate US phone number format.
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid phone format
        
    Example:
        >>> validate_phone("(555) 123-4567")
        True
        >>> validate_phone("555-1234")
        False
    """
    return bool(PHONE_PATTERN.match(phone)) if isinstance(phone, str) else False


def format_output(data: Any, format_type: str = "json", indent: int = 2) -> str:
    """
    Format data for output in various formats.
    
    Args:
        data: Data to format
        format_type: Output format ("json", "yaml", "pretty", "csv")
        indent: Indentation level for formatted output
        
    Returns:
        Formatted string
        
    Example:
        >>> data = {"name": "test", "value": 42}
        >>> formatted = format_output(data, "json")
        >>> "name" in formatted and "value" in formatted
        True
    """
    try:
        if format_type == "json":
            return json.dumps(data, indent=indent, ensure_ascii=False, default=str)
        
        elif format_type == "yaml":
            try:
                import yaml
                return yaml.dump(data, default_flow_style=False, indent=indent)
            except ImportError:
                logger.warning("PyYAML not available, falling back to JSON")
                return json.dumps(data, indent=indent)
        
        elif format_type == "pretty":
            return _pretty_format(data, indent)
        
        elif format_type == "csv" and isinstance(data, (list, tuple)):
            return _format_as_csv(data)
        
        else:
            return str(data)
    
    except Exception as e:
        logger.error(f"Failed to format output: {e}")
        return str(data)


def _pretty_format(data: Any, indent: int = 2) -> str:
    """Format data in a pretty, human-readable format."""
    def _format_recursive(obj, level=0):
        prefix = " " * (level * indent)
        
        if isinstance(obj, dict):
            if not obj:
                return "{}"
            lines = ["{"]
            for key, value in obj.items():
                formatted_value = _format_recursive(value, level + 1)
                lines.append(f"{prefix}  {key}: {formatted_value}")
            lines.append(f"{prefix}}}")
            return "\n".join(lines)
        
        elif isinstance(obj, (list, tuple)):
            if not obj:
                return "[]"
            lines = ["["]
            for item in obj:
                formatted_item = _format_recursive(item, level + 1)
                lines.append(f"{prefix}  {formatted_item}")
            lines.append(f"{prefix}]")
            return "\n".join(lines)
        
        elif isinstance(obj, str):
            return f'"{obj}"'
        
        else:
            return str(obj)
    
    return _format_recursive(data)


def _format_as_csv(data: List[Any]) -> str:
    """Format list data as CSV."""
    import csv
    import io
    
    if not data:
        return ""
    
    output = io.StringIO()
    
    # Handle list of dicts
    if isinstance(data[0], dict):
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    else:
        # Handle list of values
        writer = csv.writer(output)
        for item in data:
            if isinstance(item, (list, tuple)):
                writer.writerow(item)
            else:
                writer.writerow([item])
    
    return output.getvalue()


def sanitize_string(text: str, max_length: int = 1000, remove_html: bool = True) -> str:
    """
    Sanitize string input by removing dangerous characters and limiting length.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        remove_html: Whether to remove HTML tags
        
    Returns:
        Sanitized string
        
    Example:
        >>> sanitize_string("<script>alert('xss')</script>Hello", remove_html=True)
        'Hello'
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Remove HTML tags if requested
    if remove_html:
        text = re.sub(r'<[^>]+>', '', text)
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>\"\'&]', '', text)
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()


def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
        
    Example:
        >>> d1 = {"a": {"x": 1}, "b": 2}
        >>> d2 = {"a": {"y": 2}, "c": 3}
        >>> result = deep_merge_dicts(d1, d2)
        >>> result["a"]["x"] == 1 and result["a"]["y"] == 2
        True
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key for recursion
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
        
    Example:
        >>> nested = {"a": {"b": {"c": 1}}, "d": 2}
        >>> flat = flatten_dict(nested)
        >>> flat["a.b.c"] == 1
        True
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@timing_decorator
def safe_file_operation(filepath: Union[str, Path], operation: str, data: Any = None) -> Any:
    """
    Safely perform file operations with proper error handling.
    
    Args:
        filepath: Path to the file
        operation: Operation type ("read", "write", "append")
        data: Data to write (for write operations)
        
    Returns:
        File content for read operations, None for write operations
        
    Example:
        >>> safe_file_operation("test.txt", "write", "Hello World")
        >>> content = safe_file_operation("test.txt", "read")
        >>> content.strip()
        'Hello World'
    """
    filepath = Path(filepath)
    
    try:
        if operation == "read":
            if not filepath.exists():
                raise FileNotFoundError(f"File not found: {filepath}")
            return filepath.read_text(encoding='utf-8')
        
        elif operation == "write":
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(str(data), encoding='utf-8')
            logger.info(f"Successfully wrote to {filepath}")
        
        elif operation == "append":
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(str(data))
            logger.info(f"Successfully appended to {filepath}")
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    except Exception as e:
        logger.error(f"File operation failed: {e}")
        raise


def calculate_file_hash(filepath: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.
    
    Args:
        filepath: Path to the file
        algorithm: Hash algorithm ("md5", "sha1", "sha256")
        
    Returns:
        Hex digest of the file hash
        
    Example:
        >>> hash_value = calculate_file_hash("test.txt")
        >>> len(hash_value) == 64  # SHA256 produces 64 character hex string
        True
    """
    import hashlib
    
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    hash_obj = getattr(hashlib, algorithm)()
    
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


class PerformanceMonitor:
    """
    Context manager for monitoring performance metrics.
    
    Example:
        >>> with PerformanceMonitor("test_operation") as monitor:
        ...     time.sleep(0.1)  # Simulate work
        ...     monitor.add_metric("items_processed", 42)
        >>> monitor.get_results()["duration"] > 0
        True
    """
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        self.metrics = {}
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting performance monitoring for: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            logger.info(f"{self.operation_name} completed in {duration:.4f} seconds")
        else:
            logger.error(f"{self.operation_name} failed after {duration:.4f} seconds")
        
        self.metrics['duration'] = duration
        self.metrics['success'] = exc_type is None
        self.metrics['timestamp'] = self.end_time
    
    def add_metric(self, name: str, value: Any) -> None:
        """Add a custom metric."""
        self.metrics[name] = value
    
    def get_results(self) -> Dict[str, Any]:
        """Get all performance metrics."""
        return {
            'operation': self.operation_name,
            **self.metrics
        }


# Factory for creating common validators
def create_validators(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    allowed_types: Optional[List[type]] = None
) -> List[ValidatorFunction]:
    """
    Create a list of common validators.
    
    Args:
        min_length: Minimum length requirement
        max_length: Maximum length requirement  
        pattern: Regex pattern to match
        allowed_types: List of allowed types
        
    Returns:
        List of validator functions
        
    Example:
        >>> validators = create_validators(min_length=3, max_length=10, allowed_types=[str])
        >>> validate_input("hello", validators)
        True
        >>> validate_input("hi", validators)
        False
    """
    validators = []
    
    if allowed_types:
        validators.append(lambda x: type(x) in allowed_types)
    
    if min_length is not None:
        validators.append(lambda x: len(str(x)) >= min_length)
    
    if max_length is not None:
        validators.append(lambda x: len(str(x)) <= max_length)
    
    if pattern:
        compiled_pattern = re.compile(pattern)
        validators.append(lambda x: bool(compiled_pattern.match(str(x))))
    
    return validators
