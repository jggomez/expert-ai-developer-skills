import os
import re
import pytest

def test_skills_trigger_coverage(skills_dirs):
    """Verifies that all skills contain descriptive triggers in their descriptions for AI selection."""
    assert len(skills_dirs) > 0, "No skills found to evaluate!"
    
    missing_triggers = []
    
    for skill_dir in skills_dirs:
        skill_name = os.path.basename(skill_dir)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract description
        desc_match = re.search(r"description:\s*(.*?)\n[a-z\-]+:", content, re.DOTALL)
        if not desc_match:
            desc_match = re.search(r"description:\s*(.*)", content)
            
        if not desc_match:
            missing_triggers.append(f"{skill_name}: Could not extract description field")
            continue
            
        desc = desc_match.group(1).strip()
        
        # Ensure description length is sufficient (>30 chars) to give the LLM intent signals
        if len(desc) < 30:
            missing_triggers.append(f"{skill_name}: Description too short ({len(desc)} chars). Needs detailed triggers for LLM routing.")
            
    assert not missing_triggers, "\n".join(missing_triggers)

def test_skill_catalog_readme_sync(skills_dirs):
    """Verifies that all skills in /skills directory are documented in skills/README.md sitemap."""
    readme_path = os.path.abspath("skills/README.md")
    assert os.path.exists(readme_path), "skills/README.md missing!"
    
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()
        
    skills_root = os.path.abspath("skills")
    unlisted_skills = []
    
    for skill_dir in skills_dirs:
        # Only check skills inside /skills root directory
        if os.path.dirname(os.path.abspath(skill_dir)) == skills_root:
            skill_name = os.path.basename(skill_dir)
            if f"`{skill_name}`" not in readme_content and f"**{skill_name}**" not in readme_content:
                unlisted_skills.append(f"Skill '{skill_name}' is not listed in skills/README.md table!")
                
    assert not unlisted_skills, "\n".join(unlisted_skills)
