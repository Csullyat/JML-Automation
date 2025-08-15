

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def process_user(ticket, steps, total_steps, ms_term, okta_term, okta_token, google_term, zoom_term):
    user_email = extract_user_email_from_ticket(ticket)
    manager_email = extract_manager_email_from_ticket(ticket)
    if not (user_email and manager_email):
        print("\nSkipping: missing user or manager email.")
        return
    # Step 2: Okta Deactivation (always first)
    step = 2
    print_progress(step, total_steps, steps[step-1])
    try:
        okta_result = okta_term.execute_complete_termination(user_email)
        print_progress(step, total_steps, steps[step-1])
        if not okta_result.get('success'):
            return
    except Exception as e:
        print_progress(step, total_steps, steps[step-1], "✖")
        print(f"\nException during Okta deactivation for {user_email}: {e}")
        return
    # Step 3: Exchange Mailbox Conversion
    step = 3
    print_progress(step, total_steps, steps[step-1])
    try:
        mailbox_status = ms_term.get_mailbox_status(user_email)
        if mailbox_status and mailbox_status.lower() == "sharedmailbox":
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
    # Step 7: Zoom Deprovision
    step = 7
    print_progress(step, total_steps, steps[step-1])
    try:
        zoom_result = zoom_term.execute_complete_termination(user_email, manager_email)
        print_progress(step, total_steps, steps[step-1])
    except Exception:
        print_progress(step, total_steps, steps[step-1], "✖")
    # After Zoom: Remove from Okta Zoom groups (only SSO-Zoom_Member_Basaic and SSO-Zoom_Member_Pro)
    try:
        okta_user = okta_term.get_user_by_email(user_email)
        if okta_user:
            user_id = okta_user['id']
            user_groups = get_user_groups(user_id, okta_token)
            zoom_group_names = ["SSO-Zoom_Member_Basaic", "SSO-Zoom_Member_Pro"]
            zoom_groups = [g for g in user_groups if g.get('profile', {}).get('name', '') in zoom_group_names]
            if zoom_groups:
                for group in zoom_groups:
                    group_id = group['id']
                    group_name = group.get('profile', {}).get('name', '')
                    remove_user_from_group(user_id, group_id, okta_token)
    except Exception:
        pass

import time

def run_microsoft_and_okta_group_cleanup_test():
    start_time = time.time()
    steps = [
        "Pulling ticket data",
        "Okta Deactivation (Sessions, Groups, Disable)",
        "Exchange Mailbox Conversion",
        "M365 Delegation",
        "M365 License Removal",
        "Google Deprovision",
        "Zoom Deprovision"
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
    from zoom_termination import ZoomTermination
    zoom_term = ZoomTermination()
    # Parallel processing for users
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(process_user, ticket, steps, total_steps, ms_term, okta_term, okta_token, google_term, zoom_term) for ticket in filtered]
        for future in as_completed(futures):
            pass
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\nTotal runtime: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")

if __name__ == "__main__":
    run_microsoft_and_okta_group_cleanup_test()
