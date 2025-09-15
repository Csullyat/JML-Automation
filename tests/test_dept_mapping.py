#!/usr/bin/env python3
"""Test script to verify department mapping for AE - Account Executives"""

import yaml
from pathlib import Path

# Test the department mapping logic
def test_department_mapping():
    cfg = yaml.safe_load((Path("config")/"groups.yaml").read_text())
    group_names = set(cfg.get("baseline", []))
    
    dept_map = (cfg.get("dept") or {})
    print(f"Available departments in config: {list(dept_map.keys())}")
    
    # Test with AE - Account Executives
    department = "AE - Account Executives"
    department_key = department
    if department == "AE - Account Executives":
        department_key = "Sales"
    
    print(f"Original department: {department}")
    print(f"Mapped department key: {department_key}")
    
    if department_key in dept_map:
        group_names.update(dept_map[department_key])
        print(f"Groups added for {department_key}: {dept_map[department_key]}")
    else:
        print(f"No groups found for department key: {department_key}")
    
    print(f"Final group names: {sorted(group_names)}")

if __name__ == "__main__":
    test_department_mapping()