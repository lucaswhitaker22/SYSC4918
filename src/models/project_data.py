"""
Data classes representing parsed project information for README generation.

This module contains all the data structures used to store and organize
information extracted from Python projects during the parsing process.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
from pathlib import Path


class ProjectType(Enum):
    """Enumeration of common Python project types."""
    LIBRARY = "library"
    APPLICATION = "application"
    CLI_TOOL = "cli_tool"
    WEB_APPLICATION = "web_application"
    API = "api"
    PACKAGE = "package"
    UNKNOWN = "unknown"


class LicenseType(Enum):
    """Enumeration of common license types."""
    MIT = "MIT"
    GPL_V3 = "GPL-3.0"
    APACHE_2 = "Apache-2.0"
    BSD_3 = "BSD-3-Clause"
    UNLICENSE = "Unlicense"
    PROPRIETARY = "Proprietary"
    UNKNOWN = "Unknown"


@dataclass
class ProjectMetadata:
    """Core project metadata extracted from setup files and git."""
    
    project_name: str
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    author_email: Optional[str] = None
    license: Optional[LicenseType] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    python_version: Optional[str] = None
    project_type: ProjectType = ProjectType.UNKNOWN
    keywords: List[str] = field(default_factory=list)
    classifiers: List[str] = field(default_factory=list)


@dataclass
class DependencyInfo:
    """Information about project dependencies and requirements."""
    
    production: List[str] = field(default_factory=list)
    development: List[str] = field(default_factory=list)
    optional: Dict[str, List[str]] = field(default_factory=dict)
    python_requires: Optional[str] = None
    extras_require: Dict[str, List[str]] = field(default_factory=dict)
    
    def get_all_dependencies(self) -> List[str]:
        """Get all dependencies combined."""
        all_deps = self.production + self.development
        for extra_deps in self.optional.values():
            all_deps.extend(extra_deps)
        for extra_deps in self.extras_require.values():
            all_deps.extend(extra_deps)
        return list(set(all_deps))


@dataclass
class FunctionInfo:
    """Information about a function or method."""
    
    name: str
    signature: str
    docstring: Optional[str] = None
    is_public: bool = True
    is_async: bool = False
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    decorators: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    return_type: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    complexity_score: Optional[int] = None


@dataclass
class ClassInfo:
    """Information about a class."""
    
    name: str
    docstring: Optional[str] = None
    methods: List[FunctionInfo] = field(default_factory=list)
    properties: List[FunctionInfo] = field(default_factory=list)
    inheritance: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    is_abstract: bool = False
    is_dataclass: bool = False
    is_enum: bool = False
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_public_methods(self) -> List[FunctionInfo]:
        """Get only public methods."""
        return [method for method in self.methods if method.is_public]
    
    def get_public_properties(self) -> List[FunctionInfo]:
        """Get only public properties."""
        return [prop for prop in self.properties if prop.is_public]


@dataclass
class ModuleInfo:
    """Information about a Python module."""
    
    name: str
    file_path: str
    docstring: Optional[str] = None
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    is_package: bool = False
    is_main: bool = False
    line_count: int = 0


@dataclass
class EntryPoint:
    """Information about project entry points."""
    
    name: str
    module: str
    function: Optional[str] = None
    script_path: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ProjectStructure:
    """Information about the overall project structure."""
    
    root_path: str
    main_package: Optional[str] = None
    src_layout: bool = False
    packages: List[str] = field(default_factory=list)
    modules: List[ModuleInfo] = field(default_factory=list)
    entry_points: List[EntryPoint] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    data_directories: List[str] = field(default_factory=list)
    test_directories: List[str] = field(default_factory=list)
    doc_directories: List[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    
    def get_main_modules(self) -> List[ModuleInfo]:
        """Get modules that are likely entry points."""
        return [module for module in self.modules if module.is_main]


@dataclass
class CodeExample:
    """A code example extracted from the project."""
    
    title: str
    code: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    example_type: str = "usage"  # usage, configuration, test, etc.
    language: str = "python"
    is_executable: bool = True
    expected_output: Optional[str] = None


@dataclass
class ConfigurationInfo:
    """Information about project configuration."""
    
    config_files: List[str] = field(default_factory=list)
    environment_variables: List[Dict[str, str]] = field(default_factory=list)
    default_settings: Dict[str, Any] = field(default_factory=dict)
    config_examples: List[CodeExample] = field(default_factory=list)


@dataclass
class TestInfo:
    """Information about project tests."""
    
    test_directories: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    test_framework: Optional[str] = None
    coverage_files: List[str] = field(default_factory=list)
    total_tests: int = 0


@dataclass
class DocumentationInfo:
    """Information about project documentation."""
    
    readme_file: Optional[str] = None
    changelog_file: Optional[str] = None
    license_file: Optional[str] = None
    doc_directories: List[str] = field(default_factory=list)
    doc_files: List[str] = field(default_factory=list)
    has_sphinx: bool = False
    has_mkdocs: bool = False


@dataclass
class ProjectData:
    """Complete parsed project information."""
    
    metadata: ProjectMetadata
    dependencies: DependencyInfo
    structure: ProjectStructure
    configuration: ConfigurationInfo
    examples: List[CodeExample] = field(default_factory=list)
    tests: Optional[TestInfo] = None
    documentation: Optional[DocumentationInfo] = None
    parsing_errors: List[str] = field(default_factory=list)
    token_count: int = 0
    parsing_timestamp: Optional[str] = None
    
    def get_api_documentation(self) -> Dict[str, Any]:
        """Get formatted API documentation."""
        return {
            "classes": [
                {
                    "name": cls.name,
                    "docstring": cls.docstring,
                    "methods": [
                        {
                            "name": method.name,
                            "signature": method.signature,
                            "docstring": method.docstring,
                            "is_public": method.is_public
                        }
                        for method in cls.get_public_methods()
                    ],
                    "inheritance": cls.inheritance,
                    "file_path": cls.file_path
                }
                for module in self.structure.modules
                for cls in module.classes
                if cls.name and not cls.name.startswith('_')
            ],
            "functions": [
                {
                    "name": func.name,
                    "signature": func.signature,
                    "docstring": func.docstring,
                    "is_public": func.is_public,
                    "file_path": func.file_path
                }
                for module in self.structure.modules
                for func in module.functions
                if func.is_public and not func.name.startswith('_')
            ]
        }
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the project."""
        total_classes = sum(len(module.classes) for module in self.structure.modules)
        total_functions = sum(len(module.functions) for module in self.structure.modules)
        public_classes = sum(
            len([cls for cls in module.classes if not cls.name.startswith('_')])
            for module in self.structure.modules
        )
        public_functions = sum(
            len([func for func in module.functions if func.is_public])
            for module in self.structure.modules
        )
        
        return {
            "total_files": self.structure.total_files,
            "total_lines": self.structure.total_lines,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "public_classes": public_classes,
            "public_functions": public_functions,
            "total_dependencies": len(self.dependencies.get_all_dependencies()),
            "total_examples": len(self.examples),
            "token_count": self.token_count
        }
