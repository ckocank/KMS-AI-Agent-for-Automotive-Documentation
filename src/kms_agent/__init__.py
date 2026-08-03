"""Automotive Office knowledge-management agent."""

from .config import Settings
from .service import KMSService

__all__ = ["KMSService", "Settings"]
