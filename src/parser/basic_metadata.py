"""
Basic metadata parser for extracting essential project information.

This simplified module focuses on core metadata extraction from setup.py and 
pyproject.toml files for MVP implementation, avoiding the complexity of the 
full metadata parser.
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from models.project_data import ProjectMetadata, ProjectType, LicenseType
from utils.file_utils import read_file_safely, FileInfo

logger = logging.getLogger(__name__)

# Try to import TOML parser
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None


class BasicMetadataParser:
    """Simplified metadata parser for MVP implementation."""
    
    def __init__(self):
        # License detection patterns
        self.license_patterns = {
            'MIT': r'MIT\s+License',
            'Apache-2.0': r'Apache\s+License\s+2\.0',
            'GPL-3.0': r'GNU\s+General\s+Public\s+License\s+v3',
            'BSD-3-Clause': r'BSD\s+3-Clause',
        }
        
        # Project type indicators
        self.project_type_indicators = {
            ProjectType.CLI_TOOL: ['cli', 'command', 'tool', 'console_scripts'],
            ProjectType.WEB_APPLICATION: ['flask', 'django', 'fastapi', 'web', 'http'],
            ProjectType.LIBRARY: ['library', 'lib', 'package'],
            ProjectType.API: ['api', 'rest', 'graphql'],
        }
    
    def parse(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectMetadata:
        """
        Parse basic project metadata from available sources.
        
        Args:
            project_path: Path to project root
            project_files: Dictionary of categorized project files
            
        Returns:
            ProjectMetadata object with extracted information
        """
        # Initialize with project name from directory
        metadata = ProjectMetadata(project_name=project_path.name)
        
        # Parse from different sources in priority order
        if self._parse_pyproject_toml(project_path, metadata):
            logger.info("Metadata extracted from pyproject.toml")
        elif self._parse_setup_py(project_path, metadata):
            logger.info("Metadata extracted from setup.py")
        else:
            logger.warning("No standard metadata files found, using defaults")
        
        # Detect project type
        metadata.project_type = self._detect_project_type(project_path, metadata)
        
        # Detect license
        if not metadata.license:
            metadata.license = self._detect_license(project_path)
        
        return metadata
    
    def _parse_pyproject_toml(self, project_path: Path, metadata: ProjectMetadata) -> bool:
        """Parse metadata from pyproject.toml file."""
        if not tomllib:
            logger.warning("TOML parser not available")
            return False
        
        pyproject_file = project_path / 'pyproject.toml'
        if not pyproject_file.exists():
            return False
        
        try:
            content = read_file_safely(str(pyproject_file))
            if not content:
                return False
            
            data = tomllib.loads(content)
            
            # Parse [project] section (PEP 621 - modern standard)
            if 'project' in data:
                project_data = data['project']
                
                metadata.project_name = project_data.get('name', metadata.project_name)
                metadata.description = project_data.get('description')
                metadata.version = project_data.get('version')
                
                # Authors
                authors = project_data.get('authors', [])
                if authors and isinstance(authors, list) and len(authors) > 0:
                    first_author = authors[0]
                    if isinstance(first_author, dict):
                        metadata.author = first_author.get('name')
                        metadata.author_email = first_author.get('email')
                
                # License
                license_info = project_data.get('license')
                if license_info:
                    if isinstance(license_info, dict):
                        license_text = license_info.get('text', '')
                    else:
                        license_text = str(license_info)
                    metadata.license = self._parse_license_string(license_text)
                
                # URLs
                urls = project_data.get('urls', {})
                metadata.homepage = urls.get('Homepage') or urls.get('homepage')
                metadata.repository = urls.get('Repository') or urls.get('repository')
                
                # Keywords
                keywords = project_data.get('keywords', [])
                if isinstance(keywords, list):
                    metadata.keywords = keywords
                
                # Python version
                metadata.python_version = project_data.get('requires-python')
                
                return True
            
            # Parse [tool.poetry] section (Poetry format)
            elif 'tool' in data and 'poetry' in data['tool']:
                poetry_data = data['tool']['poetry']
                
                metadata.project_name = poetry_data.get('name', metadata.project_name)
                metadata.description = poetry_data.get('description')
                metadata.version = poetry_data.get('version')
                metadata.author = poetry_data.get('author')
                metadata.license = self._parse_license_string(poetry_data.get('license', ''))
                metadata.homepage = poetry_data.get('homepage')
                metadata.repository = poetry_data.get('repository')
                
                # Keywords
                keywords = poetry_data.get('keywords', [])
                if isinstance(keywords, list):
                    metadata.keywords = keywords
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml: {e}")
            return False
    
    def _parse_setup_py(self, project_path: Path, metadata: ProjectMetadata) -> bool:
        """Parse metadata from setup.py file using AST."""
        setup_file = project_path / 'setup.py'
        if not setup_file.exists():
            return False
        
        try:
            content = read_file_safely(str(setup_file))
            if not content:
                return False
            
            # Parse as AST to extract setup() call arguments
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if this is a setup() call
                    if ((isinstance(node.func, ast.Name) and node.func.id == 'setup') or
                        (isinstance(node.func, ast.Attribute) and node.func.attr == 'setup')):
                        
                        # Extract metadata from keyword arguments
                        for keyword in node.keywords:
                            self._extract_setup_metadata(keyword, metadata)
                        
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error parsing setup.py: {e}")
            return False
    
    def _extract_setup_metadata(self, keyword: ast.keyword, metadata: ProjectMetadata) -> None:
        """Extract metadata from setup() keyword arguments."""
        try:
            arg_name = keyword.arg
            
            if arg_name == 'name':
                if isinstance(keyword.value, ast.Constant):
                    metadata.project_name = keyword.value.value
            
            elif arg_name == 'description':
                if isinstance(keyword.value, ast.Constant):
                    metadata.description = keyword.value.value
            
            elif arg_name == 'version':
                if isinstance(keyword.value, ast.Constant):
                    metadata.version = keyword.value.value
            
            elif arg_name == 'author':
                if isinstance(keyword.value, ast.Constant):
                    metadata.author = keyword.value.value
            
            elif arg_name == 'author_email':
                if isinstance(keyword.value, ast.Constant):
                    metadata.author_email = keyword.value.value
            
            elif arg_name == 'license':
                if isinstance(keyword.value, ast.Constant):
                    metadata.license = self._parse_license_string(keyword.value.value)
            
            elif arg_name == 'url':
                if isinstance(keyword.value, ast.Constant):
                    metadata.homepage = keyword.value.value
            
            elif arg_name == 'keywords':
                # Keywords can be string or list
                if isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, str):
                        metadata.keywords = [k.strip() for k in keyword.value.value.split(',')]
                elif isinstance(keyword.value, ast.List):
                    keywords = []
                    for item in keyword.value.elts:
                        if isinstance(item, ast.Constant):
                            keywords.append(item.value)
                    metadata.keywords = keywords
            
            elif arg_name == 'python_requires':
                if isinstance(keyword.value, ast.Constant):
                    metadata.python_version = keyword.value.value
            
        except Exception as e:
            logger.debug(f"Error extracting metadata for {keyword.arg}: {e}")
    
    def _detect_project_type(self, project_path: Path, metadata: ProjectMetadata) -> ProjectType:
        """Detect project type based on various indicators."""
        try:
            # Check keywords first
            if metadata.keywords:
                keywords_str = ' '.join(metadata.keywords).lower()
                for project_type, indicators in self.project_type_indicators.items():
                    if any(indicator in keywords_str for indicator in indicators):
                        return project_type
            
            # Check description
            if metadata.description:
                description_lower = metadata.description.lower()
                for project_type, indicators in self.project_type_indicators.items():
                    if any(indicator in description_lower for indicator in indicators):
                        return project_type
            
            # Check for specific files that indicate project type
            if (project_path / 'main.py').exists() or (project_path / '__main__.py').exists():
                return ProjectType.APPLICATION
            
            # Check for CLI indicators in setup.py
            if self._has_console_scripts(project_path):
                return ProjectType.CLI_TOOL
            
            # Check for web framework files
            web_indicators = ['app.py', 'wsgi.py', 'asgi.py', 'manage.py']
            if any((project_path / indicator).exists() for indicator in web_indicators):
                return ProjectType.WEB_APPLICATION
            
            # Default to library if nothing else matches
            return ProjectType.LIBRARY
            
        except Exception as e:
            logger.debug(f"Error detecting project type: {e}")
            return ProjectType.UNKNOWN
    
    def _has_console_scripts(self, project_path: Path) -> bool:
        """Check if project has console scripts defined."""
        # Check setup.py for console_scripts
        setup_file = project_path / 'setup.py'
        if setup_file.exists():
            try:
                content = read_file_safely(str(setup_file))
                if content and 'console_scripts' in content:
                    return True
            except Exception:
                pass
        
        # Check pyproject.toml for scripts
        pyproject_file = project_path / 'pyproject.toml'
        if pyproject_file.exists() and tomllib:
            try:
                content = read_file_safely(str(pyproject_file))
                if content:
                    data = tomllib.loads(content)
                    if 'project' in data and 'scripts' in data['project']:
                        return True
                    if ('tool' in data and 'poetry' in data['tool'] and 
                        'scripts' in data['tool']['poetry']):
                        return True
            except Exception:
                pass
        
        return False
    
    def _detect_license(self, project_path: Path) -> Optional[LicenseType]:
        """Detect license from LICENSE file or other sources."""
        # Common license file names
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING', 'COPYING.txt']
        
        for license_file in license_files:
            file_path = project_path / license_file
            if file_path.exists():
                try:
                    content = read_file_safely(str(file_path))
                    if content:
                        return self._parse_license_string(content)
                except Exception:
                    continue
        
        return None
    
    def _parse_license_string(self, license_text: str) -> Optional[LicenseType]:
        """Parse license type from license text."""
        if not license_text:
            return None
        
        license_text = license_text.strip()
        
        # Direct matches
        license_mappings = {
            'MIT': LicenseType.MIT,
            'Apache-2.0': LicenseType.APACHE_2,
            'Apache 2.0': LicenseType.APACHE_2,
            'GPL-3.0': LicenseType.GPL_V3,
            'GPLv3': LicenseType.GPL_V3,
            'BSD-3-Clause': LicenseType.BSD_3,
            'BSD': LicenseType.BSD_3,
            'Unlicense': LicenseType.UNLICENSE,
        }
        
        # Check for direct matches first
        for key, license_type in license_mappings.items():
            if key.lower() in license_text.lower():
                return license_type
        
        # Pattern matching for longer license texts
        for license_name, pattern in self.license_patterns.items():
            if re.search(pattern, license_text, re.IGNORECASE):
                return LicenseType(license_name)
        
        return LicenseType.UNKNOWN


# Convenience functions
def extract_basic_metadata(project_path: str, project_files: Dict[str, List[FileInfo]]) -> ProjectMetadata:
    """
    Extract basic metadata from a project directory.
    
    Args:
        project_path: Path to project root
        project_files: Dictionary of categorized project files
        
    Returns:
        ProjectMetadata object
    """
    parser = BasicMetadataParser()
    return parser.parse(Path(project_path), project_files)


def get_project_name(project_path: str) -> str:
    """
    Get project name from metadata files or directory name.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Project name string
    """
    parser = BasicMetadataParser()
    metadata = parser.parse(Path(project_path), {})
    return metadata.project_name


def detect_project_version(project_path: str) -> Optional[str]:
    """
    Detect project version from metadata files.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Version string or None
    """
    parser = BasicMetadataParser()
    metadata = parser.parse(Path(project_path), {})
    return metadata.version
