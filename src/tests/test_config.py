import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from config import Config, load_config, save_config

class TestConfigDefaults:
    """Test cases for Config default values."""
    
    def test_config_initialization_defaults(self):
        """Test that Config initializes with correct default values."""
        config = Config()
        
        assert config.model_name == "gemini_2_5_pro"
        assert config.max_tokens == 1_000_000
        assert config.api_key is None
        assert config.include_tests is False
        assert config.include_private is False
        assert config.verbose is False
        assert config.quiet is False
        assert config.debug is False
        assert config.timeout == 90
        assert config.cache_enabled is True
        assert config.parse_only is False
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test-env-key'})
    def test_config_loads_api_key_from_env(self):
        """Test that Config loads API key from environment variables."""
        config = Config()
        assert config.api_key == 'test-env-key'
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'openai-key'})
    def test_config_loads_different_api_key_for_different_model(self):
        """Test API key loading for different models."""
        config = Config()
        config.model_name = "gpt_4o"
        config._load_api_key_from_env()
        assert config.api_key == 'openai-key'

class TestConfigUpdate:
    """Test cases for Config update functionality."""
    
    def test_update_with_dict(self):
        """Test updating config with dictionary values."""
        config = Config()
        update_data = {
            "model_name": "gpt_4o",
            "max_tokens": 500000,
            "verbose": True,
            "include_tests": True
        }
        
        config.update(update_data)
        
        assert config.model_name == "gpt_4o"
        assert config.max_tokens == 500000
        assert config.verbose is True
        assert config.include_tests is True
        # Other values should remain unchanged
        assert config.timeout == 90
        assert config.debug is False
    
    def test_update_with_another_config(self):
        """Test updating config with another Config object."""
        config1 = Config()
        config2 = Config()
        
        config2.model_name = "claude_sonnet"
        config2.verbose = True
        config2.max_tokens = 750000
        
        config1.update(config2)
        
        assert config1.model_name == "claude_sonnet"
        assert config1.verbose is True
        assert config1.max_tokens == 750000
    
    def test_update_ignores_invalid_attributes(self):
        """Test that update ignores attributes that don't exist on Config."""
        config = Config()
        original_model = config.model_name
        
        update_data = {
            "model_name": "gpt_4o",
            "nonexistent_attr": "should_be_ignored",
            "another_invalid": 12345
        }
        
        config.update(update_data)
        
        assert config.model_name == "gpt_4o"
        assert not hasattr(config, "nonexistent_attr")
        assert not hasattr(config, "another_invalid")

class TestConfigSerialization:
    """Test cases for Config serialization."""
    
    def test_to_dict(self):
        """Test converting Config to dictionary."""
        config = Config()
        config.model_name = "test_model"
        config.verbose = True
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["model_name"] == "test_model"
        assert config_dict["verbose"] is True
        assert config_dict["max_tokens"] == 1_000_000
        
        # Should not include private methods or callable attributes
        assert "_load_api_key_from_env" not in config_dict
        assert "update" not in config_dict
        assert "to_dict" not in config_dict

class TestConfigFileOperations:
    """Test cases for Config file loading and saving."""
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration to/from file."""
        config = Config()
        config.model_name = "claude_sonnet"
        config.max_tokens = 500000
        config.verbose = True
        config.include_tests = True
        
        config_file = tmp_path / "test_config.json"
        
        # Save configuration
        save_config(config, str(config_file))
        
        # Check file was created
        assert config_file.exists()
        
        # Load configuration
        loaded_config = load_config(str(config_file))
        
        assert isinstance(loaded_config, Config)
        assert loaded_config.model_name == "claude_sonnet"
        assert loaded_config.max_tokens == 500000
        assert loaded_config.verbose is True
        assert loaded_config.include_tests is True
    
    def test_save_config_creates_directory(self, tmp_path):
        """Test that save_config creates directories if they don't exist."""
        config = Config()
        nested_dir = tmp_path / "nested" / "dir"
        config_file = nested_dir / "config.json"
        
        save_config(config, str(config_file))
        
        assert config_file.exists()
        
        # Verify content is valid JSON
        with open(config_file, 'r') as f:
            data = json.load(f)
        assert data["model_name"] == "gemini_2_5_pro"
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config("/nonexistent/config.json")
        assert "Configuration file not found" in str(exc_info.value)
    
    def test_load_config_invalid_json(self, tmp_path):
        """Test loading configuration file with invalid JSON."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json content")
        
        with pytest.raises(ValueError) as exc_info:
            load_config(str(config_file))
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_load_config_partial_data(self, tmp_path):
        """Test loading configuration with only partial data."""
        config_file = tmp_path / "partial_config.json"
        partial_data = {
            "model_name": "gpt_4o_mini",
            "verbose": True
            # Missing other fields
        }
        
        with open(config_file, 'w') as f:
            json.dump(partial_data, f)
        
        loaded_config = load_config(str(config_file))
        
        # Should have loaded values
        assert loaded_config.model_name == "gpt_4o_mini"
        assert loaded_config.verbose is True
        
        # Should have defaults for missing values
        assert loaded_config.max_tokens == 1_000_000
        assert loaded_config.include_tests is False
    
    def test_save_config_io_error(self, tmp_path):
        """Test save_config handles IO errors gracefully."""
        config = Config()
        
        # FIXED: Mock the open function instead of mkdir to trigger the right error path
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with pytest.raises(IOError) as exc_info:
                save_config(config, str(tmp_path / "config.json"))
            assert "Failed to save configuration" in str(exc_info.value)

class TestConfigIntegration:
    """Integration test cases for Config."""
    
    def test_full_config_workflow(self, tmp_path):
        """Test complete configuration workflow."""
        # Create initial config
        config1 = Config()
        config1.model_name = "claude_sonnet"
        config1.max_tokens = 750000
        config1.verbose = True
        config1.api_key = "test-key"
        
        config_file = tmp_path / "workflow_config.json"
        
        # Save config
        save_config(config1, str(config_file))
        
        # Load config
        config2 = load_config(str(config_file))
        
        # Update loaded config
        config2.model_name = "gpt_4o"
        config2.include_tests = True
        
        # Save updated config
        save_config(config2, str(config_file))
        
        # Load final config
        config3 = load_config(str(config_file))
        
        # Verify all changes persisted
        assert config3.model_name == "gpt_4o"
        assert config3.max_tokens == 750000
        assert config3.verbose is True
        assert config3.include_tests is True
        assert config3.api_key == "test-key"
    
    def test_config_with_environment_override(self, tmp_path):
        """Test config behavior with environment variables."""
        config_file = tmp_path / "env_config.json"
        
        # Save config without API key
        config = Config()
        config.model_name = "gpt_4o"  # FIXED: Changed from "openai_model" to valid model name
        save_config(config, str(config_file))
        
        # Load config with environment variable set
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-override-key'}):
            loaded_config = load_config(str(config_file))
            # API key should come from environment during initialization
            assert loaded_config.api_key == 'env-override-key'
