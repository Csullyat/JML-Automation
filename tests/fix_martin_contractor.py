"""
Test script to fix Martin Culba's SSO-Swagbucks group membership
"""

def fix_martin_contractor_group():
    from src.jml_automation.services.okta import OktaService
    from src.jml_automation.config import Config
    
    try:
        config = Config()
        okta = OktaService(
            base_url=config.get_okta_url(),
            token=config.get_okta_token()
        )
        
        # Find Martin Culba's user
        martin_email = "martinculba@filevine.com"
        user_id = okta.find_user_by_email(martin_email)
        
        if not user_id:
            print(f"❌ User {martin_email} not found in Okta")
            return
        
        print(f"✅ Found Martin Culba: {user_id}")
        
        # Find SSO-Swagbucks group
        swagbucks_group_id = okta.find_group_id("SSO-Swagbucks")
        
        if not swagbucks_group_id:
            print(f"❌ SSO-Swagbucks group not found in Okta")
            return
            
        print(f"✅ Found SSO-Swagbucks group: {swagbucks_group_id}")
        
        # Remove Martin from SSO-Swagbucks group
        print(f"🔄 Removing {martin_email} from SSO-Swagbucks group...")
        okta.remove_from_groups(user_id, [swagbucks_group_id])
        print(f"✅ Successfully removed {martin_email} from SSO-Swagbucks group")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_martin_contractor_group()