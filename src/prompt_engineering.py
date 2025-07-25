import json
from typing import List, Dict, Any, Optional


def truncate_text(text: str, max_length: int = 3000) -> str:
    """
    Safely truncate text to a max character length for prompt inclusion.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + " ... [truncated]"


def build_readme_prompt(
    extracted_data: List[Dict[str, Any]],
    project_name: Optional[str] = None,
    max_json_chars: int = 100000
) -> str:
    """
    Convert extracted codebase data into a prompt string for LLM README generation.

    Args:
        extracted_data: List of dicts containing extracted code info (module docstrings, classes, functions).
        project_name: Optional project name to provide as context.
        max_json_chars: Maximum characters of JSON data to embed in prompt to prevent token overflow.

    Returns:
        A formatted prompt string ready for submission to the LLM.
    """

    # Compose a simplified context dictionary to avoid overly large payloads
    simplified_data = []

    for file_data in extracted_data:
        entry = {
            "file_path": file_data.get("file_path", ""),
            "module_docstring": truncate_text(file_data.get("module_docstring", "")),
            "classes": [],
            "functions": [],
        }

        for cls in file_data.get("classes", []):
            cls_entry = {
                "name": cls.get("name", ""),
                "docstring": truncate_text(cls.get("docstring", "")),
                "methods": [],
            }
            for method in cls.get("methods", []):
                cls_entry["methods"].append({
                    "name": method.get("name", ""),
                    "docstring": truncate_text(method.get("docstring", "")),
                })
            entry["classes"].append(cls_entry)

        for func in file_data.get("functions", []):
            entry["functions"].append({
                "name": func.get("name", ""),
                "docstring": truncate_text(func.get("docstring", "")),
            })

        simplified_data.append(entry)

    # Convert simplified data to JSON string
    json_data_str = json.dumps(simplified_data, indent=2, ensure_ascii=False)
    
    # Truncate JSON if too long
    if len(json_data_str) > max_json_chars:
        json_data_str = json_data_str[:max_json_chars] + "\n... [truncated]\n"

    # Build prompt with clear task instructions
    prompt = f"""
            You are a Python documentation assistant tasked with generating a professional, detailed README.md file in Markdown format for a Python project.

            The following JSON contains extracted project metadata:
            - Module-level docstrings (brief project/module descriptions)
            - Class names with their docstrings and methods
            - Function names with their docstrings

            Use this information to compose a well-structured README that includes these sections:

            1. Project Name: {project_name or '[Unknown Project]'}
            2. Short Project Description (from module-level docstrings)
            3. Table of Contents
            4. Installation instructions (assume dependencies can be installed via 'pip install -r requirements.txt')
            5. Usage examples (summarize from main functions or classes if possible)
            6. API Reference:
            - List each module, class, function, method with their docstrings.
            - Include example usage or code snippets if provided.
            7. Contributing guidelines (you can provide a stock message)
            8. License (you may add a placeholder if not provided)

            Format your output strictly as Markdown with appropriate headings (#, ##, ###) and code snippets fenced with triple backticks.

            JSON extracted data (truncated if necessary):
            {json_data_str}

            text

            Please generate a complete, clear, and concise README markdown text now.
            """

    return prompt.strip()