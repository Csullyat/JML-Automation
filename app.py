from flask import Flask, redirect, url_for, session, request
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import and setup centralized logging
from jml_automation.logger import setup_logging

# Setup logging for Flask app
logger = setup_logging(log_level="INFO", log_to_file=True)

# Importing JML workflows
from jml_automation.workflows.onboarding import run as onboard_run 
from jml_automation.workflows.partner_onboarding import run as partner_run
from jml_automation.workflows.termination import TerminationWorkflow

# Load environment variables from .env file
load_dotenv()

# Configure Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Initialize OAuth
oauth = OAuth(app)

# Register Okta as an OAuth Provider
okta = oauth.register(
    name='okta',
    client_id=os.getenv('OKTA_CLIENT_ID'),
    client_secret=os.getenv('OKTA_CLIENT_SECRET'),
    server_metadata_url=f"https://{os.getenv('OKTA_DOMAIN')}/.well-known/openid-configuration",
    client_kwargs={
        'scope': 'openid profile email'
    }
)

# Function to fetch recent tickets for dropdown
def fetch_recent_tickets():
    """Fetch the 15 most recent ACTIVE tickets from specific groups."""
    try:
        from jml_automation.services.solarwinds import SolarWindsService
        sw = SolarWindsService.from_config()
        
        all_tickets = []
        
        # Define group mappings
        group_mapping = {
            'New Users': {'type': 'onboard', 'label': 'Onboarding'},
            'Terminations': {'type': 'terminate', 'label': 'Termination'},
            'New Partners': {'type': 'partner', 'label': 'Partner'}
        }
        
        active_states = {'Awaiting Input', 'New', 'Assigned', 'In Progress'}
        
        # Fetch 5 pages concurrently (500 tickets)
        all_incidents = []

        def fetch_page(page):
            resp = sw._get("/incidents.json", params={
                "page": page,
                "per_page": 100,
                "sort": "created_at",
                "sort_order": "desc"
            })
            return resp.json()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page, page) for page in range(1, 6)]
            for future in as_completed(futures):
                all_incidents.extend(future.result())

        for incident in all_incidents:
            # Skip if not in active state
            state = incident.get('state', '')
            if state not in active_states:
                continue
            
            # Get assigned group name
            assignee = incident.get('assignee', {})
            group_name = assignee.get('name', '') if isinstance(assignee, dict) else ''
            
            # Check if this ticket is assigned to one of our target groups
            if group_name in group_mapping:
                ticket_info = group_mapping[group_name]
                
                # Extract employee/partner name
                employee_name = 'Unknown'
                subject = incident.get('name', '')
                
                if ticket_info['type'] == 'onboard':
                    custom_fields = incident.get('custom_fields_values', [])
                    for field in custom_fields:
                        if field.get('name') == 'New Employee Name':
                            employee_name = field.get('value', 'Unknown')
                            break
                            
                elif ticket_info['type'] == 'terminate':
                    if ' - ' in subject:
                        employee_name = subject.split(' - ', 1)[1].strip()
                        
                elif ticket_info['type'] == 'partner':
                    custom_fields = incident.get('custom_fields_values', [])
                    for field in custom_fields:
                        if 'Partner Name' in field.get('name', ''):
                            employee_name = field.get('value', 'Unknown')
                            break
                
                all_tickets.append({
                    'id': str(incident.get('id', '')),
                    'number': str(incident.get('number', '')),
                    'name': employee_name,
                    'type': ticket_info['type'],
                    'type_label': ticket_info['label'],
                    'state': state
                })
        
        # Return top 15
        return all_tickets[:15]
        
    except Exception as e:
        logger.error(f"Failed to fetch tickets: {e}")
        return []

# Routes go here
@app.route("/")
def home():
    user = session.get('user')
    if user:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>User Lifecycle Portal</title>
            <link href="https://fonts.googleapis.com/css2?family=IM+Fell+English&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'IM Fell English', serif;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    background-image: url('https://images.steamusercontent.com/ugc/778406211606205211/0672A8435AA614B1F8D8D9C7F8362EC43FFB4A3B/?imw=5000&imh=5000&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=false');
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    position: relative;
                }}
                
                .speech-bubble {{
                    position: fixed;
                    left: 415px;
                    top: 665px;
                    background: rgba(240, 230, 200, 0.95);
                    color: #2c2416;
                    padding: 20px 25px;
                    border-radius: 15px;
                    border: 3px solid #8b7355;
                    max-width: 300px;
                    font-size: 18px;
                    text-align: center;
                    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
                    z-index: 10;
                    opacity: 0;
                    transition: opacity 2s ease-in-out;
                }}
                
                .speech-bubble.show {{
                    opacity: 1;
                }}
                
                .form-container {{
                    position: fixed;
                    top: 30px;
                    left: 30px;
                    z-index: 1;
                    background: rgba(40, 40, 40, 0.9);
                    padding: 40px;
                    border-radius: 12px;
                    border: 2px solid rgba(212, 175, 55, 0.3);
                    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
                    max-width: 500px;
                }}
                
                label {{
                    color: #d4d4d4;
                    display: block;
                    margin-bottom: 8px;
                    font-size: 16px;
                }}
                
                select, input {{
                    width: 100%;
                    padding: 12px;
                    margin-bottom: 20px;
                    border-radius: 6px;
                    border: 2px solid rgba(212, 175, 55, 0.3);
                    background: rgba(30, 30, 30, 0.8);
                    color: #d4d4d4;
                    font-family: 'IM Fell English', serif;
                    font-size: 16px;
                    box-sizing: border-box;
                }}
                
                select:focus, input:focus {{
                    outline: none;
                    border-color: rgba(212, 175, 55, 0.6);
                }}
                
                button {{
                    width: 100%;
                    background: rgba(212, 175, 55, 0.9);
                    color: #2c2416;
                    padding: 15px;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 16px;
                    font-family: 'IM Fell English', serif;
                    cursor: pointer;
                    transition: all 0.3s;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                }}
                
                button:hover {{
                    background: rgba(245, 230, 163, 0.95);
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.7);
                }}
                
                .logout-button {{
                    position: fixed;
                    bottom: 30px;
                    left: 30px;
                    background: rgba(30, 30, 30, 0.85);
                    color: #b0b0b0;
                    padding: 12px 25px;
                    text-decoration: none;
                    border-radius: 8px;
                    border: 2px solid rgba(176, 176, 176, 0.2);
                    font-weight: 600;
                    transition: all 0.3s;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                    z-index: 20;
                }}
                
                .logout-button:hover {{
                    background: rgba(50, 50, 50, 0.9);
                    color: #d0d0d0;
                    border-color: rgba(176, 176, 176, 0.4);
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.7);
                }}
                
                .success-banner {{
                    position: fixed;
                    top: 30px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(76, 175, 80, 0.95);
                    color: white;
                    padding: 15px 25px;
                    border-radius: 8px;
                    border: 2px solid rgba(129, 199, 132, 0.6);
                    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                    z-index: 30;
                    font-size: 16px;
                }}
                
                .error-banner {{
                    position: fixed;
                    top: 30px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(244, 67, 54, 0.95);
                    color: white;
                    padding: 15px 25px;
                    border-radius: 8px;
                    border: 2px solid rgba(239, 83, 80, 0.6);
                    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                    z-index: 30;
                    font-size: 16px;
                }}

                #loading {{
                    color: #d4d4d4;
                    text-align: center;
                    padding: 20px;
                }}
                
                #loading h2 {{
                    color: #d4af37;
                    font-size: 24px;
                }}
                
                #loading p {{
                    color: #d4d4d4;
                    font-size: 16px;
                }}

                .ticket-panel {{
                    position: fixed;
                    top: 30px;
                    right: 30px;
                    width: 350px;
                    max-height: 600px;
                    background: rgba(40, 40, 40, 0.95);
                    border-radius: 12px;
                    border: 2px solid rgba(212, 175, 55, 0.3);
                    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
                    z-index: 25;
                    overflow: hidden;
                }}

                .ticket-panel-header {{
                    background: rgba(30, 30, 30, 0.9);
                    padding: 15px 20px;
                    border-bottom: 2px solid rgba(212, 175, 55, 0.3);
                    color: #d4af37;
                    font-size: 18px;
                    font-weight: 600;
                }}

                .ticket-list {{
                    max-height: 540px;
                    overflow-y: auto;
                    padding: 10px;
                }}

                .ticket-item {{
                    background: rgba(30, 30, 30, 0.8);
                    padding: 15px;
                    margin-bottom: 10px;
                    border-radius: 8px;
                    border: 2px solid rgba(212, 175, 55, 0.2);
                    cursor: pointer;
                    transition: all 0.3s;
                }}

                .ticket-item:hover {{
                    background: rgba(50, 50, 50, 0.9);
                    border-color: rgba(212, 175, 55, 0.5);
                    transform: translateX(-5px);
                }}

                .ticket-number {{
                    color: #d4af37;
                    font-weight: 600;
                    font-size: 16px;
                    margin-bottom: 5px;
                }}

                .ticket-name {{
                    color: #d4d4d4;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}

                .ticket-type {{
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }}

                .type-onboard {{
                    background: rgba(76, 175, 80, 0.3);
                    color: #81c784;
                    border: 1px solid rgba(76, 175, 80, 0.5);
                }}

                .type-terminate {{
                    background: rgba(244, 67, 54, 0.3);
                    color: #e57373;
                    border: 1px solid rgba(244, 67, 54, 0.5);
                }}

                .type-partner {{
                    background: rgba(33, 150, 243, 0.3);
                    color: #64b5f6;
                    border: 1px solid rgba(33, 150, 243, 0.5);
                }}

                .view-link {{
                    color: #64b5f6;
                    text-decoration: none;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 4px 12px;
                    border: 1px solid rgba(100, 181, 246, 0.4);
                    border-radius: 4px;
                    transition: all 0.2s;
                }}

                .view-link:hover {{
                    background: rgba(100, 181, 246, 0.2);
                    border-color: rgba(100, 181, 246, 0.7);
                }}

                /* Scrollbar styling */
                .ticket-list::-webkit-scrollbar {{
                    width: 8px;
                }}

                .ticket-list::-webkit-scrollbar-track {{
                    background: rgba(30, 30, 30, 0.5);
                    border-radius: 4px;
                }}

                .ticket-list::-webkit-scrollbar-thumb {{
                    background: rgba(212, 175, 55, 0.5);
                    border-radius: 4px;
                }}

                .ticket-list::-webkit-scrollbar-thumb:hover {{
                    background: rgba(212, 175, 55, 0.7);
                }}
            </style>
        </head>
        <body>
            <div class="speech-bubble" id="speechBubble"></div>
            
            <!-- Success banner -->
            <div class="success-banner" id="successBanner" style="display:none;"></div>

            <!-- Error banner -->
            <div class="error-banner" id="errorBanner" style="display:none;"></div>
            
            <!-- Ticket panel -->
            <div class="ticket-panel">
                <div class="ticket-panel-header">Recent Tickets</div>
                <div class="ticket-list" id="ticketList">
                    <p style="color: #b0b0b0; text-align: center; padding: 20px;">Loading...</p>
                </div>
            </div>

            <div class="form-container">
                <form id="processingForm" action="/processing/submit" method="post" onsubmit="showLoading()">
                    <label>Action:</label>
                    <select name="action_type" required>
                        <option value="onboard">Employee Onboarding</option>
                        <option value="terminate">Employee Termination</option>
                        <option value="partner">Partner Onboarding/Group Creation</option>
                    </select>

                    <label>Ticket Number:</label>
                    <input type="text" name="ticket_number" required>

                    <button type="submit">Submit</button>
                </form>
                
                <div id="loading" style="display:none;">
                    <h2>Processing...</h2>
                    <p>Please wait, this may take ~3 minutes. Do not refresh the page.</p>
                </div>
            </div>
            
            <a href='/logout' class="logout-button">Logout</a>
            
            <script>
                const userName = "{user['name']}";
                
                function showBubble(text, displayDuration) {{
                    const bubble = document.getElementById('speechBubble');
                    bubble.textContent = text;
                    bubble.classList.add('show');
                    
                    setTimeout(() => {{
                        bubble.classList.remove('show');
                    }}, displayDuration);
                }}
                
                function showLoading() {{
                    // Disable the submit button immediately
                    const submitBtn = document.querySelector('button[type="submit"]');
                    submitBtn.disabled = true;
                    submitBtn.style.opacity = '0.5';
                    submitBtn.style.cursor = 'not-allowed';
                    
                    document.getElementById('processingForm').style.display = 'none';
                    document.getElementById('loading').style.display = 'block';
                    
                    return true; // Allow form submission to proceed
                }}
                
                // Show welcome message on load
                const firstName = userName.split(' ')[0];
                showBubble("Well met, " + firstName + ".", 6000);
                
                // Show success banner if redirected from submit
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('success') === 'true') {{
                    const action = urlParams.get('action');
                    const ticket = urlParams.get('ticket');
                    const banner = document.getElementById('successBanner');
                    banner.textContent = `Task complete: ${{action}} for ticket ${{ticket}}`;
                    banner.style.display = 'block';
                    
                    // Fade out after 6 seconds
                    setTimeout(() => {{
                        banner.style.opacity = '0';
                        banner.style.transition = 'opacity 1s';
                        setTimeout(() => {{
                            banner.style.display = 'none';
                            // Reset form
                            document.getElementById('processingForm').style.display = 'block';
                            document.getElementById('loading').style.display = 'none';
                        }}, 1000);
                    }}, 6000);
                    
                    // Clean URL (remove params)
                    window.history.replaceState({{}}, '', '/');
                }}

                // Show error banner if redirected with error
                if (urlParams.get('status') === 'error') {{
                    const action = urlParams.get('action');
                    const ticket = urlParams.get('ticket');
                    const error = urlParams.get('error');
                    const banner = document.getElementById('errorBanner');
                    banner.textContent = `Error: ${{action}} failed for ticket ${{ticket}}`;
                    banner.style.display = 'block';
                    
                    // Fade out after 6 seconds
                    setTimeout(() => {{
                        banner.style.opacity = '0';
                        banner.style.transition = 'opacity 1s';
                        setTimeout(() => {{
                            banner.style.display = 'none';
                            document.getElementById('processingForm').style.display = 'block';
                            document.getElementById('loading').style.display = 'none';
                        }}, 1000);
                    }}, 6000);
                    
                    // Clean URL
                    window.history.replaceState({{}}, '', '/');
                }}

                // Fetch and display tickets
                function loadTickets() {{
                    fetch('/api/tickets')
                        .then(response => response.json())
                        .then(data => {{
                            const ticketList = document.getElementById('ticketList');
                            const tickets = data.tickets || [];
                            
                            if (tickets.length === 0) {{
                                ticketList.innerHTML = '<p style="color: #b0b0b0; text-align: center; padding: 20px;">No tickets found</p>';
                                return;
                            }}
                            
                            ticketList.innerHTML = tickets.map(ticket => `
                                <div class="ticket-item" onclick="fillForm('${{ticket.type}}', '${{ticket.number}}')">
                                    <div class="ticket-number">#${{ticket.number}}</div>
                                    <div class="ticket-name">${{ticket.name}}</div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                                        <span class="ticket-type type-${{ticket.type}}">${{ticket.type_label}}</span>
                                        <a href="https://filevine.samanage.com/incidents/${{ticket.id}}" 
                                        target="_blank" 
                                        onclick="event.stopPropagation()"
                                        class="view-link">View</a>
                                    </div>
                                </div>
                            `).join('');
                        }})
                        .catch(error => {{
                            console.error('Error loading tickets:', error);
                            document.getElementById('ticketList').innerHTML = '<p style="color: #e57373; text-align: center; padding: 20px;">Error loading tickets</p>';
                        }});
                }}

                // Fill form when ticket is clicked
                function fillForm(type, ticketNumber) {{
                    document.querySelector('select[name="action_type"]').value = type;
                    document.querySelector('input[name="ticket_number"]').value = ticketNumber;
                }}

                // Load tickets on page load
                loadTickets();

                // Refresh tickets every 5 minutes
                setInterval(loadTickets, 300000);
            </script>
        </body>
        </html>
        """
    else:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>User Lifecycle Portal</title>
            <link href="https://fonts.googleapis.com/css2?family=IM+Fell+English&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'IM Fell English', serif;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background-image: url('https://images.steamusercontent.com/ugc/778406211606205211/0672A8435AA614B1F8D8D9C7F8362EC43FFB4A3B/?imw=5000&imh=5000&ima=fit&impolicy=Letterbox&imcolor=%23000000&letterbox=false');
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    position: relative;
                }
                
                .container {
                    position: relative;
                    z-index: 1;
                    padding: 50px 60px;
                    text-align: center;
                    max-width: 500px;
                    width: 90%;
                }
                
                .button {
                    display: inline-block;
                    background: rgba(40, 40, 40, 0.9);
                    color: #d4af37;
                    padding: 15px 40px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    transition: all 0.3s;
                    border: 2px solid rgba(212, 175, 55, 0.3);
                    cursor: pointer;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
                    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                }
                
                .button:hover {
                    background: rgba(60, 60, 60, 0.95);
                    border-color: rgba(212, 175, 55, 0.6);
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.7);
                    color: #f5e6a3;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <a href='/login' class="button">Log In</a>
            </div>
        </body>
        </html>
        """
    
@app.route("/login")
def login():
    redirect_uri = url_for('callback', _external=True)
    return okta.authorize_redirect(redirect_uri)

@app.route("/callback")
def callback():
    token = okta.authorize_access_token()
    user_info = token.get('userinfo')
    session['user'] = user_info
    return redirect(url_for('home'))

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route("/processing/submit", methods=["POST"])
def processing_submit():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    
    action_type = request.form.get('action_type')
    ticket_number = request.form.get('ticket_number')

    try:
        if action_type == 'onboard':
            result = onboard_run(ticket_id=ticket_number, ticket_raw=None, dry_run=False, push_domo=False)
            status = "success" if result == 0 else "failed"

        elif action_type == 'terminate':
            workflow = TerminationWorkflow()
            results = workflow.execute_comprehensive_termination_from_ticket(ticket_number)
            status = "success" if results.get('overall_success') else "failed"

        elif action_type == 'partner':
            result = partner_run(ticket_id=ticket_number, ticket_raw=None, dry_run=False)
            status = "success" if result == 0 else "failed"

        else:
            return "Invalid action type", 400

        return redirect(url_for('home', success='true', action=action_type, ticket=ticket_number))
    
    except Exception as e:
        logger.error(f"Error processing {action_type} for ticket {ticket_number}: {e}")
        return redirect(url_for('home', status='error', action=action_type, ticket=ticket_number, error=str(e)))

@app.route("/api/tickets")
def api_tickets():
    user = session.get('user')
    if not user:
        return {"error": "Not authenticated"}, 401
    
    tickets = fetch_recent_tickets()
    return {"tickets": tickets}

if __name__ == '__main__':
    app.run(debug=True, port=5000)