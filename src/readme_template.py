from typing import List, Dict, Any, Optional


README_SECTIONS = [
    "Project Name",
    "Description",
    "Table of Contents",
    "Installation",
    "Usage",
    "API Reference",
    "Contributing",
    "License",
]


def generate_table_of_contents(sections: List[str]) -> str:
    """
    Create a Markdown Table of Contents from section headers.

    Args:
        sections (List[str]): List of section headers.

    Returns:
        str: Markdown-formatted TOC with links.
    """
    toc_lines = []
    for section in sections:
        # Anchor format: all lowercase, spaces -> '-', remove special chars
        anchor = section.lower().replace(' ', '-')
        toc_lines.append(f"- [{section}](#{anchor})")
    return "\n".join(toc_lines)


def map_extracted_data_to_readme(extracted_data: List[Dict[str, Any]], project_name: Optional[str] = None,
                                license_text: Optional[str] = None,
                                contributing_text: Optional[str] = None) -> str:
    """
    Convert extracted codebase data into README markdown sections.

    Args:
        extracted_data (List[Dict[str, Any]]): List of extracted files' metadata and docstrings.
        project_name (Optional[str]): Project name override; if None, inferred from directory or code.
        license_text (Optional[str]): License text to include.
        contributing_text (Optional[str]): Contributing guidelines text.

    Returns:
        str: Generated README in Markdown.
    """
    # Helper to find best module-level docstring for Description
    description = None
    for file_data in extracted_data:
        if file_data.get('module_docstring'):
            description = file_data['module_docstring']
            break
    if not description:
        description = "Project description goes here."

    # Installation and Usage can be generic placeholder or extended to parse setup files
    installation = (
        
        "pip install -r requirements.txt\n"
    )
    usage = (
        "Provide usage instructions and example code here.\n"
        "For example:\n"
        "import your_package\n"
        "your_package.main()\n"
        "```\n"
    )

    # API Reference: Generate markdown entries for classes and functions
    api_reference_lines = []
    for file_data in extracted_data:
        file_path = file_data.get('file_path', 'Unknown file')
        api_reference_lines.append(f"### `{file_path}`\n")

        # Classes
        for class_info in file_data.get('classes', []):
            class_name = class_info.get('name', 'UnnamedClass')
            class_doc = class_info.get('docstring', '').strip() or "No class docstring available."
            api_reference_lines.append(f"#### Class `{class_name}`\n")
            api_reference_lines.append(class_doc + "\n")

            # Methods
            for method in class_info.get('methods', []):
                method_name = method.get('name', 'unnamed_method')
                method_doc = method.get('docstring', '').strip() or "No method docstring available."
                api_reference_lines.append(f"- **Method** `{method_name}`:\n\n    {method_doc}\n")

        # Functions
        for func in file_data.get('functions', []):
            func_name = func.get('name', 'unnamed_function')
            func_doc = func.get('docstring', '').strip() or "No function docstring available."
            api_reference_lines.append(f"- **Function** `{func_name}`:\n\n    {func_doc}\n")

        api_reference_lines.append("")  # Blank line for spacing

    api_reference = "\n".join(api_reference_lines) if api_reference_lines else "No API documentation available."

    # Default contributing section if none provided
    if not contributing_text:
        contributing_text = (
            "Contributions are welcome! Please open issues or pull requests on GitHub.\n"
        )

    # Default license section if none provided
    if not license_text:
        license_text = (
            "This project is licensed under the MIT License - see the LICENSE file for details.\n"
        )

    # Compose README
    readme_lines = [
        f"# {project_name or 'Project Title'}\n",
        "## Description\n",
        f"{description}\n",
        "## Table of Contents\n",
        generate_table_of_contents(README_SECTIONS),
        "\n## Installation\n",
        installation,
        "\n## Usage\n",
        usage,
        "\n## API Reference\n",
        api_reference,
        "\n## Contributing\n",
        contributing_text,
        "\n## License\n",
        license_text,
    ]

    return "\n".join(readme_lines)
