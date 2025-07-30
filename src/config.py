"""
Minimal configuration management for the README generator.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class Config:
    """Minimal configuration for README generator."""
    
    def __init__(self):
        # Core settings used by CLI
        self.model_name: str = "gemini_2_5_pro"
        self.max_tokens: int = 1_000_000
        self.api_key: Optional[str] = None
        
        # Parsing options
        self.include_tests: bool = False
        self.include_private: bool = False
        
        # CLI options
        self.verbose: bool = False
        self.quiet: bool = False
        self.debug: bool = False
        self.timeout: int = 90
        self.cache_enabled: bool = True
        self.parse_only: bool = False
        
        # Try to get API key from environment
        self._load_api_key_from_env()
    
    def _load_api_key_from_env(self) -> None:
        """Load API key from environment variables."""
        env_keys = {
            "gemini_2_5_pro": "GEMINI_API_KEY",
            "gemini_2_5_flash": "GEMINI_API_KEY",
            "gpt_4o": "OPENAI_API_KEY",
            "gpt_4o_mini": "OPENAI_API_KEY",
            "claude_sonnet": "ANTHROPIC_API_KEY",
        }
        
        env_key = env_keys.get(self.model_name)
        if env_key and not self.api_key:
            self.api_key = os.getenv(env_key)
    
    def update(self, other: Union['Config', Dict[str, Any]]) -> None:
        """Update configuration with values from another config or dictionary."""
        if isinstance(other, Config):
            other_dict = self._to_dict(other)
        else:
            other_dict = other
        
        for key, value in other_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _to_dict(self, config: 'Config') -> Dict[str, Any]:
        """Convert config object to dictionary."""
        return {
            attr: getattr(config, attr) 
            for attr in dir(config) 
            if not attr.startswith('_') and not callable(getattr(config, attr))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this configuration to dictionary."""
        return self._to_dict(self)

def load_config(config_path: Union[str, Path]) -> Config:
    """Load configuration from JSON file."""
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = Config()
        config.update(data)
        
        # FIXED: Reload API key from environment after updating model_name from file
        config._load_api_key_from_env()
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")


def save_config(config: Config, config_path: Union[str, Path]) -> None:
    """Save configuration to JSON file."""
    config_path = Path(config_path)
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved configuration to {config_path}")
        
    except Exception as e:
        raise IOError(f"Failed to save configuration: {e}")
