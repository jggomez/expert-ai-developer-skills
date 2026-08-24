#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import date

def walk_tree(root_dir, max_depth=3):
    """Generates a tree map of the repository up to max_depth."""
    ignore_dirs = {
        '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env',
        '.gemini', '.pytest_cache', '.my_cache', 'build', 'dist', 'target'
    }
    ignore_extensions = {'.pyc', '.pyo', '.pyd', '.class', '.o', '.obj', '.dll', '.so', '.dylib', '.DS_Store'}
    
    lines = []
    
    def walk(directory, depth):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            return
            
        for entry in entries:
            if entry in ignore_dirs:
                continue
            if any(entry.endswith(ext) for ext in ignore_extensions):
                continue
                
            path = os.path.join(directory, entry)
            rel_path = os.path.relpath(path, root_dir)
            indent = "  " * (depth - 1)
            
            if os.path.isdir(path):
                lines.append(f"{indent}{entry}/")
                walk(path, depth + 1)
            else:
                lines.append(f"{indent}{entry}")
                
    walk(root_dir, 1)
    return "\n".join(lines)

def detect_technologies(root_dir):
    """Scans root configs to identify language, frameworks, and dependencies."""
    tech_stack = {
        "languages": [],
        "frameworks": [],
        "database": "None detected",
        "package_manager": "None",
        "dependencies": []
    }
    
    # Check for Node.js
    pkg_json_path = os.path.join(root_dir, 'package.json')
    if os.path.exists(pkg_json_path):
        tech_stack["languages"].append("JavaScript/TypeScript")
        tech_stack["package_manager"] = "npm/yarn/pnpm"
        try:
            with open(pkg_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tech_stack["dependencies"].extend(list(data.get("dependencies", {}).keys()))
                tech_stack["dependencies"].extend(list(data.get("devDependencies", {}).keys()))
                # Detect framework
                deps = tech_stack["dependencies"]
                if any("react" in d for d in deps):
                    tech_stack["frameworks"].append("React")
                if any("next" in d for d in deps):
                    tech_stack["frameworks"].append("Next.js")
                if any("vue" in d for d in deps):
                    tech_stack["frameworks"].append("Vue")
                if any("express" in d for d in deps):
                    tech_stack["frameworks"].append("Express")
        except Exception:
            pass
            
    # Check for Python
    pyproject_path = os.path.join(root_dir, 'pyproject.toml')
    reqs_path = os.path.join(root_dir, 'requirements.txt')
    pipfile_path = os.path.join(root_dir, 'Pipfile')
    
    if os.path.exists(pyproject_path) or os.path.exists(reqs_path) or os.path.exists(pipfile_path):
        tech_stack["languages"].append("Python")
        if os.path.exists(pyproject_path):
            tech_stack["package_manager"] = "poetry/pip/uv"
            try:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # simple regex extract deps
                    deps = re.findall(r'^([a-zA-Z0-9_\-]+)\s*=\s*', content, re.MULTILINE)
                    tech_stack["dependencies"].extend(deps)
            except Exception:
                pass
        elif os.path.exists(reqs_path):
            tech_stack["package_manager"] = "pip"
            try:
                with open(reqs_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # remove versions
                            dep = re.split(r'[=<>~]', line)[0].strip()
                            tech_stack["dependencies"].append(dep)
            except Exception:
                pass
                
        # Framework detection for python
        deps = tech_stack["dependencies"]
        if any("django" in d.lower() for d in deps):
            tech_stack["frameworks"].append("Django")
        if any("flask" in d.lower() for d in deps):
            tech_stack["frameworks"].append("Flask")
        if any("fastapi" in d.lower() for d in deps):
            tech_stack["frameworks"].append("FastAPI")
            
    # Check for Go
    go_mod_path = os.path.join(root_dir, 'go.mod')
    if os.path.exists(go_mod_path):
        tech_stack["languages"].append("Go")
        tech_stack["package_manager"] = "go modules"
        try:
            with open(go_mod_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('require'):
                        tech_stack["dependencies"].append("See go.mod requirements")
                        break
        except Exception:
            pass
            
    # Database detection based on dependencies
    all_deps_str = " ".join(tech_stack["dependencies"]).lower()
    if "postgres" in all_deps_str or "psycopg" in all_deps_str or "pg" in all_deps_str:
        tech_stack["database"] = "PostgreSQL"
    elif "mysql" in all_deps_str:
        tech_stack["database"] = "MySQL"
    elif "mongo" in all_deps_str:
        tech_stack["database"] = "MongoDB"
    elif "sqlite" in all_deps_str:
        tech_stack["database"] = "SQLite"
        
    return tech_stack

def find_entry_points(root_dir):
    """Finds potential entry points in the project."""
    entry_candidates = [
        "main.py", "app.py", "server.py", "index.js", "index.ts", 
        "server.js", "server.ts", "main.go", "src/main.ts", "src/index.ts"
    ]
    found = []
    for candidate in entry_candidates:
        if os.path.exists(os.path.join(root_dir, candidate)):
            found.append(candidate)
    return found if found else ["Not explicitly found (check root or src/)"]

def find_config_files(root_dir):
    """Lists configuration files in the root."""
    config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.env'}
    found = []
    for file in os.listdir(root_dir):
        if os.path.isfile(os.path.join(root_dir, file)):
            _, ext = os.path.splitext(file)
            if ext in config_extensions or file.startswith('.') or 'config' in file.lower():
                if file not in {'.DS_Store', '.gitignore'}:
                    found.append(file)
    return found

def generate_context_markdown(root_dir, template_path):
    """Generates the context markdown by replacing placeholders in the template."""
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
        
    repo_name = os.path.basename(os.path.abspath(root_dir))
    tree_map = walk_tree(root_dir)
    tech = detect_technologies(root_dir)
    entry_points = find_entry_points(root_dir)
    config_files = find_config_files(root_dir)
    
    # Format metadata
    template = template.replace("[Project Name]", repo_name)
    template = template.replace("[YYYY-MM-DD]", str(date.today()))
    
    # Fill identity
    template = template.replace("Name: [...]", f"Name: {repo_name}")
    
    # Fill technology stack
    langs = ", ".join(set(tech["languages"])) if tech["languages"] else "Unknown"
    fworks = ", ".join(set(tech["frameworks"])) if tech["frameworks"] else "None detected"
    deps_list = "\n  - ".join(tech["dependencies"][:15]) if tech["dependencies"] else "None detected"
    if len(tech["dependencies"]) > 15:
        deps_list += f"\n  - ... and {len(tech['dependencies']) - 15} more dependencies."
        
    template = template.replace("Language(s): [...]", f"Language(s): {langs}")
    template = template.replace("Frameworks & Core Libraries: [...]", f"Frameworks & Core Libraries: {fworks}")
    template = template.replace("Database / Data Storage: [...]", f"Database / Data Storage: {tech['database']}")
    template = template.replace("Package Manager / Build Tools: [...]", f"Package Manager / Build Tools: {tech['package_manager']}")
    template = template.replace("  - [...]", f"  - {deps_list}")
    
    # Fill structure
    template = template.replace("[Visual tree or summary of key directories]", tree_map)
    template = template.replace("Entry points: [...]", f"Entry points: {', '.join(entry_points)}")
    template = template.replace("Config files: [...]", f"Config files: {', '.join(config_files)}")
    
    return template

def main():
    root_dir = "."
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
        
    # Locate templates relative to script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "../references/project-context-template.md")
    
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}")
        sys.exit(1)
        
    output_dir = os.path.join(root_dir, ".agents/rules")
    output_path = os.path.join(output_dir, "project-context.md")
    
    print(f"Analyzing repository at {root_dir}...")
    markdown_content = generate_context_markdown(root_dir, template_path)
    
    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"Successfully generated project context at {output_path}")

if __name__ == "__main__":
    main()
