import ast
import re
from pathlib import Path
from typing import List, Dict, Any

def parse_examples(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract code examples from multiple sources:
    - Docstring examples (doctest format)
    - Code blocks in docstrings
    - Main guard blocks
    - Function/class usage patterns
    - Comments with example code
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return []
    
    examples = []
    
    # Extract from docstrings
    examples.extend(_extract_docstring_examples(tree, file_path, source))
    
    # Extract main guard examples
    examples.extend(_extract_main_guard_examples(tree, file_path, source))
    
    # Extract comment examples
    examples.extend(_extract_comment_examples(source, file_path))
    
    # Extract usage patterns
    examples.extend(_extract_usage_patterns(tree, file_path, source))
    
    return examples

def _extract_docstring_examples(tree: ast.AST, file_path: str, source: str) -> List[Dict[str, Any]]:
    """Extract examples from docstrings (doctests and code blocks)."""
    examples = []
    
    # Module docstring
    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        examples.extend(_parse_docstring_for_examples(module_docstring, file_path, "module"))
    
    # Walk through all nodes
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_docstring = ast.get_docstring(node)
            if class_docstring:
                examples.extend(_parse_docstring_for_examples(
                    class_docstring, file_path, f"class {node.name}"
                ))
        elif isinstance(node, ast.FunctionDef):
            func_docstring = ast.get_docstring(node)
            if func_docstring:
                examples.extend(_parse_docstring_for_examples(
                    func_docstring, file_path, f"function {node.name}"
                ))
    
    return examples

def _parse_docstring_for_examples(docstring: str, file_path: str, context: str) -> List[Dict[str, Any]]:
    """Parse a docstring for various types of examples."""
    examples = []
    
    if not docstring:
        return examples
    
    # 1. Doctest examples (>>> format)
    doctest_examples = _extract_doctest_examples(docstring)
    for example in doctest_examples:
        examples.append({
            "file": file_path,
            "context": context,
            "type": "doctest",
            "code": example,
            "language": "python"
        })
    
    # 2. Code blocks (markdown style)
    code_blocks = _extract_code_blocks(docstring)
    for block in code_blocks:
        examples.append({
            "file": file_path,
            "context": context,
            "type": "code_block",
            "code": block["code"],
            "language": block.get("language", "python")
        })
    
    # 3. Example sections
    example_sections = _extract_example_sections(docstring)
    for section in example_sections:
        examples.append({
            "file": file_path,
            "context": context,
            "type": "example_section",
            "code": section,
            "language": "python"
        })
    
    return examples

def _extract_doctest_examples(docstring: str) -> List[str]:
    """Extract doctest-style examples (>>> format)."""
    examples = []
    current_example = []
    
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.startswith(">>>"):
            current_example.append(stripped)
        elif stripped.startswith("...") and current_example:
            current_example.append(stripped)
        elif current_example and not stripped:
            # Empty line, might be end of example
            continue
        elif current_example:
            # Non-continuation line, end current example
            examples.append('\n'.join(current_example))
            current_example = []
    
    # Don't forget the last example
    if current_example:
        examples.append('\n'.join(current_example))
    
    return examples

def _extract_code_blocks(docstring: str) -> List[Dict[str, Any]]:
    """Extract code blocks from markdown-style formatting."""
    blocks = []
    
    # Pattern for fenced code blocks
    fenced_pattern = r'``````'
    matches = re.findall(fenced_pattern, docstring, re.DOTALL)
    
    for language, code in matches:
        blocks.append({
            "code": code.strip(),
            "language": language or "python"
        })
    
    # Pattern for indented code blocks (following "Example:" or similar)
    example_pattern = r'(?:Example|Usage|Code):\s*\n((?:    .*\n?)+)'
    matches = re.findall(example_pattern, docstring, re.MULTILINE)
    
    for match in matches:
        # Remove common indentation
        lines = match.split('\n')
        if lines:
            # Find minimum indentation
            min_indent = min(len(line) - len(line.lstrip()) 
                           for line in lines if line.strip())
            # Remove common indentation
            code_lines = [line[min_indent:] if len(line) >= min_indent else line 
                         for line in lines]
            code = '\n'.join(code_lines).strip()
            if code:
                blocks.append({
                    "code": code,
                    "language": "python"
                })
    
    return blocks

def _extract_example_sections(docstring: str) -> List[str]:
    """Extract dedicated example sections."""
    examples = []
    
    # Look for sections starting with "Examples:", "Example:", etc.
    sections = re.split(r'\n\s*(Examples?|Usage|Sample Code):\s*\n', docstring, flags=re.IGNORECASE)
    
    for i in range(1, len(sections), 2):  # Every other section starting from 1
        if i + 1 < len(sections):
            example_content = sections[i + 1].split('\n\n')[0]  # Take first paragraph
            if example_content.strip():
                examples.append(example_content.strip())
    
    return examples

def _extract_main_guard_examples(tree: ast.AST, file_path: str, source: str) -> List[Dict[str, Any]]:
    """Extract examples from if __name__ == '__main__': blocks."""
    examples = []
    
    for node in ast.walk(tree):
        if (isinstance(node, ast.If) and 
            isinstance(node.test, ast.Compare) and
            isinstance(node.test.left, ast.Name) and
            node.test.left.id == '__name__'):
            
            # Extract the code from the main guard
            start_line = node.lineno - 1
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
            
            source_lines = source.split('\n')
            if start_line < len(source_lines):
                # Find the actual end of the if block
                main_guard_lines = []
                indent_level = None
                
                for i in range(start_line, min(end_line, len(source_lines))):
                    line = source_lines[i]
                    if indent_level is None and line.strip():
                        indent_level = len(line) - len(line.lstrip())
                    
                    if line.strip():  # Non-empty line
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent >= indent_level:
                            main_guard_lines.append(line)
                        else:
                            break
                    else:
                        main_guard_lines.append(line)
                
                if main_guard_lines:
                    code = '\n'.join(main_guard_lines)
                    examples.append({
                        "file": file_path,
                        "context": "main guard",
                        "type": "main_example",
                        "code": code.strip(),
                        "language": "python"
                    })
    
    return examples

def _extract_comment_examples(source: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract examples from comments."""
    examples = []
    
    # Look for comment blocks that contain example code
    comment_blocks = []
    current_block = []
    
    for line in source.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#') and len(stripped) > 1:
            comment_text = stripped[1:].strip()
            if comment_text:
                current_block.append(comment_text)
        elif current_block:
            comment_blocks.append('\n'.join(current_block))
            current_block = []
    
    if current_block:
        comment_blocks.append('\n'.join(current_block))
    
    # Look for example patterns in comment blocks
    for block in comment_blocks:
        if any(keyword in block.lower() for keyword in ['example', 'usage', 'sample', 'demo']):
            # Try to extract code-like content
            code_lines = []
            for line in block.split('\n'):
                # Look for lines that look like code
                if (any(char in line for char in ['=', '(', ')', '.', 'import', 'from', 'def', 'class']) 
                    and not line.lower().startswith(('example', 'usage', 'sample', 'demo'))):
                    code_lines.append(line)
            
            if code_lines:
                examples.append({
                    "file": file_path,
                    "context": "comment",
                    "type": "comment_example",
                    "code": '\n'.join(code_lines),
                    "language": "python"
                })
    
    return examples

def _extract_usage_patterns(tree: ast.AST, file_path: str, source: str) -> List[Dict[str, Any]]:
    """Extract common usage patterns from the code itself."""
    examples = []
    
    # Look for class instantiation patterns
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # Look for assignments that might be examples
            if (isinstance(node.value, ast.Call) and 
                isinstance(node.value.func, ast.Name)):
                
                # Get the source code for this assignment
                if hasattr(node, 'lineno'):
                    line_no = node.lineno - 1
                    source_lines = source.split('\n')
                    if line_no < len(source_lines):
                        line = source_lines[line_no].strip()
                        if line and not line.startswith(('_', 'self.')):
                            examples.append({
                                "file": file_path,
                                "context": "usage pattern",
                                "type": "instantiation",
                                "code": line,
                                "language": "python"
                            })
    
    return examples
