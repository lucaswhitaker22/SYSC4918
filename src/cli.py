import argparse
import os
import sys
import json
import logging

from typing import Optional

# Import your existing modules
from src import code_extractor        # Code extraction and prioritization
from src import prompt_engineering    # Build structured LLM prompts
from src import llm_integration       # Gemini LLM API integration
from src import readme_template       # (Optional) final README templating helpers
from src import utils                 # Utilities like token counting, file IO

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)


def load_json(file_path: str) -> Optional[dict]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON from {file_path}: {e}")
        return None


def save_text(text: str, path: str):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        logging.info(f"Saved output to {path}")
    except Exception as e:
        logging.error(f"Failed to write output file {path}: {e}")


def generate_readme_from_json(extracted_data: list, project_name: Optional[str] = None) -> str:
    """
    Uses prompt_engineering and llm_integration to generate README markdown from
    extracted JSON data via Gemini 2.5 API.
    """
    # Step 1: Build prompt string from extracted JSON
    prompt = prompt_engineering.build_readme_prompt(extracted_data, project_name=project_name)

    # Step 2: Call Gemini API to generate README content
    readme_md = llm_integration.generate_readme_with_gemini(
        extracted_json=extracted_data,
        project_name=project_name,
        # Using default model and temperature, can be customized if desired
    )

    if readme_md is None:
        logging.error("Failed to generate README from LLM.")
        # Fallback to a placeholder readme
        readme_md = (
            "# README Generation Failed\n\n"
            "The README generation failed due to an error in LLM API call."
        )

    return readme_md


def main():
    parser = argparse.ArgumentParser(
        description='Generate a README.md from a Python project using code extraction and Gemini LLM.'
    )

    parser.add_argument(
        'project_dir',
        type=str,
        help='Path to the root directory of the Python project to analyze'
    )

    parser.add_argument(
        '--json_output',
        type=str,
        default='extracted_code.json',
        help='Path to save the extracted code JSON output (default: extracted_code.json)'
    )

    parser.add_argument(
        '--readme_output',
        type=str,
        default='README.md',
        help='Path to save the generated README markdown file (default: README.md)'
    )

    parser.add_argument(
        '--max_tokens',
        type=int,
        default=500000,
        help='Maximum token budget for code extraction prioritization (default: 500000)'
    )

    parser.add_argument(
        '--project_name',
        type=str,
        default=None,
        help='Optional project name to include in README generation context'
    )

    args = parser.parse_args()

    project_dir = args.project_dir
    json_path = args.json_output
    readme_path = args.readme_output
    max_tokens = args.max_tokens
    project_name = args.project_name

    if not os.path.isdir(project_dir):
        logging.error(f"The specified project directory does not exist or is not a directory: {project_dir}")
        sys.exit(1)

    logging.info(f"Starting code extraction for project: {project_dir}")

    # Step 1: Extract and prioritize code with token budget
    extracted_data = code_extractor.traverse_and_extract(project_dir)
    logging.info(f"Extraction complete, found {len(extracted_data)} Python files")

    prioritized_data = code_extractor.prioritize_and_limit(extracted_data, max_tokens=max_tokens)
    logging.info(f"Selected {len(prioritized_data)} files after prioritization")

    # Save the extracted JSON data for inspection/debugging
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(prioritized_data, f, indent=2, ensure_ascii=False)
        logging.info(f"Extracted code JSON saved to {json_path}")
    except Exception as e:
        logging.error(f"Failed to save JSON output: {e}")
        sys.exit(1)

    # Step 2: Generate README using the JSON data and Gemini LLM API
    logging.info("Generating README from extracted data via LLM...")
    readme_content = generate_readme_from_json(prioritized_data, project_name=project_name)

    # Optional: Use readme_template to post-process or reformat (if desired)
    # For instance, if you want to wrap or validate the Markdown further:
    # readme_content = readme_template.some_postprocessing_function(readme_content)

    # Save the generated README
    save_text(readme_content, readme_path)
    logging.info("README generation process completed.")


if __name__ == '__main__':
    main()
