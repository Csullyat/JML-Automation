from jml_automation.services.solarwinds import SolarWindsService

try:
    svc = SolarWindsService.from_config()
    print("SUCCESS! SolarWindsService created")
    print(f"Base URL: {svc.base_url}")
    print(f"Token exists: {bool(svc.token)}")
    print(f"Token length: {len(svc.token) if svc.token else 0}")
    print(f"Token prefix (first 10 chars): {svc.token[:10] if svc.token else 'None'}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
