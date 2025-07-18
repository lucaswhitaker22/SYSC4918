"""
Command-line interface for the README generator.

This module provides the main CLI functionality for automatically generating
comprehensive README files for Python projects using LLM APIs, specifically
optimized for Gemini 2.5 Pro with 1M token context window.
"""

import os
import sys
import argparse
import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Third-party imports
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

from config import Config, load_config, save_config
from parser.project_parser import parse_project
from utils.token_counter import TokenCounter, get_token_budget_allocation
from utils.file_utils import create_directory, read_file_safely
from utils.json_serializer import serialize_project_data, save_json_to_file

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Custom exception for CLI errors."""
    pass


class LLMAPIError(Exception):
    """Custom exception for LLM API errors."""
    pass


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="readme-generator",
        description="description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  readme-generator /path/to/project
  readme-generator . --output custom_readme.md
  readme-generator /path/to/project --model gemini_2_5_pro
  readme-generator /path/to/project --api-key YOUR_API_KEY
  readme-generator --init-config
  
Performance Target:
  Generates README for projects up to 25 files/5,000 lines in under 90 seconds
        """
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s 1.0',
    )
    
    parser.add_argument(
        '--parse-only',
        action='store_true',
        help='Only parse project data to JSON, skip README generation'
    )

    # Main argument
    parser.add_argument(
        'project_path',
        nargs='?',
        help='Path to the Python project root directory'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='README.md',
        help='Output README file path (default: README.md in project root)'
    )
    
    parser.add_argument(
        '--json-output',
        type=str,
        help='Save parsed project data as JSON file'
    )
    
    # Model configuration (based on research recommendations)
    parser.add_argument(
        '--model',
        choices=['gemini_2_5_pro', 'gemini_2_5_flash', 'gpt_4o', 'gpt_4o_mini', 'claude_sonnet'],
        default='gemini_2_5_pro',
        help='LLM model to use (default: gemini_2_5_pro - recommended for balance of cost/context/accuracy)'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        help='API key for LLM service (or set via environment variables)'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=1_000_000,
        help='Maximum token budget (default: 1000000 for Gemini 2.5 Pro)'
    )
    
    # Parsing options
    parser.add_argument(
        '--include-tests',
        action='store_true',
        help='Include test files in analysis'
    )
    
    parser.add_argument(
        '--include-private',
        action='store_true',
        help='Include private methods and classes'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--init-config',
        action='store_true',
        help='Initialize configuration file with default settings'
    )
    
    parser.add_argument(
        '--save-config',
        type=str,
        help='Save current settings to configuration file'
    )
    
    # Verbosity and debugging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with detailed logging'
    )
    
    # Performance options
    parser.add_argument(
        '--timeout',
        type=int,
        default=90,
        help='Timeout in seconds (default: 90 - meets performance requirement)'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable result caching'
    )
    
    # Template options
    parser.add_argument(
        '--template',
        type=str,
        help='Custom README template file'
    )
    
    parser.add_argument(
        '--sections',
        type=str,
        nargs='+',
        default=['description', 'installation', 'usage', 'structure', 'dependencies'],
        help='README sections to generate'
    )
    
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command-line arguments."""
    # Special commands that don't require project path
    if args.init_config:
        return
    
    # Validate project path
    if not args.project_path:
        raise CLIError("Project path is required. Use --help for usage information.")
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        raise CLIError(f"Project path does not exist: {args.project_path}")
    
    if not project_path.is_dir():
        raise CLIError(f"Project path is not a directory: {args.project_path}")
    
    # Check if it looks like a Python project
    python_indicators = ['setup.py', 'pyproject.toml', 'requirements.txt', '__init__.py']
    has_python_files = any((project_path / indicator).exists() for indicator in python_indicators)
    has_py_files = any(project_path.glob('**/*.py'))
    
    if not has_python_files and not has_py_files:
        logger.warning(f"No Python project indicators found in {project_path}")
    
    # Validate token limit
    if args.max_tokens < 1000:
        raise CLIError("Maximum tokens must be at least 1000")
    
    # Validate timeout (performance requirement: under 90 seconds)
    if args.timeout < 1:
        raise CLIError("Timeout must be at least 1 second")
    
    if args.timeout > 300:
        logger.warning(f"Timeout of {args.timeout}s exceeds recommended 90s performance target")


def validate_api_requirements(model_name: str, api_key: Optional[str]) -> str:
    """Validate API requirements and return the API key."""
    # Environment variable mappings based on research
    env_key_mapping = {
        'gemini_2_5_pro': 'GEMINI_API_KEY',
        'gemini_2_5_flash': 'GEMINI_API_KEY', 
        'gpt_4o': 'OPENAI_API_KEY',
        'gpt_4o_mini': 'OPENAI_API_KEY',
        'claude_sonnet': 'ANTHROPIC_API_KEY'
    }
    
    # Get API key from argument or environment
    if not api_key:
        env_var = env_key_mapping.get(model_name)
        if env_var:
            api_key = os.getenv(env_var)
    
    if not api_key:
        env_var = env_key_mapping.get(model_name, 'API_KEY')
        raise CLIError(
            f"API key required for {model_name}. "
            f"Provide via --api-key argument or {env_var} environment variable."
        )
    
    # Validate required packages
    if model_name.startswith('gemini') and not genai:
        raise CLIError("google-generativeai package required for Gemini models. Install with: pip install google-generativeai")
    elif model_name.startswith('gpt') and not openai:
        raise CLIError("openai package required for OpenAI models. Install with: pip install openai")
    elif model_name.startswith('claude') and not anthropic:
        raise CLIError("anthropic package required for Claude models. Install with: pip install anthropic")
    
    return api_key


def load_configuration(args: argparse.Namespace) -> Config:
    """Load configuration from file and command-line arguments."""
    config = Config()
    
    # Load from config file if specified
    if args.config:
        try:
            loaded_config = load_config(args.config)
            config.update(loaded_config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.warning(f"Failed to load configuration from {args.config}: {e}")
    
    # Override with command-line arguments
    config.model_name = args.model
    config.max_tokens = args.max_tokens
    config.include_tests = args.include_tests
    config.include_private = args.include_private
    config.verbose = args.verbose
    config.quiet = args.quiet
    config.debug = args.debug
    config.timeout = args.timeout
    config.cache_enabled = not args.no_cache
    
    if args.api_key:
        config.api_key = args.api_key
    
    return config


async def generate_readme_with_llm(project_data: Any, config: Config, api_key: str) -> str:
    """Generate README content using the specified LLM API."""
    try:
        # Serialize project data for LLM prompt
        serialized_data = serialize_project_data(project_data)
        
        # Count tokens to ensure we're within limits
        token_counter = TokenCounter(config.model_name)
        token_count = token_counter.count_tokens_in_dict(serialized_data)
        
        logger.info(f"Sending {token_count:,} tokens to {config.model_name}")
        
        if token_count > config.max_tokens:
            logger.warning(f"Token count ({token_count:,}) exceeds limit ({config.max_tokens:,})")
        
        # Create prompt based on project requirements
        prompt = create_readme_prompt(serialized_data, project_data.metadata.project_name)
        
        # Generate content based on model type
        if config.model_name.startswith('gemini'):
            return await generate_with_gemini(prompt, config, api_key)
        elif config.model_name.startswith('gpt'):
            return await generate_with_openai(prompt, config, api_key)
        elif config.model_name.startswith('claude'):
            return await generate_with_claude(prompt, config, api_key)
        else:
            raise LLMAPIError(f"Unsupported model: {config.model_name}")
            
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise LLMAPIError(f"Failed to generate README with {config.model_name}: {e}")


def create_readme_prompt(project_data: Dict[str, Any], project_name: str) -> str:
    """Create a comprehensive prompt for README generation based on project requirements."""
    return f"""You are an expert technical writer specializing in creating comprehensive README files for Python projects. 

Generate a professional, well-structured README.md file for the Python project "{project_name}" based on the following parsed project information:

{json.dumps(project_data, indent=2)}

Requirements:
1. Create a complete README with these essential sections:
   - Project Description (clear, concise overview)
   - Installation Instructions (accurate dependency handling)
   - Usage Examples (practical, working code examples)
   - Project Structure (organized file/directory overview)
   - Dependencies (production and development)
   - API Documentation (for key classes and functions)

2. Follow these guidelines:
   - Use proper Markdown formatting
   - Include working code examples where appropriate
   - Be accurate to the actual project structure and dependencies
   - Make installation instructions clear and correct
   - Ensure examples are practical and executable
   - Maintain professional, clear writing style

3. Focus on:
   - Accuracy of project description based on actual code
   - Correctness of installation and dependency information
   - Clarity and usefulness of usage examples
   - Overall coherence and readability

Generate only the README content in Markdown format, without any additional commentary or explanations."""


async def generate_with_gemini(prompt: str, config: Config, api_key: str) -> str:
    """Generate README using Gemini API (recommended model based on research)."""
    if not genai:
        raise LLMAPIError("google-generativeai package not available")
    
    try:
        genai.configure(api_key=api_key)
        
        # Configure model based on research findings
        model_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_output_tokens": 8192,
        }
        
        model_name = "gemini-2.5-pro" if "pro" in config.model_name else "gemini-2.5-flash"
        model = genai.GenerativeModel(model_name=model_name, generation_config=model_config)
        
        logger.info(f"Generating README with {model_name} (1M token context window)")
        
        response = await model.generate_content_async(prompt)
        
        if not response.text:
            raise LLMAPIError("Empty response from Gemini API")
        
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise LLMAPIError(f"Gemini API call failed: {e}")


async def generate_with_openai(prompt: str, config: Config, api_key: str) -> str:
    """Generate README using OpenAI API."""
    if not openai:
        raise LLMAPIError("openai package not available")
    
    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        
        model_mapping = {
            'gpt_4o': 'gpt-4o',
            'gpt_4o_mini': 'gpt-4o-mini'
        }
        
        model_name = model_mapping.get(config.model_name, 'gpt-4o-mini')
        
        logger.info(f"Generating README with {model_name} (128K context window)")
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert technical writer specializing in README documentation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4096
        )
        
        if not response.choices or not response.choices[0].message.content:
            raise LLMAPIError("Empty response from OpenAI API")
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise LLMAPIError(f"OpenAI API call failed: {e}")


async def generate_with_claude(prompt: str, config: Config, api_key: str) -> str:
    """Generate README using Claude API (highest coding accuracy per research)."""
    if not anthropic:
        raise LLMAPIError("anthropic package not available")
    
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        logger.info("Generating README with Claude Sonnet (200K context window, highest coding accuracy)")
        
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        if not response.content or not response.content[0].text:
            raise LLMAPIError("Empty response from Claude API")
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        raise LLMAPIError(f"Claude API call failed: {e}")


def init_config_command(args: argparse.Namespace) -> None:
    """Initialize a configuration file with project-specific defaults."""
    config_path = "readme_generator_config.json"
    
    try:
        # Create configuration with research-based defaults
        config = Config()
        config.model_name = "gemini_2_5_pro"  # Research recommendation
        config.max_tokens = 1_000_000  # Gemini 2.5 Pro context window
        config.timeout = 90  # Performance requirement
        
        save_config(config, config_path)
        
        print(f"✓ Configuration file created: {config_path}")
        print("\nRecommended model settings based on research:")
        print("  - Gemini 2.5 Pro: Best balance of cost, context (1M tokens), and coding accuracy")
        print("  - GPT-4o-mini: Most cost-efficient option")
        print("  - Claude Sonnet: Highest coding accuracy (72.7% SWE-bench)")
        print(f"\nEdit {config_path} to customize settings, then use:")
        print(f"readme-generator /path/to/project --config {config_path}")
        
    except Exception as e:
        raise CLIError(f"Failed to create configuration file: {e}")


async def parse_and_generate_command(args: argparse.Namespace, config: Config) -> None:
    """Execute the main project parsing and README generation command."""
    start_time = time.time()
    
    try:
        project_path = Path(args.project_path).resolve()
        
        logger.info(f"Parsing project: {project_path}")
        logger.info(f"Token budget: {config.max_tokens:,}")
        
        # Parse the project
        parsing_start = time.time()
        result = parse_project(
            project_path=str(project_path),
            model_name=config.model_name,
            max_tokens=config.max_tokens,
            include_tests=config.include_tests,
            include_private=config.include_private
        )
        parsing_time = time.time() - parsing_start
        
        if not result.success:
            raise CLIError(f"Project parsing failed: {'; '.join(result.errors)}")
        
        # Display parsing results
        if not config.quiet:
            print(f"✓ Project parsed successfully in {parsing_time:.2f}s")
            print(f"  Files processed: {result.stats.get('files_processed', 0)}")
            print(f"  Lines processed: {result.stats.get('lines_processed', 0):,}")
            print(f"  Classes found: {result.stats.get('classes_found', 0)}")
            print(f"  Functions found: {result.stats.get('functions_found', 0)}")
            print(f"  Examples found: {result.stats.get('examples_found', 0)}")
            print(f"  Token count: {result.project_data.token_count:,}")
            
            if result.warnings:
                print(f"  Warnings: {len(result.warnings)}")
                if config.verbose:
                    for warning in result.warnings:
                        print(f"    - {warning}")
        
        # Always save JSON output (either to specified file or default)
        json_output_path = args.json_output or f"{project_path.name}_parsed_data.json"
        serialized_data = serialize_project_data(result.project_data)
        success = save_json_to_file(serialized_data, json_output_path)
        
        if success and not config.quiet:
            print(f"✓ JSON data saved to: {json_output_path}")
        
        # Skip README generation if parse-only mode
        if args.parse_only:
            total_time = time.time() - start_time
            if not config.quiet:
                print(f"✓ Parse-only mode completed in {total_time:.2f}s")
            return
        
        # README generation (requires API key)
        api_key = validate_api_requirements(config.model_name, config.api_key)
        
        if not config.quiet:
            print(f"\nGenerating README with {config.model_name}...")
        
        generation_start = time.time()
        readme_content = await generate_readme_with_llm(result.project_data, config, api_key)
        generation_time = time.time() - generation_start
        
        # Save README file
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = project_path / output_path
        
        try:
            create_directory(str(output_path.parent))
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            total_time = time.time() - start_time
            
            if not config.quiet:
                print(f"✓ README generated in {generation_time:.2f}s")
                print(f"✓ Total time: {total_time:.2f}s")
                print(f"✓ README saved to: {output_path}")
            
        except Exception as e:
            raise CLIError(f"Failed to write README file: {e}")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Command failed after {elapsed_time:.2f}s: {e}")
        raise



def print_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message to stderr."""
    print(f"Warning: {message}", file=sys.stderr)


def main() -> None:
    """Main CLI entry point."""
    try:
        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()
        
        # Handle special commands
        if args.init_config:
            init_config_command(args)
            return
        
        # Validate arguments
        validate_arguments(args)
        
        # Load configuration
        config = load_configuration(args)
        
        # Add parse-only flag to config
        config.parse_only = getattr(args, 'parse_only', False)
        
        # Set up logging level based on config
        if config.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        elif config.verbose:
            logging.getLogger().setLevel(logging.INFO)
        elif config.quiet:
            logging.getLogger().setLevel(logging.ERROR)
        
        # Save configuration if requested
        if args.save_config:
            save_config(config, args.save_config)
            if not config.quiet:
                print(f"✓ Configuration saved to: {args.save_config}")
        
        # Execute main command
        asyncio.run(parse_and_generate_command(args, config))
        
    except CLIError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print_error(f"An unexpected error occurred: {e}")
        sys.exit(1)



if __name__ == "__main__":
    main()
