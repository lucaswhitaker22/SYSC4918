"""
Code parser for extracting classes, functions, and methods from Python files using AST.

This module provides comprehensive AST-based parsing to extract detailed information
about Python code structures including classes, functions, methods, decorators,
type hints, and docstrings.
"""

import ast
import re
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

from models.project_data import (
    ClassInfo, FunctionInfo, ModuleInfo, CodeExample
)
from utils.file_utils import read_file_safely

logger = logging.getLogger(__name__)


class CodeParsingError(Exception):
    """Custom exception for code parsing errors."""
    pass


class ASTVisitor(ast.NodeVisitor):
    """Custom AST visitor for extracting code information."""
    
    def __init__(self, file_path: str, include_private: bool = False):
        self.file_path = file_path
        self.include_private = include_private
        self.classes = []
        self.functions = []
        self.constants = []
        self.imports = []
        self.module_docstring = None
        self.current_class = None
        self.current_function_level = 0
        
    def visit_Module(self, node: ast.Module) -> None:
        """Visit module node to extract module-level docstring."""
        self.module_docstring = ast.get_docstring(node)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition node."""
        # Skip private classes unless explicitly included
        if not self.include_private and node.name.startswith('_'):
            return
            
        class_info = ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node),
            line_number=node.lineno,
            file_path=self.file_path
        )
        
        # Extract inheritance
        class_info.inheritance = self._extract_inheritance(node)
        
        # Extract decorators
        class_info.decorators = self._extract_decorators(node)
        
        # Check for special class types
        class_info.is_abstract = self._is_abstract_class(node)
        class_info.is_dataclass = self._is_dataclass(node)
        class_info.is_enum = self._is_enum_class(node)
        
        # Extract class attributes
        class_info.attributes = self._extract_class_attributes(node)
        
        # Process methods
        previous_class = self.current_class
        self.current_class = class_info
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_function_info(item, is_method=True)
                if method_info:
                    if method_info.is_property:
                        class_info.properties.append(method_info)
                    else:
                        class_info.methods.append(method_info)
        
        self.current_class = previous_class
        self.classes.append(class_info)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition node."""
        # Skip if we're inside a class (handled by visit_ClassDef)
        if self.current_class is not None:
            return
            
        # Skip private functions unless explicitly included
        if not self.include_private and node.name.startswith('_'):
            return
            
        function_info = self._extract_function_info(node, is_method=False)
        if function_info:
            self.functions.append(function_info)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition node."""
        # Skip if we're inside a class
        if self.current_class is not None:
            return
            
        # Skip private functions unless explicitly included
        if not self.include_private and node.name.startswith('_'):
            return
            
        function_info = self._extract_function_info(node, is_method=False, is_async=True)
        if function_info:
            self.functions.append(function_info)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment node to extract constants."""
        # Extract module-level constants
        if self.current_class is None and self.current_function_level == 0:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if it's a constant (all uppercase)
                    if target.id.isupper():
                        constant_info = {
                            'name': target.id,
                            'value': self._extract_value(node.value),
                            'type': self._infer_type(node.value),
                            'line_number': node.lineno
                        }
                        self.constants.append(constant_info)
        
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import node."""
        for alias in node.names:
            import_name = alias.asname if alias.asname else alias.name
            self.imports.append(import_name)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit import from node."""
        module = node.module or ''
        for alias in node.names:
            if alias.name == '*':
                self.imports.append(f"from {module} import *")
            else:
                import_name = alias.asname if alias.asname else alias.name
                self.imports.append(f"from {module} import {import_name}")
    
    def _extract_function_info(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], 
                             is_method: bool = False, is_async: bool = False) -> Optional[FunctionInfo]:
        """Extract detailed function information from AST node."""
        try:
            function_info = FunctionInfo(
                name=node.name,
                signature=self._extract_signature(node),
                docstring=ast.get_docstring(node),
                is_public=not node.name.startswith('_'),
                is_async=is_async or isinstance(node, ast.AsyncFunctionDef),
                line_number=node.lineno,
                file_path=self.file_path
            )
            
            # Extract decorators
            function_info.decorators = self._extract_decorators(node)
            
            # Check for special method types
            function_info.is_property = '@property' in function_info.decorators
            function_info.is_classmethod = '@classmethod' in function_info.decorators
            function_info.is_staticmethod = '@staticmethod' in function_info.decorators
            
            # Extract return type
            if hasattr(node, 'returns') and node.returns:
                function_info.return_type = ast.unparse(node.returns)
            
            # Extract parameters
            function_info.parameters = self._extract_parameters(node)
            
            # Calculate complexity score
            function_info.complexity_score = self._calculate_complexity(node)
            
            return function_info
            
        except Exception as e:
            logger.error(f"Error extracting function info for {node.name}: {e}")
            return None
    
    def _extract_signature(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Extract function signature as string."""
        try:
            # Build signature manually for better control
            parts = []
            
            # Add async keyword if needed
            if isinstance(node, ast.AsyncFunctionDef):
                parts.append('async')
            
            parts.append('def')
            parts.append(node.name)
            
            # Build arguments
            args_parts = []
            
            # Positional-only arguments
            if hasattr(node.args, 'posonlyargs'):
                for arg in node.args.posonlyargs:
                    arg_str = self._format_arg(arg)
                    args_parts.append(arg_str)
                if node.args.posonlyargs:
                    args_parts.append('/')
            
            # Regular arguments
            defaults = node.args.defaults
            num_defaults = len(defaults)
            num_args = len(node.args.args)
            
            for i, arg in enumerate(node.args.args):
                arg_str = self._format_arg(arg)
                
                # Add default if available
                default_index = i - (num_args - num_defaults)
                if default_index >= 0:
                    default_val = ast.unparse(defaults[default_index])
                    arg_str += f"={default_val}"
                
                args_parts.append(arg_str)
            
            # Varargs
            if node.args.vararg:
                args_parts.append(f"*{self._format_arg(node.args.vararg)}")
            
            # Keyword-only arguments
            if node.args.kwonlyargs:
                if not node.args.vararg:
                    args_parts.append('*')
                
                kw_defaults = node.args.kw_defaults
                for i, arg in enumerate(node.args.kwonlyargs):
                    arg_str = self._format_arg(arg)
                    if i < len(kw_defaults) and kw_defaults[i]:
                        default_val = ast.unparse(kw_defaults[i])
                        arg_str += f"={default_val}"
                    args_parts.append(arg_str)
            
            # Kwargs
            if node.args.kwarg:
                args_parts.append(f"**{self._format_arg(node.args.kwarg)}")
            
            signature = f"{' '.join(parts)}({', '.join(args_parts)})"
            
            # Add return type annotation
            if hasattr(node, 'returns') and node.returns:
                signature += f" -> {ast.unparse(node.returns)}"
            
            return signature
            
        except Exception as e:
            logger.error(f"Error extracting signature for {node.name}: {e}")
            return f"def {node.name}(...)"
    
    def _format_arg(self, arg: ast.arg) -> str:
        """Format argument with type annotation."""
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        return arg_str
    
    def _extract_parameters(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> List[Dict[str, Any]]:
        """Extract detailed parameter information."""
        parameters = []
        
        try:
            # Regular arguments
            defaults = node.args.defaults
            num_defaults = len(defaults)
            num_args = len(node.args.args)
            
            for i, arg in enumerate(node.args.args):
                param_info = {
                    'name': arg.arg,
                    'type': ast.unparse(arg.annotation) if arg.annotation else None,
                    'default': None,
                    'description': None
                }
                
                # Add default if available
                default_index = i - (num_args - num_defaults)
                if default_index >= 0:
                    param_info['default'] = ast.unparse(defaults[default_index])
                
                parameters.append(param_info)
            
            # Varargs
            if node.args.vararg:
                param_info = {
                    'name': f"*{node.args.vararg.arg}",
                    'type': ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None,
                    'default': None,
                    'description': None
                }
                parameters.append(param_info)
            
            # Keyword-only arguments
            kw_defaults = node.args.kw_defaults
            for i, arg in enumerate(node.args.kwonlyargs):
                param_info = {
                    'name': arg.arg,
                    'type': ast.unparse(arg.annotation) if arg.annotation else None,
                    'default': None,
                    'description': None
                }
                
                if i < len(kw_defaults) and kw_defaults[i]:
                    param_info['default'] = ast.unparse(kw_defaults[i])
                
                parameters.append(param_info)
            
            # Kwargs
            if node.args.kwarg:
                param_info = {
                    'name': f"**{node.args.kwarg.arg}",
                    'type': ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None,
                    'default': None,
                    'description': None
                }
                parameters.append(param_info)
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")
        
        return parameters
    
    def _extract_inheritance(self, node: ast.ClassDef) -> List[str]:
        """Extract class inheritance information."""
        inheritance = []
        for base in node.bases:
            try:
                inheritance.append(ast.unparse(base))
            except Exception:
                inheritance.append(str(base))
        return inheritance
    
    def _extract_decorators(self, node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]) -> List[str]:
        """Extract decorator information."""
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(f"@{ast.unparse(decorator)}")
            except Exception:
                decorators.append(f"@{str(decorator)}")
        return decorators
    
    def _is_abstract_class(self, node: ast.ClassDef) -> bool:
        """Check if class is abstract."""
        # Check for ABC inheritance
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ['ABC', 'ABCMeta']:
                return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ['ABC', 'ABCMeta']:
                    return True
        
        # Check for abstract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod':
                        return True
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == 'abstractmethod':
                        return True
        
        return False
    
    def _is_dataclass(self, node: ast.ClassDef) -> bool:
        """Check if class is a dataclass."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == 'dataclass':
                return True
            elif isinstance(decorator, ast.Attribute) and decorator.attr == 'dataclass':
                return True
        return False
    
    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """Check if class is an enum."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'Enum':
                return True
            elif isinstance(base, ast.Attribute) and base.attr == 'Enum':
                return True
        return False
    
    def _extract_class_attributes(self, node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract class attributes."""
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Type-annotated attribute
                attr_info = {
                    'name': item.target.id,
                    'type': ast.unparse(item.annotation) if item.annotation else None,
                    'description': None
                }
                attributes.append(attr_info)
            elif isinstance(item, ast.Assign):
                # Regular assignment
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attr_info = {
                            'name': target.id,
                            'type': None,
                            'description': None
                        }
                        attributes.append(attr_info)
        
        return attributes
    
    def _extract_value(self, node: ast.AST) -> Any:
        """Extract value from AST node."""
        try:
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Num):  # For older Python versions
                return node.n
            elif isinstance(node, ast.Str):  # For older Python versions
                return node.s
            elif isinstance(node, ast.NameConstant):  # For older Python versions
                return node.value
            else:
                return ast.unparse(node)
        except Exception:
            return None
    
    def _infer_type(self, node: ast.AST) -> Optional[str]:
        """Infer type from AST node."""
        try:
            if isinstance(node, ast.Constant):
                return type(node.value).__name__
            elif isinstance(node, ast.List):
                return 'list'
            elif isinstance(node, ast.Dict):
                return 'dict'
            elif isinstance(node, ast.Set):
                return 'set'
            elif isinstance(node, ast.Tuple):
                return 'tuple'
            else:
                return None
        except Exception:
            return None
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity


class CodeParser:
    """Main code parser for extracting information from Python files."""
    
    def __init__(self, include_private: bool = False):
        self.include_private = include_private
    
    def parse_file(self, file_path: str) -> ModuleInfo:
        """
        Parse a Python file and extract code information.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            ModuleInfo object with extracted information
        """
        try:
            content = read_file_safely(file_path)
            if not content:
                raise CodeParsingError(f"Could not read file: {file_path}")
            
            # Parse the file
            tree = ast.parse(content, filename=file_path)
            
            # Extract information using visitor
            visitor = ASTVisitor(file_path, self.include_private)
            visitor.visit(tree)
            
            # Create module info
            module_name = Path(file_path).stem
            module_info = ModuleInfo(
                name=module_name,
                file_path=file_path,
                docstring=visitor.module_docstring,
                classes=visitor.classes,
                functions=visitor.functions,
                constants=visitor.constants,
                imports=visitor.imports,
                is_package=module_name == '__init__',
                is_main=module_name == '__main__' or module_name == 'main',
                line_count=len(content.splitlines())
            )
            
            return module_info
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            raise CodeParsingError(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            raise CodeParsingError(f"Error parsing {file_path}: {e}")
    
    def parse_code_string(self, code: str, file_path: str = "<string>") -> ModuleInfo:
        """
        Parse Python code from string.
        
        Args:
            code: Python code as string
            file_path: Virtual file path for reference
            
        Returns:
            ModuleInfo object with extracted information
        """
        try:
            tree = ast.parse(code, filename=file_path)
            
            visitor = ASTVisitor(file_path, self.include_private)
            visitor.visit(tree)
            
            module_name = Path(file_path).stem
            module_info = ModuleInfo(
                name=module_name,
                file_path=file_path,
                docstring=visitor.module_docstring,
                classes=visitor.classes,
                functions=visitor.functions,
                constants=visitor.constants,
                imports=visitor.imports,
                line_count=len(code.splitlines())
            )
            
            return module_info
            
        except SyntaxError as e:
            logger.error(f"Syntax error in code: {e}")
            raise CodeParsingError(f"Syntax error in code: {e}")
        except Exception as e:
            logger.error(f"Error parsing code: {e}")
            raise CodeParsingError(f"Error parsing code: {e}")


# Convenience functions
def extract_code_information(file_path: str, include_private: bool = False) -> ModuleInfo:
    """
    Extract code information from a Python file.
    
    Args:
        file_path: Path to the Python file
        include_private: Whether to include private methods/classes
        
    Returns:
        ModuleInfo object with extracted information
    """
    parser = CodeParser(include_private=include_private)
    return parser.parse_file(file_path)


def parse_python_file(file_path: str) -> ModuleInfo:
    """
    Parse a Python file and return module information.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        ModuleInfo object
    """
    parser = CodeParser()
    return parser.parse_file(file_path)


def analyze_ast_node(node: ast.AST) -> Dict[str, Any]:
    """
    Analyze an AST node and return information about it.
    
    Args:
        node: AST node to analyze
        
    Returns:
        Dictionary with node information
    """
    return {
        'type': type(node).__name__,
        'line_number': getattr(node, 'lineno', None),
        'col_offset': getattr(node, 'col_offset', None),
        'fields': node._fields if hasattr(node, '_fields') else []
    }
