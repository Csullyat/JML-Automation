"""
User model for JML Automation.

This module defines the UserProfile dataclass that represents
a user to be onboarded or terminated.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class UserProfile:
	"""
	Represents a user profile for onboarding/termination.
    
	This dataclass contains all the information needed to create
	or remove a user across various services (Okta, Google, etc.)
	"""
	# ========== Required Fields ==========
	# These MUST be provided for every user
	name: str  # Full name of the employee
	title: str  # Job title
	department: str  # Department name
	# ========== Required Address Fields ==========
	streetAddress: str  # Street address
	city: str  # City name
	countryCode: str = "US"  # Country code (default: US)
	# ========== Optional Address Fields ==========
	# These are optional as of the latest update
	state: Optional[str] = None  # State code (e.g., "UT", "CA")
	zipCode: Optional[str] = None  # ZIP/Postal code
	# ========== Contact Information ==========
	mobilePhone: Optional[str] = None  # Formatted phone number (e.g., "555-123-4567")
	secondEmail: Optional[str] = None  # Personal email address
	# ========== Manager Information ==========
	managerId: Optional[str] = None  # Manager's ID (formatted as "LastName, FirstName")
	managerEmail: Optional[str] = None  # Manager's email address
	# ========== Okta-Specific Fields ==========
	preferredLanguage: str = "en"  # Language preference
	organization: str = "Filevine"  # Organization name
	timezone: str = "America/Denver"  # Timezone (calculated based on location)
	primary: bool = True  # Primary account flag
	swrole: str = "Requester"  # SolarWinds role
	# ========== Computed Fields ==========
	# These are typically set by the system
	email: Optional[str] = None  # Work email (usually firstname.lastname@filevine.com)
	okta_user_id: Optional[str] = None  # Okta user ID (set after creation)
	# ========== Additional Service IDs ==========
	# These can be added as users are created in various services
	google_user_id: Optional[str] = None
	microsoft_user_id: Optional[str] = None
