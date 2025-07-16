# src/parsing/ast_parser.py

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple


class ASTParser:
    """
    Enhanced AST parser that extracts structural information and comments
    from Python source files.
    """
    
    def __init__(self):
        self.current_file = None
        self.source_lines = []
    
    def parse_python_file(self, filepath: str) -> Dict[str, Any]:
        """
        Parses a Python file and extracts comprehensive structural information
        including function comments, docstrings, and inline comments.
        
        Args:
            filepath: Path to the Python file to parse.
        
        Returns:
            A dictionary containing parsed information including docstrings,
            imports, functions, classes, comments, and other metadata.
        """
        self.current_file = filepath
        result = {
            'filepath': filepath,
            'module_docstring': None,
            'imports': [],
            'functions': [],
            'classes': [],
            'constants': [],
            'function_comments': [],
            'class_comments': [],
            'errors': []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Store source lines for comment extraction
            self.source_lines = content.split('\n')
            
            tree = ast.parse(content, filename=filepath)
            
            # Extract module-level docstring
            result['module_docstring'] = ast.get_docstring(tree)
            
            # Extract imports
            result['imports'] = self.get_imports(tree)
            
            # Extract functions and classes with enhanced comment parsing
            functions_classes = self.extract_functions_classes_with_comments(tree)
            result['functions'] = functions_classes['functions']
            result['classes'] = functions_classes['classes']
            result['function_comments'] = functions_classes['function_comments']
            result['class_comments'] = functions_classes['class_comments']
            
            # Extract constants (module-level assignments)
            result['constants'] = self._extract_constants(tree)
            
        except FileNotFoundError:
            result['errors'].append(f"File not found: {filepath}")
        except SyntaxError as e:
            result['errors'].append(f"Syntax error in {filepath}: {e}")
        except UnicodeDecodeError:
            result['errors'].append(f"Encoding error in {filepath}")
        except Exception as e:
            result['errors'].append(f"Unexpected error parsing {filepath}: {e}")
        
        return result
    
    def extract_functions_classes_with_comments(self, ast_node: ast.AST) -> Dict[str, List[Dict[str, Any]]]:
        """
        Enhanced extraction of functions and classes with comprehensive comment parsing.
        
        Args:
            ast_node: The AST node to extract from.
        
        Returns:
            A dictionary with functions, classes, and their associated comments.
        """
        functions = []
        classes = []
        function_comments = []
        class_comments = []
        
        for node in ast.walk(ast_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_info = self._extract_function_info_with_comments(node)
                functions.append(function_info['function'])
                if function_info['comments']:
                    function_comments.append(function_info['comments'])
            
            elif isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info_with_comments(node)
                classes.append(class_info['class'])
                if class_info['comments']:
                    class_comments.append(class_info['comments'])
        
        return {
            'functions': functions,
            'classes': classes,
            'function_comments': function_comments,
            'class_comments': class_comments
        }
    
    def _extract_function_info_with_comments(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Dict[str, Any]:
        """
        Extracts detailed information from a function definition including all comments.
        
        Args:
            node: The function definition AST node.
        
        Returns:
            A dictionary containing function information and comments.
        """
        function_info = {
            'name': node.name,
            'type': 'async_function' if isinstance(node, ast.AsyncFunctionDef) else 'function',
            'docstring': ast.get_docstring(node),
            'arguments': self._extract_function_args(node),
            'decorators': [self._get_decorator_name(decorator) for decorator in node.decorator_list],
            'returns': self._get_return_annotation(node),
            'line_number': node.lineno,
            'end_line_number': getattr(node, 'end_lineno', node.lineno),
            'is_private': node.name.startswith('_'),
            'is_dunder': node.name.startswith('__') and node.name.endswith('__')
        }
        
        # Extract comments associated with this function
        comments_info = self._extract_function_comments(node)
        
        return {
            'function': function_info,
            'comments': comments_info
        }
    
    def _extract_class_info_with_comments(self, node: ast.ClassDef) -> Dict[str, Any]:
        """
        Extracts detailed information from a class definition including all comments.
        
        Args:
            node: The class definition AST node.
        
        Returns:
            A dictionary containing class information and comments.
        """
        methods = []
        attributes = []
        
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info_with_comments(child)
                method_data = method_info['function']
                method_data['is_method'] = True
                method_data['is_static'] = any(d.id == 'staticmethod' if isinstance(d, ast.Name) else False 
                                             for d in child.decorator_list)
                method_data['is_class_method'] = any(d.id == 'classmethod' if isinstance(d, ast.Name) else False 
                                                   for d in child.decorator_list)
                methods.append(method_data)
            
            elif isinstance(child, ast.Assign):
                # Extract class attributes
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        attributes.append({
                            'name': target.id,
                            'line_number': child.lineno,
                            'is_private': target.id.startswith('_')
                        })
        
        class_info = {
            'name': node.name,
            'type': 'class',
            'docstring': ast.get_docstring(node),
            'bases': [self._get_base_class_name(base) for base in node.bases],
            'decorators': [self._get_decorator_name(decorator) for decorator in node.decorator_list],
            'methods': methods,
            'attributes': attributes,
            'line_number': node.lineno,
            'end_line_number': getattr(node, 'end_lineno', node.lineno),
            'is_private': node.name.startswith('_')
        }
        
        # Extract comments associated with this class
        comments_info = self._extract_class_comments(node)
        
        return {
            'class': class_info,
            'comments': comments_info
        }
    
    def _extract_function_comments(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Dict[str, Any]:
        """
        Extracts all types of comments associated with a function.
        
        Args:
            node: The function definition AST node.
        
        Returns:
            A dictionary containing various types of comments.
        """
        comments = {
            'function_name': node.name,
            'file_path': self.current_file,
            'line_number': node.lineno,
            'docstring': ast.get_docstring(node),
            'preceding_comments': [],
            'inline_comments': [],
            'body_comments': []
        }
        
        # Extract comments immediately before the function definition
        comments['preceding_comments'] = self._get_preceding_comments(node.lineno)
        
        # Extract inline comments in function signature
        if hasattr(node, 'end_lineno') and node.end_lineno:
            comments['inline_comments'] = self._get_inline_comments(node.lineno, node.end_lineno)
        
        # Extract comments within function body
        comments['body_comments'] = self._get_function_body_comments(node)
        
        return comments
    
    def _extract_class_comments(self, node: ast.ClassDef) -> Dict[str, Any]:
        """
        Extracts all types of comments associated with a class.
        
        Args:
            node: The class definition AST node.
        
        Returns:
            A dictionary containing various types of comments.
        """
        comments = {
            'class_name': node.name,
            'file_path': self.current_file,
            'line_number': node.lineno,
            'docstring': ast.get_docstring(node),
            'preceding_comments': [],
            'inline_comments': [],
            'body_comments': []
        }
        
        # Extract comments immediately before the class definition
        comments['preceding_comments'] = self._get_preceding_comments(node.lineno)
        
        # Extract inline comments in class signature
        if hasattr(node, 'end_lineno') and node.end_lineno:
            comments['inline_comments'] = self._get_inline_comments(node.lineno, node.end_lineno)
        
        # Extract comments within class body (excluding method comments)
        comments['body_comments'] = self._get_class_body_comments(node)
        
        return comments
    
    def _get_preceding_comments(self, line_number: int, max_lines: int = 10) -> List[str]:
        """
        Gets comments immediately preceding a function or class definition.
        
        Args:
            line_number: The line number of the function/class definition.
            max_lines: Maximum number of lines to look back.
        
        Returns:
            A list of comment lines found before the definition.
        """
        comments = []
        start_line = max(0, line_number - max_lines - 1)
        end_line = line_number - 1
        
        # Look backwards from the function/class definition
        for i in range(end_line - 1, start_line - 1, -1):
            if i < len(self.source_lines):
                line = self.source_lines[i].strip()
                if line.startswith('#'):
                    comments.insert(0, line)
                elif line and not line.isspace():
                    # Stop at first non-comment, non-empty line
                    break
        
        return comments
    
    def _get_inline_comments(self, start_line: int, end_line: int) -> List[str]:
        """
        Gets inline comments within a range of lines.
        
        Args:
            start_line: Starting line number.
            end_line: Ending line number.
        
        Returns:
            A list of inline comments found in the range.
        """
        comments = []
        
        for line_num in range(start_line - 1, min(end_line, len(self.source_lines))):
            line = self.source_lines[line_num]
            
            # Look for inline comments (# after code)
            if '#' in line:
                # Simple heuristic: find # that's not in a string
                comment_pos = line.find('#')
                # Check if it's not inside quotes (basic check)
                before_comment = line[:comment_pos]
                quote_count = before_comment.count('"') + before_comment.count("'")
                
                if quote_count % 2 == 0:  # Even number of quotes before #
                    comment = line[comment_pos:].strip()
                    if comment:
                        comments.append(f"Line {line_num + 1}: {comment}")
        
        return comments
    
    def _get_function_body_comments(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> List[str]:
        """
        Gets comments within a function body.
        
        Args:
            node: The function definition AST node.
        
        Returns:
            A list of comments found in the function body.
        """
        comments = []
        
        if not hasattr(node, 'end_lineno') or not node.end_lineno:
            return comments
        
        start_line = node.lineno
        end_line = node.end_lineno
        
        for line_num in range(start_line, min(end_line + 1, len(self.source_lines))):
            line = self.source_lines[line_num].strip()
            
            # Look for comment-only lines within function body
            if line.startswith('#'):
                comments.append(f"Line {line_num + 1}: {line}")
        
        return comments
    
    def _get_class_body_comments(self, node: ast.ClassDef) -> List[str]:
        """
        Gets comments within a class body (excluding method comments).
        
        Args:
            node: The class definition AST node.
        
        Returns:
            A list of comments found in the class body.
        """
        comments = []
        
        if not hasattr(node, 'end_lineno') or not node.end_lineno:
            return comments
        
        start_line = node.lineno
        end_line = node.end_lineno
        
        # Get line numbers of methods to exclude their comments
        method_lines = set()
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_start = child.lineno
                method_end = getattr(child, 'end_lineno', child.lineno)
                method_lines.update(range(method_start, method_end + 1))
        
        for line_num in range(start_line, min(end_line + 1, len(self.source_lines))):
            if line_num not in method_lines:  # Skip method lines
                line = self.source_lines[line_num].strip()
                
                # Look for comment-only lines within class body
                if line.startswith('#'):
                    comments.append(f"Line {line_num + 1}: {line}")
        
        return comments

    # Keep existing helper methods
    def get_imports(self, ast_node: ast.AST) -> List[Dict[str, Any]]:
        """Extract import statements from an AST node."""
        imports = []
        
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'level': 0
                    })
            
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ''
                level = node.level
                
                for alias in node.names:
                    imports.append({
                        'type': 'from_import',
                        'module': module_name,
                        'name': alias.name,
                        'alias': alias.asname,
                        'level': level
                    })
        
        return imports

    def _extract_function_args(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> List[Dict[str, Any]]:
        """Extract function argument information."""
        args = []
        
        # Regular arguments
        for arg in node.args.args:
            args.append({
                'name': arg.arg,
                'type': 'regular',
                'annotation': self._get_annotation(arg.annotation),
                'default': None
            })
        
        # Handle defaults
        defaults = node.args.defaults
        if defaults:
            for i, default in enumerate(defaults):
                arg_index = len(node.args.args) - len(defaults) + i
                if arg_index < len(args):
                    args[arg_index]['default'] = self._get_default_value(default)
        
        # *args
        if node.args.vararg:
            args.append({
                'name': node.args.vararg.arg,
                'type': 'vararg',
                'annotation': self._get_annotation(node.args.vararg.annotation),
                'default': None
            })
        
        # **kwargs
        if node.args.kwarg:
            args.append({
                'name': node.args.kwarg.arg,
                'type': 'kwarg',
                'annotation': self._get_annotation(node.args.kwarg.annotation),
                'default': None
            })
        
        return args

    def _extract_constants(self, ast_node: ast.AST) -> List[Dict[str, Any]]:
        """Extract module-level constants."""
        constants = []
        
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper():
                            constants.append({
                                'name': target.id,
                                'value': self._get_constant_value(node.value),
                                'line_number': node.lineno
                            })
        
        return constants

    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get the name of a decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_attribute_name(decorator.value)}.{decorator.attr}"
        return str(decorator)

    def _get_base_class_name(self, base: ast.AST) -> str:
        """Get the name of a base class."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{self._get_attribute_name(base.value)}.{base.attr}"
        return str(base)

    def _get_attribute_name(self, node: ast.AST) -> str:
        """Get the name of an attribute node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return str(node)

    def _get_annotation(self, annotation: Optional[ast.AST]) -> Optional[str]:
        """Get string representation of type annotation."""
        if annotation is None:
            return None
        
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return f"{self._get_attribute_name(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        
        return str(annotation)

    def _get_return_annotation(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Optional[str]:
        """Get return type annotation."""
        return self._get_annotation(node.returns)

    def _get_default_value(self, node: ast.AST) -> str:
        """Get string representation of default value."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return str(node)

    def _get_constant_value(self, node: ast.AST) -> str:
        """Get string representation of constant value."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return str(node)
        return str(node)


# Keep existing standalone functions for backward compatibility
def extract_docstrings(ast_node: ast.AST) -> List[str]:
    """Extract all docstrings from an AST node."""
    docstrings = []
    
    for node in ast.walk(ast_node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            docstring = ast.get_docstring(node)
            if docstring:
                docstrings.append(docstring)
    
    return docstrings
