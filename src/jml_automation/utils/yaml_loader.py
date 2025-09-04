import yaml
from pathlib import Path

def load_yaml(filename):
    """Load a YAML file from the config directory."""
    config_dir = Path(__file__).resolve().parents[3] / "config"
    file_path = config_dir / filename
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
