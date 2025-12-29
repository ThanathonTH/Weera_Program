"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PATH CONFIGURATION MODULE                                  ║
║              Centralized Path Management for Frozen/Dev Modes                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🏭 Production Mode: Detects PyInstaller frozen state                        ║
║  🛠️ Development Mode: Uses script directory                                   ║
║  📁 All paths defined relative to BASE_DIR                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys


def is_frozen() -> bool:
    """
    Detect if application is running as a frozen PyInstaller executable.
    
    Returns:
        bool: True if running as .exe, False if running as .py script
    """
    return getattr(sys, 'frozen', False)


def _get_base_dir() -> str:
    """
    Determine the base directory based on execution mode.
    
    Returns:
        str: Absolute path to the application's base directory
    """
    if is_frozen():
        # 🏭 Production Mode (.exe)
        # Use the directory of the executable itself
        return os.path.dirname(sys.executable)
    else:
        # 🛠️ Development Mode (.py)
        # Navigate up from src/utils/paths.py to project root
        current_file = os.path.abspath(__file__)
        utils_dir = os.path.dirname(current_file)  # src/utils/
        src_dir = os.path.dirname(utils_dir)        # src/
        project_root = os.path.dirname(src_dir)     # project root
        return project_root


# ══════════════════════════════════════════════════════════════════════════════
# 📁 DIRECTORY PATHS
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR: str = _get_base_dir()
ENGINE_DIR: str = os.path.join(BASE_DIR, "engine")
FONT_DIR: str = os.path.join(BASE_DIR, "font")
ICON_DIR: str = os.path.join(BASE_DIR, "icon")
SETTINGS_FILE: str = os.path.join(BASE_DIR, "settings.json")

# Ensure critical directories exist
os.makedirs(ENGINE_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# 🔧 BINARY PATHS
# ══════════════════════════════════════════════════════════════════════════════

YTDLP_PATH: str = os.path.join(ENGINE_DIR, "yt-dlp.exe")
FFMPEG_PATH: str = os.path.join(ENGINE_DIR, "ffmpeg.exe")
FFPROBE_PATH: str = os.path.join(ENGINE_DIR, "ffprobe.exe")


# ══════════════════════════════════════════════════════════════════════════════
# 🌐 DOWNLOAD URLs
# ══════════════════════════════════════════════════════════════════════════════

YTDLP_DOWNLOAD_URL: str = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_DOWNLOAD_URL: str = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


# ══════════════════════════════════════════════════════════════════════════════
# 🔄 APP VERSION & UPDATE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

APP_VERSION: str = "3.3.1"
UPDATE_JSON_URL: str = "https://raw.githubusercontent.com/ThanathonTH/Weera_Program/main/version.json"


# ══════════════════════════════════════════════════════════════════════════════
# 🎨 UI ICON PATH
# ══════════════════════════════════════════════════════════════════════════════

def get_icon_path() -> str:
    """
    Get the path to the application icon.
    
    Returns:
        str: Absolute path to the .ico file, or empty string if not found
    """
    icon_path = os.path.join(ICON_DIR, "weeraOwner.ico")
    return icon_path if os.path.exists(icon_path) else ""


# Debug output on import (only in dev mode)
if not is_frozen():
    print(f"📁 [paths.py] BASE_DIR: {BASE_DIR}")
    print(f"📁 [paths.py] ENGINE_DIR: {ENGINE_DIR}")
    print(f"📁 [paths.py] Mode: {'Frozen' if is_frozen() else 'Development'}")
