"""
Core Package - Business Logic (Decoupled from GUI)
"""

from .settings import SettingsManager
from .downloader import Downloader
from .updater import (
    run_full_update_routine,
    UpdateResult,
    VersionInfo,
    check_ytdlp_update,
)

__all__ = [
    "SettingsManager",
    "Downloader",
    "run_full_update_routine",
    "UpdateResult",
    "VersionInfo",
    "check_ytdlp_update",
]
