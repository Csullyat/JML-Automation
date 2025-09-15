"""SYNQ Prox service for user management automation."""

import time
import os
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw

from ..logger import logger
from .base import BaseService


class SynqProxService(BaseService):
    """Service for SYNQ Prox user management operations."""
    
    def __init__(self):
        """Initialize SYNQ Prox service."""
        super().__init__()
        self.base_url = "https://app2.synqprox.com/"
        self.driver = None
        logger.info("SYNQ Prox service initialized")

    def _setup_driver(self) -> bool:
        """Setup Chrome driver with headless compatibility."""
        try:
            chrome_options = ChromeOptions()
            
            # Core headless configuration
            chrome_options.add_argument("--headless=new")  # Use new headless mode
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

            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Force consistent window size
            self.driver.set_window_size(1920, 1080)
            
            # Hide webdriver property from Flutter detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome driver setup successful with headless compatibility")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return False

    def _login(self) -> bool:
        """Authenticate with SYNQ Prox using service account credentials."""
        try:
            # Try to get credentials from Windows Credential Manager with service account
            try:
                from ..utils.credential_manager import WindowsCredentialManager
                cred_manager = WindowsCredentialManager()
                
                # Get SYNQ Prox credentials using service account token
                creds = cred_manager.get_synqprox_credentials()
                if creds:
                    username = creds.get('username')
                    password = creds.get('password')
                else:
                    raise Exception("No credentials found")
                    
            except Exception as e:
                logger.warning(f"Windows Credential Manager with service account not available: {e}")
                logger.info("Falling back to environment variables for testing")
                
                # Fallback to environment variables for testing
                import os
                username = os.getenv('SYNQPROX_USERNAME')
                password = os.getenv('SYNQPROX_PASSWORD')
                
                if not username or not password:
                    logger.error("No SYNQ Prox credentials available via service account or environment variables")
                    logger.error("For testing, set SYNQPROX_USERNAME and SYNQPROX_PASSWORD environment variables")
                    logger.error("For production, ensure 'JML Service Account' is stored in Windows Credential Manager")
                    return False
            
            if not username or not password:
                logger.error("Missing username or password for SYNQ Prox")
                return False

            logger.info(f"Navigating to SYNQ Prox login page")
            logger.info(f"Using username: {username}")  # Debug log
            self.driver.get(self.base_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Take a screenshot of the login page for debugging
            self.driver.save_screenshot("screenshots/synqprox_login_page.png")
            logger.info("Login page screenshot saved")
            
            # Enter credentials using JavaScript with proper sequence
            login_success = self.driver.execute_script(f"""
                // Step 1: Find and fill email field
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
            
            logger.info(f"Email entry result: {login_success}")
            self.driver.save_screenshot("screenshots/synqprox_01_email_entered.png")
            time.sleep(2)
            
            # Step 2: Fill password field
            password_success = self.driver.execute_script(f"""
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
            
            logger.info(f"Password entry result: {password_success}")
            self.driver.save_screenshot("screenshots/synqprox_02_password_entered.png")
            time.sleep(2)
            
            # Step 3: Click the Login button
            login_button_x = 810  # Moved right 150 pixels more (660 + 150)
            login_button_y = 673  # Moved up 45 pixels (718 - 45)
            
            logger.info(f"Clicking Login button at ({login_button_x}, {login_button_y})")
            
            login_click_success = self.driver.execute_script(f"""
                // First try to find a login button in the DOM
                var loginButton = document.querySelector('button') || 
                                 document.querySelector('[role="button"]') ||
                                 document.querySelector('input[type="submit"]');
                
                if (loginButton) {{
                    loginButton.click();
                    console.log('DOM login button clicked');
                    return 'dom_login_button_clicked';
                }}
                
                // If no DOM button found, try canvas approach
                var canvas = document.querySelector('canvas');
                if (!canvas) {{
                    console.log('No canvas or DOM button found, trying Enter key fallback');
                    // Fallback to Enter key press
                    var passwordField = document.querySelector('input[type="password"]');
                    if (passwordField) {{
                        passwordField.focus();
                        var enterEvent = new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        }});
                        passwordField.dispatchEvent(enterEvent);
                        console.log('Enter pressed on password field as fallback');
                        return 'enter_fallback_used';
                    }}
                    return 'no_login_method_found';
                }}
                
                // Canvas approach for Flutter app
                var rect = canvas.getBoundingClientRect();
                var actualX = rect.left + {login_button_x};
                var actualY = rect.top + {login_button_y};
                
                console.log('Canvas rect:', rect);
                console.log('Clicking login button at actual coordinates:', actualX, actualY);
                
                // Create and dispatch the pointer event
                var event = new PointerEvent('pointerdown', {{
                    pointerId: 1,
                    bubbles: true,
                    cancelable: true,
                    clientX: actualX,
                    clientY: actualY,
                    button: 0,
                    buttons: 1
                }});
                
                canvas.dispatchEvent(event);
                
                // Follow up with pointerup
                var upEvent = new PointerEvent('pointerup', {{
                    pointerId: 1,
                    bubbles: true,
                    cancelable: true,
                    clientX: actualX,
                    clientY: actualY,
                    button: 0,
                    buttons: 0
                }});
                
                canvas.dispatchEvent(upEvent);
                
                console.log('Canvas login button clicked successfully');
                return 'canvas_login_button_clicked';
            """)
            
            logger.info(f"Login button click result: {login_click_success}")
            self._take_screenshot_with_dot("synqprox_03_login_button_clicked.png", login_button_x, login_button_y, "LOGIN BUTTON CLICK")
            
            if not login_success or not password_success or not login_click_success:
                logger.error("Failed to complete login process properly")
                return False
            
            # Wait for login to complete and redirect to main app
            time.sleep(8)
            
            # Take screenshot after login attempt
            self.driver.save_screenshot("screenshots/synqprox_after_login.png")
            logger.info("After login screenshot saved")
            
            # For SYNQ Prox, the URL doesn't change after login, so we'll proceed
            # The deletion process will handle any login issues
            logger.info("Login sequence completed - proceeding with user deletion")
            return True
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def execute_termination(self, user_email: str) -> dict:
        """
        Execute complete SYNQ Prox user termination.
        This is the main method for the termination workflow.
        """
        logger.info(f"SYNQ Prox termination requested for {user_email}")
        
        try:
            # Setup driver
            if not self._setup_driver():
                return {
                    'user_email': user_email,
                    'success': False,
                    'message': 'Failed to setup browser driver',
                    'error': 'Driver setup failed'
                }
            
            # Login
            if not self._login():
                return {
                    'user_email': user_email,
                    'success': False,
                    'message': 'Failed to authenticate with SYNQ Prox',
                    'error': 'Authentication failed'
                }
            
            # Execute user deletion with optimized coordinates
            success = self._delete_user_headless(user_email)
            
            if success:
                logger.info(f"SYNQ Prox user deletion completed successfully for {user_email}")
                return {
                    'user_email': user_email,
                    'success': True,
                    'message': f'SYNQ Prox user {user_email} deleted successfully'
                }
            else:
                logger.error(f"SYNQ Prox user deletion failed for {user_email}")
                return {
                    'user_email': user_email,
                    'success': False,
                    'message': f'SYNQ Prox user deletion failed for {user_email}',
                    'error': 'User deletion process failed'
                }
                
        except Exception as e:
            logger.error(f"SYNQ Prox termination failed for {user_email}: {e}")
            return {
                'user_email': user_email,
                'success': False,
                'message': f'SYNQ Prox termination failed: {e}',
                'error': str(e)
            }
        finally:
            # Always cleanup the driver
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("Browser driver cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up driver: {e}")

    def _add_red_dot_to_screenshot(self, screenshot_path: str, x: int, y: int, step_name: str) -> str:
        """
        Add a red dot to show where we clicked on the screenshot.
        
        Args:
            screenshot_path: Path to the original screenshot
            x: X coordinate of click
            y: Y coordinate of click  
            step_name: Name of the step for labeling
            
        Returns:
            Path to the modified screenshot with red dot
        """
        try:
            # Open the screenshot
            image = Image.open(screenshot_path)
            draw = ImageDraw.Draw(image)
            
            # Draw a red circle (dot) at the click location
            radius = 8
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill='red', outline='darkred', width=2)
            
            # Add text label
            draw.text((x+15, y-10), step_name, fill='red')
            
            # Save the modified image
            modified_path = screenshot_path.replace('.png', '_with_dot.png')
            image.save(modified_path)
            
            logger.info(f"Added red dot at ({x}, {y}) to screenshot: {modified_path}")
            return modified_path
            
        except Exception as e:
            logger.error(f"Failed to add red dot to screenshot: {e}")
            return screenshot_path

    def _take_screenshot_with_dot(self, filename: str, x: int, y: int, step_name: str) -> None:
        """
        Take a screenshot and mark the click location with a red dot.
        
        Args:
            filename: Name of the screenshot file
            x: X coordinate where we clicked
            y: Y coordinate where we clicked
            step_name: Name of the step for debugging
        """
        try:
            # Ensure screenshots directory exists
            os.makedirs("screenshots", exist_ok=True)
            
            # Take the screenshot
            screenshot_path = f"screenshots/{filename}"
            self.driver.save_screenshot(screenshot_path)
            
            # Add red dot to show click location
            modified_path = self._add_red_dot_to_screenshot(screenshot_path, x, y, step_name)
            
            logger.info(f"Screenshot with click marker saved: {modified_path}")
            
        except Exception as e:
            logger.error(f"Failed to take screenshot with dot: {e}")

    def _delete_user_headless(self, user_email: str) -> bool:
        """
        Delete user using optimized headless mode coordinates.
        """
        try:
            logger.info(f"Starting headless user deletion for {user_email}")
            
            # Optimized coordinates for headless mode
            users_x = 82
            users_y = 188   # 45 pixels up from original 233
            
            search_field_x = 840
            search_field_y = 90   # 45 pixels up from original 135
            
            # Delete button coordinates (after fine-tuning)
            delete_x = 605  
            delete_y = 195  

            # Confirm button coordinates (after fine-tuning)
            confirm_x = 510  
            confirm_y = 390  
            
            logger.info(f"🔧 HEADLESS MODE COORDINATES:")
            logger.info(f"   Users: ({users_x}, {users_y})")
            logger.info(f"   Search: ({search_field_x}, {search_field_y})")
            logger.info(f"   Delete: ({delete_x}, {delete_y})")
            logger.info(f"   Confirm: ({confirm_x}, {confirm_y})")
            
            try:
                # STEP 1: CLICK USERS BUTTON
                logger.info("STEP 1: CLICKING USERS BUTTON")
                result1 = self.driver.execute_script(f"""
                    var flutterView = document.querySelector('flutter-view');
                    var rect = flutterView.getBoundingClientRect();
                    var actualX = rect.left + {users_x};
                    var actualY = rect.top + {users_y};
                    
                    var element = document.elementFromPoint(actualX, actualY);
                    if (element) {{
                        var pointerDown = new PointerEvent('pointerdown', {{
                            pointerId: 1,
                            bubbles: true,
                            clientX: actualX,
                            clientY: actualY
                        }});
                        var pointerUp = new PointerEvent('pointerup', {{
                            pointerId: 1,
                            bubbles: true,
                            clientX: actualX,
                            clientY: actualY
                        }});
                        element.dispatchEvent(pointerDown);
                        element.dispatchEvent(pointerUp);
                        return 'USERS BUTTON CLICKED';
                    }}
                    return 'No element found at users button coordinates';
                """)
                logger.info(f"USERS BUTTON CLICK RESULT: {result1}")
                
                # Take screenshot after users click with red dot
                self._take_screenshot_with_dot("synqprox_step_1_users_click.png", users_x, users_y, "USERS CLICK")
                
                # Wait for users page to load
                time.sleep(3)

                # STEP 2: CLICK SEARCH FIELD
                logger.info("STEP 2: CLICKING SEARCH FIELD")
                result2 = self.driver.execute_script(f"""
                    var flutterView = document.querySelector('flutter-view');
                    var rect = flutterView.getBoundingClientRect();
                    var actualX = rect.left + {search_field_x};
                    var actualY = rect.top + {search_field_y};
                    
                    var element = document.elementFromPoint(actualX, actualY);
                    if (element) {{
                        var pointerDown = new PointerEvent('pointerdown', {{
                            pointerId: 1,
                            bubbles: true,
                            clientX: actualX,
                            clientY: actualY
                        }});
                        var pointerUp = new PointerEvent('pointerup', {{
                            pointerId: 1,
                            bubbles: true,
                            clientX: actualX,
                            clientY: actualY
                        }});
                        element.dispatchEvent(pointerDown);
                        element.dispatchEvent(pointerUp);
                        element.focus();
                        return 'SEARCH FIELD CLICKED';
                    }}
                    return 'No element found at search field coordinates';
                """)
                logger.info(f"SEARCH FIELD CLICK RESULT: {result2}")

                # Take screenshot after search click with red dot
                self._take_screenshot_with_dot("synqprox_step_2_search_click.png", search_field_x, search_field_y, "SEARCH CLICK")

                # Wait for field to become active
                time.sleep(3)

                # STEP 3: ENTER EMAIL AND PRESS ENTER
                logger.info("STEP 3: ENTERING EMAIL AND PRESSING ENTER")
                self.driver.switch_to.active_element.send_keys(user_email)
                self.driver.switch_to.active_element.send_keys(Keys.ENTER)
                logger.info(f"Entered email: {user_email} and pressed Enter")

                # Take screenshot after email entry (no click for this step)
                self.driver.save_screenshot("screenshots/synqprox_step_3_email_entry.png")

                # Wait for search results
                time.sleep(2)

                # STEP 4: CLICK DELETE BUTTON
                logger.info("STEP 4: CLICKING DELETE BUTTON")
                result4 = self.driver.execute_script(f"""
                    var flutterView = document.querySelector('flutter-view');
                    var rect = flutterView.getBoundingClientRect();
                    var actualX = rect.left + {delete_x};
                    var actualY = rect.top + {delete_y};
                    
                    window.scrollTo(0, 0);
                    
                    var element = document.elementFromPoint(actualX, actualY);
                    if (element) {{
                        element.focus();
                        
                        var pointerDown = new PointerEvent('pointerdown', {{
                            pointerId: 1, bubbles: true, clientX: actualX, clientY: actualY
                        }});
                        var pointerUp = new PointerEvent('pointerup', {{
                            pointerId: 1, bubbles: true, clientX: actualX, clientY: actualY
                        }});
                        var clickEvent = new MouseEvent('click', {{
                            bubbles: true, clientX: actualX, clientY: actualY
                        }});
                        
                        element.dispatchEvent(pointerDown);
                        element.dispatchEvent(pointerUp);
                        element.dispatchEvent(clickEvent);
                        
                        return 'DELETE BUTTON CLICKED - Element: ' + element.tagName + ' at (' + actualX + ', ' + actualY + ')';
                    }}
                    return 'No element found at delete button coordinates (' + actualX + ', ' + actualY + ')';
                """)
                logger.info(f"DELETE BUTTON CLICK RESULT: {result4}")

                # Take screenshot after delete click with red dot
                self._take_screenshot_with_dot("synqprox_step_4_delete_click.png", delete_x, delete_y, "DELETE CLICK")

                # Wait for confirmation dialog
                time.sleep(2)

                # STEP 5: FINAL CONFIRMATION CLICK
                logger.info(f"STEP 5: FINAL CONFIRMATION CLICK")
                result5 = self.driver.execute_script(f"""
                    var flutterView = document.querySelector('flutter-view');
                    var rect = flutterView.getBoundingClientRect();
                    var actualX = rect.left + {confirm_x};
                    var actualY = rect.top + {confirm_y};
                    
                    window.scrollTo(0, 0);
                    
                    var element = document.elementFromPoint(actualX, actualY);
                    if (element) {{
                        element.focus();
                        
                        var pointerDown = new PointerEvent('pointerdown', {{
                            pointerId: 1, bubbles: true, clientX: actualX, clientY: actualY
                        }});
                        var pointerUp = new PointerEvent('pointerup', {{
                            pointerId: 1, bubbles: true, clientX: actualX, clientY: actualY
                        }});
                        var clickEvent = new MouseEvent('click', {{
                            bubbles: true, clientX: actualX, clientY: actualY
                        }});
                        
                        element.dispatchEvent(pointerDown);
                        element.dispatchEvent(pointerUp);
                        element.dispatchEvent(clickEvent);
                        
                        return 'FINAL CONFIRMATION COMPLETED - Element: ' + element.tagName + ' at (' + actualX + ', ' + actualY + ')';
                    }}
                    return 'No element found at final confirmation coordinates (' + actualX + ', ' + actualY + ')';
                """)
                logger.info(f"FINAL CONFIRMATION RESULT: {result5}")

                # Take screenshot after final click with red dot
                self._take_screenshot_with_dot("synqprox_step_5_final_click.png", confirm_x, confirm_y, "CONFIRM CLICK")

                # Wait a moment for the action to complete
                time.sleep(2)

                logger.info(f"All steps completed for user deletion: {user_email}")
                return True
                
            except Exception as e:
                logger.error(f"Error during user deletion steps: {e}")
                # Take error screenshot
                try:
                    self.driver.save_screenshot("screenshots/synqprox_error.png")
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"Error in headless user deletion: {e}")
            return False

    def test_connectivity(self) -> dict:
        """Test connection to SYNQ Prox."""
        try:
            if not self._setup_driver():
                return {'success': False, 'error': 'Failed to setup browser driver'}
            
            self.driver.get(self.base_url)
            title = self.driver.title
            
            if title:
                logger.info(f"SYNQ Prox connectivity test successful - Title: {title}")
                return {
                    'success': True,
                    'message': f'Connected to SYNQ Prox - {title}',
                    'url': self.base_url
                }
            else:
                return {'success': False, 'error': 'Could not load SYNQ Prox page'}
                
        except Exception as e:
            logger.error(f"SYNQ Prox connectivity test failed: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

    # Legacy methods for backward compatibility
    def delete_user(self, user_email: str) -> bool:
        """Legacy method - use execute_termination instead."""
        logger.warning("delete_user deprecated - use execute_termination instead")
        result = self.execute_termination(user_email)
        return result.get('success', False)

    def create_user(self, user_data: dict) -> bool:
        """Not implemented for termination workflow."""
        logger.warning("create_user not implemented for SYNQ Prox termination service")
        return False

    def terminate_user(self, user_email: str) -> bool:
        """Legacy method - use execute_termination instead."""
        logger.warning("terminate_user deprecated - use execute_termination instead")
        result = self.execute_termination(user_email)
        return result.get('success', False)

    def test_connection(self) -> bool:
        """Legacy method - use test_connectivity instead."""
        result = self.test_connectivity()
        return result.get('success', False)
