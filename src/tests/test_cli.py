import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from argparse import Namespace
import tempfile
from pathlib import Path

from cli import (
    create_parser, 
    validate_arguments, 
    load_configuration,
    validate_api_requirements,
    init_config_command,
    CLIError,
    LLMAPIError
)
from config import Config

class TestCLIParser:
    """Test cases for CLI argument parsing."""
    
    def test_create_parser_defaults(self):
        """Test parser creation with default values."""
        parser = create_parser()
        args = parser.parse_args(["/test/path"])
        
        assert args.project_path == "/test/path"
        assert args.model == "gemini_2_5_pro"
        assert args.max_tokens == 1_000_000
        assert args.include_tests is False
        assert args.include_private is False
        assert args.verbose is False
        assert args.quiet is False
        assert args.debug is False
        assert args.timeout == 90
        assert args.output == "README.md"
        assert args.parse_only is False
    
    def test_parse_args_with_all_options(self):
        """Test parsing arguments with various options."""
        parser = create_parser()
        args = parser.parse_args([
            "/test/path",
            "--model", "gpt_4o",
            "--max-tokens", "500000",
            "--include-tests",
            "--include-private",
            "--verbose",
            "--debug",
            "--output", "custom_readme.md",
            "--json-output", "data.json",
            "--api-key", "test-key",
            "--timeout", "120",
            "--parse-only",
            "--config", "config.json",
            "--save-config", "save.json"
        ])
        
        assert args.project_path == "/test/path"
        assert args.model == "gpt_4o"
        assert args.max_tokens == 500000
        assert args.include_tests is True
        assert args.include_private is True
        assert args.verbose is True
        assert args.debug is True
        assert args.output == "custom_readme.md"
        assert args.json_output == "data.json"
        assert args.api_key == "test-key"
        assert args.timeout == 120
        assert args.parse_only is True
        assert args.config == "config.json"
        assert args.save_config == "save.json"
    
    def test_model_choices(self):
        """Test that only valid model choices are accepted."""
        parser = create_parser()
        
        # Valid models should work
        for model in ['gemini_2_5_pro', 'gemini_2_5_flash', 'gpt_4o', 'gpt_4o_mini', 'claude_sonnet']:
            args = parser.parse_args(["/test/path", "--model", model])
            assert args.model == model
        
        # Invalid model should raise SystemExit (argparse error)
        with pytest.raises(SystemExit):
            parser.parse_args(["/test/path", "--model", "invalid_model"])

class TestArgumentValidation:
    """Test cases for argument validation."""
    
    def test_validate_arguments_init_config(self):
        """Test that init-config bypasses other validation."""
        args = Namespace(init_config=True, project_path=None)
        # Should not raise an exception
        validate_arguments(args)
    
    def test_validate_arguments_success(self, tmp_path):
        """Test successful argument validation."""
        test_dir = tmp_path
        (test_dir / "__init__.py").write_text("")
        
        args = Namespace(
            project_path=str(test_dir),
            init_config=False,
            max_tokens=10000,
            timeout=60
        )
        # Should not raise an exception
        validate_arguments(args)
    
    def test_validate_arguments_missing_path(self):
        """Test validation fails when project path is missing."""
        args = Namespace(project_path=None, init_config=False)
        
        with pytest.raises(CLIError) as exc_info:
            validate_arguments(args)
        assert "Project path is required" in str(exc_info.value)
    
    def test_validate_arguments_nonexistent_path(self):
        """Test validation fails for nonexistent path."""
        args = Namespace(
            project_path="/nonexistent/path",
            init_config=False,
            max_tokens=10000,
            timeout=60
        )
        
        with pytest.raises(CLIError) as exc_info:
            validate_arguments(args)
        assert "does not exist" in str(exc_info.value)
    
    def test_validate_arguments_not_directory(self, tmp_path):
        """Test validation fails when path is not a directory."""
        test_file = tmp_path / "not_a_dir.txt"
        test_file.write_text("content")
        
        args = Namespace(
            project_path=str(test_file),
            init_config=False,
            max_tokens=10000,
            timeout=60
        )
        
        with pytest.raises(CLIError) as exc_info:
            validate_arguments(args)
        assert "not a directory" in str(exc_info.value)
    
    def test_validate_arguments_token_limit_too_low(self, tmp_path):
        """Test validation fails when max_tokens is too low."""
        args = Namespace(
            project_path=str(tmp_path),
            init_config=False,
            max_tokens=500,  # Below minimum of 1000
            timeout=60
        )
        
        with pytest.raises(CLIError) as exc_info:
            validate_arguments(args)
        assert "at least 1000" in str(exc_info.value)
    
    def test_validate_arguments_timeout_too_low(self, tmp_path):
        """Test validation fails when timeout is too low."""
        args = Namespace(
            project_path=str(tmp_path),
            init_config=False,
            max_tokens=10000,
            timeout=0  # Below minimum of 1
        )
        
        with pytest.raises(CLIError) as exc_info:
            validate_arguments(args)
        assert "at least 1 second" in str(exc_info.value)

class TestConfigurationLoading:
    """Test cases for configuration loading."""
    
    def test_load_configuration_defaults(self):
        """Test loading configuration with default command-line args."""
        args = Namespace(
            model="gpt_4o",
            max_tokens=500000,
            include_tests=True,
            include_private=False,
            verbose=True,
            quiet=False,
            debug=False,
            timeout=120,
            config=None,
            api_key="test-key"
        )
        
        config = load_configuration(args)
        
        assert isinstance(config, Config)
        assert config.model_name == "gpt_4o"
        assert config.max_tokens == 500000
        assert config.include_tests is True
        assert config.include_private is False
        assert config.verbose is True
        assert config.quiet is False
        assert config.debug is False
        assert config.timeout == 120
        assert config.api_key == "test-key"
        assert config.cache_enabled is True
    
    @patch('cli.load_config')  # FIXED: Changed from 'src.cli.load_config'
    def test_load_configuration_from_file(self, mock_load_config):
        """Test loading configuration from file."""
        # Mock the loaded config
        mock_config = Config()
        mock_config.model_name = "claude_sonnet"
        mock_config.max_tokens = 750000
        mock_load_config.return_value = mock_config
        
        args = Namespace(
            model="gpt_4o",  # This should override the file config
            max_tokens=500000,  # This should override the file config
            include_tests=False,
            include_private=False,
            verbose=False,
            quiet=False,
            debug=False,
            timeout=90,
            config="test_config.json",
            api_key=None
        )
        
        config = load_configuration(args)
        
        mock_load_config.assert_called_once_with("test_config.json")
        # Command line args should override file config
        assert config.model_name == "gpt_4o"
        assert config.max_tokens == 500000
    
    @patch('cli.load_config')  # FIXED: Changed from 'src.cli.load_config'
    def test_load_configuration_file_error(self, mock_load_config, caplog):
        """Test handling of configuration file loading errors."""
        mock_load_config.side_effect = Exception("File error")
        
        args = Namespace(
            model="gemini_2_5_pro",
            max_tokens=1000000,
            include_tests=False,
            include_private=False,
            verbose=False,
            quiet=False,
            debug=False,
            timeout=90,
            config="bad_config.json",
            api_key=None
        )
        
        # Should not raise, but should log warning
        config = load_configuration(args)
        assert isinstance(config, Config)
        assert "Failed to load configuration" in caplog.text

class TestAPIValidation:
    """Test cases for API requirements validation."""
    
    def test_validate_api_requirements_with_key(self):
        """Test API validation when key is provided."""
        api_key = validate_api_requirements("gemini_2_5_pro", "test-key")
        assert api_key == "test-key"
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'env-key'})
    def test_validate_api_requirements_from_env(self):
        """Test API validation gets key from environment."""
        api_key = validate_api_requirements("gemini_2_5_pro", None)
        assert api_key == "env-key"
    
    def test_validate_api_requirements_missing_key(self):
        """Test API validation fails when no key is available."""
        with pytest.raises(CLIError) as exc_info:
            validate_api_requirements("gemini_2_5_pro", None)
        assert "API key required" in str(exc_info.value)
    
    @patch('cli.genai', None)  # FIXED: Changed from 'src.cli.genai'
    def test_validate_api_requirements_missing_package(self):
        """Test API validation fails when required package is missing."""
        with pytest.raises(CLIError) as exc_info:
            validate_api_requirements("gemini_2_5_pro", "test-key")
        assert "google-generativeai package required" in str(exc_info.value)

class TestInitConfig:
    """Test cases for init-config command."""
    
    @patch('cli.save_config')  # FIXED: Changed from 'src.cli.save_config'
    def test_init_config_command_success(self, mock_save_config, capsys):
        """Test successful config initialization."""
        args = Namespace()
        
        init_config_command(args)
        
        # Check that save_config was called
        mock_save_config.assert_called_once()
        call_args = mock_save_config.call_args
        config_arg = call_args[0][0]
        
        assert isinstance(config_arg, Config)
        assert config_arg.model_name == "gemini_2_5_pro"
        assert config_arg.max_tokens == 1_000_000
        assert config_arg.timeout == 90
        
        # Check output
        captured = capsys.readouterr()
        assert "Configuration file created" in captured.out
    
    @patch('cli.save_config')  # FIXED: Changed from 'src.cli.save_config'
    def test_init_config_command_failure(self, mock_save_config):
        """Test config initialization failure."""
        mock_save_config.side_effect = Exception("Save failed")
        args = Namespace()
        
        with pytest.raises(CLIError) as exc_info:
            init_config_command(args)
        assert "Failed to create configuration file" in str(exc_info.value)

class TestIntegration:
    """Integration test cases."""
    
    def test_full_argument_flow(self, tmp_path):
        """Test complete argument parsing and validation flow."""
        # Create a mock Python project
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "__init__.py").write_text("")
        (project_dir / "main.py").write_text("print('hello')")
        
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args([
            str(project_dir),
            "--model", "gpt_4o_mini",
            "--include-tests",
            "--verbose"
        ])
        
        # Validate arguments
        validate_arguments(args)  # Should not raise
        
        # Load configuration
        config = load_configuration(args)
        
        assert config.model_name == "gpt_4o_mini"
        assert config.include_tests is True
        assert config.verbose is True
