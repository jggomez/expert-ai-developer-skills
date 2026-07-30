import os
import re
import pytest
import yaml

def parse_frontmatter(file_path):
    """Parses YAML frontmatter from a SKILL.md file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return None, content
        
    frontmatter_raw = match.group(1)
    try:
        data = yaml.safe_load(frontmatter_raw)
        return data, content
    except Exception:
        return None, content

def test_skills_frontmatter_and_metadata(skills_dirs):
    """Verifies that all SKILL.md files have valid frontmatter with name and description."""
    assert len(skills_dirs) > 0, "No skills found in repository!"
    
    errors = []
    for skill_dir in skills_dirs:
        skill_name = os.path.basename(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        
        data, _ = parse_frontmatter(skill_md)
        if not data:
            errors.append(f"{skill_name}: Missing or invalid YAML frontmatter in SKILL.md")
            continue
            
        if "name" not in data or not data["name"]:
            errors.append(f"{skill_name}: 'name' field is missing or empty in frontmatter")
            
        if "description" not in data or not data["description"]:
            errors.append(f"{skill_name}: 'description' field is missing or empty in frontmatter")
            
    assert not errors, "\n".join(errors)

def test_skills_relative_links_and_files(skills_dirs):
    """Verifies that relative Markdown links in SKILL.md point to existing files."""
    errors = []
    
    # Match markdown links: [label](path)
    link_pattern = r"\[.*?\]\((?!http|https|#|mailto:)(.*?)\)"
    
    for skill_dir in skills_dirs:
        skill_name = os.path.basename(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        
        _, content = parse_frontmatter(skill_md)
        links = re.findall(link_pattern, content)
        
        for link in links:
            # Strip anchors if any (e.g. file.md#L10 or file.md#section)
            clean_link = link.split("#")[0]
            if not clean_link:
                continue
                
            # Resolve relative path from SKILL.md directory
            target_path = os.path.normpath(os.path.join(skill_dir, clean_link))
            if not os.path.exists(target_path):
                errors.append(f"{skill_name}: Broken relative link '{link}' -> Resolved to '{target_path}' which does not exist.")
                
    assert not errors, "\n".join(errors)

def test_no_hardcoded_user_absolute_paths(skills_dirs):
    """Verifies that SKILL.md files do not contain hardcoded user machine absolute paths."""
    errors = []
    # Check for hardcoded paths starting with /Users/ or C:\ Users\
    user_path_pattern = r"/(?:Users|home)/[a-zA-Z0-9_.-]+"
    
    for skill_dir in skills_dirs:
        skill_name = os.path.basename(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
            
        matches = re.findall(user_path_pattern, content)
        if matches:
            errors.append(f"{skill_name}: Contains hardcoded user absolute path: {matches[:3]}")
            
    assert not errors, "\n".join(errors)
