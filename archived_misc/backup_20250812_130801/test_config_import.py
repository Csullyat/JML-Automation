import traceback
try:
    print("About to import config...")
    import config
    print("✓ Config imported successfully")
    print(f"Module file: {config.__file__}")
    print(f"Available attributes: {[x for x in dir(config) if not x.startswith('_')]}")
    if hasattr(config, 'get_okta_domain'):
        print(f"✓ get_okta_domain exists: {config.get_okta_domain()}")
    else:
        print("✗ get_okta_domain not found")
        
    # Try to execute the config file directly
    print("\nTrying to execute config.py directly...")
    with open('config.py', 'r') as f:
        code = f.read()
    exec(code)
    print("✓ Direct execution successful")
    
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
