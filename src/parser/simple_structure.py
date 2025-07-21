"""
Simple structure parser for extracting basic project organization information.

This simplified module focuses on essential project structure detection for MVP
implementation, avoiding the complexity of detailed AST analysis while providing
the core information needed for README generation.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from models.project_data import (
    ProjectStructure, ModuleInfo, EntryPoint, ClassInfo, FunctionInfo
)
from utils.file_utils import FileInfo, read_file_safely

logger = logging.getLogger(__name__)


class SimpleStructureParser:
    """Simplified structure parser for MVP implementation."""
    
    def __init__(self):
        # Common Python package indicators
        self.package_indicators = [
            '__init__.py', 'setup.py', 'pyproject.toml', 'requirements.txt'
        ]
        
        # Entry point file patterns
        self.entry_point_patterns = [
            'main.py', '__main__.py', 'app.py', 'run.py', 'cli.py',
            'server.py', 'start.py', 'launcher.py'
        ]
        
        # Configuration file patterns
        self.config_patterns = [
            '*.ini', '*.cfg', '*.conf', '*.yaml', '*.yml', '*.json',
            '*.toml', '.env*', 'Dockerfile', 'docker-compose*.yml'
        ]
        
        # Documentation directory patterns
        self.doc_patterns = ['docs', 'doc', 'documentation', 'sphinx']
        
        # Test directory patterns
        self.test_patterns = ['test', 'tests', 'testing']
        
        # Data directory patterns
        self.data_patterns = ['data', 'assets', 'resources', 'static', 'media']
    
    def parse(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectStructure:
        """
        Parse basic project structure information.
        
        Args:
            project_path: Path to project root
            project_files: Dictionary of categorized project files
            
        Returns:
            ProjectStructure object with extracted information
        """
        structure = ProjectStructure(root_path=str(project_path))
        
        try:
            # Detect project layout
            structure.src_layout = self._detect_src_layout(project_path)
            
            # Find main package
            structure.main_package = self._find_main_package(project_path, structure.src_layout)
            
            # Find all packages
            structure.packages = self._find_packages(project_path, project_files)
            
            # Process Python modules
            structure.modules = self._process_python_modules(project_files.get('python', []))
            
            # Find entry points
            structure.entry_points = self._find_entry_points(project_path, project_files)
            
            # Categorize other files
            structure.config_files = self._find_config_files(project_files)
            structure.data_directories = self._find_data_directories(project_path)
            structure.test_directories = self._find_test_directories(project_path)
            structure.doc_directories = self._find_doc_directories(project_path)
            
            # Calculate totals
            structure.total_files = self._calculate_total_files(project_files)
            structure.total_lines = self._calculate_total_lines(structure.modules)
            
            logger.info(f"Parsed project structure: {len(structure.modules)} modules, {len(structure.packages)} packages")
            
        except Exception as e:
            logger.error(f"Error parsing project structure: {e}")
        
        return structure
    
    def _detect_src_layout(self, project_path: Path) -> bool:
        """Detect if project uses src/ layout."""
        src_dir = project_path / 'src'
        if not src_dir.exists() or not src_dir.is_dir():
            return False
        
        # Check if src/ contains Python packages
        python_files = list(src_dir.glob('**/*.py'))
        return len(python_files) > 0
    
    def _find_main_package(self, project_path: Path, src_layout: bool) -> Optional[str]:
        """Find the main package name."""
        # Define search paths based on layout
        if src_layout:
            search_paths = [project_path / 'src']
        else:
            search_paths = [project_path]
        
        # Look for packages (directories with __init__.py)
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for item in search_path.iterdir():
                if (item.is_dir() and 
                    (item / '__init__.py').exists() and
                    not item.name.startswith('.') and
                    item.name not in self.test_patterns):
                    return item.name
        
        # Fallback: use project directory name
        return project_path.name.replace('-', '_').replace(' ', '_')
    
    def _find_packages(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> List[str]:
        """Find all Python packages in the project."""
        packages = []
        
        # Get all Python files
        python_files = project_files.get('python', [])
        
        # Find directories with __init__.py files
        package_dirs = set()
        for file_info in python_files:
            if file_info.path.endswith('__init__.py'):
                package_dir = os.path.dirname(file_info.path)
                # Convert to relative path from project root
                rel_path = os.path.relpath(package_dir, str(project_path))
                if rel_path != '.':
                    # Convert path separators to dots for package name
                    package_name = rel_path.replace(os.sep, '.')
                    package_dirs.add(package_name)
        
        return sorted(package_dirs)
    
    def _process_python_modules(self, python_files: List[FileInfo]) -> List[ModuleInfo]:
        """Process Python files into ModuleInfo objects."""
        modules = []
        
        for file_info in python_files:
            try:
                module_info = self._create_basic_module_info(file_info)
                if module_info:
                    modules.append(module_info)
            except Exception as e:
                logger.error(f"Error processing module {file_info.path}: {e}")
        
        return modules
    
    def _create_basic_module_info(self, file_info: FileInfo) -> Optional[ModuleInfo]:
        """Create basic module information without detailed AST parsing."""
        try:
            # Get module name from file path
            module_name = Path(file_info.path).stem
            
            # Read file content for basic analysis
            content = read_file_safely(file_info.path)
            if not content:
                return None
            
            # Create module info
            module_info = ModuleInfo(
                name=module_name,
                file_path=file_info.path,
                line_count=len(content.splitlines()),
                is_package=module_name == '__init__',
                is_main=module_name in ['__main__', 'main']
            )
            
            # Basic content analysis
            self._analyze_module_content(content, module_info)
            
            return module_info
            
        except Exception as e:
            logger.error(f"Error creating module info for {file_info.path}: {e}")
            return None
    
    def _analyze_module_content(self, content: str, module_info: ModuleInfo) -> None:
        """Perform basic content analysis without AST parsing."""
        lines = content.split('\n')
        
        # Extract module docstring (simple heuristic)
        if len(lines) > 0:
            first_line = lines[0].strip()
            if first_line.startswith('"""') or first_line.startswith("'''"):
                # Find end of docstring
                quote_type = first_line[:3]
                if first_line.count(quote_type) >= 2:
                    # Single line docstring
                    module_info.docstring = first_line.strip(quote_type).strip()
                else:
                    # Multi-line docstring
                    docstring_lines = [first_line.strip(quote_type)]
                    for line in lines[1:]:
                        docstring_lines.append(line)
                        if quote_type in line:
                            docstring_lines[-1] = line.split(quote_type)[0]
                            break
                    module_info.docstring = '\n'.join(docstring_lines).strip()
        
        # Find classes and functions (basic pattern matching)
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Find class definitions
            if stripped.startswith('class ') and ':' in stripped:
                class_name = self._extract_class_name(stripped)
                if class_name and not class_name.startswith('_'):
                    class_info = ClassInfo(
                        name=class_name,
                        line_number=line_num,
                        file_path=module_info.file_path
                    )
                    module_info.classes.append(class_info)
            
            # Find function definitions
            elif stripped.startswith('def ') and ':' in stripped:
                func_name = self._extract_function_name(stripped)
                if func_name:
                    is_public = not func_name.startswith('_')
                    func_info = FunctionInfo(
                        name=func_name,
                        signature=stripped,
                        is_public=is_public,
                        line_number=line_num,
                        file_path=module_info.file_path
                    )
                    module_info.functions.append(func_info)
            
            # Find imports (basic)
            elif stripped.startswith(('import ', 'from ')):
                module_info.imports.append(stripped)
            
            # Find constants (uppercase variables)
            elif '=' in stripped and not stripped.startswith(('class ', 'def ', '#')):
                var_name = stripped.split('=')[0].strip()
                if var_name.isupper() and var_name.isidentifier():
                    constant_info = {
                        'name': var_name,
                        'line_number': line_num
                    }
                    module_info.constants.append(constant_info)
    
    def _extract_class_name(self, line: str) -> Optional[str]:
        """Extract class name from class definition line."""
        try:
            # Basic pattern: class ClassName(...):
            parts = line.split()
            if len(parts) >= 2:
                class_part = parts[1]
                # Remove inheritance part
                if '(' in class_part:
                    class_name = class_part.split('(')[0]
                elif ':' in class_part:
                    class_name = class_part.split(':')[0]
                else:
                    class_name = class_part
                
                return class_name if class_name.isidentifier() else None
        except Exception:
            pass
        return None
    
    def _extract_function_name(self, line: str) -> Optional[str]:
        """Extract function name from function definition line."""
        try:
            # Basic pattern: def function_name(...):
            parts = line.split()
            if len(parts) >= 2:
                func_part = parts[1]
                # Remove parameters part
                if '(' in func_part:
                    func_name = func_part.split('(')[0]
                else:
                    func_name = func_part
                
                return func_name if func_name.isidentifier() else None
        except Exception:
            pass
        return None
    
    def _find_entry_points(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> List[EntryPoint]:
        """Find project entry points."""
        entry_points = []
        
        # Check for common entry point files
        python_files = project_files.get('python', [])
        
        for file_info in python_files:
            file_name = Path(file_info.path).name
            
            # Check if it's a known entry point pattern
            if file_name in self.entry_point_patterns:
                module_name = Path(file_info.path).stem
                entry_point = EntryPoint(
                    name=module_name,
                    module=module_name,
                    script_path=file_info.path,
                    description=f"Entry point: {file_name}"
                )
                entry_points.append(entry_point)
        
        # Check for __main__.py in packages
        for file_info in python_files:
            if file_info.path.endswith('__main__.py'):
                package_dir = os.path.dirname(file_info.path)
                package_name = os.path.basename(package_dir)
                
                entry_point = EntryPoint(
                    name=f"{package_name}.__main__",
                    module=f"{package_name}.__main__",
                    script_path=file_info.path,
                    description=f"Package main entry point"
                )
                entry_points.append(entry_point)
        
        # Check for console scripts in setup files (basic detection)
        self._detect_console_scripts(project_path, entry_points)
        
        return entry_points
    
    def _detect_console_scripts(self, project_path: Path, entry_points: List[EntryPoint]) -> None:
        """Detect console scripts from setup files (simplified)."""
        # Check setup.py for console_scripts
        setup_py = project_path / 'setup.py'
        if setup_py.exists():
            try:
                content = read_file_safely(str(setup_py))
                if content and 'console_scripts' in content:
                    # This is a very basic detection - could be improved
                    entry_point = EntryPoint(
                        name="console_script",
                        module="setup",
                        description="Console script defined in setup.py"
                    )
                    entry_points.append(entry_point)
            except Exception:
                pass
        
        # Check pyproject.toml for scripts
        pyproject_toml = project_path / 'pyproject.toml'
        if pyproject_toml.exists():
            try:
                content = read_file_safely(str(pyproject_toml))
                if content and ('scripts' in content or 'console_scripts' in content):
                    entry_point = EntryPoint(
                        name="project_script",
                        module="pyproject",
                        description="Script defined in pyproject.toml"
                    )
                    entry_points.append(entry_point)
            except Exception:
                pass
    
    def _find_config_files(self, project_files: Dict[str, List[FileInfo]]) -> List[str]:
        """Find configuration files."""
        config_files = []
        
        # Get config files from categorized files
        if 'config' in project_files:
            config_files.extend([f.path for f in project_files['config']])
        
        return config_files
    
    def _find_data_directories(self, project_path: Path) -> List[str]:
        """Find data directories."""
        data_dirs = []
        
        for pattern in self.data_patterns:
            data_dir = project_path / pattern
            if data_dir.exists() and data_dir.is_dir():
                data_dirs.append(str(data_dir.relative_to(project_path)))
        
        return data_dirs
    
    def _find_test_directories(self, project_path: Path) -> List[str]:
        """Find test directories."""
        test_dirs = []
        
        for pattern in self.test_patterns:
            test_dir = project_path / pattern
            if test_dir.exists() and test_dir.is_dir():
                test_dirs.append(str(test_dir.relative_to(project_path)))
        
        return test_dirs
    
    def _find_doc_directories(self, project_path: Path) -> List[str]:
        """Find documentation directories."""
        doc_dirs = []
        
        for pattern in self.doc_patterns:
            doc_dir = project_path / pattern
            if doc_dir.exists() and doc_dir.is_dir():
                doc_dirs.append(str(doc_dir.relative_to(project_path)))
        
        return doc_dirs
    
    def _calculate_total_files(self, project_files: Dict[str, List[FileInfo]]) -> int:
        """Calculate total number of files."""
        return sum(len(files) for files in project_files.values())
    
    def _calculate_total_lines(self, modules: List[ModuleInfo]) -> int:
        """Calculate total lines of code."""
        return sum(module.line_count for module in modules)


# Convenience functions
def extract_project_structure(project_path: str, project_files: Dict[str, List[FileInfo]]) -> ProjectStructure:
    """
    Extract basic project structure information.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        ProjectStructure object
    """
    parser = SimpleStructureParser()
    return parser.parse(Path(project_path), project_files)


def find_main_package(project_path: str) -> Optional[str]:
    """
    Find the main package name for a project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Main package name or None
    """
    parser = SimpleStructureParser()
    
    # Detect layout
    src_layout = parser._detect_src_layout(Path(project_path))
    
    # Find main package
    return parser._find_main_package(Path(project_path), src_layout)


def detect_project_layout(project_path: str) -> Dict[str, Any]:
    """
    Detect project layout and structure.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Dictionary with layout information
    """
    parser = SimpleStructureParser()
    project_path = Path(project_path)
    
    return {
        'src_layout': parser._detect_src_layout(project_path),
        'main_package': parser._find_main_package(project_path, parser._detect_src_layout(project_path)),
        'has_tests': any((project_path / pattern).exists() for pattern in parser.test_patterns),
        'has_docs': any((project_path / pattern).exists() for pattern in parser.doc_patterns),
        'entry_points': len([f for f in project_path.glob('*.py') if f.name in parser.entry_point_patterns])
    }


def get_project_stats(project_path: str, project_files: Dict[str, List[FileInfo]]) -> Dict[str, int]:
    """
    Get basic project statistics.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        Dictionary with project statistics
    """
    parser = SimpleStructureParser()
    
    # Process modules for line count
    python_files = project_files.get('python', [])
    modules = parser._process_python_modules(python_files)
    
    return {
        'total_files': parser._calculate_total_files(project_files),
        'python_files': len(python_files),
        'total_lines': parser._calculate_total_lines(modules),
        'total_modules': len(modules),
        'total_classes': sum(len(module.classes) for module in modules),
        'total_functions': sum(len(module.functions) for module in modules)
    }
