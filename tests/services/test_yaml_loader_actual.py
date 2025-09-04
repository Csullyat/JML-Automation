import yaml
from pathlib import Path

# Simulate exactly what yaml_loader.py does
yaml_loader_path = Path("src/jml_automation/utils/yaml_loader.py").resolve()
config_dir = yaml_loader_path.parents[3] / "config"
file_path = config_dir / "termination_order.yaml"

print(f"Trying to load: {file_path}")
print(f"File exists: {file_path.exists()}")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    print("SUCCESS! Loaded via yaml_loader method")
    print(f"Keys: {data.keys()}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
