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
    slack_user_id: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Generate work email if not provided
        if not self.email and self.name:
            # Convert "FirstName LastName" to "firstname.lastname@filevine.com"
            name_parts = self.name.lower().split()
            if len(name_parts) >= 2:
                self.email = f"{name_parts[0]}.{name_parts[-1]}@filevine.com"
    
    def to_okta_format(self) -> Dict[str, Any]:
        """
        Convert UserProfile to Okta API format.
        
        Returns:
            Dictionary formatted for Okta user creation API
        """
        okta_data = {
            "profile": {
                "firstName": self.first_name,
                "lastName": self.last_name,
                "email": self.email,
                "login": self.email,
                "title": self.title,
                "department": self.department,
                "organization": self.organization,
                "preferredLanguage": self.preferredLanguage,
                "timezone": self.timezone,
                "streetAddress": self.streetAddress,
                "city": self.city,
                "countryCode": self.countryCode,
                "primaryPhone": self.mobilePhone,
                "secondEmail": self.secondEmail,
            }
        }
        
        # Add optional fields if present
        if self.state:
            okta_data["profile"]["state"] = self.state
        if self.zipCode:
            okta_data["profile"]["zipCode"] = self.zipCode
        if self.managerId:
            okta_data["profile"]["managerId"] = self.managerId
        if self.managerEmail:
            okta_data["profile"]["manager"] = self.managerEmail
            
        # Remove None values
        okta_data["profile"] = {k: v for k, v in okta_data["profile"].items() if v is not None}
        
        return okta_data
    
    @property
    def first_name(self) -> str:
        """Extract first name from full name."""
        parts = self.name.split()
        return parts[0] if parts else ""
    
    @property
    def last_name(self) -> str:
        """Extract last name from full name."""
        parts = self.name.split()
        return parts[-1] if len(parts) > 1 else parts[0] if parts else ""
    
    @property
    def display_name(self) -> str:
        """Return a formatted display name."""
        return self.name
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"UserProfile(name='{self.name}', title='{self.title}', dept='{self.department}', email='{self.email}')"