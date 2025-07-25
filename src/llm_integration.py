import os
import logging
import json
from typing import Any, Dict, Optional

try:
    from google import genai
except ImportError as e:
    raise ImportError(
        "google-genai is not installed. Use 'pip install google-genai' to install it."
    )

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# LLM Model name, may use "gemini-2.5-pro" or "gemini-2.5-flash"
GEMINI_MODEL = "gemini-2.5-pro"  # Consider "gemini-2.5-flash" for cheaper/faster requests

def load_api_key() -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable is not set.")
        return None
    return api_key

def generate_readme_with_gemini(
    extracted_json: Dict[str, Any],
    project_name: Optional[str] = None,
    model: str = GEMINI_MODEL,
    temperature: float = 0.2,
    max_output_tokens: int = 4096
) -> Optional[str]:
    """
    Sends extracted codebase data to Gemini 2.5 model to generate a Markdown README.

    Args:
        extracted_json: Python dict of prioritized extracted code data (from your extractor).
        project_name: Optional project name to supply context.
        model: Model to use.
        temperature: LLM randomness (0–1).
        max_output_tokens: LLM response size cap.

    Returns:
        README as Markdown string, or None on error.
    """

    # Set up the Gemini AI client (API key loaded from env)
    try:
        client = genai.Client()
    except Exception as e:
        logging.error(f"Failed to initialize Gemini AI client: {e}")
        return None

    # Compose prompt
    prompt = (
        f"You are an expert Python software documentation writer.\n"
        f"Generate a well-structured, professional `README.md` in Markdown format for this Python project."
        f"\n"
        f"Contextual extracted information is provided as JSON below. "
        f"Organize the README into sections like: Project Name, Description, Table of Contents, Installation, Usage, API Reference, Contributing, and License."
        f"\n"
        f"Summarize and format the codebase details accordingly. "
        f"Include API details for key classes/functions, using code snippets when available. "
        f"Be concise, but ensure coverage of the code's structure and purpose. "
        f"\n"
        f"Project Name: {project_name or extracted_json.get('project_name','')}\n\n"
        f"Extracted Data (JSON):\n{json.dumps(extracted_json)[:100000]}\n"
    )

    try:
        # Make the Gemini API call
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
            # Optionally enforce Markdown output
            config={
                "response_mime_type": "text/markdown"
            }
        )
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return None

    # Gemini returns Markdown as .text
    readme_md = getattr(response, 'text', None)
    if not readme_md:
        logging.error("No README content returned from Gemini.")
        return None

    return readme_md

# Example usage (for manual test/CLI debug)
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("Gemini README Generator")
    parser.add_argument(
        "json_input", type=str, help="Path to prioritized extracted code JSON file."
    )
    parser.add_argument(
        "--output", type=str, default="README_generated.md", help="Where to save generated README."
    )
    parser.add_argument("--project_name", type=str, default=None, help="Optional project name.")
    parser.add_argument("--model", type=str, default=GEMINI_MODEL, help="Gemini model to use.")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM creativity.")
    parser.add_argument("--max_output_tokens", type=int, default=4096, help="Max output tokens.")

    args = parser.parse_args()
    api_key = load_api_key()
    if not api_key:
        exit(1)

    try:
        with open(args.json_input, "r", encoding="utf-8") as f:
            extracted_data = json.load(f)
    except Exception as e:
        logging.error(f"Could not load file {args.json_input}: {e}")
        exit(1)

    readme_md = generate_readme_with_gemini(
        extracted_json=extracted_data,
        project_name=args.project_name,
        model=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
    )
    if not readme_md:
        logging.error("Failed to generate README with Gemini.")
        exit(1)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(readme_md)
        logging.info(f"Generated README written to {args.output}")
    except Exception as e:
        logging.error(f"Could not write README: {e}")
        exit(1)
