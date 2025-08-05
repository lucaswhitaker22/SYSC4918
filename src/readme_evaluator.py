#!/usr/bin/env python3
"""
Advanced README Accuracy Evaluator

Evaluates comprehensive READMEs with complex structures, nested sections,
code blocks, and detailed content analysis.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from difflib import SequenceMatcher
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add src directory for imports
current_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

try:
    from parser.project_parser import parse_project
except ImportError as e:
    print(f"❌ Error: Could not import parsing modules: {e}")
    sys.exit(1)


@dataclass
class EvaluationResults:
    """Comprehensive evaluation results."""
    overall_accuracy: float = 0.0
    
    # Core sections
    title_present: bool = False
    description_present: bool = False
    description_quality: float = 0.0
    installation_present: bool = False
    usage_present: bool = False
    
    # Advanced sections
    table_of_contents_present: bool = False
    features_present: bool = False  
    project_structure_present: bool = False
    api_documentation_present: bool = False
    dependencies_present: bool = False
    contributing_present: bool = False
    license_present: bool = False
    
    # Content quality metrics
    code_examples_count: int = 0
    cli_examples_count: int = 0
    python_examples_count: int = 0
    badges_count: int = 0
    
    # Coverage metrics
    dependency_coverage: float = 0.0
    api_coverage: float = 0.0
    entry_point_coverage: float = 0.0
    
    # Structure analysis
    heading_levels_used: List[int] = None
    sections_found: List[str] = None
    total_content_length: int = 0
    
    def __post_init__(self):
        if self.heading_levels_used is None:
            self.heading_levels_used = []
        if self.sections_found is None:
            self.sections_found = []


class AdvancedREADMEParser:
    """Advanced README parser for complex documents."""
    
    def __init__(self, content: str):
        self.content = content.strip()
        self.lines = self.content.splitlines()
        self.headings = self._parse_headings()
        self.sections = self._build_section_map()
        
    def _parse_headings(self) -> List[Dict[str, Any]]:
        """Parse all headings with levels and positions."""
        headings = []
        
        for i, line in enumerate(self.lines):
            line = line.strip()
            
            # Markdown ATX headings (# ## ###)
            if line.startswith('#'):
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                if level <= 6:  # Valid heading levels
                    text = line[level:].strip()
                    headings.append({
                        'level': level,
                        'text': text,
                        'normalized': self._normalize_text(text),
                        'line_number': i
                    })
            
            # Setext headings (underlined with = or -)
            elif i + 1 < len(self.lines):
                next_line = self.lines[i + 1].strip()
                if re.match(r'^=+$', next_line):
                    headings.append({
                        'level': 1,
                        'text': line,
                        'normalized': self._normalize_text(line),
                        'line_number': i
                    })
                elif re.match(r'^-+$', next_line):
                    headings.append({
                        'level': 2,
                        'text': line,
                        'normalized': self._normalize_text(line),
                        'line_number': i
                    })
        
        return headings
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove version numbers, special chars, etc.
        text = re.sub(r'v?\d+\.\d+(\.\d+)?', '', text)  # Remove versions
        text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars
        text = re.sub(r'\s+', ' ', text).strip().lower()
        return text
    
    def _build_section_map(self) -> Dict[str, str]:
        """Build map of normalized section names to content."""
        sections = {}
        
        for i, heading in enumerate(self.headings):
            start_line = heading['line_number'] + 1
            
            # Find end of this section (next heading of same or higher level)
            end_line = len(self.lines)
            for j in range(i + 1, len(self.headings)):
                next_heading = self.headings[j]
                if next_heading['level'] <= heading['level']:
                    end_line = next_heading['line_number']
                    break
            
            # Extract content
            content_lines = self.lines[start_line:end_line]
            content = '\n'.join(content_lines).strip()
            
            sections[heading['normalized']] = content
            
        return sections
    
    def get_section(self, *names: str) -> str:
        """Get section content by trying multiple names."""
        normalized_names = [self._normalize_text(name) for name in names]
        
        # Direct matches first
        for name in normalized_names:
            if name in self.sections:
                return self.sections[name]
        
        # Fuzzy matching
        for name in normalized_names:
            for section_key in self.sections:
                if name in section_key or section_key in name:
                    return self.sections[section_key]
                
                # Partial word matching
                name_words = set(name.split())
                section_words = set(section_key.split())
                if name_words.intersection(section_words):
                    return self.sections[section_key]
        
        return ""
    
    def has_section(self, *names: str) -> bool:
        """Check if any of the named sections exist."""
        return bool(self.get_section(*names))
    
    def count_badges(self) -> int:
        """Count shield/badge images."""
        badge_patterns = [
            r'!\[.*\]\(https://img\.shields\.io/',
            r'!\[.*\]\(https://badge\.fury\.io/',
            r'!\[.*\]\(.*\.svg\)',
            r'\[!\[.*\]\(.*\)\]\(.*\)',  # Linked badges
        ]
        
        count = 0
        for pattern in badge_patterns:
            count += len(re.findall(pattern, self.content))
        
        return count
    
    def extract_code_blocks(self) -> Dict[str, List[str]]:
        """Extract all code blocks categorized by language."""
        blocks = defaultdict(list)
        
        # Fenced code blocks
        pattern = r'``````'
        matches = re.findall(pattern, self.content, re.DOTALL)
        
        for lang, code in matches:
            lang = lang.lower() if lang else 'unknown'
            blocks[lang].append(code.strip())
        
        # Indented code blocks (basic detection)
        lines = self.content.split('\n')
        in_indented_block = False
        current_block = []
        
        for line in lines:
            if re.match(r'^    \S', line):  # 4+ spaces, not just whitespace
                if not in_indented_block:
                    in_indented_block = True
                    current_block = []
                current_block.append(line[4:])  # Remove 4 spaces
            else:
                if in_indented_block and current_block:
                    blocks['indented'].append('\n'.join(current_block).strip())
                in_indented_block = False
        
        return dict(blocks)
    
    def classify_code_blocks(self) -> Dict[str, int]:
        """Classify code blocks by type."""
        blocks = self.extract_code_blocks()
        classification = {'cli': 0, 'python': 0, 'other': 0, 'total': 0}
        
        for lang, code_list in blocks.items():
            for code in code_list:
                classification['total'] += 1
                
                if lang in ['bash', 'sh', 'shell', 'console', 'terminal']:
                    classification['cli'] += 1
                elif lang in ['python', 'py']:
                    classification['python'] += 1
                elif 'pip install' in code or code.strip().startswith('$'):
                    classification['cli'] += 1
                elif any(keyword in code for keyword in ['import ', 'def ', 'class ', 'from ']):
                    classification['python'] += 1
                else:
                    classification['other'] += 1
        
        return classification
    
    def analyze_table_of_contents(self) -> Dict[str, Any]:
        """Analyze table of contents quality."""
        toc_content = self.get_section('table of contents', 'contents', 'toc')
        
        if not toc_content:
            return {'present': False, 'links': 0, 'structure': 'none'}
        
        # Count markdown links
        links = re.findall(r'\[.*?\]\(#.*?\)', toc_content)
        
        # Analyze structure depth
        lines = toc_content.split('\n')
        max_indent = 0
        for line in lines:
            if line.strip().startswith('-') or line.strip().startswith('*'):
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)
        
        structure = 'flat' if max_indent <= 2 else 'nested'
        
        return {
            'present': True,
            'links': len(links),
            'structure': structure,
            'lines': len([l for l in lines if l.strip()])
        }
    
    def extract_dependencies(self) -> Set[str]:
        """Extract dependencies from multiple sections."""
        deps = set()
        
        # Check dependencies sections
        dep_content = self.get_section(
            'dependencies', 'requirements', 'prerequisites',
            'core dependencies', 'development dependencies'
        )
        
        if dep_content:
            # Extract from bullet lists
            for line in dep_content.split('\n'):
                line = line.strip()
                # Remove markdown formatting
                line = re.sub(r'^\s*[-*+]\s*', '', line)
                line = re.sub(r'[*_`]+', '', line)
                
                # Extract package names
                matches = re.findall(r'\b([a-zA-Z0-9_-]+)\b', line)
                for match in matches:
                    if len(match) > 2 and not match.isdigit():
                        deps.add(match.lower())
        
        # Check installation commands
        install_content = self.get_section('installation', 'install', 'getting started')
        if install_content:
            pip_commands = re.findall(r'pip install\s+([^\n`]+)', install_content, re.IGNORECASE)
            for cmd in pip_commands:
                packages = cmd.strip().split()
                for pkg in packages:
                    if not pkg.startswith('-'):
                        clean_pkg = re.match(r'([a-zA-Z0-9_-]+)', pkg)
                        if clean_pkg:
                            deps.add(clean_pkg.group(1).lower())
        
        return deps


class AdvancedProjectAnalyzer:
    """Enhanced project analyzer."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self._data = None
    
    def get_data(self) -> Dict[str, Any]:
        """Get parsed project data."""
        if self._data is None:
            self._data = parse_project(str(self.project_path))
        return self._data
    
    def get_dependencies(self) -> Set[str]:
        """Get normalized project dependencies."""
        data = self.get_data()
        deps = set()
        
        for dep in data.get('dependencies', []):
            # Clean dependency specification
            clean_dep = re.split(r'[>=<!~\s]', dep)[0].strip()
            if clean_dep:
                deps.add(clean_dep.lower())
        
        return deps
    
    def get_api_symbols(self) -> Set[str]:
        """Get public API symbols."""
        data = self.get_data()
        symbols = set()
        
        for module in data.get('modules', []):
            # Add public classes
            for cls in module.get('classes', []):
                name = cls.get('name', '')
                if name and not name.startswith('_'):
                    symbols.add(name.lower())
            
            # Add public functions
            for func in module.get('functions', []):
                name = func.get('name', '')
                if name and not name.startswith('_'):
                    symbols.add(name.lower())
        
        return symbols
    
    def get_entry_points(self) -> List[Dict[str, Any]]:
        """Get all entry points."""
        data = self.get_data()
        entry_points = []
        
        for category, eps in data.get('entry_points', {}).items():
            if isinstance(eps, list):
                entry_points.extend(eps)
        
        return entry_points


class AdvancedREADMEEvaluator:
    """Comprehensive README evaluator."""
    
    def __init__(self, readme_path: str, project_path: str):
        # Load and parse README
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        self.readme = AdvancedREADMEParser(readme_content)
        self.project = AdvancedProjectAnalyzer(project_path)
    
    def evaluate(self) -> EvaluationResults:
        """Perform comprehensive evaluation."""
        results = EvaluationResults()
        
        # Basic structure analysis
        results.sections_found = list(self.readme.sections.keys())
        results.heading_levels_used = list(set(h['level'] for h in self.readme.headings))
        results.total_content_length = len(self.readme.content)
        
        # Section presence checks
        results.title_present = self._check_title()
        results.description_present = self._check_description()
        results.installation_present = self.readme.has_section('installation', 'install', 'getting started')
        results.usage_present = self.readme.has_section('usage', 'how to use', 'examples')
        results.features_present = self.readme.has_section('features', 'key features')
        results.project_structure_present = self.readme.has_section('project structure', 'structure', 'directory structure')
        results.api_documentation_present = self.readme.has_section('api', 'api documentation', 'reference')
        results.dependencies_present = self.readme.has_section('dependencies', 'requirements', 'prerequisites')
        results.contributing_present = self.readme.has_section('contributing', 'contribution', 'development')
        results.license_present = self.readme.has_section('license', 'licensing')
        
        # Table of contents analysis
        toc_analysis = self.readme.analyze_table_of_contents()
        results.table_of_contents_present = toc_analysis['present']
        
        # Content quality metrics
        results.badges_count = self.readme.count_badges()
        code_classification = self.readme.classify_code_blocks()
        results.code_examples_count = code_classification['total']
        results.cli_examples_count = code_classification['cli']
        results.python_examples_count = code_classification['python']
        
        # Quality assessments
        results.description_quality = self._assess_description_quality()
        results.dependency_coverage = self._assess_dependency_coverage()
        results.api_coverage = self._assess_api_coverage()
        results.entry_point_coverage = self._assess_entry_point_coverage()
        
        # Calculate overall score
        results.overall_accuracy = self._calculate_overall_score(results)
        
        return results
    
    def _check_title(self) -> bool:
        """Check if README has a proper title."""
        if not self.readme.headings:
            return False
        
        first_heading = self.readme.headings[0]
        return first_heading['level'] == 1 and len(first_heading['text']) > 0
    
    def _check_description(self) -> bool:
        """Check if README has a description."""
        # Look for description in various places
        desc_content = self.readme.get_section('description', 'overview', 'about')
        
        # Also check content after title but before first major section
        if self.readme.headings and len(self.readme.headings) > 1:
            title_line = self.readme.headings[0]['line_number']
            next_heading_line = self.readme.headings[1]['line_number']
            
            intro_content = '\n'.join(self.readme.lines[title_line + 1:next_heading_line]).strip()
            if len(intro_content) > 50:  # Substantial intro content
                return True
        
        return len(desc_content) > 30  # Minimum description length
    
    def _assess_description_quality(self) -> float:
        """Assess quality of project description."""
        desc_content = self.readme.get_section('description', 'overview', 'about')
        
        # Also check intro content after title
        intro_content = ""
        if self.readme.headings and len(self.readme.headings) > 1:
            title_line = self.readme.headings[0]['line_number']
            next_heading_line = self.readme.headings[1]['line_number']
            intro_content = '\n'.join(self.readme.lines[title_line + 1:next_heading_line]).strip()
        
        combined_desc = (desc_content + ' ' + intro_content).strip()
        
        if not combined_desc:
            return 0.0
        
        score = 0.0
        
        # Length check
        if len(combined_desc) > 100:
            score += 0.3
        elif len(combined_desc) > 50:
            score += 0.2
        elif len(combined_desc) > 20:
            score += 0.1
        
        # Quality indicators
        quality_indicators = [
            'provides', 'features', 'supports', 'enables', 'includes',
            'designed', 'built', 'framework', 'library', 'tool'
        ]
        
        desc_lower = combined_desc.lower()
        for indicator in quality_indicators:
            if indicator in desc_lower:
                score += 0.1
                break
        
        # Project-specific terms
        project_data = self.project.get_data()
        project_name = project_data.get('project_metadata', {}).get('name', '')
        if project_name.lower() in desc_lower:
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_dependency_coverage(self) -> float:
        """Assess how well dependencies are documented."""
        readme_deps = self.readme.extract_dependencies()
        project_deps = self.project.get_dependencies()
        
        if not project_deps:
            return 1.0 if not readme_deps else 0.8
        
        if not readme_deps:
            return 0.0
        
        # Calculate coverage
        common = readme_deps.intersection(project_deps)
        coverage = len(common) / len(project_deps)
        
        return coverage
    
    def _assess_api_coverage(self) -> float:
        """Assess API documentation coverage."""
        if not self.readme.has_section('api', 'api documentation', 'reference'):
            return 0.0
        
        api_content = self.readme.get_section('api', 'api documentation', 'reference').lower()
        project_symbols = self.project.get_api_symbols()
        
        if not project_symbols:
            return 1.0
        
        # Count documented symbols
        documented = 0
        for symbol in project_symbols:
            if symbol in api_content:
                documented += 1
        
        return documented / len(project_symbols)
    
    def _assess_entry_point_coverage(self) -> float:
        """Assess entry point documentation coverage."""
        entry_points = self.project.get_entry_points()
        
        if not entry_points:
            return 1.0
        
        usage_content = self.readme.get_section('usage', 'cli', 'command line', 'examples').lower()
        
        if not usage_content:
            return 0.0
        
        # Check coverage
        documented = 0
        for ep in entry_points:
            usage_str = ep.get('usage', '').lower()
            name = ep.get('name', '').lower()
            
            if (usage_str and usage_str in usage_content) or (name and name in usage_content):
                documented += 1
        
        return documented / len(entry_points)
    
    def _calculate_overall_score(self, results: EvaluationResults) -> float:
        """Calculate weighted overall score."""
        # Essential sections (high weight)
        essential_score = 0.0
        essential_weight = 0.4
        essential_sections = [
            results.title_present,
            results.description_present,
            results.installation_present,
            results.usage_present
        ]
        essential_score = sum(essential_sections) / len(essential_sections)
        
        # Important sections (medium weight)
        important_score = 0.0
        important_weight = 0.3
        important_sections = [
            results.features_present,
            results.api_documentation_present,
            results.dependencies_present,
            results.table_of_contents_present
        ]
        important_score = sum(important_sections) / len(important_sections)
        
        # Nice-to-have sections (low weight)
        nice_score = 0.0
        nice_weight = 0.1
        nice_sections = [
            results.project_structure_present,
            results.contributing_present,
            results.license_present
        ]
        nice_score = sum(nice_sections) / len(nice_sections)
        
        # Content quality (medium weight)
        quality_score = (
            results.description_quality * 0.4 +
            results.dependency_coverage * 0.2 +
            results.api_coverage * 0.2 +
            results.entry_point_coverage * 0.2
        )
        quality_weight = 0.2
        
        # Calculate final score
        total_score = (
            essential_score * essential_weight +
            important_score * important_weight +
            nice_score * nice_weight +
            quality_score * quality_weight
        )
        
        return total_score


def print_detailed_report(results: EvaluationResults, verbose: bool = False):
    """Print comprehensive evaluation report."""
    print("=" * 80)
    print("ADVANCED README EVALUATION REPORT")
    print("=" * 80)
    
    # Overall score with detailed rating
    score = results.overall_accuracy
    if score >= 0.9:
        rating = f"🏆 OUTSTANDING: {score:.3f}"
    elif score >= 0.8:
        rating = f"🎯 EXCELLENT: {score:.3f}"
    elif score >= 0.7:
        rating = f"👍 GOOD: {score:.3f}"
    elif score >= 0.6:
        rating = f"⚠️  ADEQUATE: {score:.3f}"
    elif score >= 0.4:
        rating = f"⚠️  NEEDS WORK: {score:.3f}"
    else:
        rating = f"❌ POOR: {score:.3f}"
    
    print(f"\nOVERALL QUALITY: {rating}")
    
    # Essential sections
    print(f"\n📋 ESSENTIAL SECTIONS:")
    print(f"Title:                    {'✅' if results.title_present else '❌'}")
    print(f"Description:              {'✅' if results.description_present else '❌'} (Quality: {results.description_quality:.2f})")
    print(f"Installation:             {'✅' if results.installation_present else '❌'}")
    print(f"Usage:                    {'✅' if results.usage_present else '❌'}")
    
    # Important sections
    print(f"\n🔧 IMPORTANT SECTIONS:")
    print(f"Features:                 {'✅' if results.features_present else '❌'}")
    print(f"Table of Contents:        {'✅' if results.table_of_contents_present else '❌'}")
    print(f"API Documentation:        {'✅' if results.api_documentation_present else '❌'} (Coverage: {results.api_coverage:.2f})")
    print(f"Dependencies:             {'✅' if results.dependencies_present else '❌'} (Coverage: {results.dependency_coverage:.2f})")
    
    # Additional sections
    print(f"\n📚 ADDITIONAL SECTIONS:")
    print(f"Project Structure:        {'✅' if results.project_structure_present else '❌'}")
    print(f"Contributing:             {'✅' if results.contributing_present else '❌'}")
    print(f"License:                  {'✅' if results.license_present else '❌'}")
    
    # Content metrics
    print(f"\n📊 CONTENT METRICS:")
    print(f"Badges:                   {results.badges_count}")
    print(f"Code Examples:            {results.code_examples_count} (CLI: {results.cli_examples_count}, Python: {results.python_examples_count})")
    print(f"Entry Point Coverage:     {results.entry_point_coverage:.2f}")
    print(f"Document Length:          {results.total_content_length:,} characters")
    
    if verbose:
        print(f"\n🔍 DETAILED ANALYSIS:")
        print(f"Sections Found ({len(results.sections_found)}):")
        for section in sorted(results.sections_found)[:15]:
            print(f"  • {section}")
        
        print(f"\nHeading Structure: {sorted(results.heading_levels_used)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Advanced README evaluator for comprehensive documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('readme_file', help='Path to README file')
    parser.add_argument('project_path', help='Path to project directory')
    parser.add_argument('--output', '-o', help='Save detailed JSON report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Validate inputs
    readme_path = Path(args.readme_file)
    project_path = Path(args.project_path)
    
    if not readme_path.exists():
        print(f"❌ README file not found: {readme_path}")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"❌ Project directory not found: {project_path}")
        sys.exit(1)
    
    try:
        # Perform evaluation
        evaluator = AdvancedREADMEEvaluator(str(readme_path), str(project_path))
        results = evaluator.evaluate()
        
        # Print report
        print_detailed_report(results, args.verbose)
        
        # Save JSON report if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(asdict(results), f, indent=2, ensure_ascii=False)
            print(f"\n📄 Detailed report saved to: {args.output}")
        
        # Exit with score-based code
        if results.overall_accuracy >= 0.9:
            sys.exit(0)  # Outstanding
        elif results.overall_accuracy >= 0.7:
            sys.exit(1)  # Good
        elif results.overall_accuracy >= 0.5:
            sys.exit(2)  # Adequate
        else:
            sys.exit(3)  # Needs work
            
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(4)


if __name__ == "__main__":
    main()
