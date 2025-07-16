# src/utils/file_utils.py

import ast
import os
import re
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

try:
    import tiktoken
except ImportError:
    tiktoken = None


def safe_read_file(filepath: str) -> Optional[str]:
    """
    Safely reads a file's content with comprehensive error handling.
    
    This function attempts to read a file using multiple encoding strategies
    to handle various file encodings commonly found in Python projects.
    
    Args:
        filepath: The path to the file to read.
    
    Returns:
        The file content as a string if successful, None otherwise.
    """
    if not filepath or not os.path.exists(filepath):
        return None
    
    # Try different encodings in order of preference
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except (IOError, OSError) as e:
            # Handle file permission errors or other IO issues
            print(f"Error reading file {filepath}: {e}")
            return None
    
    # If all encodings fail, try reading as binary and decode with error handling
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            return content.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Failed to read file {filepath}: {e}")
        return None


def get_relative_path(base_path: str, target_path: str) -> str:
    """
    Gets the relative path from base_path to target_path.
    
    Args:
        base_path: The base directory path.
        target_path: The target file or directory path.
    
    Returns:
        The relative path from base to target, normalized with forward slashes.
    """
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        
        # Calculate relative path
        relative = target.relative_to(base)
        
        # Convert to forward slashes for consistency
        return str(relative).replace(os.sep, '/')
    
    except ValueError:
        # Paths are not relative to each other, return absolute target path
        return str(Path(target_path).resolve())
    except Exception:
        # Fallback to string manipulation
        return os.path.relpath(target_path, base_path).replace(os.sep, '/')


def is_text_file(filepath: str) -> bool:
    """
    Determines if a file is likely to be a text file.
    
    This function uses multiple strategies to determine if a file is text:
    1. Check file extension against known text file types
    2. Use mimetypes library to guess content type
    3. Attempt to read the beginning of the file to check for binary content
    
    Args:
        filepath: The path to the file to check.
    
    Returns:
        True if the file is likely a text file, False otherwise.
    """
    if not filepath or not os.path.exists(filepath):
        return False
    
    # Convert to Path object for easier manipulation
    path = Path(filepath)
    
    # Check if it's a directory
    if path.is_dir():
        return False
    
    # Known text file extensions
    text_extensions = {
        '.py', '.txt', '.md', '.rst', '.cfg', '.ini', '.conf', '.json',
        '.yaml', '.yml', '.xml', '.html', '.css', '.js', '.toml',
        '.requirements', '.in', '.lock', '.log', '.sh', '.bat',
        '.sql', '.csv', '.tsv', '.gitignore', '.dockerignore'
    }
    
    # Check file extension
    if path.suffix.lower() in text_extensions:
        return True
    
    # Check files without extensions that are commonly text
    if not path.suffix and path.name.lower() in {
        'readme', 'license', 'changelog', 'authors', 'contributors',
        'dockerfile', 'makefile', 'pipfile', 'procfile'
    }:
        return True
    
    # Use mimetypes to guess content type
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type and mime_type.startswith('text/'):
        return True
    
    # Try to read the beginning of the file to check for binary content
    try:
        with open(filepath, 'rb') as f:
            # Read first 1024 bytes
            chunk = f.read(1024)
            
            # Check for null bytes (common in binary files)
            if b'\x00' in chunk:
                return False
            
            # Try to decode as UTF-8
            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ['latin-1', 'cp1252']:
                    try:
                        chunk.decode(encoding)
                        return True
                    except UnicodeDecodeError:
                        continue
                
                return False
    
    except Exception:
        return False


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensures that a directory exists, creating it if necessary.
    
    Args:
        directory_path: The path to the directory to create.
    
    Returns:
        True if the directory exists or was created successfully, False otherwise.
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False


def get_file_size(filepath: str) -> int:
    """
    Gets the size of a file in bytes.
    
    Args:
        filepath: The path to the file.
    
    Returns:
        The file size in bytes, or 0 if the file doesn't exist or can't be accessed.
    """
    try:
        return os.path.getsize(filepath)
    except Exception:
        return 0


def is_python_package(directory_path: str) -> bool:
    """
    Determines if a directory is a Python package (contains __init__.py).
    
    Args:
        directory_path: The path to the directory to check.
    
    Returns:
        True if the directory contains an __init__.py file, False otherwise.
    """
    if not os.path.isdir(directory_path):
        return False
    
    init_file = os.path.join(directory_path, '__init__.py')
    return os.path.exists(init_file)


def get_file_extension(filepath: str) -> str:
    """
    Gets the file extension from a filepath.
    
    Args:
        filepath: The path to the file.
    
    Returns:
        The file extension (including the dot), or empty string if no extension.
    """
    return Path(filepath).suffix.lower()


def normalize_path(path: str) -> str:
    """
    Normalizes a file path by resolving relative components and converting separators.
    
    Args:
        path: The path to normalize.
    
    Returns:
        The normalized path as a string.
    """
    return str(Path(path).resolve())


# New Enhanced Functions for LLM Integration

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens for specific LLM model using tiktoken.
    
    Args:
        text: The text to count tokens for
        model: The LLM model to use for tokenization
        
    Returns:
        Number of tokens in the text
    """
    if not text:
        return 0
    
    if tiktoken is None:
        # Fallback estimation: roughly 1.3 tokens per word
        return int(len(text.split()) * 1.3)
    
    try:
        # Map common model names to tiktoken encodings
        model_mapping = {
            "gpt-4": "cl100k_base",
            "gpt-4o": "o200k_base",
            "gpt-4o-mini": "o200k_base",
            "gpt-3.5-turbo": "cl100k_base",
            "gemini-2.5-flash": "cl100k_base",  # Approximate
            "claude-sonnet": "cl100k_base",     # Approximate
        }
        
        # Try to get encoding for the specific model
        if model in model_mapping:
            encoding = tiktoken.get_encoding(model_mapping[model])
        else:
            # Try direct model name
            encoding = tiktoken.encoding_for_model(model)
        
        return len(encoding.encode(text))
    
    except Exception:
        # Fallback estimation
        return int(len(text.split()) * 1.3)


def optimize_content_for_llm(content: str, max_tokens: int, model: str = "gpt-4") -> str:
    """
    Optimize content to fit within token limits using intelligent truncation.
    
    Args:
        content: The content to optimize
        max_tokens: Maximum token limit
        model: LLM model for token counting
        
    Returns:
        Optimized content that fits within token limits
    """
    current_tokens = count_tokens(content, model)
    
    if current_tokens <= max_tokens:
        return content
    
    # Calculate reduction needed
    reduction_ratio = max_tokens / current_tokens
    
    # Apply various optimization strategies
    optimized_content = content
    
    # 1. Remove excessive whitespace
    optimized_content = re.sub(r'\n\s*\n\s*\n', '\n\n', optimized_content)
    optimized_content = re.sub(r' +', ' ', optimized_content)
    
    # 2. Remove comments (but preserve docstrings)
    optimized_content = _remove_comments(optimized_content)
    
    # 3. Compress long functions if still too long
    if count_tokens(optimized_content, model) > max_tokens:
        optimized_content = _compress_functions(optimized_content, reduction_ratio)
    
    # 4. Truncate by priority if still too long
    if count_tokens(optimized_content, model) > max_tokens:
        optimized_content = _truncate_by_priority(optimized_content, max_tokens, model)
    
    return optimized_content


def _remove_comments(content: str) -> str:
    """Remove comments while preserving docstrings."""
    lines = content.split('\n')
    result_lines = []
    in_docstring = False
    docstring_quote = None
    
    for line in lines:
        stripped = line.strip()
        
        # Check for docstring start/end
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = True
                docstring_quote = stripped[:3]
                result_lines.append(line)
                if stripped.count(docstring_quote) >= 2:
                    in_docstring = False
                continue
        else:
            result_lines.append(line)
            if docstring_quote in stripped:
                in_docstring = False
            continue
        
        # Remove single-line comments
        if stripped.startswith('#'):
            continue
        
        # Remove inline comments
        if '#' in line:
            # Simple heuristic: remove everything after # if not in string
            comment_pos = line.find('#')
            quote_count = line[:comment_pos].count('"') + line[:comment_pos].count("'")
            if quote_count % 2 == 0:  # Even number of quotes before #
                line = line[:comment_pos].rstrip()
        
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def _compress_functions(content: str, reduction_ratio: float) -> str:
    """Compress long functions by summarizing their content."""
    try:
        tree = ast.parse(content)
        lines = content.split('\n')
        result_lines = lines.copy()
        
        # Find long functions to compress
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    if func_length > 10:  # Compress functions longer than 10 lines
                        # Replace function body with summary
                        docstring = ast.get_docstring(node) or "Function implementation"
                        summary = f'    """{docstring}"""'
                        summary += f'\n    # Implementation ({func_length} lines) - truncated for brevity'
                        summary += f'\n    pass'
                        
                        # Replace lines
                        for i in range(node.lineno, min(node.end_lineno, len(result_lines))):
                            if i == node.lineno:
                                # Keep function signature
                                continue
                            elif i == node.lineno + 1:
                                result_lines[i] = summary
                            else:
                                result_lines[i] = ""
        
        return '\n'.join(line for line in result_lines if line is not None)
    
    except Exception:
        # If AST parsing fails, just return original content
        return content


def _truncate_by_priority(content: str, max_tokens: int, model: str) -> str:
    """Truncate content by priority, keeping most important parts."""
    lines = content.split('\n')
    
    # Categorize lines by priority
    high_priority = []
    medium_priority = []
    low_priority = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # High priority: imports, class/function definitions, docstrings
        if (stripped.startswith(('import ', 'from ', 'class ', 'def ', 'async def ')) or
            stripped.startswith(('"""', "'''")) or
            stripped.startswith('#') and 'TODO' in stripped):
            high_priority.append((i, line))
        
        # Medium priority: non-empty lines with code
        elif stripped and not stripped.startswith('#'):
            medium_priority.append((i, line))
        
        # Low priority: comments, empty lines
        else:
            low_priority.append((i, line))
    
    # Build result by priority
    result_lines = [''] * len(lines)
    
    # Add high priority lines
    for i, line in high_priority:
        result_lines[i] = line
    
    # Add medium priority lines if we have token budget
    temp_content = '\n'.join(result_lines)
    for i, line in medium_priority:
        temp_content_with_line = temp_content + '\n' + line
        if count_tokens(temp_content_with_line, model) <= max_tokens:
            result_lines[i] = line
            temp_content = temp_content_with_line
        else:
            break
    
    # Add low priority lines if we still have budget
    temp_content = '\n'.join(result_lines)
    for i, line in low_priority:
        temp_content_with_line = temp_content + '\n' + line
        if count_tokens(temp_content_with_line, model) <= max_tokens:
            result_lines[i] = line
            temp_content = temp_content_with_line
        else:
            break
    
    return '\n'.join(line for line in result_lines if line)


def extract_code_examples(filepath: str) -> List[str]:
    """
    Extract code examples from Python files.
    
    Args:
        filepath: Path to the Python file
        
    Returns:
        List of code examples found in the file
    """
    examples = []
    
    try:
        content = safe_read_file(filepath)
        if not content:
            return examples
        
        # Parse the file as AST
        tree = ast.parse(content)
        
        # Extract if __name__ == "__main__" blocks
        main_examples = _extract_main_blocks(content, tree)
        examples.extend(main_examples)
        
        # Extract docstring examples
        docstring_examples = _extract_docstring_examples(tree)
        examples.extend(docstring_examples)
        
        # Extract test examples
        test_examples = _extract_test_examples(tree)
        examples.extend(test_examples)
        
    except Exception as e:
        print(f"Error extracting examples from {filepath}: {e}")
    
    return examples


def _extract_main_blocks(content: str, tree: ast.AST) -> List[str]:
    """Extract code from if __name__ == "__main__" blocks."""
    examples = []
    lines = content.split('\n')
    
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check if this is a __name__ == "__main__" condition
            if _is_main_guard(node.test):
                # Extract the code block
                start_line = node.lineno - 1
                end_line = getattr(node, 'end_lineno', len(lines)) - 1
                
                block_lines = lines[start_line:end_line + 1]
                
                # Clean up the block (remove the if statement itself)
                example_lines = []
                for line in block_lines[1:]:  # Skip the if statement
                    if line.strip():
                        example_lines.append(line)
                
                if example_lines:
                    examples.append('\n'.join(example_lines))
    
    return examples


def _is_main_guard(test_node: ast.AST) -> bool:
    """Check if a test node is a __name__ == "__main__" condition."""
    if isinstance(test_node, ast.Compare):
        if (isinstance(test_node.left, ast.Name) and 
            test_node.left.id == '__name__' and
            len(test_node.ops) == 1 and
            isinstance(test_node.ops[0], ast.Eq) and
            len(test_node.comparators) == 1):
            
            comparator = test_node.comparators[0]
            if isinstance(comparator, ast.Constant):
                return comparator.value == '__main__'
            elif isinstance(comparator, ast.Str):  # Python < 3.8
                return comparator.s == '__main__'
    
    return False


def _extract_docstring_examples(tree: ast.AST) -> List[str]:
    """Extract code examples from docstrings."""
    examples = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                # Look for code blocks in docstring
                code_blocks = _parse_docstring_examples(docstring)
                examples.extend(code_blocks)
    
    return examples


def _parse_docstring_examples(docstring: str) -> List[str]:
    """Parse code examples from docstring text."""
    examples = []
    
    # Look for code blocks after "Example:" or "Examples:"
    example_pattern = r'(?:Examples?|Usage):\s*\n(.*?)(?:\n\s*\n|\n\s*[A-Z]|\Z)'
    matches = re.findall(example_pattern, docstring, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        # Clean up the example
        example = match.strip()
        if example:
            examples.append(example)
    
    # Look for code blocks marked with >>> (doctest style)
    doctest_pattern = r'>>> (.*?)(?:\n(?!>>>|\s*\.\.\.|\s*$)|\Z)'
    doctest_matches = re.findall(doctest_pattern, docstring, re.MULTILINE | re.DOTALL)
    
    for match in doctest_matches:
        if match.strip():
            examples.append(match.strip())
    
    return examples


def _extract_test_examples(tree: ast.AST) -> List[str]:
    """Extract examples from test functions."""
    examples = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith('test_'):
                # This is a test function
                docstring = ast.get_docstring(node)
                if docstring:
                    examples.append(f"# Test: {node.name}\n{docstring}")
    
    return examples


def create_template_content(template_vars: Dict[str, Any]) -> str:
    """
    Create content from template variables for README generation.
    
    Args:
        template_vars: Dictionary of template variables
        
    Returns:
        Formatted template content
    """
    template = """
        # {project_name}

        {description}

        ## Installation

        {installation_instructions}

        ## Usage

        {usage_examples}

        ## Project Structure

        {project_structure}


        ## Dependencies

        {dependencies}

        ## Contributing

        {contributing_info}

        ## License

        {license_info}
        """
    
    return template.format(**template_vars)


def estimate_content_tokens(content_dict: Dict[str, str], model: str = "gpt-4") -> Dict[str, int]:
    """
    Estimate token counts for different content sections.
    
    Args:
        content_dict: Dictionary of content sections
        model: LLM model for token counting
        
    Returns:
        Dictionary with token counts for each section
    """
    token_counts = {}
    
    for section, content in content_dict.items():
        if content:
            token_counts[section] = count_tokens(str(content), model)
        else:
            token_counts[section] = 0
    
    return token_counts


def chunk_content_by_tokens(content: str, max_tokens: int, model: str = "gpt-4", 
                           overlap: int = 100) -> List[str]:
    """
    Split content into chunks based on token limits.
    
    Args:
        content: Content to chunk
        max_tokens: Maximum tokens per chunk
        model: LLM model for token counting
        overlap: Token overlap between chunks
        
    Returns:
        List of content chunks
    """
    if count_tokens(content, model) <= max_tokens:
        return [content]
    
    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_tokens = 0
    
    for line in lines:
        line_tokens = count_tokens(line, model)
        
        if current_tokens + line_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunks.append('\n'.join(current_chunk))
            
            # Start new chunk with overlap
            if overlap > 0:
                overlap_lines = []
                overlap_tokens = 0
                for prev_line in reversed(current_chunk):
                    line_tokens_check = count_tokens(prev_line, model)
                    if overlap_tokens + line_tokens_check <= overlap:
                        overlap_lines.insert(0, prev_line)
                        overlap_tokens += line_tokens_check
                    else:
                        break
                current_chunk = overlap_lines
                current_tokens = overlap_tokens
            else:
                current_chunk = []
                current_tokens = 0
        
        current_chunk.append(line)
        current_tokens += line_tokens
    
    # Add final chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks


def get_content_summary(content: str, max_length: int = 500) -> str:
    """
    Generate a brief summary of content.
    
    Args:
        content: Content to summarize
        max_length: Maximum summary length
        
    Returns:
        Content summary
    """
    if len(content) <= max_length:
        return content
    
    # Extract first paragraph or docstring
    lines = content.split('\n')
    summary_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            summary_lines.append(line)
            if len('\n'.join(summary_lines)) > max_length:
                break
    
    summary = '\n'.join(summary_lines)
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return summary
