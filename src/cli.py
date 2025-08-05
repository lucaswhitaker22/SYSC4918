"""
Command-line interface for the README generator.

This module provides the main CLI functionality for automatically generating
comprehensive README files for Python projects using LLM APIs,
optimized for Gemini 2.5 Pro with a 1M token window.
"""

import os
import sys
import argparse
import time
import json
import asyncio
from pathlib import Path
import logging

# Optional: Third-party LLM APIs
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
from utils.token_counter import estimate_tokens
from utils.file_utils import create_directory
from utils.json_serializer import serialize_project_data, save_json_to_file

logger = logging.getLogger(__name__)

class CLIError(Exception):
    pass

class LLMAPIError(Exception):
    pass

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readme-generator",
        description="Generate a README for a Python project using LLMs.",
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
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--parse-only', action='store_true', help='Only parse project data to JSON, skip README generation')
    parser.add_argument('project_path', nargs='?', help='Path to the Python project root directory')
    parser.add_argument('--output', '-o', type=str, default='README.md', help='Output README file path')
    parser.add_argument('--json-output', type=str, help='Save parsed project data as JSON file')
    parser.add_argument('--model', choices=['gemini_2_5_pro', 'gemini_2_5_flash', 'gpt_4o', 'gpt_4o_mini', 'claude_sonnet'], default='gemini_2_5_pro', help='LLM model to use')
    parser.add_argument('--api-key', type=str, help='API key for LLM service')
    parser.add_argument('--max-tokens', type=int, default=1000000, help='Maximum token budget')
    parser.add_argument('--include-tests', action='store_true', help='Include test files in analysis')
    parser.add_argument('--include-private', action='store_true', help='Include private methods and classes')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--init-config', action='store_true', help='Initialize configuration file with default settings')
    parser.add_argument('--save-config', type=str, help='Save current settings to configuration file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress non-error output')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with detailed logging')
    parser.add_argument('--timeout', type=int, default=90, help='Timeout in seconds')
    return parser

def validate_arguments(args: argparse.Namespace) -> None:
    if args.init_config:
        return
    if not args.project_path:
        raise CLIError("Project path is required. Use --help for usage information.")
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        raise CLIError(f"Project path does not exist: {args.project_path}")
    if not project_path.is_dir():
        raise CLIError(f"Project path is not a directory: {args.project_path}")
    python_indicators = ['setup.py', 'pyproject.toml', 'requirements.txt', '__init__.py']
    has_python_files = any((project_path / indicator).exists() for indicator in python_indicators)
    has_py_files = any(project_path.glob('**/*.py'))
    if not has_python_files and not has_py_files:
        logger.warning(f"No Python project indicators found in {project_path}")
    if args.max_tokens < 1000:
        raise CLIError("Maximum tokens must be at least 1000")
    if args.timeout < 1:
        raise CLIError("Timeout must be at least 1 second")
    if args.timeout > 300:
        logger.warning(f"Timeout of {args.timeout}s exceeds recommended 90s performance target")

def validate_api_requirements(model_name: str, api_key: str) -> str:
    env_key_mapping = {
        'gemini_2_5_pro': 'AIzaSyCaB-JT3ear0wPh32huI1XjRAoosJAzAZw',
        'gemini_2_5_flash': 'AIzaSyCaB-JT3ear0wPh32huI1XjRAoosJAzAZw', 
        'gpt_4o': 'OPENAI_API_KEY',
        'gpt_4o_mini': 'OPENAI_API_KEY',
        'claude_sonnet': 'ANTHROPIC_API_KEY'
    }
    if not api_key:
        env_var = env_key_mapping.get(model_name)
        if env_var:
            api_key = os.getenv(env_var)
    if not api_key:
        env_var = env_key_mapping.get(model_name, 'API_KEY')
        raise CLIError(
            f"API key required for {model_name}. Provide via --api-key or {env_var}."
        )
    if model_name.startswith('gemini') and not genai:
        raise CLIError("google-generativeai package required for Gemini models.")
    elif model_name.startswith('gpt') and not openai:
        raise CLIError("openai package required for OpenAI models.")
    elif model_name.startswith('claude') and not anthropic:
        raise CLIError("anthropic package required for Claude models.")
    return api_key

def load_configuration(args: argparse.Namespace) -> Config:
    config = Config()
    if args.config:
        try:
            loaded_config = load_config(args.config)
            config.update(loaded_config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")
    config.model_name = args.model
    config.max_tokens = args.max_tokens
    config.include_tests = args.include_tests
    config.include_private = args.include_private
    config.verbose = args.verbose
    config.quiet = args.quiet
    config.debug = args.debug
    config.timeout = args.timeout
    # Fixed: Removed broken cache reference since --no-cache doesn't exist
    config.cache_enabled = True  # Default to enabled
    if args.api_key:
        config.api_key = args.api_key
    return config

async def generate_readme_with_llm(project_data: dict, config: Config, api_key: str) -> str:
    # MVP: project_data is a dict from the MVP parser
    serialized_data = serialize_project_data(project_data)
    token_count = estimate_tokens(json.dumps(serialized_data))
    logger.info(f"Sending ~{token_count:,} tokens to {config.model_name}")
    if token_count > config.max_tokens:
        logger.warning(f"Token count ({token_count:,}) exceeds limit ({config.max_tokens:,})")
    prompt = create_readme_prompt(serialized_data, serialized_data.get('project_metadata', {}).get('name', 'Project'))
    if config.model_name.startswith('gemini'):
        return await generate_with_gemini(prompt, api_key)
    elif config.model_name.startswith('gpt'):
        return await generate_with_openai(prompt, api_key)
    elif config.model_name.startswith('claude'):
        return await generate_with_claude(prompt, api_key)
    else:
        raise LLMAPIError(f"Unsupported model: {config.model_name}")

def create_readme_prompt(project_data: dict, project_name: str) -> str:
    return f"""
You are an expert technical writer for open-source Python projects. 
Write a professional, accurate, and comprehensive README.md for the project "{project_name}", based **solely** on this parsed project data:
{json.dumps(project_data, indent=2)}

Requirements:
1. The README must have these sections, in order:
   - Project Title and Badges (CI, version, license, etc. if present in metadata)
   - Overview (1-2 sentence summary of project purpose and key features)
   - Detailed Description (expand on what the project does and its unique value)
   - Installation Instructions (with real commands for pip/conda, list all dependencies)
   - Usage (clear code examples with realistic usage patterns and expected output)
   - Project Structure (directory/files tree as Markdown, based on the parsed files)
   - API Reference (for all public classes/functions, including parameters and return values)
   - Running Tests (if test files detected, show exact test commands)
   - Contributing Guidelines (if supporting contributions)
   - License (pull text or identifier from metadata if available)
2. Use Markdown best practices: fenced code blocks, tables for API/commands, real file/dir trees, and badge syntax.
3. Avoid placeholder text. If information is missing, omit the section rather than guessing.
4. All content **must** match the actual project metadata and structure given above.
Output ONLY the Markdown for a README file.
"""


async def generate_with_gemini(prompt: str, api_key: str) -> str:
    if not genai:
        raise LLMAPIError("google-generativeai package not available")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        logger.info(f"Generating README with Gemini 2.5 Pro")
        response = await model.generate_content_async(prompt)
        if not response.text:
            raise LLMAPIError("No content from Gemini API")
        return response.text
    except Exception as e:
        raise LLMAPIError(str(e))

async def generate_with_openai(prompt: str, api_key: str) -> str:
    if not openai:
        raise LLMAPIError("openai package not available")
    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model='gpt-4o',
            messages=[{"role": "system", "content": "You are an expert technical writer."},{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096
        )
        if not response.choices or not response.choices[0].message.content:
            raise LLMAPIError("No content from OpenAI API")
        return response.choices[0].message.content
    except Exception as e:
        raise LLMAPIError(str(e))

async def generate_with_claude(prompt: str, api_key: str) -> str:
    if not anthropic:
        raise LLMAPIError("anthropic package not available")
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        if not response.content or not response.content[0].text:
            raise LLMAPIError("No content from Claude API")
        return response.content[0].text
    except Exception as e:
        raise LLMAPIError(str(e))

def init_config_command(args: argparse.Namespace) -> None:
    config_path = "readme_generator_config.json"
    try:
        config = Config()
        config.model_name = "gemini_2_5_pro"
        config.max_tokens = 1_000_000
        config.timeout = 90
        save_config(config, config_path)
        print(f"✓ Configuration file created: {config_path}")
        print("Edit it to customize settings.")
    except Exception as e:
        raise CLIError(f"Failed to create configuration file: {e}")

async def parse_and_generate_command(args: argparse.Namespace, config: Config) -> None:
    start_time = time.time()
    try:
        project_path = Path(args.project_path).resolve()
        logger.info(f"Parsing project: {project_path}")
        parsing_start = time.time()
        
        # FIXED: Now properly passing include_tests and include_private arguments
        result = parse_project(
            str(project_path),
            include_tests=config.include_tests,
            include_private=config.include_private
        )
        parsing_time = time.time() - parsing_start

        if not config.quiet:
            print(f"✓ Project parsed in {parsing_time:.2f}s")
            # Show stats if available
            if 'stats' in result:
                stats = result['stats']
                print(f"  Files processed: {stats.get('files_processed', 0)}")
                print(f"  Examples found: {stats.get('examples_found', 0)}")

        # Save JSON output
        json_output_path = args.json_output or f"{project_path.name}_parsed_data.json"
        serialized_data = serialize_project_data(result)
        success = save_json_to_file(serialized_data, json_output_path)
        if success and not config.quiet:
            print(f"✓ JSON data saved to: {json_output_path}")

        if args.parse_only:
            if not config.quiet:
                print(f"✓ Parse-only mode completed in {time.time() - start_time:.2f}s")
            return

        api_key = validate_api_requirements(config.model_name, config.api_key)
        if not config.quiet:
            print(f"Generating README with {config.model_name}...")

        generation_start = time.time()
        readme_content = await generate_readme_with_llm(result, config, api_key)
        generation_time = time.time() - generation_start

        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = project_path / output_path
        create_directory(str(output_path.parent))
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        if not config.quiet:
            print(f"✓ README generated in {generation_time:.2f}s")
            print(f"✓ README saved to: {output_path}")

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Command failed after {elapsed_time:.2f}s: {e}")
        raise

def main():
    try:
        parser = create_parser()
        args = parser.parse_args()
        if args.init_config:
            init_config_command(args)
            return
        validate_arguments(args)
        config = load_configuration(args)
        config.parse_only = getattr(args, 'parse_only', False)
        if config.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        elif config.verbose:
            logging.getLogger().setLevel(logging.INFO)
        elif config.quiet:
            logging.getLogger().setLevel(logging.ERROR)
        if args.save_config:
            save_config(config, args.save_config)
            if not config.quiet:
                print(f"✓ Configuration saved to: {args.save_config}")
        asyncio.run(parse_and_generate_command(args, config))
    except CLIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
