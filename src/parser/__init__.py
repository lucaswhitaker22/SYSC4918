"""
Parser module for the README generator project.

This module contains the main orchestrator and all sub-parsers responsible
for extracting information from Python projects for README generation.
"""

from .project_parser import (
    ProjectParser,
    ParseResult,
    ParsingError,
    parse_project,
    parse_project_to_json
)

from .metadata_parser import (
    MetadataParser,
    extract_project_metadata,
    detect_project_type,
    find_license_info
)

from .dependency_parser import (
    DependencyParser,
    extract_dependencies,
    parse_requirements_file,
    detect_python_version
)

from .code_parser import (
    CodeParser,
    extract_code_information,
    parse_python_file,
    analyze_ast_node
)

from .structure_parser import (
    StructureParser,
    analyze_project_structure,
    find_entry_points,
    categorize_directories
)

from .example_parser import (
    ExampleParser,
    extract_code_examples,
    parse_docstring_examples,
    find_usage_patterns
)

__all__ = [
    # Main orchestrator
    "ProjectParser",
    "ParseResult", 
    "ParsingError",
    "parse_project",
    "parse_project_to_json",
    
    # Metadata parser
    "MetadataParser",
    "extract_project_metadata",
    "detect_project_type",
    "find_license_info",
    
    # Dependency parser
    "DependencyParser",
    "extract_dependencies",
    "parse_requirements_file",
    "detect_python_version",
    
    # Code parser
    "CodeParser",
    "extract_code_information",
    "parse_python_file",
    "analyze_ast_node",
    
    # Structure parser
    "StructureParser",
    "analyze_project_structure",
    "find_entry_points",
    "categorize_directories",
    
    # Example parser
    "ExampleParser",
    "extract_code_examples",
    "parse_docstring_examples",
    "find_usage_patterns"
]

__version__ = "0.1.0"
