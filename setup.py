# setup.py

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Enhanced dependencies for LLM integration
install_requires = [
    # Core LLM integration dependencies
    "tiktoken>=0.5.0",              # Token counting for LLM context management
    "openai>=1.0.0",                # OpenAI API integration
    "google-generativeai>=0.3.0",   # Gemini API integration
    "anthropic>=0.7.0",             # Claude API integration
    
    # Template and output formatting
    "jinja2>=3.0.0",                # Template engine for README generation
    "click>=8.0.0",                 # Better CLI framework
    "rich>=13.0.0",                 # Enhanced CLI output and progress bars
    
    # Data handling and validation
    "pydantic>=2.0.0",              # Data validation and settings management
    "tomli>=2.0.0",                 # TOML parsing for older Python versions
    
    # Additional utilities
    "requests>=2.28.0",             # HTTP requests for API calls
    "python-dotenv>=0.19.0",        # Environment variable management
    "pathspec>=0.10.0",             # Git-style path matching
]

setup(
    name="readme-generator",
    version="1.0.0",
    author="README Generator Team",
    author_email="contact@readme-generator.com",
    description="AI-powered README generator for Python projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/readme-generator/readme-generator",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing :: Markup",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "readme-gen=main:main",
            "readme-generator=main:main",
        ],
    },
    keywords="readme generator ai llm documentation python",
    project_urls={
        "Bug Reports": "https://github.com/readme-generator/readme-generator/issues",
        "Source": "https://github.com/readme-generator/readme-generator",
        "Documentation": "https://readme-generator.readthedocs.io/",
    },
)
