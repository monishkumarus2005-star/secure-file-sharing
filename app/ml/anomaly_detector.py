"""
Machine Learning Anomaly Detection Module
Uses Isolation Forest for detecting anomalous file access patterns
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable, cast
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models

logger = logging.getLogger(__name__)


try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None

try:
    from sklearn.ensemble import IsolationForest  # type: ignore
except Exception:  # pragma: no cover
    IsolationForest = None


@runtime_checkable
class _AnomalyModel(Protocol):
    def fit(self, X: List[List[float]]): ...
    def predict(self, X: List[List[float]]): ...


class AnomalyDetector:
    """
    Sliding window anomaly detector for file access patterns.
    Tracks event frequency per user and consecutive same-file downloads.
    """

    def __init__(self, window_seconds: int = 50, threshold: int = 10):
        self.window_seconds = window_seconds
        self.threshold = threshold
        self._user_events: Dict[int, List[datetime]] = {}
        # Track consecutive downloads of same file: user_id -> file_id -> list of timestamps
        self._user_file_downloads: Dict[int, Dict[int, List[datetime]]] = {}
        # Stricter threshold for same-file consecutive downloads
        self.same_file_window_seconds = 10  # 10 seconds
        self.same_file_threshold = 3  # 3 consecutive downloads

    def detect_anomaly(self, user_id: int, file_id: Optional[int], action_type: str) -> bool:
        """
        Detect if a user's access pattern is anomalous based on frequency.
        Also checks for consecutive downloads of the same file (3 in 10 seconds).
        
        Args:
            user_id: ID of the user
            file_id: ID of the file (can be None)
            action_type: Type of action (upload, download, delete, etc.)
            
        Returns:
            bool: True if anomalous, False otherwise
        """
        now = datetime.utcnow()
        
        # Initialize user events if not exists
        if user_id not in self._user_events:
            self._user_events[user_id] = []
            
        # Add current event
        self._user_events[user_id].append(now)
        
        # Prune timestamps older than window
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._user_events[user_id] = [ts for ts in self._user_events[user_id] if ts > cutoff]
        
        event_count = len(self._user_events[user_id])
        
        # Debug logging
        logger.info(f"User {user_id} has {event_count} events in last {self.window_seconds}s (threshold: {self.threshold})")
        print(f"[ANOMALY DEBUG] User {user_id}: {event_count} events, threshold: {self.threshold}", flush=True)
        
        # Check general threshold
        if event_count > self.threshold:
            logger.warning(
                f"ANOMALY DETECTED: User {user_id} exceeded threshold. "
                f"Action: {action_type}, File ID: {file_id}, "
                f"Events in last {self.window_seconds}s: {event_count}"
            )
            return True
        
        # Check consecutive same-file downloads (3 downloads of same file in 10 seconds)
        if action_type == "download" and file_id is not None:
            if user_id not in self._user_file_downloads:
                self._user_file_downloads[user_id] = {}
            
            if file_id not in self._user_file_downloads[user_id]:
                self._user_file_downloads[user_id][file_id] = []
            
            # Add current download timestamp
            self._user_file_downloads[user_id][file_id].append(now)
            
            # Prune timestamps older than 10 seconds
            file_cutoff = now - timedelta(seconds=self.same_file_window_seconds)
            self._user_file_downloads[user_id][file_id] = [
                ts for ts in self._user_file_downloads[user_id][file_id] if ts > file_cutoff
            ]
            
            file_download_count = len(self._user_file_downloads[user_id][file_id])
            print(f"[ANOMALY DEBUG] User {user_id} downloading file {file_id}: {file_download_count} times in last {self.same_file_window_seconds}s", flush=True)
            
            if file_download_count >= self.same_file_threshold:
                logger.warning(
                    f"SAME-FILE ANOMALY DETECTED: User {user_id} downloaded file {file_id} "
                    f"{file_download_count} times in {self.same_file_window_seconds}s"
                )
                print(f"[ANOMALY] Blocked: User {user_id} exceeded 3 downloads of file {file_id} in 10 seconds", flush=True)
                return True
            
        return False



# Global instance
anomaly_detector = AnomalyDetector()
