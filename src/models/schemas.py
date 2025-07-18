"""
JSON schema definitions for project data validation and documentation.

This module provides schema definitions that correspond to the data classes
in project_data.py, enabling validation and documentation of the JSON output.
"""

from typing import Dict, Any

# Schema for function/method information
FUNCTION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "signature": {"type": "string"},
        "docstring": {"type": ["string", "null"]},
        "is_public": {"type": "boolean"},
        "is_async": {"type": "boolean"},
        "is_property": {"type": "boolean"},
        "is_classmethod": {"type": "boolean"},
        "is_staticmethod": {"type": "boolean"},
        "decorators": {
            "type": "array",
            "items": {"type": "string"}
        },
        "line_number": {"type": ["integer", "null"]},
        "file_path": {"type": ["string", "null"]},
        "return_type": {"type": ["string", "null"]},
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": ["string", "null"]},
                    "default": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]}
                },
                "required": ["name"]
            }
        },
        "complexity_score": {"type": ["integer", "null"]}
    },
    "required": ["name", "signature"]
}

# Schema for class information
CLASS_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "docstring": {"type": ["string", "null"]},
        "methods": {
            "type": "array",
            "items": FUNCTION_SCHEMA
        },
        "properties": {
            "type": "array",
            "items": FUNCTION_SCHEMA
        },
        "inheritance": {
            "type": "array",
            "items": {"type": "string"}
        },
        "decorators": {
            "type": "array",
            "items": {"type": "string"}
        },
        "is_abstract": {"type": "boolean"},
        "is_dataclass": {"type": "boolean"},
        "is_enum": {"type": "boolean"},
        "line_number": {"type": ["integer", "null"]},
        "file_path": {"type": ["string", "null"]},
        "attributes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]}
                },
                "required": ["name"]
            }
        }
    },
    "required": ["name"]
}

# Schema for module information
MODULE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "file_path": {"type": "string"},
        "docstring": {"type": ["string", "null"]},
        "classes": {
            "type": "array",
            "items": CLASS_SCHEMA
        },
        "functions": {
            "type": "array",
            "items": FUNCTION_SCHEMA
        },
        "constants": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": ["string", "number", "boolean", "null"]},
                    "type": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]}
                },
                "required": ["name"]
            }
        },
        "imports": {
            "type": "array",
            "items": {"type": "string"}
        },
        "is_package": {"type": "boolean"},
        "is_main": {"type": "boolean"},
        "line_count": {"type": "integer"}
    },
    "required": ["name", "file_path"]
}

# Schema for project metadata
METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "version": {"type": ["string", "null"]},
        "author": {"type": ["string", "null"]},
        "author_email": {"type": ["string", "null"]},
        "license": {
            "type": ["string", "null"],
            "enum": ["MIT", "GPL-3.0", "Apache-2.0", "BSD-3-Clause", "Unlicense", "Proprietary", "Unknown", None]
        },
        "homepage": {"type": ["string", "null"]},
        "repository": {"type": ["string", "null"]},
        "python_version": {"type": ["string", "null"]},
        "project_type": {
            "type": "string",
            "enum": ["library", "application", "cli_tool", "web_application", "api", "package", "unknown"]
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"}
        },
        "classifiers": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["project_name"]
}

# Schema for dependencies
DEPENDENCIES_SCHEMA = {
    "type": "object",
    "properties": {
        "production": {
            "type": "array",
            "items": {"type": "string"}
        },
        "development": {
            "type": "array",
            "items": {"type": "string"}
        },
        "optional": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "python_requires": {"type": ["string", "null"]},
        "extras_require": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
    },
    "required": ["production", "development"]
}

# Schema for entry points
ENTRY_POINT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "module": {"type": "string"},
        "function": {"type": ["string", "null"]},
        "script_path": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]}
    },
    "required": ["name", "module"]
}

# Schema for project structure
STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "root_path": {"type": "string"},
        "main_package": {"type": ["string", "null"]},
        "src_layout": {"type": "boolean"},
        "packages": {
            "type": "array",
            "items": {"type": "string"}
        },
        "modules": {
            "type": "array",
            "items": MODULE_SCHEMA
        },
        "entry_points": {
            "type": "array",
            "items": ENTRY_POINT_SCHEMA
        },
        "config_files": {
            "type": "array",
            "items": {"type": "string"}
        },
        "data_directories": {
            "type": "array",
            "items": {"type": "string"}
        },
        "test_directories": {
            "type": "array",
            "items": {"type": "string"}
        },
        "doc_directories": {
            "type": "array",
            "items": {"type": "string"}
        },
        "total_files": {"type": "integer"},
        "total_lines": {"type": "integer"}
    },
    "required": ["root_path", "total_files", "total_lines"]
}

# Schema for code examples
CODE_EXAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "code": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "file_path": {"type": ["string", "null"]},
        "line_number": {"type": ["integer", "null"]},
        "example_type": {"type": "string"},
        "language": {"type": "string"},
        "is_executable": {"type": "boolean"},
        "expected_output": {"type": ["string", "null"]}
    },
    "required": ["title", "code"]
}

# Schema for configuration information
CONFIGURATION_SCHEMA = {
    "type": "object",
    "properties": {
        "config_files": {
            "type": "array",
            "items": {"type": "string"}
        },
        "environment_variables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "default": {"type": ["string", "null"]},
                    "required": {"type": "boolean"}
                },
                "required": ["name"]
            }
        },
        "default_settings": {
            "type": "object",
            "patternProperties": {
                ".*": {}
            }
        },
        "config_examples": {
            "type": "array",
            "items": CODE_EXAMPLE_SCHEMA
        }
    }
}

# Schema for test information
TEST_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "test_directories": {
            "type": "array",
            "items": {"type": "string"}
        },
        "test_files": {
            "type": "array",
            "items": {"type": "string"}
        },
        "test_framework": {"type": ["string", "null"]},
        "coverage_files": {
            "type": "array",
            "items": {"type": "string"}
        },
        "total_tests": {"type": "integer"}
    }
}

# Schema for documentation information
DOCUMENTATION_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "readme_file": {"type": ["string", "null"]},
        "changelog_file": {"type": ["string", "null"]},
        "license_file": {"type": ["string", "null"]},
        "doc_directories": {
            "type": "array",
            "items": {"type": "string"}
        },
        "doc_files": {
            "type": "array",
            "items": {"type": "string"}
        },
        "has_sphinx": {"type": "boolean"},
        "has_mkdocs": {"type": "boolean"}
    }
}

# Main schema for the complete project data
PROJECT_DATA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "metadata": METADATA_SCHEMA,
        "dependencies": DEPENDENCIES_SCHEMA,
        "structure": STRUCTURE_SCHEMA,
        "configuration": CONFIGURATION_SCHEMA,
        "examples": {
            "type": "array",
            "items": CODE_EXAMPLE_SCHEMA
        },
        "tests": {
            "oneOf": [
                {"type": "null"},
                TEST_INFO_SCHEMA
            ]
        },
        "documentation": {
            "oneOf": [
                {"type": "null"},
                DOCUMENTATION_INFO_SCHEMA
            ]
        },
        "parsing_errors": {
            "type": "array",
            "items": {"type": "string"}
        },
        "token_count": {"type": "integer"},
        "parsing_timestamp": {"type": ["string", "null"]}
    },
    "required": ["metadata", "dependencies", "structure", "configuration"]
}


def validate_project_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate project data against the schema.
    
    Args:
        data: The project data to validate
        
    Returns:
        Dict containing validation results
    """
    try:
        import jsonschema
        jsonschema.validate(data, PROJECT_DATA_SCHEMA)
        return {"valid": True, "errors": []}
    except ImportError:
        return {"valid": None, "errors": ["jsonschema library not available"]}
    except jsonschema.ValidationError as e:
        return {"valid": False, "errors": [str(e)]}
    except Exception as e:
        return {"valid": False, "errors": [f"Validation error: {str(e)}"]}


def get_schema_version() -> str:
    """Get the current schema version."""
    return "1.0.0"


def get_schema_documentation() -> Dict[str, Any]:
    """Get human-readable documentation for the schema."""
    return {
        "version": get_schema_version(),
        "description": "JSON schema for Python project parsing data",
        "sections": {
            "metadata": "Basic project information from setup files",
            "dependencies": "Project dependencies and requirements",
            "structure": "Project organization and file structure",
            "configuration": "Configuration files and settings",
            "examples": "Code examples and usage patterns",
            "tests": "Test-related information",
            "documentation": "Documentation files and structure"
        },
        "token_budget": {
            "target_max": 1000000,
            "typical_range": "50000-800000",
            "priority_order": [
                "metadata",
                "dependencies", 
                "structure.entry_points",
                "structure.modules (public APIs)",
                "examples",
                "configuration",
                "tests",
                "documentation"
            ]
        }
    }


# Export the main schema for external use
__all__ = [
    "PROJECT_DATA_SCHEMA",
    "METADATA_SCHEMA",
    "DEPENDENCIES_SCHEMA",
    "STRUCTURE_SCHEMA",
    "CONFIGURATION_SCHEMA",
    "CODE_EXAMPLE_SCHEMA",
    "validate_project_data",
    "get_schema_version",
    "get_schema_documentation"
]
