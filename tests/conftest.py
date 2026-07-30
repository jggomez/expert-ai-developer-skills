import os
import pytest
import yaml

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@pytest.fixture
def workspace_root():
    return WORKSPACE_ROOT

@pytest.fixture
def skills_dirs():
    """Returns a list of all absolute paths to skill directories in both /skills and /plugins."""
    skill_paths = []
    
    # 1. /skills directory
    skills_root = os.path.join(WORKSPACE_ROOT, "skills")
    if os.path.exists(skills_root):
        for item in os.listdir(skills_root):
            full_path = os.path.join(skills_root, item)
            if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "SKILL.md")):
                skill_paths.append(full_path)
                
    # 2. /plugins directory
    plugins_root = os.path.join(WORKSPACE_ROOT, "plugins")
    if os.path.exists(plugins_root):
        for plugin in os.listdir(plugins_root):
            plugin_skills = os.path.join(plugins_root, plugin, "skills")
            if os.path.exists(plugin_skills):
                for item in os.listdir(plugin_skills):
                    full_path = os.path.join(plugin_skills, item)
                    if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "SKILL.md")):
                        skill_paths.append(full_path)
                        
    return skill_paths
