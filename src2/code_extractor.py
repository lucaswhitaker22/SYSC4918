import os
import ast
import json
from typing import List, Dict, Any


def count_tokens_approx(text: str) -> int:
    """
    Approximate token count from characters.
    Uses conservative estimate of 4 characters per token.
    """
    return len(text) // 4


def extract_docstrings_and_sources(filepath: str) -> Dict[str, Any]:
    """
    Extract module docstring, classes, functions, and their docstrings from a Python file.
    
    Args:
        filepath: Path to the Python file to analyze
        
    Returns:
        Dictionary containing extracted code elements and metadata
    """
    with open(filepath, 'r', encoding='utf-8') as file:
        source = file.read()

    tree = ast.parse(source)
    result = {
        'file_path': filepath,
        'file_source': source
    }

    # Extract module-level docstring
    module_doc = ast.get_docstring(tree)
    if module_doc:
        result['module_docstring'] = module_doc

    classes = []
    functions = []

    # Parse top-level nodes
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                'name': node.name,
                'docstring': ast.get_docstring(node) or "",
                'methods': [],
            }
            
            # Extract methods from class
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_source = ast.get_source_segment(source, item) or ""
                    class_info['methods'].append({
                        'name': item.name,
                        'docstring': ast.get_docstring(item) or "",
                        'source': method_source,
                    })
            classes.append(class_info)
            
        elif isinstance(node, ast.FunctionDef):
            func_source = ast.get_source_segment(source, node) or ""
            functions.append({
                'name': node.name,
                'docstring': ast.get_docstring(node) or "",
                'source': func_source,
            })

    result['classes'] = classes
    result['functions'] = functions
    
    return result


def traverse_and_extract(project_dir: str) -> List[Dict[str, Any]]:
    """
    Traverse project directory and extract code from all Python files.
    
    Args:
        project_dir: Root directory of the Python project
        
    Returns:
        List of dictionaries containing extracted code from each file
    """
    extracted_files = []
    
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                try:
                    data = extract_docstrings_and_sources(full_path)
                    extracted_files.append(data)
                except Exception as e:
                    # Skip files that cannot be parsed (syntax errors, encoding issues, etc.)
                    print(f"Warning: Could not parse {full_path}: {e}")
                    continue
                    
    return extracted_files


def calculate_file_score(file_data: Dict[str, Any]) -> float:
    """
    Calculate priority score for a file based on documentation quality and size.
    Higher scores indicate higher priority for README generation.
    
    Args:
        file_data: Dictionary containing extracted file data
        
    Returns:
        Priority score (higher = more important)
    """
    score = 0.0
    
    # High priority for module docstring
    if file_data.get('module_docstring'):
        score += 50
    
    # Medium priority for class docstrings
    for class_info in file_data.get('classes', []):
        if class_info.get('docstring'):
            score += 10
        # Lower priority for method docstrings
        for method in class_info.get('methods', []):
            if method.get('docstring'):
                score += 5
    
    # Medium priority for function docstrings
    for func in file_data.get('functions', []):
        if func.get('docstring'):
            score += 8
    
    # Favor smaller, more focused files
    source_len = len(file_data.get('file_source', ''))
    if source_len > 0:
        # Inverse relationship with file size
        score += min(20, 10000 / source_len)
    
    return score


def prioritize_and_limit(extracted_data: List[Dict[str, Any]], max_tokens: int = 500000) -> List[Dict[str, Any]]:
    """
    Sort files by priority and limit content to fit within token budget.
    
    Args:
        extracted_data: List of extracted file data
        max_tokens: Maximum token limit for output
        
    Returns:
        Prioritized and limited list of file data
    """
    # Sort by priority score (highest first)
    extracted_data.sort(key=calculate_file_score, reverse=True)
    
    total_tokens = 0
    limited_data = []
    
    for file_data in extracted_data:
        # Calculate tokens for this file
        text_parts = []
        
        if file_data.get('module_docstring'):
            text_parts.append(file_data['module_docstring'])
        
        for class_info in file_data.get('classes', []):
            text_parts.append(class_info.get('docstring', ''))
            for method in class_info.get('methods', []):
                text_parts.append(method.get('docstring', ''))
                text_parts.append(method.get('source', ''))
        
        for func in file_data.get('functions', []):
            text_parts.append(func.get('docstring', ''))
            text_parts.append(func.get('source', ''))
        
        combined_text = '\n'.join(filter(None, text_parts))
        file_tokens = count_tokens_approx(combined_text)
        
        # Add file if it fits within budget
        if total_tokens + file_tokens <= max_tokens:
            limited_data.append(file_data)
            total_tokens += file_tokens
        else:
            # Try to add partial content from this file
            partial_file = create_partial_file_data(file_data, max_tokens - total_tokens)
            if partial_file:
                limited_data.append(partial_file)
            break
    
    return limited_data


def create_partial_file_data(file_data: Dict[str, Any], remaining_tokens: int) -> Dict[str, Any]:
    """
    Create a partial version of file data that fits within remaining token budget.
    
    Args:
        file_data: Original file data
        remaining_tokens: Available token budget
        
    Returns:
        Partial file data or None if nothing fits
    """
    partial = {
        'file_path': file_data.get('file_path', ''),
        'classes': [],
        'functions': []
    }
    
    used_tokens = 0
    
    # Add module docstring if it fits
    module_doc = file_data.get('module_docstring', '')
    if module_doc:
        doc_tokens = count_tokens_approx(module_doc)
        if used_tokens + doc_tokens <= remaining_tokens:
            partial['module_docstring'] = module_doc
            used_tokens += doc_tokens
    
    # Add classes and methods that fit
    for class_info in file_data.get('classes', []):
        class_partial = {'name': class_info['name'], 'methods': []}
        
        # Add class docstring if it fits
        class_doc = class_info.get('docstring', '')
        if class_doc:
            doc_tokens = count_tokens_approx(class_doc)
            if used_tokens + doc_tokens <= remaining_tokens:
                class_partial['docstring'] = class_doc
                used_tokens += doc_tokens
        
        # Add methods that fit
        for method in class_info.get('methods', []):
            method_text = method.get('docstring', '') + '\n' + method.get('source', '')
            method_tokens = count_tokens_approx(method_text)
            if used_tokens + method_tokens <= remaining_tokens:
                class_partial['methods'].append(method)
                used_tokens += method_tokens
            else:
                break
        
        if class_partial.get('docstring') or class_partial['methods']:
            partial['classes'].append(class_partial)
    
    # Add functions that fit
    for func in file_data.get('functions', []):
        func_text = func.get('docstring', '') + '\n' + func.get('source', '')
        func_tokens = count_tokens_approx(func_text)
        if used_tokens + func_tokens <= remaining_tokens:
            partial['functions'].append(func)
            used_tokens += func_tokens
        else:
            break
    
    return partial if used_tokens > 0 else None


def generate_readme_context_json(project_dir: str, output_file: str = 'output.json'):
    """
    Main function to extract and prioritize Python project code for README generation.
    
    Args:
        project_dir: Path to the Python project directory
        output_file: Path for the output JSON file
    """
    print(f"Analyzing Python project in: {project_dir}")
    
    # Extract code from all Python files
    extracted_data = traverse_and_extract(project_dir)
    print(f"Found {len(extracted_data)} Python files")
    
    # Prioritize and limit content
    prioritized_data = prioritize_and_limit(extracted_data, max_tokens=500000)
    
    # Calculate final statistics
    total_tokens = sum(
        count_tokens_approx(
            str(file_data.get('module_docstring', '')) +
            str([c.get('docstring', '') for c in file_data.get('classes', [])]) +
            str([f.get('docstring', '') + f.get('source', '') for f in file_data.get('functions', [])])
        ) for file_data in prioritized_data
    )
    
    print(f"Selected {len(prioritized_data)} files (~{total_tokens:,} tokens)")
    
    # Write output JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(prioritized_data, f, indent=2, ensure_ascii=False)
    
    print(f"Generated: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python code_extractor.py <project_directory>")
        sys.exit(1)
    
    project_path = sys.argv[1]
    if not os.path.isdir(project_path):
        print(f"Error: {project_path} is not a valid directory")
        sys.exit(1)
    
    generate_readme_context_json(project_path)
