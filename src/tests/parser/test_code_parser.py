import pytest
import tempfile
from pathlib import Path
from textwrap import dedent

from parser.code_parser import parse_code_file, _get_name_from_node
import ast

class TestParseCodeFile:
    """Test cases for parse_code_file function."""
    
    def test_parse_simple_python_file(self, tmp_path):
        """Test parsing a simple Python file with basic structure."""
        test_file = tmp_path / "simple.py"
        test_content = dedent('''
        """This is a simple module."""
        
        def hello_world():
            """Say hello to the world."""
            return "Hello, World!"
        
        class SimpleClass:
            """A simple class example."""
            
            def __init__(self):
                self.value = 42
                
            def get_value(self):
                """Get the stored value."""
                return self.value
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert result["name"] == "simple"
        assert result["file"] == str(test_file)
        assert result["docstring"] == "This is a simple module."
        assert len(result["classes"]) == 1
        assert len(result["functions"]) == 1
        assert result["classes"][0]["name"] == "SimpleClass"
        assert result["functions"][0]["name"] == "hello_world"
    
    def test_parse_file_with_full_code_extraction(self, tmp_path):
        """Test parsing with full source code extraction enabled."""
        test_file = tmp_path / "entry_point.py"
        test_content = dedent('''
        #!/usr/bin/env python3
        """Entry point module."""
        
        def main():
            print("Hello from main!")
            
        if __name__ == "__main__":
            main()
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file), extract_full_code=True)
        
        assert result is not None
        assert "source_code" in result
        assert result["source_code"] == test_content
        assert result["functions"][0]["name"] == "main"
    
    def test_parse_file_without_full_code_extraction(self, tmp_path):
        """Test parsing without full source code extraction."""
        test_file = tmp_path / "regular.py"
        test_content = '''def test(): pass'''
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file), extract_full_code=False)
        
        assert result is not None
        assert "source_code" not in result
        assert result["functions"][0]["name"] == "test"
    
    def test_parse_file_with_classes_and_methods(self, tmp_path):
        """Test parsing file with classes containing methods."""
        test_file = tmp_path / "class_example.py"
        test_content = dedent('''
        class Calculator:
            """A calculator class."""
            
            def __init__(self, initial_value=0):
                """Initialize calculator with optional initial value."""
                self.value = initial_value
            
            @property
            def current_value(self):
                """Get current calculator value."""
                return self.value
                
            @staticmethod
            def add_numbers(a, b):
                """Add two numbers."""
                return a + b
            
            @classmethod    
            def from_string(cls, value_str):
                """Create calculator from string value."""
                return cls(int(value_str))
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert len(result["classes"]) == 1
        
        calc_class = result["classes"][0]
        assert calc_class["name"] == "Calculator"
        assert calc_class["docstring"] == "A calculator class."
        assert len(calc_class["methods"]) == 4
        
        # Check method details
        method_names = [m["name"] for m in calc_class["methods"]]
        assert "__init__" in method_names
        assert "current_value" in method_names
        assert "add_numbers" in method_names
        assert "from_string" in method_names
        
        # Check method with decorators
        static_method = next(m for m in calc_class["methods"] if m["name"] == "add_numbers")
        assert "staticmethod" in static_method["decorators"]
        
        class_method = next(m for m in calc_class["methods"] if m["name"] == "from_string")
        assert "classmethod" in class_method["decorators"]
    
    def test_parse_file_with_inheritance(self, tmp_path):
        """Test parsing file with class inheritance."""
        test_file = tmp_path / "inheritance.py"
        test_content = dedent('''
        class Animal:
            """Base animal class."""
            pass
            
        class Dog(Animal):
            """Dog class inheriting from Animal."""
            
            def bark(self):
                return "Woof!"
                
        class GermanShepherd(Dog, object):
            """German Shepherd inheriting from Dog and object."""
            
            def guard(self):
                return "Protecting!"
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert len(result["classes"]) == 3
        
        # Check base classes
        dog_class = next(c for c in result["classes"] if c["name"] == "Dog")
        assert dog_class["bases"] == ["Animal"]
        
        german_shepherd = next(c for c in result["classes"] if c["name"] == "GermanShepherd") 
        assert "Dog" in german_shepherd["bases"]
        assert "object" in german_shepherd["bases"]
    
    def test_parse_file_with_imports(self, tmp_path):
        """Test parsing file with various import statements."""
        test_file = tmp_path / "imports.py"
        test_content = dedent('''
        import os
        import sys
        from pathlib import Path
        from typing import List, Dict
        from . import relative_module
        from ..parent import parent_module
        
        def use_imports():
            pass
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert len(result["imports"]) >= 6
        
        imports = result["imports"]
        assert "os" in imports
        assert "sys" in imports
        assert "from pathlib import Path" in imports
        assert "from typing import List" in imports
        assert "from typing import Dict" in imports
    
    def test_parse_file_with_decorators(self, tmp_path):
        """Test parsing file with decorated functions and classes."""
        test_file = tmp_path / "decorators.py"
        test_content = dedent('''
        from functools import wraps
        
        def my_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        
        @my_decorator
        @staticmethod
        def decorated_function():
            """A decorated function."""
            return "decorated"
            
        @property
        class DecoratedClass:
            """A decorated class."""
            pass
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        
        # Check function decorators
        decorated_func = next(f for f in result["functions"] if f["name"] == "decorated_function")
        assert "my_decorator" in decorated_func["decorators"]
        assert "staticmethod" in decorated_func["decorators"]
        
        # Check class decorators  
        decorated_class = next(c for c in result["classes"] if c["name"] == "DecoratedClass")
        assert "property" in decorated_class["decorators"]
    
    def test_parse_empty_file(self, tmp_path):
        """Test parsing an empty Python file."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert result["name"] == "empty"
        assert result["docstring"] is None
        assert len(result["classes"]) == 0
        assert len(result["functions"]) == 0
        assert len(result["imports"]) == 0
    
    def test_parse_file_with_module_docstring_only(self, tmp_path):
        """Test parsing file with only module docstring."""
        test_file = tmp_path / "docstring_only.py"
        test_content = '''"""This module only has a docstring."""'''
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert result["docstring"] == "This module only has a docstring."
        assert len(result["classes"]) == 0
        assert len(result["functions"]) == 0
    
    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        result = parse_code_file("/nonexistent/file.py")
        assert result is None
    
    def test_parse_invalid_python_syntax(self, tmp_path):
        """Test parsing file with invalid Python syntax."""
        test_file = tmp_path / "invalid.py"
        test_content = '''
        def broken_function(
            # Missing closing parenthesis and colon
        '''
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        assert result is None
    
    def test_parse_binary_file(self, tmp_path):
        """Test parsing a binary file."""
        test_file = tmp_path / "binary.py"
        # Write some binary data
        test_file.write_bytes(b'\x00\x01\x02\x03')
        
        result = parse_code_file(str(test_file))
        assert result is None
    
    def test_parse_file_with_complex_expressions(self, tmp_path):
        """Test parsing file with complex expressions and edge cases."""
        test_file = tmp_path / "complex.py"
        test_content = dedent('''
        """Module with complex expressions."""
        
        # Constants at module level
        VERSION = "1.0.0"
        DEBUG = True
        
        class ComplexClass(dict, metaclass=type):
            """Class with complex inheritance and metaclass."""
            
            @property
            @lru_cache(maxsize=128)
            def complex_property(self):
                """Property with multiple decorators."""
                return self._value
            
            def method_with_complex_args(self, pos_arg, *args, **kwargs):
                """Method with complex argument signature."""
                return locals()
        
        def function_with_defaults(a=1, b="default", c=[]):
            """Function with default arguments."""
            return a, b, c
        
        async def async_function():
            """An async function."""
            await something()
        
        def generator_function():
            """A generator function."""
            yield 1
            yield 2
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file))
        
        assert result is not None
        assert result["docstring"] == "Module with complex expressions."
        
        # Check complex class
        complex_class = result["classes"][0]
        assert complex_class["name"] == "ComplexClass"
        assert "dict" in complex_class["bases"]
        
        # Check function names
        func_names = [f["name"] for f in result["functions"]]
        assert "function_with_defaults" in func_names
        assert "async_function" in func_names
        assert "generator_function" in func_names


class TestGetNameFromNode:
    """Test cases for _get_name_from_node helper function."""
    
    def test_name_node(self):
        """Test extracting name from Name node."""
        node = ast.Name(id="test_name")
        result = _get_name_from_node(node)
        assert result == "test_name"
    
    def test_attribute_node(self):
        """Test extracting name from Attribute node."""
        # Create ast.Attribute for "module.attribute"
        value_node = ast.Name(id="module")
        node = ast.Attribute(value=value_node, attr="attribute")
        result = _get_name_from_node(node)
        assert result == "module.attribute"
    
    def test_nested_attribute_node(self):
        """Test extracting name from nested Attribute node."""
        # Create ast.Attribute for "package.module.attribute"
        package_node = ast.Name(id="package")
        module_node = ast.Attribute(value=package_node, attr="module")
        attribute_node = ast.Attribute(value=module_node, attr="attribute")
        
        result = _get_name_from_node(attribute_node)
        assert result == "package.module.attribute"
    
    def test_constant_node(self):
        """Test extracting name from Constant node."""
        node = ast.Constant(value="string_constant")
        result = _get_name_from_node(node)
        assert result == "string_constant"
        
        node = ast.Constant(value=42)
        result = _get_name_from_node(node)
        assert result == "42"
    
    def test_unknown_node_type(self):
        """Test extracting name from unknown node type."""
        # Use a List node which isn't handled specifically
        node = ast.List(elts=[], ctx=ast.Load())
        result = _get_name_from_node(node)
        # Should return string representation
        assert isinstance(result, str)
        assert "List" in result


class TestCodeParserIntegration:
    """Integration tests for the code parser."""
    
    def test_parse_real_world_module(self, tmp_path):
        """Test parsing a realistic Python module."""
        test_file = tmp_path / "real_world.py"
        test_content = dedent('''
        #!/usr/bin/env python3
        """
        A real-world Python module example.
        
        This module demonstrates common Python patterns and structures
        that the parser should handle correctly.
        """
        
        import os
        import sys
        from typing import Optional, List, Dict, Any
        from pathlib import Path
        from dataclasses import dataclass
        
        __version__ = "1.0.0"
        __author__ = "Test Author"
        
        # Module-level constants
        DEFAULT_CONFIG = {
            "debug": False,
            "max_retries": 3
        }
        
        @dataclass
        class Configuration:
            """Configuration data class."""
            debug: bool = False
            max_retries: int = 3
            output_path: Optional[Path] = None
            
            def validate(self) -> bool:
                """Validate configuration settings."""
                return self.max_retries > 0
        
        class BaseProcessor:
            """Base class for all processors."""
            
            def __init__(self, config: Configuration):
                """Initialize with configuration."""
                self.config = config
                self._state = "initialized"
            
            @property
            def is_ready(self) -> bool:
                """Check if processor is ready."""
                return self._state == "ready"
            
            @abstractmethod
            def process(self, data: Any) -> Any:
                """Process data - must be implemented by subclasses."""
                raise NotImplementedError
            
            @classmethod
            def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseProcessor':
                """Create processor from dictionary."""
                config = Configuration(**config_dict)
                return cls(config)
        
        class FileProcessor(BaseProcessor):
            """Processor for file operations."""
            
            def __init__(self, config: Configuration, file_patterns: List[str] = None):
                """Initialize file processor."""
                super().__init__(config)
                self.file_patterns = file_patterns or ["*.py"]
            
            def process(self, file_path: Path) -> Dict[str, Any]:
                """Process a single file."""
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                return {
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "processed": True
                }
            
            async def process_async(self, file_path: Path) -> Dict[str, Any]:
                """Asynchronously process a file."""
                return await self._async_process_impl(file_path)
            
            def _async_process_impl(self, file_path: Path) -> Dict[str, Any]:
                """Implementation detail for async processing."""
                return self.process(file_path)
        
        def main(args: Optional[List[str]] = None) -> int:
            """Main entry point."""
            if args is None:
                args = sys.argv[1:]
            
            config = Configuration(debug="--debug" in args)
            processor = FileProcessor(config)
            
            try:
                # Process files
                for arg in args:
                    if not arg.startswith("--"):
                        result = processor.process(Path(arg))
                        print(f"Processed: {result}")
                return 0
            except Exception as e:
                print(f"Error: {e}")
                return 1
        
        if __name__ == "__main__":
            sys.exit(main())
        ''').strip()
        
        test_file.write_text(test_content)
        
        result = parse_code_file(str(test_file), extract_full_code=True)
        
        # Comprehensive validation
        assert result is not None
        assert result["name"] == "real_world"
        assert "A real-world Python module example." in result["docstring"]
        assert "source_code" in result
        
        # Check imports
        imports = result["imports"]
        assert "os" in imports
        assert "sys" in imports
        assert any("from typing import" in imp for imp in imports)
        
        # Check classes
        class_names = [c["name"] for c in result["classes"]]
        assert "Configuration" in class_names
        assert "BaseProcessor" in class_names
        assert "FileProcessor" in class_names
        
        # Check inheritance
        file_processor = next(c for c in result["classes"] if c["name"] == "FileProcessor")
        assert "BaseProcessor" in file_processor["bases"]
        
        # Check decorators
        config_class = next(c for c in result["classes"] if c["name"] == "Configuration")
        assert "dataclass" in config_class["decorators"]
        
        # Check functions
        func_names = [f["name"] for f in result["functions"]]
        assert "main" in func_names
        
        # Verify methods are captured
        base_processor = next(c for c in result["classes"] if c["name"] == "BaseProcessor")
        method_names = [m["name"] for m in base_processor["methods"]]
        assert "__init__" in method_names
        assert "is_ready" in method_names
        assert "process" in method_names
        assert "from_dict" in method_names
