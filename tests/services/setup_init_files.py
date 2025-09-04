#!/usr/bin/env python3
"""
Script to create all necessary __init__.py files for proper Python imports.
Run this from your project root: python setup_init_files.py
"""

import os
from pathlib import Path

def create_init_files():
    """Create all necessary __init__.py files."""
    
    # Define the directories that need __init__.py files
        directories = [
            "src/jml_automation",
            "src/jml_automation/extractors",
            "src/jml_automation/models",
            "src/jml_automation/services",
            "src/jml_automation/workflows",
            "src/jml_automation/parsers",
            "src/jml_automation/utils",
        ]
    
    project_root = Path.cwd()
    created_count = 0
    
    for dir_path in directories:
        full_path = project_root / dir_path
        init_file = full_path / "__init__.py"
        
        # Create directory if it doesn't exist
        full_path.mkdir(parents=True, exist_ok=True)
        
        # Create or update __init__.py
        if not init_file.exists():
            init_file.write_text("")
            print(f"✓ Created: {init_file}")
            created_count += 1
        else:
            print(f"  Already exists: {init_file}")
    
    # Create main src/filevine/__init__.py with imports
        main_init = project_root / "src/jml_automation/__init__.py"
        main_init_content = '''"""
    JML Automation package.
    """

    __version__ = "1.0.0"
    '''
    
    main_init.write_text(main_init_content)
    print(f"✓ Updated main init: {main_init}")
    
    print(f"\n✅ Created/verified {len(directories)} __init__.py files")
    return created_count

if __name__ == "__main__":
    print("Setting up __init__.py files...")
    print("-" * 40)
    create_init_files()
    print("-" * 40)
    print("Done!")
