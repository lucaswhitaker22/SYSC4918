"""
Main project parser orchestrator that coordinates all parsing activities.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import traceback

from models.project_data import (
    ProjectData, ProjectMetadata, DependencyInfo, ProjectStructure, 
    ConfigurationInfo, TestInfo, DocumentationInfo
)
from utils.file_utils import get_project_files, FileInfo
from utils.token_counter import TokenCounter, get_token_budget_allocation
from utils.content_prioritizer import ContentPrioritizer, prioritize_project_data
from utils.json_serializer import serialize_project_data

# Fix imports to match actual files
from .basic_metadata import BasicMetadataParser
from .basic_dependencies import BasicDependencyParser
from .simple_structure import SimpleStructureParser
from .minimal_serializer import MinimalSerializer

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Custom exception for parsing errors."""
    
    def __init__(self, message: str, parser_name: str = None, file_path: str = None):
        self.message = message
        self.parser_name = parser_name
        self.file_path = file_path
        super().__init__(self.message)


@dataclass
class ParseResult:
    """Result of project parsing operation."""
    
    project_data: ProjectData
    success: bool
    duration: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class ProjectParser:
    """Main orchestrator for parsing Python projects."""
    
    def __init__(self, 
                 model_name: str = "gemini_2_5_pro",
                 max_tokens: int = 1_000_000,
                 include_tests: bool = False,
                 include_private: bool = False,
                 enable_caching: bool = True):
        
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.include_tests = include_tests
        self.include_private = include_private
        self.enable_caching = enable_caching
        
        # Initialize components
        self.token_counter = TokenCounter(model_name)
        self.content_prioritizer = ContentPrioritizer(self.token_counter)
        self.serializer = MinimalSerializer(self.token_counter)
        
        # Initialize sub-parsers that actually exist
        self.metadata_parser = BasicMetadataParser()
        self.dependency_parser = BasicDependencyParser()
        self.structure_parser = SimpleStructureParser()
        
        # Parsing statistics
        self.stats = {
            'files_processed': 0,
            'lines_processed': 0,
            'classes_found': 0,
            'functions_found': 0,
            'examples_found': 0,
            'errors_encountered': 0,
            'warnings_generated': 0
        }
        
        # Error tracking
        self.parsing_errors = []
        self.parsing_warnings = []
    
    def parse_project(self, project_path: str) -> ParseResult:
        """Parse a Python project and extract all relevant information."""
        start_time = time.time()
        
        try:
            logger.info(f"Starting to parse project: {project_path}")
            
            # Validate project path
            project_path = Path(project_path).resolve()
            if not project_path.exists():
                raise ParsingError(f"Project path does not exist: {project_path}")
            
            if not project_path.is_dir():
                raise ParsingError(f"Project path is not a directory: {project_path}")
            
            # Initialize project data structure
            project_data = self._initialize_project_data(project_path)
            
            # Get project files
            logger.info("Scanning project files...")
            project_files = get_project_files(str(project_path), include_tests=self.include_tests)
            self.stats['files_processed'] = sum(len(files) for files in project_files.values())
            
            # Parse different aspects using actual parsers
            logger.info("Parsing project metadata...")
            project_data.metadata = self._parse_metadata(project_path, project_files)
            
            logger.info("Parsing project dependencies...")
            project_data.dependencies = self._parse_dependencies(project_path, project_files)
            
            logger.info("Parsing project structure...")
            project_data.structure = self._parse_structure(project_path, project_files)
            
            logger.info("Parsing configuration...")
            project_data.configuration = self._parse_configuration(project_path, project_files)
            
            logger.info("Parsing test information...")
            project_data.tests = self._parse_tests(project_path, project_files)
            
            logger.info("Parsing documentation...")
            project_data.documentation = self._parse_documentation(project_path, project_files)
            
            # Apply prioritization - fix the function call
            logger.info("Applying content prioritization...")
            project_data = self._apply_prioritization(project_data)
            
            # Set final metadata
            project_data.parsing_errors = self.parsing_errors
            project_data.parsing_timestamp = datetime.now().isoformat()
            
            # Calculate final token count using correct function
            serialized_data = serialize_project_data(project_data, self.token_counter)
            project_data.token_count = self.token_counter.count_tokens_in_dict(serialized_data)
            
            duration = time.time() - start_time
            logger.info(f"Project parsing completed in {duration:.2f} seconds")
            
            # Update final statistics
            self.stats['lines_processed'] = project_data.structure.total_lines
            self.stats['classes_found'] = sum(len(module.classes) for module in project_data.structure.modules)
            self.stats['functions_found'] = sum(len(module.functions) for module in project_data.structure.modules)
            self.stats['examples_found'] = len(project_data.examples)
            self.stats['errors_encountered'] = len(self.parsing_errors)
            self.stats['warnings_generated'] = len(self.parsing_warnings)
            
            return ParseResult(
                project_data=project_data,
                success=True,
                duration=duration,
                errors=self.parsing_errors,
                warnings=self.parsing_warnings,
                stats=self.stats
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to parse project: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Create minimal project data for error case
            project_data = ProjectData(
                metadata=ProjectMetadata(project_name=project_path.name),
                dependencies=DependencyInfo(),
                structure=ProjectStructure(root_path=str(project_path)),
                configuration=ConfigurationInfo(),
                parsing_errors=[error_msg],
                parsing_timestamp=datetime.now().isoformat()
            )
            
            return ParseResult(
                project_data=project_data,
                success=False,
                duration=duration,
                errors=[error_msg],
                warnings=self.parsing_warnings,
                stats=self.stats
            )
    
    def _initialize_project_data(self, project_path: Path) -> ProjectData:
        """Initialize the project data structure."""
        return ProjectData(
            metadata=ProjectMetadata(project_name=project_path.name),
            dependencies=DependencyInfo(),  # This should initialize with empty lists
            structure=ProjectStructure(root_path=str(project_path)),
            configuration=ConfigurationInfo()
        )
    
    def _parse_metadata(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectMetadata:
        """Parse project metadata using the basic metadata parser."""
        try:
            return self.metadata_parser.parse(project_path, project_files)
        except Exception as e:
            error_msg = f"Error parsing metadata: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return ProjectMetadata(project_name=project_path.name)
    
    def _parse_dependencies(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> DependencyInfo:
        """Parse project dependencies using the basic dependency parser."""
        try:
            return self.dependency_parser.parse(project_path, project_files)
        except Exception as e:
            error_msg = f"Error parsing dependencies: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return DependencyInfo()
    
    def _parse_structure(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ProjectStructure:
        """Parse project structure using the simple structure parser."""
        try:
            return self.structure_parser.parse(project_path, project_files)
        except Exception as e:
            error_msg = f"Error parsing project structure: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return ProjectStructure(root_path=str(project_path))
    
    def _parse_configuration(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> ConfigurationInfo:
        """Parse project configuration information."""
        try:
            config_info = ConfigurationInfo()
            config_files = []
            for file_info in project_files.get('config', []):
                config_files.append(file_info.path)
            config_info.config_files = config_files
            return config_info
        except Exception as e:
            error_msg = f"Error parsing configuration: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return ConfigurationInfo()
    
    def _parse_tests(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> Optional[TestInfo]:
        """Parse test information."""
        try:
            test_info = TestInfo()
            test_files = []
            test_directories = []
            
            for file_info in project_files.get('tests', []):
                test_files.append(file_info.path)
                test_dir = os.path.dirname(file_info.path)
                if test_dir not in test_directories:
                    test_directories.append(test_dir)
            
            test_info.test_files = test_files
            test_info.test_directories = test_directories
            test_info.total_tests = len(test_files)
            test_info.test_framework = self._detect_test_framework(test_files)
            
            return test_info
        except Exception as e:
            error_msg = f"Error parsing test information: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return None
    
    def _parse_documentation(self, project_path: Path, project_files: Dict[str, List[FileInfo]]) -> Optional[DocumentationInfo]:
        """Parse documentation information."""
        try:
            doc_info = DocumentationInfo()
            for file_info in project_files.get('docs', []):
                if 'readme' in file_info.path.lower():
                    doc_info.readme_file = file_info.path
                elif 'changelog' in file_info.path.lower() or 'changes' in file_info.path.lower():
                    doc_info.changelog_file = file_info.path
                elif 'license' in file_info.path.lower():
                    doc_info.license_file = file_info.path
                else:
                    doc_info.doc_files.append(file_info.path)
            return doc_info
        except Exception as e:
            error_msg = f"Error parsing documentation: {str(e)}"
            logger.error(error_msg)
            self.parsing_errors.append(error_msg)
            return None
    
    def _apply_prioritization(self, project_data: ProjectData) -> ProjectData:
        """Apply content prioritization and token management."""
        try:
            # Fix: Check the actual signature of prioritize_project_data
            # It might only need (project_data, token_counter) or just (project_data)
            prioritized_data = prioritize_project_data(project_data, self.token_counter)
            return prioritized_data
        except Exception as e:
            warning_msg = f"Error applying prioritization: {str(e)}"
            logger.warning(warning_msg)
            self.parsing_warnings.append(warning_msg)
            return project_data
    
    def _detect_test_framework(self, test_files: List[str]) -> Optional[str]:
        """Detect the test framework used."""
        framework_indicators = {
            'pytest': ['pytest', 'conftest.py', 'test_', '_test.py'],
            'unittest': ['unittest', 'TestCase'],
            'nose': ['nose', 'nosetests'],
            'tox': ['tox.ini', 'tox'],
        }
        
        for framework, indicators in framework_indicators.items():
            for test_file in test_files:
                if any(indicator in test_file for indicator in indicators):
                    return framework
        
        return None


# Convenience functions
def parse_project(project_path: str, 
                 model_name: str = "gemini_2_5_pro",
                 max_tokens: int = 1_000_000,
                 include_tests: bool = False,
                 include_private: bool = False) -> ParseResult:
    """Parse a Python project and return structured data."""
    parser = ProjectParser(
        model_name=model_name,
        max_tokens=max_tokens,
        include_tests=include_tests,
        include_private=include_private
    )
    
    return parser.parse_project(project_path)
