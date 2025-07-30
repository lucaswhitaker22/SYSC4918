#!/usr/bin/env python3
"""
Setup configuration for sample-project.

This file provides backward compatibility for systems that don't support
PEP 517/518 build systems. Modern installations should prefer pyproject.toml.
"""

from setuptools import setup, find_packages
from pathlib import Path
import re

# Read version from package
def get_version():
    """Extract version from package __init__.py"""
    init_file = Path(__file__).parent / "sample_project" / "__init__.py"
    if init_file.exists():
        with open(init_file, encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'^__version__ = ["\']([^"\']+)["\']', content, re.M)
            if match:
                return match.group(1)
    return "1.2.3"  # fallback version

# Read long description from README
def get_long_description():
    """Read long description from README file"""
    readme_file = Path(__file__).parent / "README.md"
    if readme_file.exists():
        with open(readme_file, encoding='utf-8') as f:
            return f.read()
    return "A comprehensive sample Python project for testing README generation"

# Read requirements from files
def get_requirements(filename):
    """Read requirements from requirements file"""
    req_file = Path(__file__).parent / filename
    if req_file.exists():
        with open(req_file, encoding='utf-8') as f:
            return [
                line.strip() 
                for line in f 
                if line.strip() and not line.startswith('#')
            ]
    return []

setup(
    # Basic package information
    name="sample-project",
    version=get_version(),
    description="A comprehensive sample Python project for testing README generation",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    
    # Author information
    author="John Developer",
    author_email="john.dev@example.com",
    maintainer="John Developer",
    maintainer_email="john.dev@example.com",
    
    # URLs
    url="https://github.com/example/sample-project",
    project_urls={
        "Documentation": "https://sample-project.readthedocs.io/",
        "Source Code": "https://github.com/example/sample-project",
        "Bug Reports": "https://github.com/example/sample-project/issues",
        "Funding": "https://github.com/sponsors/example",
        "Changelog": "https://github.com/example/sample-project/blob/main/CHANGELOG.md",
    },
    
    # Package discovery
    packages=find_packages(exclude=["tests*", "docs*", "scripts*"]),
    package_dir={"": "."},
    
    # Package data
    package_data={
        "sample_project": [
            "data/*.json",
            "templates/*.txt", 
            "config/*.yaml",
            "static/*.css",
            "static/*.js"
        ],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=[
        "requests>=2.25.0",
        "click>=8.0.0", 
        "pydantic>=1.8.0,<3.0.0",
        "rich>=10.0.0",
        "typer>=0.4.0",
        "pyyaml>=6.0",
        "configparser>=5.0.0"
    ],
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0"
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0", 
            "pytest-mock>=3.10.0",
            "coverage>=6.0.0"
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0"
        ],
        "async": [
            "aiohttp>=3.8.0",
            "asyncio-mqtt>=0.11.0"
        ],
        "all": [
            # Combines all optional dependencies
            "pytest>=7.0.0", "pytest-cov>=4.0.0", "pytest-mock>=3.10.0",
            "black>=22.0.0", "flake8>=4.0.0", "mypy>=1.0.0", "pre-commit>=2.20.0",
            "coverage>=6.0.0", "sphinx>=4.0.0", "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0", "aiohttp>=3.8.0", "asyncio-mqtt>=0.11.0"
        ]
    },
    
    # Entry points
    entry_points={
        "console_scripts": [
            "sample-cli=sample_project.cli:main",
            "sample-tool=sample_project.main:run_tool",
            "sample-project=sample_project.cli:main",
        ],
        "sample_project.plugins": [
            "default=sample_project.plugins:DefaultPlugin",
            "advanced=sample_project.plugins:AdvancedPlugin",
        ],
    },
    
    # Metadata
    keywords=["sample", "example", "demo", "cli", "utility"],
    license="MIT",
    
    # Classifiers
    classifiers=[
        # Development Status
        "Development Status :: 4 - Beta",
        
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Operating Systems
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        
        # Programming Languages
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        
        # Topics
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Tools",
        "Topic :: Utilities",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        
        # Natural Language
        "Natural Language :: English",
        
        # Environment
        "Environment :: Console",
        "Environment :: Web Environment",
    ],
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Additional options
    zip_safe=False,
    platforms=["any"],
    
    # Test suite
    test_suite="tests",
    tests_require=get_requirements("requirements-test.txt"),
    
    # Command class customizations (if needed)
    # cmdclass={
    #     'test': CustomTestCommand,
    #     'build_ext': CustomBuildExtCommand,
    # },
)
