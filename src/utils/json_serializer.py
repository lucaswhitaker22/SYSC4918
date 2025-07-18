"""
JSON serialization utilities for project data output.

This module provides functions to serialize project data to JSON format
with proper formatting, validation, and error handling.
"""

import json
import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import asdict, is_dataclass
from enum import Enum
import logging

from models.project_data import ProjectData, ProjectType, LicenseType
from models.schemas import validate_project_data, PROJECT_DATA_SCHEMA
from .token_counter import TokenCounter, ContentType

logger = logging.getLogger(__name__)


class ProjectDataEncoder(json.JSONEncoder):
    """Custom JSON encoder for project data objects."""
    
    def default(self, obj):
        """Handle special object types for JSON serialization."""
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return super().default(obj)


class ProjectDataSerializer:
    """Advanced project data serializer with validation and optimization."""
    
    def __init__(self, token_counter: Optional[TokenCounter] = None):
        self.token_counter = token_counter or TokenCounter()
        self.encoder = ProjectDataEncoder()
        
    def serialize(self, project_data: ProjectData, 
                  validate: bool = True, 
                  optimize_for_tokens: bool = True) -> Dict[str, Any]:
        """
        Serialize project data to dictionary format.
        
        Args:
            project_data: Project data to serialize
            validate: Whether to validate against schema
            optimize_for_tokens: Whether to optimize for token usage
            
        Returns:
            Serialized project data dictionary
        """
        try:
            # Convert to dictionary
            data_dict = self._convert_to_dict(project_data)
            
            # Add metadata
            data_dict['serialization_info'] = {
                'timestamp': datetime.datetime.now().isoformat(),
                'version': '1.0.0',
                'token_optimized': optimize_for_tokens
            }
            
            # Optimize for tokens if requested
            if optimize_for_tokens:
                data_dict = self._optimize_for_tokens(data_dict)
            
            # Update token count
            data_dict['token_count'] = self._calculate_total_tokens(data_dict)
            
            # Validate if requested
            if validate:
                validation_result = validate_project_data(data_dict)
                if not validation_result.get('valid', True):
                    logger.warning(f"Validation warnings: {validation_result.get('errors', [])}")
            
            return data_dict
            
        except Exception as e:
            logger.error(f"Error serializing project data: {e}")
            raise
    
    def _convert_to_dict(self, project_data: ProjectData) -> Dict[str, Any]:
        """Convert project data to dictionary format."""
        return {
            'metadata': self._serialize_metadata(project_data.metadata),
            'dependencies': self._serialize_dependencies(project_data.dependencies),
            'structure': self._serialize_structure(project_data.structure),
            'configuration': self._serialize_configuration(project_data.configuration),
            'examples': self._serialize_examples(project_data.examples),
            'tests': self._serialize_tests(project_data.tests),
            'documentation': self._serialize_documentation(project_data.documentation),
            'parsing_errors': project_data.parsing_errors,
            'parsing_timestamp': project_data.parsing_timestamp
        }
    
    def _serialize_metadata(self, metadata) -> Dict[str, Any]:
        """Serialize metadata with proper type handling."""
        return {
            'project_name': metadata.project_name,
            'description': metadata.description,
            'version': metadata.version,
            'author': metadata.author,
            'author_email': metadata.author_email,
            'license': metadata.license.value if metadata.license else None,
            'homepage': metadata.homepage,
            'repository': metadata.repository,
            'python_version': metadata.python_version,
            'project_type': metadata.project_type.value,
            'keywords': metadata.keywords,
            'classifiers': metadata.classifiers
        }
    
    def _serialize_dependencies(self, dependencies) -> Dict[str, Any]:
        """Serialize dependencies information."""
        return {
            'production': dependencies.production,
            'development': dependencies.development,
            'optional': dependencies.optional,
            'python_requires': dependencies.python_requires,
            'extras_require': dependencies.extras_require
        }
    
    def _serialize_structure(self, structure) -> Dict[str, Any]:
        """Serialize project structure information."""
        return {
            'root_path': structure.root_path,
            'main_package': structure.main_package,
            'src_layout': structure.src_layout,
            'packages': structure.packages,
            'modules': [self._serialize_module(module) for module in structure.modules],
            'entry_points': [self._serialize_entry_point(ep) for ep in structure.entry_points],
            'config_files': structure.config_files,
            'data_directories': structure.data_directories,
            'test_directories': structure.test_directories,
            'doc_directories': structure.doc_directories,
            'total_files': structure.total_files,
            'total_lines': structure.total_lines
        }
    
    def _serialize_module(self, module) -> Dict[str, Any]:
        """Serialize module information."""
        return {
            'name': module.name,
            'file_path': module.file_path,
            'docstring': module.docstring,
            'classes': [self._serialize_class(cls) for cls in module.classes],
            'functions': [self._serialize_function(func) for func in module.functions],
            'constants': module.constants,
            'imports': module.imports,
            'is_package': module.is_package,
            'is_main': module.is_main,
            'line_count': module.line_count
        }
    
    def _serialize_class(self, class_info) -> Dict[str, Any]:
        """Serialize class information."""
        return {
            'name': class_info.name,
            'docstring': class_info.docstring,
            'methods': [self._serialize_function(method) for method in class_info.methods],
            'properties': [self._serialize_function(prop) for prop in class_info.properties],
            'inheritance': class_info.inheritance,
            'decorators': class_info.decorators,
            'is_abstract': class_info.is_abstract,
            'is_dataclass': class_info.is_dataclass,
            'is_enum': class_info.is_enum,
            'line_number': class_info.line_number,
            'file_path': class_info.file_path,
            'attributes': class_info.attributes
        }
    
    def _serialize_function(self, function) -> Dict[str, Any]:
        """Serialize function information."""
        return {
            'name': function.name,
            'signature': function.signature,
            'docstring': function.docstring,
            'is_public': function.is_public,
            'is_async': function.is_async,
            'is_property': function.is_property,
            'is_classmethod': function.is_classmethod,
            'is_staticmethod': function.is_staticmethod,
            'decorators': function.decorators,
            'line_number': function.line_number,
            'file_path': function.file_path,
            'return_type': function.return_type,
            'parameters': function.parameters,
            'complexity_score': function.complexity_score
        }
    
    def _serialize_entry_point(self, entry_point) -> Dict[str, Any]:
        """Serialize entry point information."""
        return {
            'name': entry_point.name,
            'module': entry_point.module,
            'function': entry_point.function,
            'script_path': entry_point.script_path,
            'description': entry_point.description
        }
    
    def _serialize_configuration(self, config) -> Dict[str, Any]:
        """Serialize configuration information."""
        if not config:
            return {}
            
        return {
            'config_files': config.config_files,
            'environment_variables': config.environment_variables,
            'default_settings': config.default_settings,
            'config_examples': [self._serialize_example(ex) for ex in config.config_examples]
        }
    
    def _serialize_examples(self, examples) -> List[Dict[str, Any]]:
        """Serialize examples list."""
        return [self._serialize_example(example) for example in examples]
    
    def _serialize_example(self, example) -> Dict[str, Any]:
        """Serialize a single example."""
        return {
            'title': example.title,
            'code': example.code,
            'description': example.description,
            'file_path': example.file_path,
            'line_number': example.line_number,
            'example_type': example.example_type,
            'language': example.language,
            'is_executable': example.is_executable,
            'expected_output': example.expected_output
        }
    
    def _serialize_tests(self, tests) -> Optional[Dict[str, Any]]:
        """Serialize test information."""
        if not tests:
            return None
            
        return {
            'test_directories': tests.test_directories,
            'test_files': tests.test_files,
            'test_framework': tests.test_framework,
            'coverage_files': tests.coverage_files,
            'total_tests': tests.total_tests
        }
    
    def _serialize_documentation(self, documentation) -> Optional[Dict[str, Any]]:
        """Serialize documentation information."""
        if not documentation:
            return None
            
        return {
            'readme_file': documentation.readme_file,
            'changelog_file': documentation.changelog_file,
            'license_file': documentation.license_file,
            'doc_directories': documentation.doc_directories,
            'doc_files': documentation.doc_files,
            'has_sphinx': documentation.has_sphinx,
            'has_mkdocs': documentation.has_mkdocs
        }
    
    def _optimize_for_tokens(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data dictionary for token usage."""
        # Remove empty or None values
        cleaned_dict = self._remove_empty_values(data_dict)
        
        # Truncate long docstrings if needed
        cleaned_dict = self._truncate_long_content(cleaned_dict)
        
        # Prioritize content based on importance
        cleaned_dict = self._prioritize_content(cleaned_dict)
        
        return cleaned_dict
    
    def _remove_empty_values(self, data: Any) -> Any:
        """Recursively remove empty values from data structure."""
        if isinstance(data, dict):
            return {k: self._remove_empty_values(v) for k, v in data.items() 
                   if v is not None and v != [] and v != {}}
        elif isinstance(data, list):
            return [self._remove_empty_values(item) for item in data if item is not None]
        else:
            return data
    
    def _truncate_long_content(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate long content to optimize token usage."""
        # Truncate very long docstrings
        if 'structure' in data_dict and 'modules' in data_dict['structure']:
            for module in data_dict['structure']['modules']:
                # Truncate module docstring
                if 'docstring' in module and module['docstring']:
                    module['docstring'] = self._truncate_text(module['docstring'], 500)
                
                # Truncate class docstrings
                for class_info in module.get('classes', []):
                    if 'docstring' in class_info and class_info['docstring']:
                        class_info['docstring'] = self._truncate_text(class_info['docstring'], 300)
                    
                    # Truncate method docstrings
                    for method in class_info.get('methods', []):
                        if 'docstring' in method and method['docstring']:
                            method['docstring'] = self._truncate_text(method['docstring'], 200)
                
                # Truncate function docstrings
                for function in module.get('functions', []):
                    if 'docstring' in function and function['docstring']:
                        function['docstring'] = self._truncate_text(function['docstring'], 200)
        
        return data_dict
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _prioritize_content(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize content based on importance."""
        # Keep only public APIs for classes and functions
        if 'structure' in data_dict and 'modules' in data_dict['structure']:
            for module in data_dict['structure']['modules']:
                # Filter classes to keep only public ones
                if 'classes' in module:
                    module['classes'] = [cls for cls in module['classes'] 
                                       if not cls.get('name', '').startswith('_')]
                
                # Filter functions to keep only public ones
                if 'functions' in module:
                    module['functions'] = [func for func in module['functions'] 
                                         if func.get('is_public', True)]
        
        return data_dict
    
    def _calculate_total_tokens(self, data_dict: Dict[str, Any]) -> int:
        """Calculate total token count for the serialized data."""
        json_str = json.dumps(data_dict, cls=ProjectDataEncoder, separators=(',', ':'))
        return self.token_counter.count_tokens(json_str, ContentType.JSON)


def serialize_project_data(project_data: ProjectData, 
                          validate: bool = True, 
                          optimize_for_tokens: bool = True) -> Dict[str, Any]:
    """
    Serialize project data to dictionary format.
    
    Args:
        project_data: Project data to serialize
        validate: Whether to validate against schema
        optimize_for_tokens: Whether to optimize for token usage
        
    Returns:
        Serialized project data dictionary
    """
    serializer = ProjectDataSerializer()
    return serializer.serialize(project_data, validate, optimize_for_tokens)


def validate_json_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate JSON output against schema.
    
    Args:
        data: Data to validate
        
    Returns:
        Validation result dictionary
    """
    return validate_project_data(data)


def format_json_output(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Format data as JSON string with proper indentation.
    
    Args:
        data: Data to format
        indent: Number of spaces for indentation
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, cls=ProjectDataEncoder, indent=indent, ensure_ascii=False)


def save_json_to_file(data: Dict[str, Any], 
                     file_path: str, 
                     indent: int = 2, 
                     validate: bool = True) -> bool:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save file
        indent: JSON indentation
        validate: Whether to validate before saving
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if validate:
            validation_result = validate_json_output(data)
            if not validation_result.get('valid', True):
                logger.warning(f"Validation warnings: {validation_result.get('errors', [])}")
        
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(format_json_output(data, indent))
        
        logger.info(f"Successfully saved JSON to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False


def load_json_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Loaded data or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None


def get_json_size_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get size information for JSON data.
    
    Args:
        data: Data to analyze
        
    Returns:
        Size information dictionary
    """
    json_str = format_json_output(data, indent=None)
    
    token_counter = TokenCounter()
    
    return {
        'characters': len(json_str),
        'bytes': len(json_str.encode('utf-8')),
        'lines': json_str.count('\n') + 1,
        'tokens': token_counter.count_tokens(json_str, ContentType.JSON),
        'size_mb': len(json_str.encode('utf-8')) / (1024 * 1024)
    }
