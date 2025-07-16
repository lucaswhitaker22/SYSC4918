# src/parsing/project_detector.py

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Optional


class ProjectDetector:
    """
    Detects key project files and determines project characteristics.
    
    This class is responsible for identifying configuration files, main modules,
    entry points, and determining whether the project is a package or script.
    """
    
    # Common setup/configuration file names
    SETUP_FILES = ["setup.py", "pyproject.toml", "setup.cfg"]
    
    # Common requirements file names
    REQUIREMENTS_FILES = [
        "requirements.txt", 
        "requirements-dev.txt", 
        "requirements-test.txt",
        "dev-requirements.txt",
        "test-requirements.txt",
        "requirements.in"
    ]
    
    # Common main module patterns
    MAIN_MODULE_PATTERNS = [
        "main.py",
        "__main__.py", 
        "app.py",
        "run.py",
        "cli.py",
        "manage.py",  # Django projects
        "server.py",  # Flask/FastAPI projects
        "wsgi.py",    # WSGI applications
        "asgi.py"     # ASGI applications
    ]


def find_setup_files(root_path: str) -> List[str]:
    """
    Finds setup and configuration files in the project root.
    
    Args:
        root_path: The root directory of the project to scan.
    
    Returns:
        A list of absolute paths to found setup files, ordered by priority.
    """
    setup_files = []
    root = Path(root_path)
    
    if not root.exists() or not root.is_dir():
        return setup_files
    
    # Check in order of priority
    for setup_file in ProjectDetector.SETUP_FILES:
        file_path = root / setup_file
        if file_path.exists() and file_path.is_file():
            setup_files.append(str(file_path))
    
    return setup_files


def find_requirements_files(root_path: str) -> List[str]:
    """
    Finds requirements files in the project root.
    
    Args:
        root_path: The root directory of the project to scan.
    
    Returns:
        A list of absolute paths to found requirements files.
    """
    requirements_files = []
    root = Path(root_path)
    
    if not root.exists() or not root.is_dir():
        return requirements_files
    
    for req_file in ProjectDetector.REQUIREMENTS_FILES:
        file_path = root / req_file
        if file_path.exists() and file_path.is_file():
            requirements_files.append(str(file_path))
    
    return requirements_files


def identify_main_modules(file_structure: Dict[str, List[str]]) -> List[str]:
    """
    Identifies main modules from the project file structure.
    Enhanced to handle both flat and src-layout projects.
    
    Args:
        file_structure: Dictionary mapping directory paths to lists of files.
    
    Returns:
        A list of identified main module file paths.
    """
    main_modules = []
    
    # Check root directory first
    root_files = file_structure.get("./", [])
    for file_name in root_files:
        if file_name in ProjectDetector.MAIN_MODULE_PATTERNS:
            main_modules.append(f"./{file_name}")
    
    # Check src/ directory (common Python project layout)
    src_files = file_structure.get("src/", [])
    for file_name in src_files:
        if file_name in ProjectDetector.MAIN_MODULE_PATTERNS:
            main_modules.append(f"src/{file_name}")
    
    # Look for __main__.py in subdirectories (package entry points)
    for dir_path, files in file_structure.items():
        if "__main__.py" in files:
            main_modules.append(f"{dir_path}__main__.py")
    
    # Look for files with "main" in the name in root and src directories
    for directory in ["./", "src/"]:
        dir_files = file_structure.get(directory, [])
        for file_name in dir_files:
            if (file_name.endswith(".py") and 
                "main" in file_name.lower() and 
                file_name not in ProjectDetector.MAIN_MODULE_PATTERNS):
                main_modules.append(f"{directory}{file_name}")
    
    return main_modules


def detect_entry_points(root_path: str) -> List[str]:
    """
    Detects potential entry points for the project.
    Enhanced to handle both flat and src-layout projects.
    
    This function combines main module detection with setup.py analysis
    to identify how the project can be executed.
    
    Args:
        root_path: The root directory of the project.
    
    Returns:
        A list of detected entry points.
    """
    entry_points = []
    root = Path(root_path)
    
    # Check for executable Python files in root
    for pattern in ProjectDetector.MAIN_MODULE_PATTERNS:
        main_file = root / pattern
        if main_file.exists():
            entry_points.append(f"python {pattern}")
    
    # Check src/ directory for main files
    src_dir = root / "src"
    if src_dir.exists():
        for pattern in ProjectDetector.MAIN_MODULE_PATTERNS:
            src_main_file = src_dir / pattern
            if src_main_file.exists():
                entry_points.append(f"python src/{pattern}")
    
    # Check if project can be run as a module (has __main__.py)
    main_py = root / "__main__.py"
    if main_py.exists():
        entry_points.append(f"python -m {root.name}")
    
    # Check for packages with __main__.py in src/
    if src_dir.exists():
        for item in src_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                package_main = item / "__main__.py"
                if package_main.exists():
                    entry_points.append(f"python -m src.{item.name}")
    
    # Check for setup.py entry points
    setup_py = root / "setup.py"
    if setup_py.exists():
        console_scripts = _extract_console_scripts_from_setup(str(setup_py))
        entry_points.extend(console_scripts)
    
    # Check for pyproject.toml entry points
    pyproject_toml = root / "pyproject.toml"
    if pyproject_toml.exists():
        toml_scripts = _extract_console_scripts_from_pyproject(str(pyproject_toml))
        entry_points.extend(toml_scripts)
    
    return entry_points


def determine_project_type(root_path: str, file_structure: Dict[str, List[str]]) -> str:
    """
    Determines if the project is a package or a script.
    
    Args:
        root_path: The root directory of the project.
        file_structure: Dictionary mapping directory paths to lists of files.
    
    Returns:
        Either "package" or "script" based on project structure.
    """
    root = Path(root_path)
    
    # Check for setup files (strong indicator of a package)
    setup_files = find_setup_files(root_path)
    if setup_files:
        return "package"
    
    # Check for __init__.py files (indicates package structure)
    for dir_path, files in file_structure.items():
        if "__init__.py" in files and dir_path != "./":
            return "package"
    
    # Check for src/ directory with packages
    src_files = file_structure.get("src/", [])
    if src_files:
        return "package"
    
    # Check for multiple Python modules in subdirectories
    python_dirs = 0
    for dir_path, files in file_structure.items():
        if dir_path != "./" and any(f.endswith(".py") for f in files):
            python_dirs += 1
    
    if python_dirs >= 2:
        return "package"
    
    # Default to script if no package indicators found
    return "script"


def infer_project_domain(file_structure: Dict[str, List[str]], 
                        dependencies: List[str]) -> str:
    """
    Infer project domain from structure and dependencies.
    
    Args:
        file_structure: Dictionary mapping directory paths to lists of files
        dependencies: List of project dependencies
        
    Returns:
        Inferred project domain category
    """
    # Data science indicators
    data_science_deps = ["pandas", "numpy", "scikit-learn", "matplotlib", "seaborn", 
                        "scipy", "jupyter", "plotly", "bokeh", "statsmodels"]
    if any(dep in dependencies for dep in data_science_deps):
        return "data_science"
    
    # Machine learning indicators (more specific than data science)
    ml_deps = ["tensorflow", "pytorch", "keras", "torch", "transformers", "sklearn", 
              "xgboost", "lightgbm", "catboost", "mlflow"]
    if any(dep in dependencies for dep in ml_deps):
        return "machine_learning"
    
    # Web development indicators
    web_deps = ["flask", "django", "fastapi", "streamlit", "bottle", "tornado", 
               "pyramid", "cherrypy", "starlette", "quart"]
    if any(dep in dependencies for dep in web_deps):
        return "web_development"
    
    # CLI tool indicators
    cli_deps = ["click", "argparse", "typer", "fire", "docopt", "cliff", "cement"]
    if any(dep in dependencies for dep in cli_deps):
        return "cli_tool"
    
    # DevOps/Infrastructure indicators
    devops_deps = ["ansible", "fabric", "paramiko", "boto3", "kubernetes", "docker", 
                  "terraform", "salt", "puppet"]
    if any(dep in dependencies for dep in devops_deps):
        return "devops"
    
    # Testing framework indicators
    testing_deps = ["pytest", "unittest", "nose", "behave", "robotframework", 
                   "hypothesis", "mock", "testfixtures"]
    if any(dep in dependencies for dep in testing_deps):
        return "testing"
    
    # Game development indicators
    game_deps = ["pygame", "panda3d", "arcade", "pyglet", "kivy", "pysimplegui"]
    if any(dep in dependencies for dep in game_deps):
        return "game_development"
    
    # Scientific computing indicators
    scientific_deps = ["sympy", "astropy", "biopython", "networkx", "igraph", 
                      "dask", "numba", "cython"]
    if any(dep in dependencies for dep in scientific_deps):
        return "scientific_computing"
    
    # Check file structure for domain indicators
    all_files = []
    for files in file_structure.values():
        all_files.extend([f.lower() for f in files])
    
    # Look for domain-specific file patterns
    if any("test" in f for f in all_files):
        return "testing"
    
    if any(f.endswith(".ipynb") for f in all_files):
        return "data_science"
    
    if any(f in ["dockerfile", "docker-compose.yml"] for f in all_files):
        return "devops"
    
    if any(f.startswith("manage") for f in all_files):
        return "web_development"
    
    # Check directory structure
    directories = list(file_structure.keys())
    if any("api" in d.lower() for d in directories):
        return "web_development"
    
    if any("models" in d.lower() for d in directories):
        return "machine_learning"
    
    return "general"


def detect_deployment_patterns(root_path: str) -> List[str]:
    """
    Detect deployment and containerization patterns.
    
    Args:
        root_path: Root directory path of the project
        
    Returns:
        List of detected deployment patterns
    """
    deployment_patterns = []
    root = Path(root_path)
    
    # Docker detection
    docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"]
    if any((root / docker_file).exists() for docker_file in docker_files):
        deployment_patterns.append("docker")
    
    # Kubernetes detection
    k8s_dirs = ["k8s", "kubernetes", "manifests", "charts"]
    k8s_files = ["*.yaml", "*.yml"]
    
    if any((root / k8s_dir).exists() for k8s_dir in k8s_dirs):
        deployment_patterns.append("kubernetes")
    
    # Check for YAML files that might be Kubernetes manifests
    yaml_files = list(root.glob("*.yaml")) + list(root.glob("*.yml"))
    for yaml_file in yaml_files:
        try:
            content = yaml_file.read_text(encoding='utf-8')
            if any(keyword in content.lower() for keyword in ["apiversion", "kind:", "metadata:"]):
                deployment_patterns.append("kubernetes")
                break
        except (IOError, UnicodeDecodeError):
            continue
    
    # Heroku detection
    heroku_files = ["Procfile", "runtime.txt", "app.json"]
    if any((root / heroku_file).exists() for heroku_file in heroku_files):
        deployment_patterns.append("heroku")
    
    # AWS detection
    aws_files = [".ebextensions", "serverless.yml", "template.yaml", "sam.yaml"]
    if any((root / aws_file).exists() for aws_file in aws_files):
        deployment_patterns.append("aws")
    
    # Google Cloud detection
    gcp_files = ["app.yaml", "cron.yaml", "dispatch.yaml", "cloudbuild.yaml"]
    if any((root / gcp_file).exists() for gcp_file in gcp_files):
        deployment_patterns.append("gcp")
    
    # Azure detection
    azure_files = ["azure-pipelines.yml", "azure-pipelines.yaml"]
    if any((root / azure_file).exists() for azure_file in azure_files):
        deployment_patterns.append("azure")
    
    # GitHub Actions detection
    github_actions_dir = root / ".github" / "workflows"
    if github_actions_dir.exists() and any(github_actions_dir.iterdir()):
        deployment_patterns.append("github_actions")
    
    # GitLab CI detection
    gitlab_files = [".gitlab-ci.yml", ".gitlab-ci.yaml"]
    if any((root / gitlab_file).exists() for gitlab_file in gitlab_files):
        deployment_patterns.append("gitlab_ci")
    
    # Travis CI detection
    travis_files = [".travis.yml", ".travis.yaml"]
    if any((root / travis_file).exists() for travis_file in travis_files):
        deployment_patterns.append("travis_ci")
    
    # Jenkins detection
    jenkins_files = ["Jenkinsfile", "jenkins.yml"]
    if any((root / jenkins_file).exists() for jenkins_file in jenkins_files):
        deployment_patterns.append("jenkins")
    
    # Terraform detection
    terraform_files = list(root.glob("*.tf")) + list(root.glob("*.tfvars"))
    if terraform_files:
        deployment_patterns.append("terraform")
    
    # Ansible detection
    ansible_files = ["ansible.cfg", "playbook.yml", "inventory"]
    ansible_dirs = ["roles", "playbooks"]
    if (any((root / ansible_file).exists() for ansible_file in ansible_files) or
        any((root / ansible_dir).exists() for ansible_dir in ansible_dirs)):
        deployment_patterns.append("ansible")
    
    return list(set(deployment_patterns))  # Remove duplicates


def detect_framework_patterns(file_structure: Dict[str, List[str]], 
                            dependencies: List[str]) -> List[str]:
    """
    Detect web frameworks and other major frameworks used in the project.
    
    Args:
        file_structure: Dictionary mapping directory paths to lists of files
        dependencies: List of project dependencies
        
    Returns:
        List of detected frameworks
    """
    frameworks = []
    
    # Framework detection based on dependencies
    framework_deps = {
        "django": ["django"],
        "flask": ["flask"],
        "fastapi": ["fastapi"],
        "streamlit": ["streamlit"],
        "tornado": ["tornado"],
        "bottle": ["bottle"],
        "pyramid": ["pyramid"],
        "cherrypy": ["cherrypy"],
        "starlette": ["starlette"],
        "quart": ["quart"],
        "aiohttp": ["aiohttp"],
        "sanic": ["sanic"],
        "falcon": ["falcon"],
        "celery": ["celery"],
        "sqlalchemy": ["sqlalchemy"],
        "pytest": ["pytest"],
        "unittest": ["unittest"],
        "scrapy": ["scrapy"],
    }
    
    for framework, deps in framework_deps.items():
        if any(dep in dependencies for dep in deps):
            frameworks.append(framework)
    
    # Framework detection based on file patterns
    all_files = []
    for files in file_structure.values():
        all_files.extend([f.lower() for f in files])
    
    # Django specific files
    django_files = ["manage.py", "settings.py", "wsgi.py", "asgi.py", "urls.py"]
    if any(f in all_files for f in django_files):
        frameworks.append("django")
    
    # Flask specific patterns
    flask_patterns = ["app.py", "wsgi.py", "flask_app.py"]
    if any(f in all_files for f in flask_patterns):
        frameworks.append("flask")
    
    # FastAPI specific patterns
    fastapi_patterns = ["main.py", "api.py"]
    if any(f in all_files for f in fastapi_patterns):
        frameworks.append("fastapi")
    
    # Streamlit specific patterns
    if any("streamlit" in f for f in all_files):
        frameworks.append("streamlit")
    
    return list(set(frameworks))  # Remove duplicates


def _extract_console_scripts_from_setup(setup_file: str) -> List[str]:
    """
    Extract console scripts from setup.py entry_points.
    
    Args:
        setup_file: Path to the setup.py file.
    
    Returns:
        A list of console script entry points.
    """
    scripts = []
    
    try:
        with open(setup_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the setup.py file as AST
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (hasattr(node.func, 'id') and node.func.id == 'setup') or \
                   (hasattr(node.func, 'attr') and node.func.attr == 'setup'):
                    
                    # Look for entry_points keyword argument
                    for keyword in node.keywords:
                        if keyword.arg == 'entry_points':
                            scripts.extend(_parse_entry_points_from_ast(keyword.value))
    
    except (FileNotFoundError, SyntaxError, UnicodeDecodeError):
        # Fallback to regex parsing if AST fails
        try:
            with open(setup_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for console_scripts patterns
            console_scripts_pattern = r'console_scripts.*?=.*?\[(.*?)\]'
            matches = re.findall(console_scripts_pattern, content, re.DOTALL)
            
            for match in matches:
                # Extract script names
                script_entries = re.findall(r'["\']([^"\'=]+)=', match)
                for script_name in script_entries:
                    scripts.append(f"{script_name} (console script)")
        
        except Exception:
            pass
    
    return scripts


def _extract_console_scripts_from_pyproject(pyproject_file: str) -> List[str]:
    """
    Extract console scripts from pyproject.toml.
    
    Args:
        pyproject_file: Path to the pyproject.toml file.
    
    Returns:
        A list of console script entry points.
    """
    scripts = []
    
    try:
        # Try to import tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return scripts
        
        with open(pyproject_file, 'rb') as f:
            data = tomllib.load(f)
        
        # Check for project.scripts
        project_scripts = data.get("project", {}).get("scripts", {})
        for script_name in project_scripts.keys():
            scripts.append(f"{script_name} (console script)")
        
        # Check for tool.poetry.scripts
        poetry_scripts = data.get("tool", {}).get("poetry", {}).get("scripts", {})
        for script_name in poetry_scripts.keys():
            scripts.append(f"{script_name} (poetry script)")
    
    except Exception:
        pass
    
    return scripts


def _parse_entry_points_from_ast(node: ast.AST) -> List[str]:
    """
    Parse entry points from an AST node.
    
    Args:
        node: AST node containing entry points data.
    
    Returns:
        A list of extracted console scripts.
    """
    scripts = []
    
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "console_scripts":
                if isinstance(value, ast.List):
                    for item in value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            script_name = item.value.split('=')[0].strip()
                            scripts.append(f"{script_name} (console script)")
    
    return scripts


def get_project_metadata_summary(root_path: str) -> Dict[str, any]:
    """
    Get a comprehensive summary of project metadata.
    
    Args:
        root_path: The root directory of the project.
    
    Returns:
        A dictionary containing project metadata summary.
    """
    from .file_scanner import scan_directory
    
    file_structure = scan_directory(root_path)
    
    # Get dependencies (simplified)
    dependencies = []
    requirements_files = find_requirements_files(root_path)
    if requirements_files:
        from .metadata_extractor import parse_dependencies
        dependencies = parse_dependencies(requirements_files[0])
    
    return {
        "project_type": determine_project_type(root_path, file_structure),
        "setup_files": find_setup_files(root_path),
        "requirements_files": requirements_files,
        "main_modules": identify_main_modules(file_structure),
        "entry_points": detect_entry_points(root_path),
        "project_domain": infer_project_domain(file_structure, dependencies),
        "deployment_patterns": detect_deployment_patterns(root_path),
        "frameworks": detect_framework_patterns(file_structure, dependencies),
        "has_src_layout": "src/" in file_structure,
        "has_tests": any("test" in dir_path.lower() for dir_path in file_structure.keys()),
        "python_files_count": sum(
            len([f for f in files if f.endswith(".py")]) 
            for files in file_structure.values()
        )
    }
