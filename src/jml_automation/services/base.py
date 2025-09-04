from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseService(ABC):
    """Abstract base class for all services."""

    @abstractmethod
    def create_user(self, user_data: Dict) -> bool:
        """Create/provision user"""
        pass

    @abstractmethod
    def terminate_user(self, email: str, manager_email: Optional[str] = None) -> bool:
        """Terminate/disable user"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test service connectivity"""
        pass
