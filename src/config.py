"""
Configuration management for the README generator.

This module handles loading, saving, and managing configuration settings
for the README generation tool, including model settings, parsing options,
and output preferences.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration settings for the README generator."""
    
    # Model configuration
    model_name: str = "gemini_2_5_pro"
    max_tokens: int = 1_000_000
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    
    # Parsing options
    include_tests: bool = False
    include_private: bool = False
    include_docs: bool = True
    
    # Output options
    output_format: str = "markdown"
    output_file: str = "README.md"
    template_path: Optional[str] = None
    
    # Performance settings
    timeout: int = 90
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    cache_enabled: bool = True
    cache_dir: Optional[str] = None
    
    # Logging and debugging
    verbose: bool = False
    quiet: bool = False
    debug: bool = False
    log_file: Optional[str] = None
    
    # Token management
    token_budget_allocation: Dict[str, float] = field(default_factory=lambda: {
        "metadata": 0.005,
        "dependencies": 0.01,
        "structure": 0.05,
        "api_documentation": 0.60,
        "examples": 0.20,
        "configuration": 0.035,
        "buffer": 0.10,
    })
    
    # Content prioritization
    priority_weights: Dict[str, float] = field(default_factory=lambda: {
        "public_classes": 10,
        "public_functions": 9,
        "main_entry_points": 10,
        "well_documented": 8,
        "has_examples": 9,
        "framework_related": 7,
        "configuration": 6,
        "private_methods": 3,
        "test_files": 4,
    })
    
    # Model-specific settings
    model_settings: Dict[str, Any] = field(default_factory=lambda: {
        "temperature": 0.7,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "max_retries": 3,
        "retry_delay": 1.0,
    })
    
    # File patterns
    ignore_patterns: list = field(default_factory=lambda: [
        ".git", ".svn", ".hg", ".bzr",
        "__pycache__", "*.pyc", "*.pyo", "*.pyd",
        "venv", "env", ".venv", ".env", "virtualenv",
        ".vscode", ".idea", "*.swp", "*.swo",
        "build", "dist", "*.egg-info", ".tox",
        ".DS_Store", "Thumbs.db",
        "*.tmp", "*.temp", "*.log"
    ])
    
    def __post_init__(self):
        """Post-initialization setup."""
        # Set up cache directory
        if self.cache_dir is None:
            self.cache_dir = str(Path.home() / ".readme_generator" / "cache")
        
        # Load API key from environment if not set
        if self.api_key is None:
            self.api_key = self._get_api_key_from_env()
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variables."""
        env_keys = {
            "gemini_2_5_pro": "AIzaSyBI-cBe8ClKDTUrJuQ8x2i94OGen6XFbvs",
            "gemini_2_5_flash": "AIzaSyBI-cBe8ClKDTUrJuQ8x2i94OGen6XFbvs",
            "gpt_4o": "OPENAI_API_KEY",
            "gpt_4o_mini": "OPENAI_API_KEY",
            "claude_sonnet": "ANTHROPIC_API_KEY",
        }
        
        env_key = env_keys.get(self.model_name)
        if env_key:
            return os.getenv(env_key)
        
        return None
    
    def update(self, other: Union['Config', Dict[str, Any]]) -> None:
        """Update configuration with values from another config or dictionary."""
        if isinstance(other, Config):
            other_dict = asdict(other)
        else:
            other_dict = other
        
        for key, value in other_dict.items():
            if hasattr(self, key):
                # Handle nested dictionaries
                if isinstance(getattr(self, key), dict) and isinstance(value, dict):
                    getattr(self, key).update(value)
                else:
                    setattr(self, key, value)
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate model name
        valid_models = [
            "gemini_2_5_pro", "gemini_2_5_flash", 
            "gpt_4o", "gpt_4o_mini", "claude_sonnet"
        ]
        if self.model_name not in valid_models:
            errors.append(f"Invalid model name: {self.model_name}")
        
        # Validate token limits
        if self.max_tokens < 1000:
            errors.append("max_tokens must be at least 1000")
        
        # Validate timeout
        if self.timeout < 1:
            errors.append("timeout must be at least 1 second")
        
        # Validate output format
        valid_formats = ["markdown", "json"]
        if self.output_format not in valid_formats:
            errors.append(f"Invalid output format: {self.output_format}")
        
        # Validate token budget allocation
        budget_sum = sum(self.token_budget_allocation.values())
        if abs(budget_sum - 1.0) > 0.001:  # Allow small floating point errors
            errors.append(f"Token budget allocation must sum to 1.0, got {budget_sum}")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors))
    
    def get_cache_path(self) -> Path:
        """Get the cache directory path."""
        cache_path = Path(self.cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model-specific configuration."""
        base_config = {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "api_key": self.api_key,
            "api_base_url": self.api_base_url,
            "timeout": self.timeout,
        }
        
        base_config.update(self.model_settings)
        return base_config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        # Filter out unknown keys
        valid_keys = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        
        return cls(**filtered_data)


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".readme_generator" / "config.json"


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, uses default location.
        
    Returns:
        Config object loaded from file
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If configuration file is invalid
    """
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = Config.from_dict(data)
        config.validate()
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")


def save_config(config: Config, config_path: Optional[Union[str, Path]] = None) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration object to save
        config_path: Path to save configuration file. If None, uses default location.
        
    Raises:
        ValueError: If configuration is invalid
        IOError: If unable to write to file
    """
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)
    
    # Validate configuration before saving
    config.validate()
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved configuration to {config_path}")
        
    except Exception as e:
        raise IOError(f"Failed to save configuration: {e}")


def create_default_config() -> Config:
    """Create a default configuration object."""
    return Config()


def get_config_template() -> Dict[str, Any]:
    """Get a configuration template with comments."""
    return {
        "_comment": "README Generator Configuration File",
        "_version": "1.0.0",
        "_description": "Configuration settings for the README generator tool",
        
        "model_name": "gemini_2_5_pro",
        "max_tokens": 1000000,
        "api_key": None,
        "api_base_url": None,
        
        "include_tests": False,
        "include_private": False,
        "include_docs": True,
        
        "output_format": "markdown",
        "output_file": "README.md",
        "template_path": None,
        
        "timeout": 90,
        "max_file_size": 10485760,
        "cache_enabled": True,
        "cache_dir": None,
        
        "verbose": False,
        "quiet": False,
        "debug": False,
        "log_file": None,
        
        "token_budget_allocation": {
            "metadata": 0.005,
            "dependencies": 0.01,
            "structure": 0.05,
            "api_documentation": 0.60,
            "examples": 0.20,
            "configuration": 0.035,
            "buffer": 0.10
        },
        
        "priority_weights": {
            "public_classes": 10,
            "public_functions": 9,
            "main_entry_points": 10,
            "well_documented": 8,
            "has_examples": 9,
            "framework_related": 7,
            "configuration": 6,
            "private_methods": 3,
            "test_files": 4
        },
        
        "model_settings": {
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "max_retries": 3,
            "retry_delay": 1.0
        },
        
        "ignore_patterns": [
            ".git", ".svn", ".hg", ".bzr",
            "__pycache__", "*.pyc", "*.pyo", "*.pyd",
            "venv", "env", ".venv", ".env", "virtualenv",
            ".vscode", ".idea", "*.swp", "*.swo",
            "build", "dist", "*.egg-info", ".tox",
            ".DS_Store", "Thumbs.db",
            "*.tmp", "*.temp", "*.log"
        ]
    }


def merge_configs(base_config: Config, override_config: Dict[str, Any]) -> Config:
    """
    Merge two configurations, with override taking precedence.
    
    Args:
        base_config: Base configuration object
        override_config: Dictionary of override values
        
    Returns:
        New Config object with merged values
    """
    merged_data = base_config.to_dict()
    
    for key, value in override_config.items():
        if key in merged_data:
            if isinstance(merged_data[key], dict) and isinstance(value, dict):
                merged_data[key].update(value)
            else:
                merged_data[key] = value
    
    return Config.from_dict(merged_data)


# Convenience functions for common operations
def init_config_file(config_path: Optional[Union[str, Path]] = None, 
                    template: bool = False) -> None:
    """
    Initialize a configuration file with default values.
    
    Args:
        config_path: Path to create configuration file
        template: Whether to create a template with comments
    """
    if config_path is None:
        config_path = get_default_config_path()
    else:
        config_path = Path(config_path)
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    if template:
        config_data = get_config_template()
    else:
        config_data = create_default_config().to_dict()
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created configuration file: {config_path}")


def validate_config_file(config_path: Union[str, Path]) -> bool:
    """
    Validate a configuration file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        load_config(config_path)
        return True
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False
