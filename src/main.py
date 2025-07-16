# src/main.py

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from parsing import CoreParser
from models.project_info import ProjectInfo


def main():
    """Main entry point for the README generator CLI."""
    parser = argparse.ArgumentParser(
        description="Generate README files for Python projects using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py /path/to/project
  python main.py . --verbose
  python main.py /path/to/project --output custom_readme.md
        """
    )
    
    parser.add_argument(
        "project_path",
        help="Path to the Python project root directory"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="README.md",
        help="Output filename (default: README.md)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output with detailed project structure"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show detailed parsing statistics"
    )
    
    parser.add_argument(
        "--data-file",
        default="data.txt",
        help="Output file for parsed data (default: data.txt)"
    )
    
    parser.add_argument(
        "--show-comments",
        action="store_true",
        help="Display function and class comments in output"
    )
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ Error: Project path '{args.project_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"❌ Error: Project path '{args.project_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    print(f"🔍 Analyzing Python project at: {project_path}")
    print("-" * 60)
    
    try:
        # Initialize parser and time the parsing operation
        start_time = time.time()
        core_parser = CoreParser()
        project_info = core_parser.parse_project(str(project_path))
        parsing_time = time.time() - start_time
        
        # Display comprehensive results
        display_parsing_results(project_info, parsing_time, args.verbose, args.stats, args.show_comments)
        
        # Test and validate the parsing results
        validation_results = validate_parsing_results(project_info)
        display_validation_results(validation_results)
        
        # Save all parsed data to data.txt
        save_parsed_data_to_file(project_info, parsing_time, validation_results, args.data_file)
        
        print(f"\n✅ Parsing completed successfully in {parsing_time:.2f} seconds!")
        print(f"📄 Ready to generate README for: {project_info.name or 'Unknown Project'}")
        print(f"💾 Parsed data saved to: {args.data_file}")
        
    except Exception as e:
        print(f"❌ Error during parsing: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def save_parsed_data_to_file(project_info: ProjectInfo, parsing_time: float, 
                           validation_results: Dict[str, bool], output_file: str):
    """Save comprehensive parsed data to a text file."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"PROJECT ANALYSIS REPORT - {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        
        # Basic Project Information
        f.write("📁 BASIC PROJECT INFORMATION\n")
        f.write("-" * 40 + "\n")
        f.write(f"Project Name: {project_info.name or 'Unknown'}\n")
        f.write(f"Root Path: {project_info.root_path}\n")
        f.write(f"Setup File: {project_info.setup_file or 'None found'}\n")
        f.write(f"Requirements File: {project_info.requirements_file or 'None found'}\n")
        f.write(f"Parsing Time: {parsing_time:.2f} seconds\n")
        f.write(f"Parsed Python Files: {len(project_info.parsed_files)}\n\n")
        
        # Main Modules
        f.write(f"🎯 MAIN MODULES ({len(project_info.main_modules)} found)\n")
        f.write("-" * 40 + "\n")
        if project_info.main_modules:
            for i, module in enumerate(project_info.main_modules, 1):
                f.write(f"{i:2d}. {module}\n")
        else:
            f.write("No main modules identified\n")
        f.write("\n")
        
        # Entry Points
        f.write(f"🚀 ENTRY POINTS ({len(project_info.entry_points)} found)\n")
        f.write("-" * 40 + "\n")
        if project_info.entry_points:
            for i, entry_point in enumerate(project_info.entry_points, 1):
                f.write(f"{i:2d}. {entry_point}\n")
        else:
            f.write("No entry points identified\n")
        f.write("\n")
        
        # Dependencies
        f.write(f"📦 DEPENDENCIES ({len(project_info.dependencies)} found)\n")
        f.write("-" * 40 + "\n")
        if project_info.dependencies:
            for i, dep in enumerate(project_info.dependencies, 1):
                f.write(f"{i:2d}. {dep}\n")
        else:
            f.write("No dependencies found\n")
        f.write("\n")
        
        # File Docstrings
        f.write(f"📝 FILE DOCSTRINGS ({len(project_info.file_docstrings)} found)\n")
        f.write("-" * 40 + "\n")
        if project_info.file_docstrings:
            for file_path, docstring in project_info.file_docstrings.items():
                f.write(f"File: {file_path}\n")
                f.write(f"Docstring: {docstring[:200]}{'...' if len(docstring) > 200 else ''}\n\n")
        else:
            f.write("No file docstrings found\n")
        f.write("\n")
        
        # Function Comments
        f.write(f"🔧 FUNCTION COMMENTS ({len(project_info.function_comments)} files with function comments)\n")
        f.write("-" * 40 + "\n")
        if project_info.function_comments:
            for file_path, function_comments in project_info.function_comments.items():
                f.write(f"File: {file_path}\n")
                for func_comment in function_comments:
                    f.write(f"  Function: {func_comment.get('function_name', 'Unknown')}\n")
                    f.write(f"  Line: {func_comment.get('line_number', 'Unknown')}\n")
                    
                    if func_comment.get('docstring'):
                        f.write(f"  Docstring: {func_comment['docstring'][:100]}{'...' if len(func_comment['docstring']) > 100 else ''}\n")
                    
                    if func_comment.get('preceding_comments'):
                        f.write(f"  Preceding Comments: {len(func_comment['preceding_comments'])} found\n")
                        for comment in func_comment['preceding_comments']:
                            f.write(f"    - {comment}\n")
                    
                    if func_comment.get('body_comments'):
                        f.write(f"  Body Comments: {len(func_comment['body_comments'])} found\n")
                        for comment in func_comment['body_comments']:
                            f.write(f"    - {comment}\n")
                    
                    f.write("\n")
                f.write("\n")
        else:
            f.write("No function comments found\n")
        f.write("\n")
        
        # Class Comments
        f.write(f"🏗️ CLASS COMMENTS ({len(project_info.class_comments)} files with class comments)\n")
        f.write("-" * 40 + "\n")
        if project_info.class_comments:
            for file_path, class_comments in project_info.class_comments.items():
                f.write(f"File: {file_path}\n")
                for class_comment in class_comments:
                    f.write(f"  Class: {class_comment.get('class_name', 'Unknown')}\n")
                    f.write(f"  Line: {class_comment.get('line_number', 'Unknown')}\n")
                    
                    if class_comment.get('docstring'):
                        f.write(f"  Docstring: {class_comment['docstring'][:100]}{'...' if len(class_comment['docstring']) > 100 else ''}\n")
                    
                    if class_comment.get('preceding_comments'):
                        f.write(f"  Preceding Comments: {len(class_comment['preceding_comments'])} found\n")
                        for comment in class_comment['preceding_comments']:
                            f.write(f"    - {comment}\n")
                    
                    if class_comment.get('body_comments'):
                        f.write(f"  Body Comments: {len(class_comment['body_comments'])} found\n")
                        for comment in class_comment['body_comments']:
                            f.write(f"    - {comment}\n")
                    
                    f.write("\n")
                f.write("\n")
        else:
            f.write("No class comments found\n")
        f.write("\n")
        
        # Project structure and other existing sections...
        # (Continue with existing code for file structure, statistics, validation, etc.)
        
        f.write("=" * 80 + "\n\n")


def display_parsing_results(project_info: ProjectInfo, parsing_time: float, 
                           verbose: bool, show_stats: bool, show_comments: bool):
    """Display comprehensive parsing results."""
    
    print("\n" + "=" * 60)
    print("📊 PROJECT ANALYSIS RESULTS")
    print("=" * 60)
    
    # Basic project information
    print(f"📁 Project Name: {project_info.name or '❓ Unknown'}")
    print(f"📂 Root Path: {project_info.root_path}")
    print(f"⚙️  Setup File: {project_info.setup_file or '❌ None found'}")
    print(f"📋 Requirements File: {project_info.requirements_file or '❌ None found'}")
    print(f"⏱️  Parsing Time: {parsing_time:.2f} seconds")
    print(f"🐍 Parsed Python Files: {len(project_info.parsed_files)}")
    
    # Main modules section
    print(f"\n🎯 MAIN MODULES ({len(project_info.main_modules)} found):")
    if project_info.main_modules:
        for module in project_info.main_modules:
            print(f"  ✓ {module}")
    else:
        print("  ❌ No main modules identified")
    
    # Entry points section
    print(f"\n🚀 ENTRY POINTS ({len(project_info.entry_points)} found):")
    if project_info.entry_points:
        for entry_point in project_info.entry_points:
            print(f"  ✓ {entry_point}")
    else:
        print("  ❌ No entry points identified")
    
    # Dependencies section
    print(f"\n📦 DEPENDENCIES ({len(project_info.dependencies)} found):")
    if project_info.dependencies:
        for i, dep in enumerate(project_info.dependencies, 1):
            print(f"  {i:2d}. {dep}")
    else:
        print("  ❌ No dependencies found")
    
    # Function Comments section
    if show_comments:
        print(f"\n🔧 FUNCTION COMMENTS ({len(project_info.function_comments)} files):")
        if project_info.function_comments:
            for file_path, function_comments in project_info.function_comments.items():
                print(f"  📄 {file_path}:")
                for func_comment in function_comments:
                    print(f"    🔸 {func_comment.get('function_name', 'Unknown')} (Line {func_comment.get('line_number', '?')})")
                    
                    if func_comment.get('docstring'):
                        docstring_preview = func_comment['docstring'][:80] + "..." if len(func_comment['docstring']) > 80 else func_comment['docstring']
                        print(f"      📝 Docstring: {docstring_preview}")
                    
                    if func_comment.get('preceding_comments'):
                        print(f"      💬 {len(func_comment['preceding_comments'])} preceding comments")
                    
                    if func_comment.get('body_comments'):
                        print(f"      📄 {len(func_comment['body_comments'])} body comments")
        else:
            print("  ❌ No function comments found")
        
        # Class Comments section
        print(f"\n🏗️ CLASS COMMENTS ({len(project_info.class_comments)} files):")
        if project_info.class_comments:
            for file_path, class_comments in project_info.class_comments.items():
                print(f"  📄 {file_path}:")
                for class_comment in class_comments:
                    print(f"    🔸 {class_comment.get('class_name', 'Unknown')} (Line {class_comment.get('line_number', '?')})")
                    
                    if class_comment.get('docstring'):
                        docstring_preview = class_comment['docstring'][:80] + "..." if len(class_comment['docstring']) > 80 else class_comment['docstring']
                        print(f"      📝 Docstring: {docstring_preview}")
                    
                    if class_comment.get('preceding_comments'):
                        print(f"      💬 {len(class_comment['preceding_comments'])} preceding comments")
                    
                    if class_comment.get('body_comments'):
                        print(f"      📄 {len(class_comment['body_comments'])} body comments")
        else:
            print("  ❌ No class comments found")
    
    # File Docstrings section
    print(f"\n📝 FILE DOCSTRINGS ({len(project_info.file_docstrings)} found):")
    if project_info.file_docstrings:
        for file_path, docstring in project_info.file_docstrings.items():
            docstring_preview = docstring[:100] + "..." if len(docstring) > 100 else docstring
            print(f"  📄 {file_path}: {docstring_preview}")
    else:
        print("  ❌ No file docstrings found")


def validate_parsing_results(project_info: ProjectInfo) -> Dict[str, bool]:
    """Validate the parsing results and return validation status."""
    
    validation_results = {
        "has_project_name": project_info.name is not None,
        "has_project_structure": bool(project_info.project_structure),
        "has_python_files": bool(project_info.parsed_files),
        "has_setup_configuration": project_info.setup_file is not None,
        "has_dependencies": bool(project_info.dependencies),
        "has_main_modules": bool(project_info.main_modules),
        "has_entry_points": bool(project_info.entry_points),
        "has_function_comments": bool(project_info.function_comments),
        "has_docstrings": bool(project_info.file_docstrings),
        "valid_root_path": Path(project_info.root_path).exists(),
    }
    
    return validation_results


def display_validation_results(validation_results: Dict[str, bool]):
    """Display validation results."""
    
    print(f"\n🔍 PARSING VALIDATION:")
    print("-" * 40)
    
    validation_labels = {
        "has_project_name": "Project name detected",
        "has_project_structure": "Project structure mapped",
        "has_python_files": "Python files parsed",
        "has_setup_configuration": "Setup configuration found",
        "has_dependencies": "Dependencies identified",
        "has_main_modules": "Main modules identified",
        "has_entry_points": "Entry points detected",
        "has_function_comments": "Function comments extracted",
        "has_docstrings": "File docstrings extracted",
        "valid_root_path": "Valid root path",
    }
    
    passed = sum(validation_results.values())
    total = len(validation_results)
    
    for key, result in validation_results.items():
        status = "✅" if result else "❌"
        label = validation_labels.get(key, key)
        print(f"  {status} {label}")
    
    print(f"\n📊 Validation Score: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All validations passed! Project parsing is complete.")
    else:
        print("⚠️  Some validations failed. Check the project structure.")


if __name__ == "__main__":
    main()
