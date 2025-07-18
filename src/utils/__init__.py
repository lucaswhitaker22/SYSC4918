"""
Utility modules for the README generator project.

This package contains utility functions for file operations, token counting,
content prioritization, and JSON serialization used throughout the project.
"""

from .file_utils import (
    read_file_safely,
    find_files_by_pattern,
    get_project_files,
    detect_encoding,
    is_python_file,
    get_file_size,
    create_directory,
    FileReader
)

from .token_counter import (
    TokenCounter,
    estimate_tokens,
    count_tokens_in_text,
    get_token_budget_allocation,
    optimize_content_for_tokens
)

from .content_prioritizer import (
    ContentPrioritizer,
    PriorityScore,
    prioritize_project_data,
    filter_content_by_priority,
    compress_content_for_budget
)

from .json_serializer import (
    ProjectDataSerializer,
    serialize_project_data,
    validate_json_output,
    format_json_output,
    save_json_to_file
)

__all__ = [
    # File utilities
    "read_file_safely",
    "find_files_by_pattern",
    "get_project_files",
    "detect_encoding",
    "is_python_file",
    "get_file_size",
    "create_directory",
    "FileReader",
    
    # Token counting
    "TokenCounter",
    "estimate_tokens",
    "count_tokens_in_text",
    "get_token_budget_allocation",
    "optimize_content_for_tokens",
    
    # Content prioritization
    "ContentPrioritizer",
    "PriorityScore",
    "prioritize_project_data",
    "filter_content_by_priority",
    "compress_content_for_budget",
    
    # JSON serialization
    "ProjectDataSerializer",
    "serialize_project_data",
    "validate_json_output",
    "format_json_output",
    "save_json_to_file"
]

__version__ = "0.1.0"
