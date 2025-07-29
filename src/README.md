# README Generator


![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)


![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)


![License](https://img.shields.io/badge/license-MIT-green.svg)


This package provides a command-line tool that automatically generates comprehensive README files for Python projects using Large Language Model APIs. It intelligently parses and extracts key information from codebases to create high-quality documentation within LLM context window constraints.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Initialize Configuration](#1-initialize-configuration)
  - [Generate a README](#2-generate-a-readme)
  - [Using Different LLM Providers](#3-using-different-llm-providers)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Core API Documentation](#core-api-documentation)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)

---

## Features

-   **Comprehensive Project Analysis**: Intelligently parses Python source code, configuration files, and project structure to gather a holistic view of the project.
-   **Token-Aware Content Optimization**: Automatically prioritizes and compresses project information to fit within the context window of the target LLM, ensuring the most critical details are included.
-   **Multi-Provider LLM Support**: Seamlessly integrates with major LLM providers, including Google (Gemini), OpenAI (GPT), and Anthropic (Claude).
-   **Intelligent Content Prioritization**: Uses a scoring system to determine the importance of different code elements (classes, functions, etc.), ensuring that the final documentation highlights the most relevant parts of your API.
-   **Robust Error Handling**: Designed with graceful degradation to handle parsing errors in complex or unconventional projects.
-   **Command-Line Interface**: A simple and powerful CLI for easy integration into your development workflow.

---

## Installation

To get started with the README Generator, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://your-repository-url/readme-generator.git
    cd readme-generator
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required dependencies:**
    The project's dependencies are listed below. You can install them using pip.
    ```bash
    pip install google-generativeai openai anthropic GitPython chardet jsonschema
    ```

4.  **Install the project in editable mode:**
    This will install the command-line tool `readme-generator`.
    ```bash
    pip install -e .
    ```

---

## Usage

The primary way to use this tool is through its command-line interface.

### 1. Initialize Configuration

Before generating a README, you can create a default configuration file in your project's root directory. This file (`.readme-generator.json`) allows you to customize the generation process.

```bash
readme-generator init
```
This will create a configuration file with sensible defaults. You can edit this file to fine-tune the behavior.

### 2. Generate a README

To generate a README for a project, use the `generate` command.

```bash
readme-generator generate --path /path/to/your/project --output README.md
```

**Arguments:**

-   `--path`: The root directory of the Python project you want to document. Defaults to the current directory (`.`).
-   `--output`: The name of the output file. Defaults to `README.md`.
-   `--model`: The LLM model to use for generation (e.g., `gemini-1.5-pro`, `gpt-4o`, `claude-3-sonnet`).
-   `--api-key`: Your API key for the chosen provider. It's recommended to use environment variables instead.

### 3. Using Different LLM Providers

You can easily switch between supported LLM providers.

**Set API Keys using Environment Variables (Recommended):**

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

**Example with Gemini (Default):**
```bash
readme-generator generate --path . --model gemini-1.5-pro
```

**Example with OpenAI:**
```bash
readme-generator generate --path . --model gpt-4o
```

**Example with Claude:**
```bash
readme-generator generate --path . --model claude-3-sonnet-20240229
```

---

## Configuration

The tool can be configured via a `.readme-generator.json` file in your project's root. You can generate a default one using `readme-generator init`.

**Key Configuration Options:**

-   `model_name`: (string) The default LLM to use (e.g., `"gemini-1.5-pro"`).
-   `max_tokens`: (integer) The maximum token context window for the model.
-   `api_key`: (string) Your API key. Best left `null` in favor of environment variables.
-   `include_tests`: (boolean) Whether to include information from test files in the analysis.
-   `include_private`: (boolean) Whether to include private methods and functions (those starting with `_`).
-   `output_file`: (string) The default name for the generated README file.

---

## Project Structure

The project is organized into several key packages, each with a specific responsibility.

```
src/
├── __init__.py             # Main package entry point
├── __main__.py             # Allows running the package as a script
├── cli.py                  # Defines the command-line interface
├── config.py               # Handles configuration management
├── models/                 # Data classes and schemas for project information
│   ├── __init__.py
│   ├── project_data.py
│   └── schemas.py
├── parser/                 # Modules for parsing different aspects of a project
│   ├── __init__.py
│   ├── code_parser.py
│   ├── dependency_parser.py
│   ├── example_parser.py
│   ├── metadata_parser.py
│   ├── project_parser.py
│   └── structure_parser.py
└── utils/                  # Utility modules for common tasks
    ├── __init__.py
    ├── content_prioritizer.py
    ├── file_utils.py
    ├── json_serializer.py
    └── token_counter.py
```

-   **`cli.py`**: Contains all logic for the command-line interface, including argument parsing and command execution.
-   **`config.py`**: Manages loading, saving, and validating configuration settings.
-   **`models/`**: Defines the data structures (`dataclasses`) that hold all the parsed information about a project. `schemas.py` provides JSON schemas for validation.
-   **`parser/`**: The core analysis engine. Each parser is specialized in extracting specific information (e.g., `dependency_parser.py` handles `requirements.txt` and `pyproject.toml`). `project_parser.py` orchestrates all other parsers.
-   **`utils/`**: A collection of helper modules for tasks like counting tokens (`token_counter.py`), prioritizing content for the LLM (`content_prioritizer.py`), and handling file I/O (`file_utils.py`).

---

## Core API Documentation

While this project is primarily a CLI tool, its components are modular and can be used programmatically. Here are some of the core classes:

### `parser.project_parser.ProjectParser`
The main orchestrator for parsing a Python project. It coordinates all sub-parsers to build a complete `ProjectData` object.

-   **`__init__(self, ...)`**: Initializes the parser with configuration options like `model_name`, `max_tokens`, etc.
-   **`parse_project(self, project_path: str) -> ParseResult`**: The main method. It takes the path to a project and returns a `ParseResult` object containing the structured `ProjectData` and parsing metadata.

### `cli.generate_readme_with_llm`
An asynchronous function that handles the interaction with the selected LLM API.

-   **Signature**: `async def generate_readme_with_llm(project_data: Any, config: Config, api_key: str) -> str`
-   **Description**: Takes the parsed project data and configuration, creates a detailed prompt, sends it to the specified LLM (Gemini, OpenAI, or Claude), and returns the generated Markdown content.

### `utils.token_counter.TokenCounter`
A utility class for estimating and counting tokens to ensure the generated prompt fits within the LLM's context window.

-   **`__init__(self, model_name: str)`**: Initializes the counter for a specific model.
-   **`count_tokens(self, text: str, content_type: ContentType) -> int`**: Counts the tokens in a given string, using content-type-aware heuristics for better accuracy.

### `utils.content_prioritizer.ContentPrioritizer`
A system for scoring and ranking different pieces of project information based on their importance. This is crucial for deciding what to include when the total project information exceeds the token budget.

-   **`calculate_priority_scores(self, project_data: ProjectData) -> List[PriorityScore]`**: Analyzes the entire `ProjectData` object and assigns a priority score to each component (module, class, function).
-   **`filter_by_budget(self, priority_scores: List[PriorityScore], budget: TokenBudget) -> List[PriorityScore]`**: Selects the highest-priority items that fit within the defined token budget.

---

## Dependencies

This project relies on the following libraries, which were inferred from its source code.

### Production Dependencies
-   `google-generativeai`: For interacting with the Google Gemini API.
-   `openai`: For interacting with the OpenAI GPT API.
-   `anthropic`: For interacting with the Anthropic Claude API.
-   `GitPython`: For extracting repository information from `.git` history.
-   `chardet`: For robust file encoding detection.
-   `jsonschema`: For validating JSON data structures.
-   `tomllib`: For parsing `pyproject.toml` files (Note: standard library in Python 3.11+).

### Development Dependencies
-   `pytest`: For running the test suite.
-   `black`: For code formatting.
-   `flake8`: For linting and style checking.

---

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and use a feature branch. Pull requests are warmly welcome.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add some amazing-feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.