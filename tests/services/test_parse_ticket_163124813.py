from jml_automation.parsers import fetch_ticket, parse_ticket

# Fetch ticket using the internal ID found previously
raw = fetch_ticket('163124813')
print("RAW TICKET KEYS:", raw.keys() if isinstance(raw, dict) else "Not a dict")
print("TICKET ID:", raw.get('id'))
print("TICKET SUBJECT:", raw.get('subject'))
print("CUSTOM FIELDS:", raw.get('custom_fields'))

# Now try to parse it
try:
    parsed = parse_ticket(raw)
    print("\nPARSED TYPE:", type(parsed).__name__)
    
    # Check user data
    user = getattr(parsed, 'user', None)
    if user:
        print("USER NAME:", user.first_name, user.last_name)
        print("USER EMAIL:", user.email)
        print("USER DEPT:", user.department)
    
    # Check ticket data
    print("START DATE:", getattr(parsed, 'start_date', None))
    print("TICKET ID:", getattr(parsed, 'ticket_id', None))
    
    # Print all attributes
    print("\nALL PARSED ATTRIBUTES:")
    for attr in dir(parsed):
        if not attr.startswith('_'):
            value = getattr(parsed, attr, None)
            if not callable(value):
                print(f"  {attr}: {value}")
except Exception as e:
    print(f"ERROR PARSING: {e}")
    import traceback
    traceback.print_exc()
