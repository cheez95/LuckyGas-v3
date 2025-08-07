"""API monitoring stub - functionality was removed during compaction."""

from typing import Any, Dict


class APIMonitor:
    """Stub API monitor for compatibility."""
    
    def __init__(self):
        self.circuit_breakers = {}
    
    def get_circuit_breaker_states(self) -> Dict[str, Any]:
        """Return empty circuit breaker states."""
        return {}
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Return empty dashboard data."""
        return {
            "status": "monitoring disabled",
            "message": "API monitoring was removed during compaction"
        }


# Create singleton instance
api_monitor = APIMonitor()