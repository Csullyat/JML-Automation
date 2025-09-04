#!/usr/bin/env python3
"""
Debug script to identify import issues.
Run from project root: python debug_imports.py
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

print("Python Import Debugger")
print("=" * 50)
print(f"Python version: {sys.version}")
print(f"Project root: {project_root}")
print(f"Src path: {src_path}")
print(f"Python path includes src: {str(src_path) in sys.path}")
print()

# Test 1: Check if config.py exists

config_file = src_path / "jml_automation" / "config.py"
print(f"1. Config file exists: {config_file.exists()}")
if config_file.exists():
    print(f"   Size: {config_file.stat().st_size} bytes")

# Test 2: Try importing the module
print("\n2. Testing module import...")
try:
    import jml_automation
    print("    Can import jml_automation package")
except ImportError as e:
    print(f"    Cannot import jml_automation: {e}")
try:
    import jml_automation.config
    print("    Can import jml_automation.config module")
    # Check what's in the module
    print("   Module contents:")
    for item in dir(jml_automation.config):
        if not item.startswith('_'):
            print(f"     - {item}")
except ImportError as e:
    print(f"    Cannot import jml_automation.config: {e}")
except Exception as e:
    print(f"    Error with jml_automation.config: {e}")
    print(f"   ✗ Cannot import filevine.config: {e}")
except Exception as e:
    print(f"   ✗ Error with filevine.config: {e}")

# Test 4: Try importing Config class
print("\n4. Testing Config class import...")
try:
    from jml_automation.config import Config
    print("    Can import Config class")
    
    # Try to instantiate
    print("\n5. Testing Config instantiation...")
    try:
        config = Config()
        print("   ✓ Config instantiated successfully")
        print(f"   Config has {len(dir(config))} attributes/methods")
    except Exception as e:
        print(f"   ✗ Cannot instantiate Config: {e}")
        
except ImportError as e:
    print(f"   ✗ Cannot import Config class: {e}")
    
    # Try to see what went wrong
    print("\n   Attempting to load and check syntax...")
    try:
        with open(config_file, 'r') as f:
            content = f.read()
            
        # Try to compile it
        compile(content, str(config_file), 'exec')
        print("   File syntax appears valid")
        
        # Check if Config class is defined
        if 'class Config' in content:
            print("   Config class IS defined in file")
        else:
            print("   ✗ Config class NOT found in file!")
            
    except SyntaxError as e:
        print(f"   ✗ Syntax error in config.py: {e}")
    except Exception as e:
        print(f"   ✗ Error checking file: {e}")

print("\n" + "=" * 50)
print("Debug complete. Check output above for issues.")
