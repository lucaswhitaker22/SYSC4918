"""
Sample Project - A comprehensive Python project for testing README generation.

This package demonstrates various Python patterns and structures including:
- Configuration management
- CLI interfaces  
- Data models
- Utility functions
- Core business logic
- Entry points and scripts

Features:
- Configurable data processing pipeline
- Command-line interface with multiple commands
- Extensible plugin architecture
- Comprehensive error handling
- Type hints and documentation

Usage:
    >>> from sample_project import SampleProcessor
    >>> processor = SampleProcessor()
    >>> result = processor.process("Hello World")
    >>> print(result)
    Processed: Hello World

Example:
    Basic usage of the package:

    ```
    from sample_project import SampleProcessor, Config
    from sample_project.models import DataModel

    # Initialize with custom config
    config = Config(debug=True, max_items=100)
    processor = SampleProcessor(config)

    # Process some data
    data = DataModel(name="test", value=42)
    result = processor.process_data_model(data)
    ```
"""

from .main import SampleProcessor, DataProcessor, ProcessingError
from .config import Config, load_config, save_config, DEFAULT_CONFIG
from .models import DataModel, ResultModel, ValidationError
from .utils import format_output, validate_input, timing_decorator

# Package metadata
__version__ = "1.2.3"
__author__ = "John Developer"
__email__ = "john.dev@example.com"
__description__ = "A comprehensive sample Python project for testing README generation"
__url__ = "https://github.com/example/sample-project"
__license__ = "MIT"

# Version info tuple
__version_info__ = tuple(map(int, __version__.split('.')))

# Package-level constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
SUPPORTED_FORMATS = ["json", "yaml", "xml", "csv"]

# Main API exports
__all__ = [
    # Core classes
    "SampleProcessor",
    "DataProcessor", 
    
    # Configuration
    "Config",
    "load_config",
    "save_config",
    "DEFAULT_CONFIG",
    
    # Data models
    "DataModel",
    "ResultModel",
    
    # Utilities
    "format_output",
    "validate_input", 
    "timing_decorator",
    
    # Exceptions
    "ProcessingError",
    "ValidationError",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "__url__",
    "__license__",
    "__version_info__",
    
    # Constants
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES", 
    "SUPPORTED_FORMATS",
]

# Package initialization
def get_version() -> str:
    """Get the current package version."""
    return __version__

def get_package_info() -> dict:
    """Get comprehensive package information."""
    return {
        "name": "sample-project",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": __description__,
        "url": __url__,
        "license": __license__,
        "python_requires": ">=3.8",
        "supported_formats": SUPPORTED_FORMATS,
    }

# Convenience function for quick setup
def quick_setup(debug: bool = False, **kwargs) -> SampleProcessor:
    """
    Quickly set up a SampleProcessor with common defaults.
    
    Args:
        debug: Enable debug mode
        **kwargs: Additional configuration options
        
    Returns:
        Configured SampleProcessor instance
        
    Example:
        >>> processor = quick_setup(debug=True, max_items=50)
        >>> isinstance(processor, SampleProcessor)
        True
    """
    config = Config(debug=debug, **kwargs)
    return SampleProcessor(config)

# Module-level logger setup
import logging

def setup_logging(level: str = "INFO") -> None:
    """Set up package-level logging configuration."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger(__name__).info(f"Sample Project v{__version__} initialized")

# Auto-setup logging when package is imported
setup_logging()
