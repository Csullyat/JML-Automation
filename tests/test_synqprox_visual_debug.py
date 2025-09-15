#!/usr/bin/env python3
"""Visual debugging test for SYNQ Prox login - runs in full browser mode."""

import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

from jml_automation.logger import logger
from jml_automation.utils.credential_manager import WindowsCredentialManager

class SynqProxVisualDebugger:
    """Visual debugger for SYNQ Prox login process."""
    
    def __init__(self):
        self.driver = None
        self.base_url = "https://app2.synqprox.com/"
        
    def setup_visible_driver(self):
        """Setup Chrome driver in VISIBLE mode for debugging."""
        try:
            chrome_options = ChromeOptions()
            
            # REMOVE headless mode - we want to see the browser!
            # chrome_options.add_argument("--headless=new")  # COMMENTED OUT
            
            # Keep essential options but make it visible
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Essential Flutter fixes
            chrome_options.add_argument("--enable-unsafe-swiftshader")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--force-device-scale-factor=1")
            
            # Anti-detection for Flutter
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Start maximized for better visibility
            chrome_options.add_argument("--start-maximized")
            
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Maximize the window and move to primary monitor
            self.driver.maximize_window()
            
            # Hide webdriver property from Flutter detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("SUCCESS: Chrome driver setup successful in VISIBLE mode")
            print(" BROWSER WINDOW OPENED - You should see Chrome browser now!")
            return True
            
        except Exception as e:
            logger.error(f"ERROR: Failed to setup visible Chrome driver: {e}")
            return False

    def get_credentials(self):
        """Get SYNQ Prox credentials."""
        try:
            cred_manager = WindowsCredentialManager()
            creds = cred_manager.get_synqprox_credentials()
            if creds:
                return creds.get('username'), creds.get('password')
            else:
                raise Exception("No credentials found")
        except Exception as e:
            logger.warning(f"Credential manager not available: {e}")
            # Fallback to environment variables
            username = os.getenv('SYNQPROX_USERNAME')
            password = os.getenv('SYNQPROX_PASSWORD')
            return username, password

    def visual_login_test(self):
        """Test login process with full visual debugging."""
        print("\n" + "="*80)
        print(" SYNQ PROX VISUAL LOGIN DEBUG TEST")
        print("="*80)
        
        try:
            # Get credentials
            username, password = self.get_credentials()
            if not username or not password:
                print("ERROR: No credentials available!")
                return False
                
            print(f" Using username: {username}")
            print(f"Key: Password length: {len(password)} characters")
            
            # Setup visible browser
            if not self.setup_visible_driver():
                print("ERROR: Failed to setup browser")
                return False
            
            print("\n STEP 1: NAVIGATING TO SYNQ PROX...")
            self.driver.get(self.base_url)
            print(f"   URL: {self.base_url}")
            
            print("\n⏳ STEP 2: WAITING FOR PAGE TO LOAD...")
            print("   Waiting 5 seconds for initial load...")
            time.sleep(5)
            
            print("   Taking login page screenshot...")
            os.makedirs("screenshots", exist_ok=True)
            self.driver.save_screenshot("screenshots/visual_debug_01_login_page.png")
            
            print("\n⏳ STEP 3: ADDITIONAL WAIT FOR SITE TO FULLY LOAD...")
            print("   Waiting additional 5 seconds...")
            time.sleep(5)
            
            # Check what fields are available
            print("\n STEP 4: CHECKING AVAILABLE FORM FIELDS...")
            field_info = self.driver.execute_script("""
                var fields = {
                    emailFields: [],
                    passwordFields: [],
                    allInputs: [],
                    forms: []
                };
                
                // Check for email fields
                var emailSelectors = [
                    'input[type="email"]',
                    'input[placeholder*="email"]',
                    'input[placeholder*="Email"]',
                    'input[name="email"]',
                    'input[name="username"]'
                ];
                
                emailSelectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        fields.emailFields.push({
                            selector: selector,
                            placeholder: el.placeholder,
                            name: el.name,
                            type: el.type,
                            visible: el.offsetParent !== null
                        });
                    });
                });
                
                // Check for password fields
                var passwordElements = document.querySelectorAll('input[type="password"]');
                passwordElements.forEach(function(el) {
                    fields.passwordFields.push({
                        placeholder: el.placeholder,
                        name: el.name,
                        visible: el.offsetParent !== null
                    });
                });
                
                // Check all inputs
                var allInputs = document.querySelectorAll('input');
                allInputs.forEach(function(el) {
                    fields.allInputs.push({
                        type: el.type,
                        placeholder: el.placeholder,
                        name: el.name,
                        visible: el.offsetParent !== null
                    });
                });
                
                // Check forms
                var forms = document.querySelectorAll('form');
                fields.forms = forms.length;
                
                return fields;
            """)
            
            print(f"    Email fields found: {len(field_info['emailFields'])}")
            for field in field_info['emailFields']:
                print(f"      - {field}")
                
            print(f"   Key: Password fields found: {len(field_info['passwordFields'])}")
            for field in field_info['passwordFields']:
                print(f"      - {field}")
                
            print(f"    Total input fields: {len(field_info['allInputs'])}")
            print(f"    Forms found: {field_info['forms']}")
            
            # Pause for manual inspection
            print("\n MANUAL INSPECTION PAUSE")
            print("   Look at the browser window now!")
            print("   Press Enter to continue with email entry...")
            input("   > ")
            
            print("\n STEP 5: ENTERING EMAIL...")
            email_result = self.driver.execute_script(f"""
                var usernameField = document.querySelector('input[type="email"]') || 
                                   document.querySelector('input[placeholder*="email"]') || 
                                   document.querySelector('input[placeholder*="Email"]') ||
                                   document.querySelector('input[name="email"]') ||
                                   document.querySelector('input[name="username"]');
                
                if (usernameField) {{
                    usernameField.focus();
                    usernameField.value = '';
                    usernameField.value = '{username}';
                    usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    usernameField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    console.log('Email entered: {username}');
                    return 'email_entered';
                }} else {{
                    console.log('Email field not found');
                    return 'email_field_not_found';
                }}
            """)
            print(f"   Email entry result: {email_result}")
            
            print("   Taking screenshot after email entry...")
            self.driver.save_screenshot("screenshots/visual_debug_02_email_entered.png")
            
            print("   Press Enter to continue with password entry...")
            input("   > ")
            
            print("\nKey: STEP 6: ENTERING PASSWORD...")
            password_result = self.driver.execute_script(f"""
                var passwordField = document.querySelector('input[type="password"]');
                if (passwordField) {{
                    passwordField.focus();
                    passwordField.value = '';
                    passwordField.value = '{password}';
                    passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passwordField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    console.log('Password entered');
                    return 'password_entered';
                }} else {{
                    console.log('Password field not found');
                    return 'password_field_not_found';
                }}
            """)
            print(f"   Password entry result: {password_result}")
            
            print("   Taking screenshot after password entry...")
            self.driver.save_screenshot("screenshots/visual_debug_03_password_entered.png")
            
            print("   Press Enter to continue with form submission...")
            input("   > ")
            
            print("\n STEP 7: FORM SUBMISSION...")
            print("   Adding form reset prevention...")
            
            self.driver.execute_script("""
                // Prevent form reset by intercepting form events
                var form = document.querySelector('form');
                if (form) {
                    form.addEventListener('reset', function(e) {
                        console.log('Form reset prevented');
                        e.preventDefault();
                        return false;
                    });
                }
                
                // Also prevent page reload
                window.addEventListener('beforeunload', function(e) {
                    console.log('Page unload detected');
                });
            """)
            
            print("   Focusing password field and preparing for Enter key...")
            
            focus_result = self.driver.execute_script(f"""
                var passwordField = document.querySelector('input[type="password"]');
                if (passwordField) {{
                    passwordField.focus();
                    passwordField.value = '{password}';
                    passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passwordField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    passwordField.focus();
                    console.log('Password field focused and value set');
                    return 'password_focused';
                }}
                return 'password_focus_failed';
            """)
            print(f"   Focus result: {focus_result}")
            
            print("    VERIFYING PASSWORD FIELD FOCUS BEFORE ENTER!")
            print("   Watch the browser carefully...")
            print("   Press Enter to send the Enter key...")
            input("   > ")
            
            # CRITICAL: Verify we're focused on password field before Enter
            focus_check = self.driver.execute_script(f"""
                var passwordField = document.querySelector('input[type="password"]');
                var activeElement = document.activeElement;
                
                if (passwordField && activeElement === passwordField) {{
                    console.log('SUCCESS: Password field is the active element - ready for Enter');
                    return 'password_field_focused';
                }} else {{
                    console.log('ERROR: Password field is NOT focused, refocusing...');
                    passwordField.focus();
                    passwordField.value = '{password}';
                    return 'refocused_password_field';
                }}
            """)
            print(f"    Focus check result: {focus_check}")
            
            print("   Sending Enter key...")
            try:
                active_element = self.driver.switch_to.active_element
                active_element.send_keys(Keys.ENTER)
                print("   SUCCESS: Enter key sent successfully")
            except Exception as e:
                print(f"   ERROR: Enter key failed: {e}")
            
            print("   Taking screenshot immediately after Enter...")
            self.driver.save_screenshot("screenshots/visual_debug_04_after_enter.png")
            
            print("\n   Waiting 3 seconds to see what happens...")
            time.sleep(3)
            
            print("   Taking screenshot after wait...")
            self.driver.save_screenshot("screenshots/visual_debug_05_after_wait.png")
            
            print("\n   Waiting 2 more seconds for login processing...")
            time.sleep(2)
            
            print("   Taking final screenshot...")
            self.driver.save_screenshot("screenshots/visual_debug_06_final.png")
            
            # Check final state
            final_state = self.driver.execute_script("""
                return {
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState
                };
            """)
            
            print(f"\n FINAL STATE:")
            print(f"   URL: {final_state['url']}")
            print(f"   Title: {final_state['title']}")
            print(f"   Ready State: {final_state['readyState']}")
            
            print("\nSUCCESS: Visual debug test completed!")
            print("   Check the screenshots in the screenshots/ directory")
            print("   Press Enter to close browser...")
            input("   > ")
            
            return True
            
        except Exception as e:
            print(f"ERROR: Visual debug test failed: {e}")
            return False
            
        finally:
            if self.driver:
                print(" Cleaning up browser...")
                self.driver.quit()

def main():
    """Run the visual debug test."""
    debugger = SynqProxVisualDebugger()
    success = debugger.visual_login_test()
    
    if success:
        print("\n Visual debug test completed successfully!")
    else:
        print("\nFAILED: Visual debug test failed!")

if __name__ == "__main__":
    main()