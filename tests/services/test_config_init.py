from jml_automation.config import Config

try:
    config = Config()
    print("SUCCESS! Config initialized")
    print(f"Settings keys: {config.settings.keys() if config.settings else 'None'}")
    print(f"Departments keys: {config.departments.keys() if config.departments else 'None'}")
    print(f"Termination keys: {config.termination.keys() if config.termination else 'None'}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
