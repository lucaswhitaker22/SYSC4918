"""
README Generator - Automated README generation for Python projects.
"""

from .parser.project_parser import parse_project
from .utils.token_counter import estimate_tokens, count_tokens_in_dict
from .utils.content_prioritizer import filter_content_under_token_limit
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
    
    # Utility functions
    "estimate_tokens",
    "count_tokens_in_dict",
    "filter_content_under_token_limit",
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
