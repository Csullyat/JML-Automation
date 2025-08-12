# Configuration validation functions for orchestrator
def get_configuration_summary() -> dict:
    """Get a summary of all configuration status."""
    try:
        # Test core credentials
        get_okta_token()
        okta_status = True
    except:
        okta_status = False
    
    try:
        get_samanage_token()
        samanage_status = True
    except:
        samanage_status = False
    
    # Test 1Password service account
    try:
        token = get_service_account_token_from_credential_manager()
        onepassword_status = bool(token)
    except:
        onepassword_status = False
    
    return {
        'onepassword_service_account': onepassword_status,
        'component_validation': {
            'okta_token': okta_status,
            'samanage_token': samanage_status
        },
        'critical_components_ready': all([okta_status, samanage_status, onepassword_status]),
        'all_components_ready': all([okta_status, samanage_status, onepassword_status])
    }
