"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       SETTINGS MANAGER MODULE                                 ║
║              Persistent Configuration with JSON Storage                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  💾 Cache-based settings to reduce I/O                                       ║
║  📁 JSON file persistence                                                     ║
║  🔄 Automatic first-run detection                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from typing import Dict, Any, Optional

from src.utils.paths import SETTINGS_FILE


class SettingsManager:
    """
    Persistent Settings Manager with Caching
    
    Manages application settings using JSON file storage.
    Uses class-level caching to minimize disk I/O.
    """
    
    _cache: Optional[Dict[str, Any]] = None
    
    DEFAULT_SETTINGS: Dict[str, Any] = {
        "download_path": "",
        "first_run_complete": False,
    }
    
    @classmethod
    def load(cls) -> Dict[str, Any]:
        """
        Load settings from file (uses cache if available).
        
        Returns:
            Dict[str, Any]: Settings dictionary merged with defaults
        """
        if cls._cache is not None:
            return cls._cache
        
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    cls._cache = {**cls.DEFAULT_SETTINGS, **settings}
                    print(f"✓ Loaded settings from: {SETTINGS_FILE}")
                    return cls._cache
        except Exception as e:
            print(f"⚠️ Failed to load settings: {e}")
        
        cls._cache = cls.DEFAULT_SETTINGS.copy()
        return cls._cache
    
    @classmethod
    def save(cls, settings: Dict[str, Any]) -> bool:
        """
        Save settings to file and update cache.
        
        Args:
            settings: Settings dictionary to save
            
        Returns:
            bool: True if save was successful
        """
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            cls._cache = settings
            print(f"✓ Saved settings to: {SETTINGS_FILE}")
            return True
        except Exception as e:
            print(f"❌ Failed to save settings: {e}")
            return False
    
    @classmethod
    def clear_path(cls) -> bool:
        """
        Clear download_path from settings (session-only mode).
        
        Returns:
            bool: True if operation was successful
        """
        settings = cls.load()
        settings["download_path"] = ""
        return cls.save(settings)
    
    @classmethod
    def save_path(cls, path: str) -> bool:
        """
        Save download_path and mark first run as complete.
        
        Args:
            path: Download directory path to save
            
        Returns:
            bool: True if operation was successful
        """
        settings = cls.load()
        settings["download_path"] = path
        settings["first_run_complete"] = True
        return cls.save(settings)
    
    @classmethod
    def get_path(cls) -> str:
        """
        Get the saved download path.
        
        Returns:
            str: Download path or empty string if not set
        """
        settings = cls.load()
        return settings.get("download_path", "")
    
    @classmethod
    def has_saved_path(cls) -> bool:
        """
        Check if a download path has been saved.
        
        Returns:
            bool: True if a non-empty path exists
        """
        settings = cls.load()
        return bool(settings.get("download_path", ""))
    
    @classmethod
    def is_first_run(cls) -> bool:
        """
        Check if this is the first application run.
        
        Returns:
            bool: True if first_run_complete is False
        """
        settings = cls.load()
        return not settings.get("first_run_complete", False)
    
    @classmethod
    def invalidate_cache(cls) -> None:
        """Force reload settings from disk on next access."""
        cls._cache = None
