#!/usr/bin/env python3
import os
import sys
from datetime import date

def generate_adr(title, status="Proposed"):
    # Clean up title for filename
    clean_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title)
    kebab_title = clean_title.lower().replace(" ", "-").replace("_", "-")
    
    # Locate/create target directory
    project_root = "."
    target_dirs = [
        os.path.join(project_root, "docs", "adrs"),
        os.path.join(project_root, "docs", "adr"),
        os.path.join(project_root, ".agents", "adrs"),
        os.path.join(project_root, "adrs")
    ]
    
    # Find which directory exists, or default to docs/adrs
    target_dir = target_dirs[0]
    for d in target_dirs:
        if os.path.isdir(d):
            target_dir = d
            break
            
    os.makedirs(target_dir, exist_ok=True)
    
    # Calculate next ADR number
    existing_files = os.listdir(target_dir)
    adr_files = [f for f in existing_files if f.lower().startswith("adr-") and f.endswith(".md")]
    
    max_num = 0
    for f in adr_files:
        try:
            # Parse number from "ADR-001-some-title.md" or "ADR-1-some-title.md"
            num_part = f.split("-")[1]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
            
    next_num = max_num + 1
    num_str = f"{next_num:03d}"
    
    # Locate template relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "../references/adr-template.md")
    
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}")
        return None
        
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
        
    # Replace placeholders
    rendered = template.replace("[Number]", num_str)
    rendered = rendered.replace("[Title]", title)
    rendered = rendered.replace("[Status]", status)
    rendered = rendered.replace("[YYYY-MM-DD]", str(date.today()))
    
    filename = f"ADR-{num_str}-{kebab_title}.md"
    file_path = os.path.join(target_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rendered)
        
    return file_path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 create_adr.py \"Decision Title\" [Status]")
        sys.exit(1)
        
    title = sys.argv[1]
    status = sys.argv[2] if len(sys.argv) > 2 else "Proposed"
    
    file_path = generate_adr(title, status)
    if file_path:
        print(f"✅ Architecture Decision Record created at: {file_path}")
    else:
        print("❌ Failed to create ADR.")
        sys.exit(1)

if __name__ == "__main__":
    main()
