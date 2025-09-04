from pathlib import Path

# Check the path resolution that yaml_loader uses
yaml_loader_file = Path("src/jml_automation/utils/yaml_loader.py")
print(f"yaml_loader file exists: {yaml_loader_file.exists()}")
print(f"yaml_loader absolute path: {yaml_loader_file.resolve()}")

# Check what parents[3] gives us
if yaml_loader_file.exists():
    resolved = yaml_loader_file.resolve()
    print(f"parents[0]: {resolved.parents[0]}")
    print(f"parents[1]: {resolved.parents[1]}")
    print(f"parents[2]: {resolved.parents[2]}")
    print(f"parents[3]: {resolved.parents[3]}")
    
    config_dir = resolved.parents[3] / "config"
    print(f"Config dir yaml_loader looks for: {config_dir}")
    print(f"Config dir exists: {config_dir.exists()}")
    
    target_file = config_dir / "termination_order.yaml"
    print(f"Target file: {target_file}")
    print(f"Target file exists: {target_file.exists()}")
