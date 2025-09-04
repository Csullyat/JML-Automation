import yaml

with open("config/termination_order.yaml", "r", encoding="utf-8") as f:
    content = f.read()
    print("File content length:", len(content))
    print("First 50 chars:", repr(content[:50]))

try:
    data = yaml.safe_load(content)
    print("YAML loaded successfully!")
    print("Keys:", data.keys() if data else "None")
except yaml.YAMLError as e:
    print(f"YAML Error: {e}")
    if hasattr(e, 'problem_mark') and e.problem_mark is not None:
        print(f"Error at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}")
