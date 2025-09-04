from jml_automation.utils.yaml_loader import load_yaml

try:
    data = load_yaml('termination_order.yaml')
    print("SUCCESS loading via imported function!")
    print(f"Keys: {data.keys()}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
