#!/usr/bin/env python3
import os
import sys
from datetime import date

def generate_sdd(title, status="Draft"):
    # Clean up title for filename
    clean_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title)
    kebab_title = clean_title.lower().replace(" ", "-").replace("_", "-")
    
    # Locate/create target directory
    project_root = "."
    target_dirs = [
        os.path.join(project_root, "docs", "design"),
        os.path.join(project_root, "docs", "specs"),
        os.path.join(project_root, ".agents", "design"),
        os.path.join(project_root, "specs")
    ]
    
    # Find which directory exists, or default to docs/design
    target_dir = target_dirs[0]
    for d in target_dirs:
        if os.path.isdir(d):
            target_dir = d
            break
            
    os.makedirs(target_dir, exist_ok=True)
    
    # Locate template relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "../references/sdd-template.md")
    
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}")
        return None
        
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
        
    # Replace placeholders
    rendered = template.replace("[System Title]", title)
    rendered = rendered.replace("[Draft | Review | Approved | Superceded]", status)
    rendered = rendered.replace("[YYYY-MM-DD]", str(date.today()))
    
    filename = f"SDD-{kebab_title}.md"
    file_path = os.path.join(target_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rendered)
        
    return file_path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 create_sdd.py \"System Name\" [Status]")
        sys.exit(1)
        
    title = sys.argv[1]
    status = sys.argv[2] if len(sys.argv) > 2 else "Draft"
    
    file_path = generate_sdd(title, status)
    if file_path:
        print(f"✅ Software Design Document created at: {file_path}")
    else:
        print("❌ Failed to create SDD.")
        sys.exit(1)

if __name__ == "__main__":
    main()
