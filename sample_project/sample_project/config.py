"""
Configuration management for the Sample Project.

This module provides comprehensive configuration handling including
loading from files, environment variables, and runtime settings.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Enumeration of supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ConfigError(Exception):
    """Raised when configuration operations fail."""
    pass


@dataclass
class Config:
    """
    Main configuration class for the Sample Project.
    
    This class manages all configuration settings including
    processing parameters, system settings, and feature flags.
    
    Attributes:
        debug: Enable debug mode
        max_items: Maximum number of items to process
        max_size: Maximum size limit for data processing
        timeout: Timeout in seconds for operations
        cache_enabled: Whether to enable result caching
        log_level: Logging level
        output_format: Default output format
        
        # Processing options
        uppercase: Convert strings to uppercase during processing
        multiply_factor: Multiplication factor for numeric processing
        
        # Advanced settings
        parallel_processing: Enable parallel processing
        max_workers: Maximum number of worker threads
        retry_attempts: Number of retry attempts for failed operations
        retry_delay: Delay between retries in seconds
        
        # Feature flags
        experimental_features: Enable experimental features
        strict_validation: Enable strict input validation
        
        # File and directory settings
        data_directory: Directory for data files
        output_directory: Directory for output files
        temp_directory: Temporary directory for processing
        
        # External service settings
        api_endpoints: Dictionary of external API endpoints
        api_timeouts: Timeout settings for external APIs
        api_keys: API keys for external services
        
    Example:
        >>> config = Config(debug=True, max_items=50)
        >>> config.debug
        True
        >>> config.is_debug_mode()
        True
    """
    
    # Core settings
    debug: bool = False
    max_items: int = 100
    max_size: int = 10000
    timeout: int = 30
    cache_enabled: bool = True
    log_level: LogLevel = LogLevel.INFO
    output_format: str = "json"
    
    # Processing options
    uppercase: bool = False
    multiply_factor: Optional[float] = None
    
    # Advanced settings
    parallel_processing: bool = False
    max_workers: int = 4
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Feature flags
    experimental_features: bool = False
    strict_validation: bool = True
    
    # File and directory settings
    data_directory: str = "data"
    output_directory: str = "output"
    temp_directory: str = "temp"
    
    # External service settings
    api_endpoints: Dict[str, str] = field(default_factory=dict)
    api_timeouts: Dict[str, int] = field(default_factory=dict)
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    # Custom settings for extensibility
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize configuration after instance creation."""
        # Load from environment variables
        self._load_from_environment()
        
        # Set up default API endpoints
        if not self.api_endpoints:
            self.api_endpoints = {
                "test_api": "https://api.example.com/v1",
                "backup_api": "https://backup.example.com/v1",
            }
        
        # Set up default API timeouts
        if not self.api_timeouts:
            self.api_timeouts = {
                "test_api": 30,
                "backup_api": 60,
            }
        
        # Validate configuration
        self.validate()
    
    def validate(self) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ConfigError: If configuration is invalid
        """
        if self.max_items <= 0:
            raise ConfigError("max_items must be positive")
        
        if self.max_size <= 0:
            raise ConfigError("max_size must be positive")
        
        if self.timeout <= 0:
            raise ConfigError("timeout must be positive")
        
        if self.max_workers <= 0:
            raise ConfigError("max_workers must be positive")
        
        if self.retry_attempts < 0:
            raise ConfigError("retry_attempts cannot be negative")
        
        if self.retry_delay < 0:
            raise ConfigError("retry_delay cannot be negative")
        
        # Validate directories exist or can be created
        for dir_attr in ['data_directory', 'output_directory', 'temp_directory']:
            dir_path = Path(getattr(self, dir_attr))
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Cannot create directory {dir_path}: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration values from environment variables."""
        env_mappings = {
            'SAMPLE_DEBUG': ('debug', lambda x: x.lower() == 'true'),
            'SAMPLE_MAX_ITEMS': ('max_items', int),
            'SAMPLE_MAX_SIZE': ('max_size', int),
            'SAMPLE_TIMEOUT': ('timeout', int),
            'SAMPLE_CACHE_ENABLED': ('cache_enabled', lambda x: x.lower() == 'true'),
            'SAMPLE_LOG_LEVEL': ('log_level', lambda x: LogLevel(x.upper())),
            'SAMPLE_OUTPUT_FORMAT': ('output_format', str),
            'SAMPLE_UPPERCASE': ('uppercase', lambda x: x.lower() == 'true'),
            'SAMPLE_MULTIPLY_FACTOR': ('multiply_factor', float),
            'SAMPLE_PARALLEL_PROCESSING': ('parallel_processing', lambda x: x.lower() == 'true'),
            'SAMPLE_MAX_WORKERS': ('max_workers', int),
            'SAMPLE_RETRY_ATTEMPTS': ('retry_attempts', int),
            'SAMPLE_RETRY_DELAY': ('retry_delay', float),
            'SAMPLE_EXPERIMENTAL': ('experimental_features', lambda x: x.lower() == 'true'),
            'SAMPLE_STRICT_VALIDATION': ('strict_validation', lambda x: x.lower() == 'true'),
            'SAMPLE_DATA_DIR': ('data_directory', str),
            'SAMPLE_OUTPUT_DIR': ('output_directory', str),
            'SAMPLE_TEMP_DIR': ('temp_directory', str),
        }
        
        for env_var, (attr_name, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    converted_value = converter(env_value)
                    setattr(self, attr_name, converted_value)
                    logger.debug(f"Loaded {attr_name} from environment: {converted_value}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert environment variable {env_var}: {e}")
        
        # Load API keys from environment
        api_key_prefixes = ['SAMPLE_API_KEY_', 'API_KEY_']
        for prefix in api_key_prefixes:
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    service_name = key[len(prefix):].lower()
                    self.api_keys[service_name] = value
                    logger.debug(f"Loaded API key for service: {service_name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary representation.
        
        Returns:
            Dictionary containing all configuration values
        """
        config_dict = asdict(self)
        
        # Convert LogLevel enum to string
        if isinstance(config_dict.get('log_level'), LogLevel):
            config_dict['log_level'] = self.log_level.value
        
        return config_dict
