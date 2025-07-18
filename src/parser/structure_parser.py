"""
Project structure parser for analyzing Python project organization.

This module analyzes the overall structure of Python projects, identifying
main packages, entry points, directory organization, and project layout patterns.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import configparser
import logging

from models.project_data import ProjectStructure, ModuleInfo, EntryPoint
from utils.file_utils import read_file_safely, is_python_file, FileInfo

logger = logging.getLogger(__name__)

# Try to import TOML parsers
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None


class StructureParser:
    """Parser for analyzing Python project structure."""
    
    def __init__(self):
        # Common entry point indicators
        self.entry_point_patterns = [
            'main.py', '__main__.py', 'app.py', 'cli.py', 'run.py',
            'manage.py', 'wsgi.py', 'asgi.py', 'server.py'
        ]
        
        # Common package structures
        self.package_indicators = [
            '__init__.py', 'setup.py', 'pyproject.toml', 'setup.cfg'
        ]
        
        # Directory patterns to analyze
        self.important_dirs = {
            'src': 'source code',
            'lib': 'library code',
            'tests': 'test files',
            'test': 'test files',
            'docs': 'documentation',
            'doc': 'documentation', 
            'examples': 'example code',
            'example': 'example code',
            'scripts': 'utility scripts',
            'bin': 'executable scripts',
            'data': 'data files',
            'assets': 'static assets',
            'static': 'static files',
            'templates': 'template files',
            'config': 'configuration files',
            'configs': 'configuration files',
        }
    
    def parse(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectStructure:
        """
        Parse project structure from project directory.
        
        Args:
            project_path: Path to project root
            project_files: Dictionary of categorized project files
            
        Returns:
            ProjectStructure object with analyzed structure
        """
        try:
            structure = ProjectStructure(root_path=str(project_path))
            
            # Analyze layout type
            structure.src_layout = self._detect_src_layout(project_path)
            
            # Find main package
            structure.main_package = self._find_main_package(project_path, project_files)
            
            # Discover packages
            structure.packages = self._discover_packages(project_path, project_files)
            
            # Create module info objects
            structure.modules = self._create_module_info_list(project_files)
            
            # Find entry points
            structure.entry_points = self._find_entry_points(project_path, project_files)
            
            # Categorize directories
            structure.config_files = self._find_config_files(project_path)
            structure.data_directories = self._find_data_directories(project_path)
            structure.test_directories = self._find_test_directories(project_path)
            structure.doc_directories = self._find_doc_directories(project_path)
            
            # Calculate statistics
            structure.total_files = sum(len(files) for files in project_files.values())
            structure.total_lines = self._calculate_total_lines(project_files)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error analyzing project structure: {e}")
            return ProjectStructure(root_path=str(project_path))
    
    def _detect_src_layout(self, project_path: Path) -> bool:
        """Detect if project uses src/ layout."""
        src_dir = project_path / 'src'
        return src_dir.exists() and src_dir.is_dir()
    
    def _find_main_package(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> Optional[str]:
        """Find the main package of the project."""
        # Look for packages in order of preference
        candidates = []
        
        # Check for src/ layout
        if self._detect_src_layout(project_path):
            src_dir = project_path / 'src'
            for item in src_dir.iterdir():
                if item.is_dir() and (item / '__init__.py').exists():
                    candidates.append(item.name)
        
        # Check for direct package layout
        for item in project_path.iterdir():
            if (item.is_dir() and 
                (item / '__init__.py').exists() and 
                not item.name.startswith('.') and
                item.name not in ['tests', 'test', 'docs', 'doc', 'examples']):
                candidates.append(item.name)
        
        # Prefer package with same name as project directory
        project_name = project_path.name.replace('-', '_')
        if project_name in candidates:
            return project_name
        
        # Return first candidate
        return candidates[0] if candidates else None
    
    def _discover_packages(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> List[str]:
        """Discover all Python packages in the project."""
        packages = []
        
        for file_info in project_files.get('python', []):
            file_path = Path(file_info.path)
            
            # Check if it's an __init__.py file
            if file_path.name == '__init__.py':
                # Get package name from directory
                package_dir = file_path.parent
                rel_path = package_dir.relative_to(project_path)
                
                # Convert path to package name
                package_name = str(rel_path).replace(os.sep, '.')
                
                # Skip if it's in common non-package directories
                if not any(part in ['tests', 'test', 'docs', 'doc', 'examples'] 
                          for part in rel_path.parts):
                    packages.append(package_name)
        
        return sorted(packages)
    
    def _create_module_info_list(self, project_files: Dict[str, List[FileInfo]]) -> List[ModuleInfo]:
        """Create ModuleInfo objects for Python files."""
        modules = []
        
        for file_info in project_files.get('python', []):
            if is_python_file(file_info.path):
                module_name = Path(file_info.path).stem
                
                # Create basic module info (will be populated by code parser)
                module_info = ModuleInfo(
                    name=module_name,
                    file_path=file_info.path,
                    is_package=module_name == '__init__',
                    is_main=module_name in ['__main__', 'main'],
                    line_count=self._count_lines_in_file(file_info.path)
                )
                
                modules.append(module_info)
        
        return modules
    
    def _find_entry_points(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> List[EntryPoint]:
        """Find project entry points."""
        entry_points = []
        
        # Check for common entry point files
        for file_info in project_files.get('python', []):
            file_path = Path(file_info.path)
            
            if file_path.name in self.entry_point_patterns:
                entry_point = EntryPoint(
                    name=file_path.stem,
                    module=self._path_to_module_name(file_path, project_path),
                    script_path=file_info.path,
                    description=f"Entry point: {file_path.name}"
                )
                entry_points.append(entry_point)
        
        # Check setup.py for console scripts
        setup_py = project_path / 'setup.py'
        if setup_py.exists():
            console_scripts = self._extract_console_scripts_from_setup_py(setup_py)
            entry_points.extend(console_scripts)
        
        # Check pyproject.toml for scripts
        pyproject_toml = project_path / 'pyproject.toml'
        if pyproject_toml.exists():
            scripts = self._extract_scripts_from_pyproject_toml(pyproject_toml)
            entry_points.extend(scripts)
        
        return entry_points
    
    def _extract_console_scripts_from_setup_py(self, setup_py: Path) -> List[EntryPoint]:
        """Extract console scripts from setup.py."""
        entry_points = []
        
        try:
            content = read_file_safely(str(setup_py))
            if not content:
                return entry_points
            
            # Look for entry_points in setup() call
            # This is a simplified approach - in practice you'd want to parse AST
            entry_points_match = re.search(
                r'entry_points\s*=\s*{[^}]*["\']console_scripts["\']\s*:\s*\[(.*?)\]',
                content, re.DOTALL
            )
            
            if entry_points_match:
                scripts_text = entry_points_match.group(1)
                # Extract individual script definitions
                for match in re.finditer(r'["\']([^"\']+)\s*=\s*([^"\']+)["\']', scripts_text):
                    script_name = match.group(1)
                    module_func = match.group(2)
                    
                    if ':' in module_func:
                        module, func = module_func.split(':', 1)
                        entry_point = EntryPoint(
                            name=script_name,
                            module=module,
                            function=func,
                            description=f"Console script: {script_name}"
                        )
                        entry_points.append(entry_point)
        
        except Exception as e:
            logger.error(f"Error extracting console scripts from setup.py: {e}")
        
        return entry_points
    
    def _extract_scripts_from_pyproject_toml(self, pyproject_toml: Path) -> List[EntryPoint]:
        """Extract scripts from pyproject.toml."""
        entry_points = []
        
        if not tomllib:
            return entry_points
        
        try:
            content = read_file_safely(str(pyproject_toml))
            if not content:
                return entry_points
            
            data = tomllib.loads(content)
            
            # Check [project.scripts] section
            if 'project' in data and 'scripts' in data['project']:
                scripts = data['project']['scripts']
                for script_name, module_func in scripts.items():
                    if ':' in module_func:
                        module, func = module_func.split(':', 1)
                        entry_point = EntryPoint(
                            name=script_name,
                            module=module,
                            function=func,
                            description=f"Project script: {script_name}"
                        )
                        entry_points.append(entry_point)
            
            # Check [tool.poetry.scripts] section
            if 'tool' in data and 'poetry' in data['tool'] and 'scripts' in data['tool']['poetry']:
                scripts = data['tool']['poetry']['scripts']
                for script_name, module_func in scripts.items():
                    if ':' in module_func:
                        module, func = module_func.split(':', 1)
                        entry_point = EntryPoint(
                            name=script_name,
                            module=module,
                            function=func,
                            description=f"Poetry script: {script_name}"
                        )
                        entry_points.append(entry_point)
        
        except Exception as e:
            logger.error(f"Error extracting scripts from pyproject.toml: {e}")
        
        return entry_points
    
    def _find_config_files(self, project_path: Path) -> List[str]:
        """Find configuration files in the project."""
        config_files = []
        
        # Common configuration file patterns
        config_patterns = [
            '*.ini', '*.cfg', '*.conf', '*.config', '*.yaml', '*.yml',
            '*.json', '*.toml', '.env*', '*.properties'
        ]
        
        for pattern in config_patterns:
            for file_path in project_path.glob(f"**/{pattern}"):
                if file_path.is_file():
                    config_files.append(str(file_path))
        
        # Add specific configuration files
        specific_configs = [
            'setup.cfg', 'pyproject.toml', 'tox.ini', 'pytest.ini',
            '.flake8', '.pylintrc', 'mypy.ini', '.pre-commit-config.yaml'
        ]
        
        for config_name in specific_configs:
            config_path = project_path / config_name
            if config_path.exists():
                config_files.append(str(config_path))
        
        return sorted(config_files)
    
    def _find_data_directories(self, project_path: Path) -> List[str]:
        """Find data directories in the project."""
        data_dirs = []
        
        data_patterns = ['data', 'assets', 'static', 'resources', 'fixtures']
        
        for pattern in data_patterns:
            for dir_path in project_path.glob(f"**/{pattern}"):
                if dir_path.is_dir():
                    data_dirs.append(str(dir_path))
        
        return sorted(data_dirs)
    
    def _find_test_directories(self, project_path: Path) -> List[str]:
        """Find test directories in the project."""
        test_dirs = []
        
        test_patterns = ['tests', 'test', 'testing']
        
        for pattern in test_patterns:
            for dir_path in project_path.glob(f"**/{pattern}"):
                if dir_path.is_dir():
                    test_dirs.append(str(dir_path))
        
        return sorted(test_dirs)
    
    def _find_doc_directories(self, project_path: Path) -> List[str]:
        """Find documentation directories in the project."""
        doc_dirs = []
        
        doc_patterns = ['docs', 'doc', 'documentation', 'sphinx']
        
        for pattern in doc_patterns:
            for dir_path in project_path.glob(f"**/{pattern}"):
                if dir_path.is_dir():
                    doc_dirs.append(str(dir_path))
        
        return sorted(doc_dirs)
    
    def _path_to_module_name(self, file_path: Path, project_path: Path) -> str:
        """Convert file path to module name."""
        try:
            rel_path = file_path.relative_to(project_path)
            
            # Remove .py extension
            if rel_path.suffix == '.py':
                rel_path = rel_path.with_suffix('')
            
            # Convert to module name
            module_name = str(rel_path).replace(os.sep, '.')
            
            # Handle __init__.py files
            if module_name.endswith('.__init__'):
                module_name = module_name[:-9]
            
            return module_name
        
        except ValueError:
            # File is not under project path
            return file_path.stem
    
    def _calculate_total_lines(self, project_files: Dict[str, List[FileInfo]]) -> int:
        """Calculate total lines of code in the project."""
        total_lines = 0
        
        for file_info in project_files.get('python', []):
            total_lines += self._count_lines_in_file(file_info.path)
        
        return total_lines
    
    def _count_lines_in_file(self, file_path: str) -> int:
        """Count lines in a file."""
        try:
            content = read_file_safely(file_path)
            if content:
                return len(content.splitlines())
        except Exception:
            pass
        return 0


# Convenience functions
def analyze_project_structure(project_path: str, project_files: Dict[str, List[FileInfo]]) -> ProjectStructure:
    """
    Analyze the structure of a Python project.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        ProjectStructure object
    """
    parser = StructureParser()
    return parser.parse(Path(project_path), project_files)


def find_entry_points(project_path: str) -> List[EntryPoint]:
    """
    Find entry points in a Python project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        List of EntryPoint objects
    """
    parser = StructureParser()
    
    # Get project files (simplified for this function)
    from ..utils.file_utils import get_project_files
    project_files = get_project_files(project_path)
    
    return parser._find_entry_points(Path(project_path), project_files)


def categorize_directories(project_path: str) -> Dict[str, List[str]]:
    """
    Categorize directories in a Python project.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Dictionary mapping categories to directory lists
    """
    parser = StructureParser()
    project_path = Path(project_path)
    
    return {
        'config': parser._find_config_files(project_path),
        'data': parser._find_data_directories(project_path),
        'tests': parser._find_test_directories(project_path),
        'docs': parser._find_doc_directories(project_path)
    }
