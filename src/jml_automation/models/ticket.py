
# from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ---- Core person model -------------------------------------------------------

class UserProfile(BaseModel):
	model_config = ConfigDict(extra="ignore")

	# Identity
	first_name: str
	last_name: str
	email: str  # company/primary email

	# Optional details (often present for onboarding; may be missing for termination)
	personal_email: Optional[str] = None
	title: Optional[str] = None
	phone_mobile: Optional[str] = None
	department: Optional[str] = None
	manager_email: Optional[str] = None
	manager_display: Optional[str] = None

	# Address / timezone
	street_address: Optional[str] = None
	city: Optional[str] = None
	state: Optional[str] = Field(default=None, description="Two-letter code (e.g., UT)")
	zip_code: Optional[str] = None
	country_code: Optional[str] = Field(default=None, description="Two-letter (e.g., US)")
	time_zone: Optional[str] = None


# ---- Onboarding ticket -------------------------------------------------------

class OnboardingTicket(BaseModel):
	model_config = ConfigDict(extra="ignore")

	ticket_id: str
	start_date: Optional[date] = None
	onboarding_location: Optional[str] = None
	office_location_after: Optional[str] = None
	laptop_style: Optional[str] = None
	delivery_time: Optional[str] = None
	hire_type: Optional[str] = None  # e.g., "Employee", "Contractor"

	# Nested user profile (recommended; parser will populate if present)
	user: Optional[UserProfile] = None


# ---- Termination ticket ------------------------------------------------------

class TerminationTicket(BaseModel):
	model_config = ConfigDict(extra="ignore")

	ticket_id: str
	termination_date: Optional[date] = None
	remove_access_date: Optional[date] = None
	term_type: Optional[str] = None
	department: Optional[str] = None
	pre_hire_termination: Optional[bool] = None
	cjis_cleared: Optional[bool] = None
	transfer_to_email: Optional[str] = None
	delivery_time: Optional[str] = None

	# Minimal user info; termination tickets are often sparse
	user: Optional[UserProfile] = None


class PartnerTicket(BaseModel):
	"""Partner onboarding ticket with partner-specific information."""
	model_config = ConfigDict(extra="ignore")

	ticket_id: str
	is_new_partner_org: Optional[bool] = None
	needs_knowbe4: Optional[bool] = None
	partner_company: Optional[str] = None
	partner_email: Optional[str] = None
	partner_name: Optional[str] = None
	filevine_email: Optional[str] = None


__all__ = ["UserProfile", "OnboardingTicket", "TerminationTicket", "PartnerTicket"]
