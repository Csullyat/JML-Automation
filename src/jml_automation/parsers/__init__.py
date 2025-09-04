# jml_automation.parsers package
from .solarwinds_parser import (
	fetch_ticket,
	detect_type,
	parse_onboarding,
	parse_termination,
	parse_ticket,
	extract_user_email_from_ticket,
	extract_manager_email_from_ticket,
	filter_termination_users,
	parse_termination_ticket_raw,
	print_terminations,
	get_termination_summary,
	process_termination_batch,
)

__all__ = [
	"fetch_ticket",
	"detect_type",
	"parse_onboarding",
	"parse_termination",
	"parse_ticket",
	"extract_user_email_from_ticket",
	"extract_manager_email_from_ticket",
	"filter_termination_users",
	"parse_termination_ticket_raw",
	"print_terminations",
	"get_termination_summary",
	"process_termination_batch",
]
