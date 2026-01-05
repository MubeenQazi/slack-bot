"""
In-memory alert storage module.
Thread-safe alert management for Phase 1.
"""
import threading
from datetime import datetime
from typing import List, Dict, Optional


class AlertStore:
    """Thread-safe in-memory alert storage."""
    
    def __init__(self):
        self._alerts: List[Dict] = []
        self._lock = threading.Lock()
        self._alert_id_counter = 0
    
    def add_alert(self, service: str, severity: str, message: str) -> Dict:
        """
        Add a new alert to the store.
        
        Args:
            service: Name of the service generating the alert
            severity: Alert severity (e.g., 'critical', 'high', 'medium', 'low')
            message: Alert message
        
        Returns:
            The created alert with metadata
        """
        with self._lock:
            self._alert_id_counter += 1
            alert = {
                'id': self._alert_id_counter,
                'service': service,
                'severity': severity,
                'message': message,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'status': 'active'
            }
            self._alerts.append(alert)
            return alert
    
    def get_all_alerts(self) -> List[Dict]:
        """
        Get all alerts.
        
        Returns:
            List of all alerts (newest first)
        """
        with self._lock:
            # Return a copy, newest first
            return list(reversed(self._alerts))
    
    def get_active_alerts(self) -> List[Dict]:
        """
        Get all active alerts.
        
        Returns:
            List of active alerts (newest first)
        """
        with self._lock:
            active = [a for a in self._alerts if a['status'] == 'active']
            return list(reversed(active))
    
    def get_alert_by_id(self, alert_id: int) -> Optional[Dict]:
        """
        Get a specific alert by ID.
        
        Args:
            alert_id: Alert ID
        
        Returns:
            Alert dict or None if not found
        """
        with self._lock:
            for alert in self._alerts:
                if alert['id'] == alert_id:
                    return alert.copy()
            return None
    
    def get_alert_count(self) -> int:
        """Get total number of alerts."""
        with self._lock:
            return len(self._alerts)
    
    def get_active_count(self) -> int:
        """Get count of active alerts."""
        with self._lock:
            return sum(1 for a in self._alerts if a['status'] == 'active')
