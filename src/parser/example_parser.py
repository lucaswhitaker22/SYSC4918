"""
Example parser for extracting code examples and usage patterns from Python projects.

This module extracts code examples from docstrings, example files, and usage patterns
throughout the codebase to help generate comprehensive README documentation.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

from models.project_data import CodeExample, ModuleInfo, ClassInfo, FunctionInfo
from utils.file_utils import read_file_safely, find_files_by_pattern

logger = logging.getLogger(__name__)


class ExampleParser:
    """Parser for extracting code examples and usage patterns."""
    
    def __init__(self):
        # Patterns for identifying examples
        self.example_patterns = {
            'doctest': re.compile(r'^\s*>>>\s+(.+)$', re.MULTILINE),
            'code_block': re.compile(r'``````', re.DOTALL),
            'example_section': re.compile(r'(?:Examples?|Usage):?\s*\n(.*?)(?=\n\s*(?:[A-Z][a-z]+:|\Z))', re.DOTALL | re.IGNORECASE),
            'import_statement': re.compile(r'(?:^|\n)((?:from\s+\w+(?:\.\w+)*\s+)?import\s+[^\n]+)', re.MULTILINE),
            'function_call': re.compile(r'(\w+)\s*\([^)]*\)', re.MULTILINE),
        }
        
        # Common example file patterns
        self.example_file_patterns = [
            'example*.py', 'examples*.py', 'demo*.py', 'sample*.py',
            'tutorial*.py', 'quickstart*.py', 'getting_started*.py'
        ]
        
        # Usage indicators
        self.usage_indicators = [
            'usage', 'how to', 'example', 'demo', 'sample', 'tutorial',
            'quickstart', 'getting started', 'basic usage', 'advanced usage'
        ]
    
    def extract_from_module(self, module: ModuleInfo) -> List[CodeExample]:
        """
        Extract code examples from a module.
        
        Args:
            module: ModuleInfo object to extract examples from
            
        Returns:
            List of CodeExample objects
        """
        examples = []
        
        try:
            # Extract from module docstring
            if module.docstring:
                module_examples = self._extract_from_docstring(
                    module.docstring, 
                    f"Module {module.name}",
                    module.file_path
                )
                examples.extend(module_examples)
            
            # Extract from classes
            for class_info in module.classes:
                class_examples = self._extract_from_class(class_info)
                examples.extend(class_examples)
            
            # Extract from functions
            for function_info in module.functions:
                function_examples = self._extract_from_function(function_info)
                examples.extend(function_examples)
            
            # Extract from source code
            source_examples = self._extract_from_source_file(module.file_path)
            examples.extend(source_examples)
            
        except Exception as e:
            logger.error(f"Error extracting examples from module {module.name}: {e}")
        
        return examples
    
    def extract_from_project(self, project_path: str) -> List[CodeExample]:
        """
        Extract code examples from an entire project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            List of CodeExample objects
        """
        examples = []
        
        try:
            project_path = Path(project_path)
            
            # Find example files
            example_files = self._find_example_files(project_path)
            
            # Extract from example files
            for file_path in example_files:
                file_examples = self._extract_from_example_file(file_path)
                examples.extend(file_examples)
            
            # Extract from README and documentation
            readme_examples = self._extract_from_readme(project_path)
            examples.extend(readme_examples)
            
            # Extract from test files (for usage patterns)
            test_examples = self._extract_from_test_files(project_path)
            examples.extend(test_examples)
            
        except Exception as e:
            logger.error(f"Error extracting examples from project: {e}")
        
        return examples
    
    def _extract_from_docstring(self, docstring: str, context: str, file_path: Optional[str] = None) -> List[CodeExample]:
        """Extract examples from a docstring."""
        examples = []
        
        # Extract doctests
        doctest_examples = self._extract_doctests(docstring, context, file_path)
        examples.extend(doctest_examples)
        
        # Extract code blocks
        code_block_examples = self._extract_code_blocks(docstring, context, file_path)
        examples.extend(code_block_examples)
        
        # Extract example sections
        example_sections = self._extract_example_sections(docstring, context, file_path)
        examples.extend(example_sections)
        
        return examples
    
    def _extract_from_class(self, class_info: ClassInfo) -> List[CodeExample]:
        """Extract examples from a class."""
        examples = []
        
        # Extract from class docstring
        if class_info.docstring:
            class_examples = self._extract_from_docstring(
                class_info.docstring,
                f"Class {class_info.name}",
                class_info.file_path
            )
            examples.extend(class_examples)
        
        # Extract from method docstrings
        for method in class_info.methods:
            if method.docstring:
                method_examples = self._extract_from_docstring(
                    method.docstring,
                    f"Method {class_info.name}.{method.name}",
                    method.file_path
                )
                examples.extend(method_examples)
        
        return examples
    
    def _extract_from_function(self, function_info: FunctionInfo) -> List[CodeExample]:
        """Extract examples from a function."""
        examples = []
        
        if function_info.docstring:
            function_examples = self._extract_from_docstring(
                function_info.docstring,
                f"Function {function_info.name}",
                function_info.file_path
            )
            examples.extend(function_examples)
        
        return examples
    
    def _extract_doctests(self, docstring: str, context: str, file_path: Optional[str] = None) -> List[CodeExample]:
        """Extract doctest examples from docstring."""
        examples = []
        
        # Find all doctest blocks
        doctest_blocks = []
        current_block = []
        
        for line in docstring.split('\n'):
            if re.match(r'^\s*>>>\s+', line):
                # Start of doctest line
                current_block.append(line.strip())
            elif re.match(r'^\s*\.\.\.\s+', line):
                # Continuation line
                current_block.append(line.strip())
            elif current_block and not line.strip():
                # Empty line, might be end of block
                continue
            elif current_block and not re.match(r'^\s*>>>', line):
                # Non-doctest line after doctest block
                if current_block:
                    doctest_blocks.append(current_block)
                    current_block = []
        
        # Add final block
        if current_block:
            doctest_blocks.append(current_block)
        
        # Convert blocks to examples
        for i, block in enumerate(doctest_blocks):
            if len(block) > 0:
                # Clean up doctest syntax
                code_lines = []
                for line in block:
                    if line.startswith('>>>'):
                        code_lines.append(line[3:].strip())
                    elif line.startswith('...'):
                        code_lines.append(line[3:].strip())
                
                code = '\n'.join(code_lines)
                
                example = CodeExample(
                    title=f"Doctest example from {context}",
                    code=code,
                    description=f"Doctest example {i+1}",
                    file_path=file_path,
                    example_type="doctest",
                    is_executable=True
                )
                examples.append(example)
        
        return examples
    
    def _extract_code_blocks(self, docstring: str, context: str, file_path: Optional[str] = None) -> List[CodeExample]:
        """Extract code blocks from docstring."""
        examples = []
        
        # Find code blocks
        code_blocks = self.example_patterns['code_block'].findall(docstring)
        
        for i, code_block in enumerate(code_blocks):
            code = code_block.strip()
            
            if code:
                example = CodeExample(
                    title=f"Code example from {context}",
                    code=code,
                    description=f"Code block {i+1}",
                    file_path=file_path,
                    example_type="code_block",
                    is_executable=self._is_executable_code(code)
                )
                examples.append(example)
        
        return examples
    
    def _extract_example_sections(self, docstring: str, context: str, file_path: Optional[str] = None) -> List[CodeExample]:
        """Extract example sections from docstring."""
        examples = []
        
        # Find example sections
        example_sections = self.example_patterns['example_section'].findall(docstring)
        
        for i, section in enumerate(example_sections):
            # Look for code within the section
            code_lines = []
            for line in section.split('\n'):
                line = line.strip()
                # Skip empty lines and common documentation patterns
                if line and not line.startswith(('Args:', 'Returns:', 'Raises:', 'Note:')):
                    # Check if line looks like code
                    if (line.startswith(('>>>', '...', 'import ', 'from ')) or
                        '(' in line or '=' in line or line.endswith(':')):
                        code_lines.append(line)
            
            if code_lines:
                code = '\n'.join(code_lines)
                
                example = CodeExample(
                    title=f"Example from {context}",
                    code=code,
                    description=f"Example section {i+1}",
                    file_path=file_path,
                    example_type="example_section",
                    is_executable=self._is_executable_code(code)
                )
                examples.append(example)
        
        return examples
    
    def _extract_from_source_file(self, file_path: str) -> List[CodeExample]:
        """Extract examples from source file by analyzing the code."""
        examples = []
        
        try:
            content = read_file_safely(file_path)
            if not content:
                return examples
            
            # Parse the file to find example patterns
            tree = ast.parse(content)
            
            # Look for if __name__ == "__main__": blocks
            main_examples = self._extract_main_block_examples(tree, file_path)
            examples.extend(main_examples)
            
            # Look for example functions
            example_functions = self._extract_example_functions(tree, file_path)
            examples.extend(example_functions)
            
        except Exception as e:
            logger.error(f"Error extracting examples from source file {file_path}: {e}")
        
        return examples
    
    def _extract_main_block_examples(self, tree: ast.AST, file_path: str) -> List[CodeExample]:
        """Extract examples from if __name__ == "__main__": blocks."""
        examples = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if this is a main block
                if self._is_main_block(node):
                    # Extract code from the main block
                    code_lines = []
                    for stmt in node.body:
                        try:
                            code_lines.append(ast.unparse(stmt))
                        except Exception:
                            pass
                    
                    if code_lines:
                        code = '\n'.join(code_lines)
                        
                        example = CodeExample(
                            title=f"Main block example from {Path(file_path).name}",
                            code=code,
                            description="Example usage from main block",
                            file_path=file_path,
                            line_number=node.lineno,
                            example_type="main_block",
                            is_executable=True
                        )
                        examples.append(example)
        
        return examples
    
    def _extract_example_functions(self, tree: ast.AST, file_path: str) -> List[CodeExample]:
        """Extract example functions."""
        examples = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function name suggests it's an example
                if any(indicator in node.name.lower() for indicator in self.usage_indicators):
                    # Extract function body
                    code_lines = []
                    for stmt in node.body:
                        try:
                            code_lines.append(ast.unparse(stmt))
                        except Exception:
                            pass
                    
                    if code_lines:
                        code = '\n'.join(code_lines)
                        
                        example = CodeExample(
                            title=f"Example function: {node.name}",
                            code=code,
                            description=f"Usage example from function {node.name}",
                            file_path=file_path,
                            line_number=node.lineno,
                            example_type="example_function",
                            is_executable=True
                        )
                        examples.append(example)
        
        return examples
    
    def _find_example_files(self, project_path: Path) -> List[str]:
        """Find example files in the project."""
        example_files = []
        
        # Common example directories
        example_dirs = ['examples', 'example', 'demos', 'demo', 'samples', 'sample']
        
        for dir_name in example_dirs:
            example_dir = project_path / dir_name
            if example_dir.exists():
                for pattern in self.example_file_patterns:
                    files = find_files_by_pattern(str(example_dir), pattern)
                    example_files.extend(files)
        
        # Also check root directory
        for pattern in self.example_file_patterns:
            files = find_files_by_pattern(str(project_path), pattern, recursive=False)
            example_files.extend(files)
        
        return example_files
    
    def _extract_from_example_file(self, file_path: str) -> List[CodeExample]:
        """Extract examples from example files."""
        examples = []
        
        try:
            content = read_file_safely(file_path)
            if not content:
                return examples
            
            # Parse the file
            tree = ast.parse(content)
            
            # Extract module docstring
            module_docstring = ast.get_docstring(tree)
            if module_docstring:
                docstring_examples = self._extract_from_docstring(
                    module_docstring,
                    f"Example file {Path(file_path).name}",
                    file_path
                )
                examples.extend(docstring_examples)
            
            # Extract main content as example
            example = CodeExample(
                title=f"Example: {Path(file_path).stem}",
                code=content,
                description=f"Complete example from {Path(file_path).name}",
                file_path=file_path,
                example_type="example_file",
                is_executable=True
            )
            examples.append(example)
            
        except Exception as e:
            logger.error(f"Error extracting from example file {file_path}: {e}")
        
        return examples
    
    def _extract_from_readme(self, project_path: Path) -> List[CodeExample]:
        """Extract examples from README files."""
        examples = []
        
        # Look for README files
        readme_patterns = ['README.md', 'README.rst', 'README.txt', 'readme.md', 'readme.rst']
        
        for pattern in readme_patterns:
            readme_file = project_path / pattern
            if readme_file.exists():
                try:
                    content = read_file_safely(str(readme_file))
                    if content:
                        # Extract code blocks
                        code_blocks = self.example_patterns['code_block'].findall(content)
                        
                        for i, code_block in enumerate(code_blocks):
                            code = code_block.strip()
                            if code and ('import ' in code or 'from ' in code):
                                example = CodeExample(
                                    title=f"README example {i+1}",
                                    code=code,
                                    description=f"Usage example from README",
                                    file_path=str(readme_file),
                                    example_type="readme",
                                    is_executable=self._is_executable_code(code)
                                )
                                examples.append(example)
                
                except Exception as e:
                    logger.error(f"Error extracting from README {readme_file}: {e}")
        
        return examples
    
    def _extract_from_test_files(self, project_path: Path) -> List[CodeExample]:
        """Extract usage patterns from test files."""
        examples = []
        
        # Find test files
        test_patterns = ['test_*.py', '*_test.py']
        test_dirs = ['tests', 'test']
        
        for test_dir in test_dirs:
            test_directory = project_path / test_dir
            if test_directory.exists():
                for pattern in test_patterns:
                    test_files = find_files_by_pattern(str(test_directory), pattern)
                    
                    for test_file in test_files[:5]:  # Limit to 5 test files
                        try:
                            file_examples = self._extract_usage_from_test_file(test_file)
                            examples.extend(file_examples)
                        except Exception as e:
                            logger.error(f"Error extracting from test file {test_file}: {e}")
        
        return examples
    
    def _extract_usage_from_test_file(self, test_file: str) -> List[CodeExample]:
        """Extract usage patterns from a test file."""
        examples = []
        
        try:
            content = read_file_safely(test_file)
            if not content:
                return examples
            
            tree = ast.parse(content)
            
            # Look for test functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    # Extract simple usage patterns
                    code_lines = []
                    for stmt in node.body:
                        # Look for simple statements that show usage
                        if isinstance(stmt, ast.Expr) or isinstance(stmt, ast.Assign):
                            try:
                                line = ast.unparse(stmt)
                                if any(pattern in line for pattern in ['assert', '=', '(']):
                                    code_lines.append(line)
                            except Exception:
                                pass
                    
                    if code_lines and len(code_lines) <= 5:  # Keep it simple
                        code = '\n'.join(code_lines)
                        
                        example = CodeExample(
                            title=f"Test usage: {node.name}",
                            code=code,
                            description=f"Usage pattern from test {node.name}",
                            file_path=test_file,
                            line_number=node.lineno,
                            example_type="test_usage",
                            is_executable=False
                        )
                        examples.append(example)
        
        except Exception as e:
            logger.error(f"Error parsing test file {test_file}: {e}")
        
        return examples
    
    def _is_main_block(self, node: ast.If) -> bool:
        """Check if an if statement is a main block."""
        try:
            # Check if condition is __name__ == "__main__"
            if isinstance(node.test, ast.Compare):
                left = node.test.left
                comparators = node.test.comparators
                
                if (isinstance(left, ast.Name) and left.id == '__name__' and
                    len(comparators) == 1 and isinstance(comparators[0], ast.Constant) and
                    comparators[0].value == '__main__'):
                    return True
        except Exception:
            pass
        
        return False
    
    def _is_executable_code(self, code: str) -> bool:
        """Check if code is likely executable."""
        # Simple heuristics to determine if code is executable
        indicators = [
            'import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ',
            'try:', 'with ', 'assert ', 'return ', 'yield ', 'print('
        ]
        
        return any(indicator in code for indicator in indicators)


# Convenience functions
def extract_code_examples(module: ModuleInfo) -> List[CodeExample]:
    """
    Extract code examples from a module.
    
    Args:
        module: ModuleInfo object to extract examples from
        
    Returns:
        List of CodeExample objects
    """
    parser = ExampleParser()
    return parser.extract_from_module(module)


def parse_docstring_examples(docstring: str, context: str = "Unknown") -> List[CodeExample]:
    """
    Parse code examples from a docstring.
    
    Args:
        docstring: Docstring text to parse
        context: Context description for the examples
        
    Returns:
        List of CodeExample objects
    """
    parser = ExampleParser()
    return parser._extract_from_docstring(docstring, context)


def find_usage_patterns(project_path: str) -> List[CodeExample]:
    """
    Find usage patterns in a Python project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        List of CodeExample objects
    """
    parser = ExampleParser()
    return parser.extract_from_project(project_path)
