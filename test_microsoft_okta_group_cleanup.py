
import sys
import time
from microsoft_termination import MicrosoftTermination
from okta_termination import OktaTermination, get_user_groups, remove_user_from_group
from termination_extractor import fetch_tickets
from ticket_processor import extract_user_email_from_ticket, extract_manager_email_from_ticket
from config import get_okta_token
from google_termination import GoogleTerminationManager

# Suppress all logging output to stdout
import logging
logging.basicConfig(level=logging.CRITICAL)

def print_progress(step, total_steps, message, status=None):
    bar_length = 30
    progress = int(bar_length * step / total_steps)
    bar = '[' + '=' * progress + ' ' * (bar_length - progress) + ']'
    print(f"{bar} {step}/{total_steps} {message}")

def run_microsoft_and_okta_group_cleanup_test():
    steps = [
        "Pulling ticket data",
        "Okta Deactivation (Sessions, Groups, Disable)",
        "Exchange Mailbox Conversion",
        "M365 Delegation",
        "M365 License Removal",
        "Google Deprovision (and Okta Google group removal)"
    ]
    total_steps = len(steps)
    step = 1
    print_progress(step, total_steps, steps[step-1])
    all_tickets = fetch_tickets(per_page=200, max_pages=30)
    filtered = []
    for t in all_tickets:
        state = t.get('state', '').strip().lower()
        assignee = t.get('assignee', '').strip().lower() if isinstance(t.get('assignee', ''), str) else ''
        if not assignee and isinstance(t.get('assignee', None), dict):
            assignee = t['assignee'].get('name', '').strip().lower()
        if state == 'awaiting input' and assignee == 'terminations':
            filtered.append(t)
    print_progress(step, total_steps, steps[step-1])
    if not filtered:
        print("\nNo actionable tickets found.")
        return
    ms_term = MicrosoftTermination()
    okta_term = OktaTermination()
    okta_token = get_okta_token()
    google_term = GoogleTerminationManager()
    for i, ticket in enumerate(filtered):
        user_email = extract_user_email_from_ticket(ticket)
        manager_email = extract_manager_email_from_ticket(ticket)
        if not (user_email and manager_email):
            print("\nSkipping: missing user or manager email.")
            continue
        # Step 2: Okta Deactivation (always first)
        step = 2
        print_progress(step, total_steps, steps[step-1])
        try:
            okta_result = okta_term.execute_complete_termination(user_email)
            print_progress(step, total_steps, steps[step-1])
            if not okta_result.get('success'):
                continue
        except Exception as e:
            print_progress(step, total_steps, steps[step-1], "✖")
            print(f"\nException during Okta deactivation for {user_email}: {e}")
            continue
        # Step 3: Exchange Mailbox Conversion
        step = 3
        print_progress(step, total_steps, steps[step-1])
        try:
            mailbox_status = ms_term.get_mailbox_status(user_email)
            if mailbox_status and mailbox_status.lower() == "sharedmailbox":
                print(f"INFO:microsoft_termination:Mailbox {user_email} is already a shared mailbox. Skipping conversion.")
                print_progress(step, total_steps, steps[step-1], "SKIP")
            else:
                mailbox_result = ms_term.convert_mailbox_to_shared(user_email)
                print_progress(step, total_steps, steps[step-1])
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # Step 4: M365 Delegation
        step = 4
        print_progress(step, total_steps, steps[step-1])
        try:
            delegate_result = ms_term.delegate_mailbox_access(user_email, manager_email)
            print_progress(step, total_steps, steps[step-1])
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # Step 5: M365 License Removal
        step = 5
        print_progress(step, total_steps, steps[step-1])
        try:
            license_result = ms_term.remove_user_licenses(user_email)
            print_progress(step, total_steps, steps[step-1])
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # After Microsoft: Remove from Okta Microsoft groups only (never all groups)
        if not (mailbox_status and mailbox_status.lower() == "shared"):
            try:
                okta_user = okta_term.get_user_by_email(user_email)
                if okta_user:
                    user_id = okta_user['id']
                    user_groups = get_user_groups(user_id, okta_token)
                    ms_groups = [g for g in user_groups if 'microsoft' in g.get('profile', {}).get('name', '').lower()]
                    if ms_groups:
                        for group in ms_groups:
                            group_id = group['id']
                            group_name = group.get('profile', {}).get('name', '')
                            remove_user_from_group(user_id, group_id, okta_token)
            except Exception:
                pass
        # Step 6: Google Deprovision
        step = 6
        print_progress(step, total_steps, steps[step-1])
        try:
            google_result = google_term.execute_complete_termination(user_email, manager_email)
            print_progress(step, total_steps, steps[step-1])
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # After Google: Remove from Okta Google groups only
        try:
            okta_user = okta_term.get_user_by_email(user_email)
            if okta_user:
                user_id = okta_user['id']
                user_groups = get_user_groups(user_id, okta_token)
                google_groups = [g for g in user_groups if 'google' in g.get('profile', {}).get('name', '').lower()]
                if google_groups:
                    for group in google_groups:
                        group_id = group['id']
                        group_name = group.get('profile', {}).get('name', '')
                        remove_user_from_group(user_id, group_id, okta_token)
        except Exception:
            pass
        break  # Only process the first ticket for safety
        try:
            mailbox_result = ms_term.convert_mailbox_to_shared(user_email)
            if mailbox_result == "already_shared":
                print_progress(step, total_steps, steps[step-1], "SKIP")
                # Skip rest of Microsoft steps, go to Google
                for skip_step in range(3, 6):
                    print_progress(skip_step, total_steps, steps[skip_step-1], "SKIP")
                step = 6
                print_progress(step, total_steps, steps[step-1])
                try:
                    google_result = google_term.execute_complete_termination(user_email, manager_email)
                    print_progress(step, total_steps, steps[step-1], "✔" if google_result else "✖")
                except Exception:
                    print_progress(step, total_steps, steps[step-1], "✖")
                break
            print_progress(step, total_steps, steps[step-1], "✔" if mailbox_result else "✖")
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # Step 3: Assign Delegates
        step = 3
        print_progress(step, total_steps, steps[step-1])
        try:
            delegate_result = ms_term.delegate_mailbox_access(user_email, manager_email)
            print_progress(step, total_steps, steps[step-1], "✔" if delegate_result else "✖")
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # Step 4: Remove License
        step = 4
        print_progress(step, total_steps, steps[step-1])
        try:
            license_result = ms_term.remove_user_licenses(user_email)
            print_progress(step, total_steps, steps[step-1], "✔" if license_result.get('success') else "✖")
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # Step 5: Remove from Okta Group(s)
        step = 5
        print_progress(step, total_steps, steps[step-1])
        try:
            okta_user = okta_term.get_user_by_email(user_email)
            if okta_user:
                user_id = okta_user['id']
                user_groups = get_user_groups(user_id, okta_token)
                ms_groups = [g for g in user_groups if 'microsoft' in g.get('profile', {}).get('name', '').lower()]
                google_groups = [g for g in user_groups if 'google' in g.get('profile', {}).get('name', '').lower()]
                all_success = True
                # Remove from Microsoft groups
                if ms_groups:
                    for group in ms_groups:
                        group_id = group['id']
                        group_name = group.get('profile', {}).get('name', '')
                        success = remove_user_from_group(user_id, group_id, okta_token)
                        if not success:
                            all_success = False
                # Remove from Google groups
                if google_groups:
                    for group in google_groups:
                        group_id = group['id']
                        group_name = group.get('profile', {}).get('name', '')
                        success = remove_user_from_group(user_id, group_id, okta_token)
                        if not success:
                            all_success = False
                if ms_groups or google_groups:
                    print_progress(step, total_steps, steps[step-1], "✔" if all_success else "✖")
                else:
                    print_progress(step, total_steps, steps[step-1], "SKIP")
            else:
                print_progress(step, total_steps, steps[step-1], "✖")
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        # Step 6: Google Deprovision (and Okta Google group removal)
        step = 6
        print_progress(step, total_steps, steps[step-1])
        try:
            google_result = google_term.execute_complete_termination(user_email, manager_email)
            # After Google deprovision, remove from Okta Google groups
            okta_user = okta_term.get_user_by_email(user_email)
            if okta_user:
                user_id = okta_user['id']
                user_groups = get_user_groups(user_id, okta_token)
                google_groups = [g for g in user_groups if 'google' in g.get('profile', {}).get('name', '').lower()]
                all_success = google_result
                if google_groups:
                    for group in google_groups:
                        group_id = group['id']
                        group_name = group.get('profile', {}).get('name', '')
                        success = remove_user_from_group(user_id, group_id, okta_token)
                        if not success:
                            all_success = False
                print_progress(step, total_steps, steps[step-1], "✔" if all_success else "✖")
            else:
                print_progress(step, total_steps, steps[step-1], "✖")
        except Exception:
            print_progress(step, total_steps, steps[step-1], "✖")
        break  # Only process the first ticket for safety

if __name__ == "__main__":
    run_microsoft_and_okta_group_cleanup_test()
