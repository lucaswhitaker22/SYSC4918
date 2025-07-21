"""
Minimal JSON serializer for project data optimized for MVP implementation.

This simplified module focuses on essential serialization functionality for
converting parsed project data to JSON format suitable for LLM input, without
the complexity of the full serialization system.
"""

import json
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from models.project_data import (
    ProjectData, ProjectMetadata, DependencyInfo, ProjectStructure,
    ModuleInfo, ClassInfo, FunctionInfo, CodeExample, ConfigurationInfo,
    TestInfo, DocumentationInfo, EntryPoint, ProjectType, LicenseType
)
from utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class SerializationError(Exception):
    """Custom exception for serialization errors."""
    pass


class MinimalSerializer:
    """Simplified JSON serializer for project data."""
    
    def __init__(self, token_counter: Optional[TokenCounter] = None):
        """
        Initialize the minimal serializer.
        
        Args:
            token_counter: Optional token counter for budget management
        """
        self.token_counter = token_counter
        
    def serialize(self, project_data: ProjectData, validate: bool = True) -> Dict[str, Any]:
        """
        Serialize project data to JSON-compatible dictionary.
        
        Args:
            project_data: ProjectData object to serialize
            validate: Whether to validate the data before serialization
            
        Returns:
            JSON-compatible dictionary
        """
        try:
            if validate:
                self._validate_project_data(project_data)
            
            serialized = {
                "metadata": self._serialize_metadata(project_data.metadata),
                "dependencies": self._serialize_dependencies(project_data.dependencies),
                "structure": self._serialize_structure(project_data.structure),
                "configuration": self._serialize_configuration(project_data.configuration),
                "examples": self._serialize_examples(project_data.examples),
                "tests": self._serialize_tests(project_data.tests),
                "documentation": self._serialize_documentation(project_data.documentation),
                "parsing_errors": project_data.parsing_errors,
                "token_count": project_data.token_count,
                "parsing_timestamp": project_data.parsing_timestamp or datetime.now().isoformat()
            }
            
            return serialized
            
        except Exception as e:
            logger.error(f"Error serializing project data: {e}")
            raise SerializationError(f"Failed to serialize project data: {e}")
    
    def serialize_to_json(self, project_data: ProjectData, indent: int = 2) -> str:
        """
        Serialize project data to JSON string.
        
        Args:
            project_data: ProjectData object to serialize
            indent: JSON indentation level
            
        Returns:
            JSON string
        """
        try:
            data_dict = self.serialize(project_data)
            return json.dumps(data_dict, indent=indent, ensure_ascii=False, default=self._json_serializer)
            
        except Exception as e:
            logger.error(f"Error serializing to JSON: {e}")
            raise SerializationError(f"Failed to serialize to JSON: {e}")
    
    def _serialize_metadata(self, metadata: ProjectMetadata) -> Dict[str, Any]:
        """Serialize project metadata."""
        return {
            "project_name": metadata.project_name,
            "description": metadata.description,
            "version": metadata.version,
            "author": metadata.author,
            "author_email": metadata.author_email,
            "license": metadata.license.value if metadata.license else None,
            "homepage": metadata.homepage,
            "repository": metadata.repository,
            "python_version": metadata.python_version,
            "project_type": metadata.project_type.value,
            "keywords": metadata.keywords,
            "classifiers": metadata.classifiers
        }
    
    def _serialize_dependencies(self, dependencies: DependencyInfo) -> Dict[str, Any]:
        """Serialize dependency information."""
        return {
            "production": dependencies.production,
            "development": dependencies.development,
            "optional": dependencies.optional,
            "python_requires": dependencies.python_requires,
            "extras_require": dependencies.extras_require
        }
    
    def _serialize_structure(self, structure: ProjectStructure) -> Dict[str, Any]:
        """Serialize project structure."""
        return {
            "root_path": structure.root_path,
            "main_package": structure.main_package,
            "src_layout": structure.src_layout,
            "packages": structure.packages,
            "modules": [self._serialize_module(module) for module in structure.modules],
            "entry_points": [self._serialize_entry_point(ep) for ep in structure.entry_points],
            "config_files": structure.config_files,
            "data_directories": structure.data_directories,
            "test_directories": structure.test_directories,
            "doc_directories": structure.doc_directories,
            "total_files": structure.total_files,
            "total_lines": structure.total_lines
        }
    
    def _serialize_module(self, module: ModuleInfo) -> Dict[str, Any]:
        """Serialize module information."""
        return {
            "name": module.name,
            "file_path": module.file_path,
            "docstring": module.docstring,
            "classes": [self._serialize_class(cls) for cls in module.classes],
            "functions": [self._serialize_function(func) for func in module.functions],
            "constants": module.constants,
            "imports": module.imports,
            "is_package": module.is_package,
            "is_main": module.is_main,
            "line_count": module.line_count
        }
    
    def _serialize_class(self, class_info: ClassInfo) -> Dict[str, Any]:
        """Serialize class information."""
        return {
            "name": class_info.name,
            "docstring": class_info.docstring,
            "methods": [self._serialize_function(method) for method in class_info.methods],
            "properties": [self._serialize_function(prop) for prop in class_info.properties],
            "inheritance": class_info.inheritance,
            "decorators": class_info.decorators,
            "is_abstract": class_info.is_abstract,
            "is_dataclass": class_info.is_dataclass,
            "is_enum": class_info.is_enum,
            "line_number": class_info.line_number,
            "file_path": class_info.file_path,
            "attributes": class_info.attributes
        }
    
    def _serialize_function(self, function_info: FunctionInfo) -> Dict[str, Any]:
        """Serialize function information."""
        return {
            "name": function_info.name,
            "signature": function_info.signature,
            "docstring": function_info.docstring,
            "is_public": function_info.is_public,
            "is_async": function_info.is_async,
            "is_property": function_info.is_property,
            "is_classmethod": function_info.is_classmethod,
            "is_staticmethod": function_info.is_staticmethod,
            "decorators": function_info.decorators,
            "line_number": function_info.line_number,
            "file_path": function_info.file_path,
            "return_type": function_info.return_type,
            "parameters": function_info.parameters,
            "complexity_score": function_info.complexity_score
        }
    
    def _serialize_entry_point(self, entry_point: EntryPoint) -> Dict[str, Any]:
        """Serialize entry point information."""
        return {
            "name": entry_point.name,
            "module": entry_point.module,
            "function": entry_point.function,
            "script_path": entry_point.script_path,
            "description": entry_point.description
        }
    
    def _serialize_configuration(self, configuration: ConfigurationInfo) -> Dict[str, Any]:
        """Serialize configuration information."""
        return {
            "config_files": configuration.config_files,
            "environment_variables": configuration.environment_variables,
            "default_settings": configuration.default_settings,
            "config_examples": [self._serialize_example(ex) for ex in configuration.config_examples]
        }
    
    def _serialize_examples(self, examples: list) -> list:
        """Serialize code examples."""
        return [self._serialize_example(example) for example in examples]
    
    def _serialize_example(self, example: CodeExample) -> Dict[str, Any]:
        """Serialize a single code example."""
        return {
            "title": example.title,
            "code": example.code,
            "description": example.description,
            "file_path": example.file_path,
            "line_number": example.line_number,
            "example_type": example.example_type,
            "language": example.language,
            "is_executable": example.is_executable,
            "expected_output": example.expected_output
        }
    
    def _serialize_tests(self, tests: Optional[TestInfo]) -> Optional[Dict[str, Any]]:
        """Serialize test information."""
        if not tests:
            return None
        
        return {
            "test_directories": tests.test_directories,
            "test_files": tests.test_files,
            "test_framework": tests.test_framework,
            "coverage_files": tests.coverage_files,
            "total_tests": tests.total_tests
        }
    
    def _serialize_documentation(self, documentation: Optional[DocumentationInfo]) -> Optional[Dict[str, Any]]:
        """Serialize documentation information."""
        if not documentation:
            return None
        
        return {
            "readme_file": documentation.readme_file,
            "changelog_file": documentation.changelog_file,
            "license_file": documentation.license_file,
            "doc_directories": documentation.doc_directories,
            "doc_files": documentation.doc_files,
            "has_sphinx": documentation.has_sphinx,
            "has_mkdocs": documentation.has_mkdocs
        }
    
    def _validate_project_data(self, project_data: ProjectData) -> None:
        """Basic validation of project data."""
        if not project_data.metadata:
            raise SerializationError("Project metadata is required")
        
        if not project_data.metadata.project_name:
            raise SerializationError("Project name is required")
        
        if not project_data.dependencies:
            raise SerializationError("Dependencies information is required")
        
        if not project_data.structure:
            raise SerializationError("Project structure is required")
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-serializable objects."""
        if isinstance(obj, (ProjectType, LicenseType)):
            return obj.value
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            logger.warning(f"Cannot serialize object of type {type(obj)}: {obj}")
            return str(obj)
    
    def estimate_token_count(self, project_data: ProjectData) -> int:
        """Estimate token count for serialized data."""
        if not self.token_counter:
            # Simple estimation: ~4 characters per token
            serialized = self.serialize(project_data)
            json_str = json.dumps(serialized)
            return len(json_str) // 4
        
        serialized = self.serialize(project_data)
        return self.token_counter.count_tokens_in_dict(serialized)


# Convenience functions for external use
def serialize_project_data(project_data: ProjectData, 
                          token_counter: Optional[TokenCounter] = None,
                          validate: bool = True) -> Dict[str, Any]:
    """
    Serialize project data to JSON-compatible dictionary.
    
    Args:
        project_data: ProjectData object to serialize
        token_counter: Optional token counter
        validate: Whether to validate data before serialization
        
    Returns:
        JSON-compatible dictionary
    """
    serializer = MinimalSerializer(token_counter)
    return serializer.serialize(project_data, validate)


def serialize_to_json_string(project_data: ProjectData,
                           token_counter: Optional[TokenCounter] = None,
                           indent: int = 2) -> str:
    """
    Serialize project data to JSON string.
    
    Args:
        project_data: ProjectData object to serialize
        token_counter: Optional token counter
        indent: JSON indentation level
        
    Returns:
        JSON string
    """
    serializer = MinimalSerializer(token_counter)
    return serializer.serialize_to_json(project_data, indent)


def save_json_to_file(data: Dict[str, Any], file_path: str) -> bool:
    """
    Save JSON data to file.
    
    Args:
        data: JSON-compatible dictionary
        file_path: Path to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON data saved to: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving JSON to file {file_path}: {e}")
        return False


def load_json_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded data or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"JSON data loaded from: {file_path}")
        return data
        
    except Exception as e:
        logger.error(f"Error loading JSON from file {file_path}: {e}")
        return None


def estimate_serialization_size(project_data: ProjectData) -> Dict[str, int]:
    """
    Estimate the size of different components after serialization.
    
    Args:
        project_data: ProjectData object
        
    Returns:
        Dictionary with size estimates in characters
    """
    serializer = MinimalSerializer()
    
    try:
        # Serialize individual components
        components = {
            'metadata': serializer._serialize_metadata(project_data.metadata),
            'dependencies': serializer._serialize_dependencies(project_data.dependencies),
            'structure': serializer._serialize_structure(project_data.structure),
            'configuration': serializer._serialize_configuration(project_data.configuration),
            'examples': serializer._serialize_examples(project_data.examples),
        }
        
        # Calculate sizes
        sizes = {}
        total_size = 0
        
        for component, data in components.items():
            json_str = json.dumps(data)
            size = len(json_str)
            sizes[component] = size
            total_size += size
        
        sizes['total'] = total_size
        sizes['estimated_tokens'] = total_size // 4  # Rough estimate
        
        return sizes
        
    except Exception as e:
        logger.error(f"Error estimating serialization size: {e}")
        return {'total': 0, 'estimated_tokens': 0}


def create_minimal_json(project_data: ProjectData) -> Dict[str, Any]:
    """
    Create a minimal JSON representation with only essential data.
    
    Args:
        project_data: ProjectData object
        
    Returns:
        Minimal JSON-compatible dictionary
    """
    try:
        # Only include essential information for MVP
        minimal_data = {
            "project_name": project_data.metadata.project_name,
            "description": project_data.metadata.description,
            "version": project_data.metadata.version,
            "dependencies": {
                "production": project_data.dependencies.production[:20],  # Limit deps
                "python_requires": project_data.dependencies.python_requires
            },
            "main_modules": [
                {
                    "name": module.name,
                    "classes": [cls.name for cls in module.classes if cls.name and not cls.name.startswith('_')][:5],
                    "functions": [func.name for func in module.functions if func.is_public][:10]
                }
                for module in project_data.structure.modules[:10]  # Limit modules
                if module.classes or module.functions
            ],
            "entry_points": [
                {"name": ep.name, "module": ep.module}
                for ep in project_data.structure.entry_points[:5]
            ],
            "total_files": project_data.structure.total_files,
            "total_lines": project_data.structure.total_lines
        }
        
        return minimal_data
        
    except Exception as e:
        logger.error(f"Error creating minimal JSON: {e}")
        return {"project_name": "Unknown", "error": str(e)}
