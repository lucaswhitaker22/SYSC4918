# src/parsing/__init__.py

import os
import sys
from pathlib import Path
from typing import Optional

# Add the src directory to Python path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

# Use absolute imports instead of relative imports
from parsing.file_scanner import scan_directory
from parsing.project_detector import (
    ProjectDetector, find_setup_files, find_requirements_files,
    identify_main_modules, detect_entry_points, determine_project_type
)
from parsing.metadata_extractor import (
    extract_project_name, parse_dependencies, extract_setup_metadata,
    parse_pyproject_toml, extract_dependencies_from_pyproject
)
from parsing.ast_parser import ASTParser
from models.project_info import ProjectInfo

class CoreParser:
    """
    Main orchestrator for parsing Python projects and extracting metadata.
    
    This class coordinates all parsing operations to analyze a Python project
    and extract comprehensive information about its structure, dependencies,
    and characteristics including function comments.
    """
    
    def __init__(self):
        self.detector = ProjectDetector()
        self.ast_parser = ASTParser()
    
    def parse_project(self, root_path: str) -> ProjectInfo:
        """
        Orchestrates all parsing operations to analyze a Python project.
        
        Args:
            root_path: Path to the root directory of the Python project.
        
        Returns:
            ProjectInfo object containing all extracted information.
        """
        # Validate root path
        if not os.path.exists(root_path) or not os.path.isdir(root_path):
            raise ValueError(f"Invalid project path: {root_path}")
        
        # Initialize ProjectInfo with root path
        project_info = ProjectInfo(root_path=os.path.abspath(root_path))
        
        # Step 1: Scan directory structure
        print(f"Scanning directory structure for {root_path}...")
        project_info.project_structure = scan_directory(root_path)
        
        # Step 2: Detect key project files
        print("Detecting key project files...")
        setup_files = find_setup_files(root_path)
        requirements_files = find_requirements_files(root_path)
        
        project_info.setup_file = setup_files[0] if setup_files else None
        project_info.requirements_file = requirements_files[0] if requirements_files else None
        
        # Step 3: Extract project metadata
        print("Extracting project metadata...")
        project_info.name = self._extract_project_name(project_info)
        project_info.dependencies = self._extract_dependencies(project_info)
        
        # Step 4: Identify main modules and entry points
        print("Identifying main modules and entry points...")
        project_info.main_modules = identify_main_modules(project_info.project_structure)
        project_info.entry_points = detect_entry_points(root_path)
        
        # Step 5: Parse Python files for comments and additional context
        print("Parsing Python files and extracting comments...")
        self._parse_python_files_with_comments(project_info)
        
        print(f"Successfully parsed project: {project_info.name or 'Unknown'}")
        return project_info
    
    def _extract_project_name(self, project_info: ProjectInfo) -> Optional[str]:
        """Extract project name from available sources."""
        if project_info.setup_file:
            name = extract_project_name(project_info.setup_file)
            if name:
                return name
        
        # Fallback to directory name
        return Path(project_info.root_path).name
    
    def _extract_dependencies(self, project_info: ProjectInfo) -> list[str]:
        """Extract dependencies from all available sources."""
        dependencies = []
        
        # From requirements.txt
        if project_info.requirements_file:
            req_deps = parse_dependencies(project_info.requirements_file)
            dependencies.extend(req_deps)
        
        # From setup.py
        if project_info.setup_file and project_info.setup_file.endswith('setup.py'):
            setup_metadata = extract_setup_metadata(project_info.setup_file)
            setup_deps = setup_metadata.get('dependencies', [])
            dependencies.extend(setup_deps)
        
        # From pyproject.toml
        if project_info.setup_file and project_info.setup_file.endswith('pyproject.toml'):
            toml_data = parse_pyproject_toml(project_info.setup_file)
            toml_deps = extract_dependencies_from_pyproject(toml_data)
            dependencies.extend(toml_deps)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(dependencies))
    
    def _parse_python_files_with_comments(self, project_info: ProjectInfo):
        """Parse Python files and extract function comments."""
        # Get all Python files from the project structure
        python_files = []
        for directory, files in project_info.project_structure.items():
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(project_info.root_path, directory.lstrip('./'), file)
                    full_path = os.path.normpath(full_path)
                    python_files.append(full_path)
        
        # Parse each Python file
        for file_path in python_files:
            if os.path.exists(file_path):
                try:
                    relative_path = os.path.relpath(file_path, project_info.root_path)
                    print(f"  Parsing {relative_path}...")
                    
                    parsed_data = self.ast_parser.parse_python_file(file_path)
                    
                    # Store file docstring
                    if parsed_data.get('module_docstring'):
                        project_info.file_docstrings[relative_path] = parsed_data['module_docstring']
                    
                    # Store function comments
                    if parsed_data.get('function_comments'):
                        project_info.function_comments[relative_path] = parsed_data['function_comments']
                    
                    # Store class comments
                    if parsed_data.get('class_comments'):
                        project_info.class_comments[relative_path] = parsed_data['class_comments']
                    
                    # Track successfully parsed files
                    project_info.parsed_files.append(relative_path)
                    
                except Exception as e:
                    print(f"  Warning: Could not parse {file_path}: {e}")
