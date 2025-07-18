"""
README Generator - Automated README generation for Python projects.

This package provides a command-line tool that automatically generates comprehensive
README files for Python projects using Large Language Model APIs. It intelligently
parses and extracts key information from codebases to create high-quality documentation
within LLM context window constraints.

Features:
- Comprehensive project analysis and parsing
- Token-aware content optimization for LLM APIs
- Multiple LLM provider support (Gemini, OpenAI, Claude)
- Intelligent content prioritization
- Error handling and graceful degradation
"""

from .parser.project_parser import parse_project, parse_project_to_json
from .utils.token_counter import estimate_tokens, count_tokens_in_text
from .utils.content_prioritizer import prioritize_project_data
from .utils.json_serializer import serialize_project_data
from .config import Config, load_config, save_config

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "Automated README generation for Python projects using LLM APIs"
__url__ = "https://github.com/yourusername/readme-generator"

# Main API exports
__all__ = [
    # Core parsing functions
    "parse_project",
    "parse_project_to_json",
    
    # Utility functions
    "estimate_tokens",
    "count_tokens_in_text",
    "prioritize_project_data",
    "serialize_project_data",
    
    # Configuration
    "Config",
    "load_config",
    "save_config",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "__url__",
]

# Package-level configuration
DEFAULT_CONFIG = {
    "model_name": "gemini_2_5_pro",
    "max_tokens": 1_000_000,
    "include_tests": False,
    "include_private": False,
    "output_format": "markdown",
    "verbose": False,
    "cache_enabled": True,
    "timeout": 90,
}

def get_version() -> str:
    """Get the current version of the package."""
    return __version__

def get_package_info() -> dict:
    """Get comprehensive package information."""
    return {
        "name": "readme-generator",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": __description__,
        "url": __url__,
        "python_requires": ">=3.8",
        "license": "MIT",
    }
