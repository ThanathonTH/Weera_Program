"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        UPDATER MODULE v2.0                                   ║
║              Smart Version Control & Chained Update System                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🧠 Smart Versioning - Check before download                                 ║
║  🔗 Chained Updates - App first, then yt-dlp                                ║
║  🔄 Swap & Restart - Self-update for .exe files                             ║
║  📞 Pure Logic - No GUI imports                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import requests
import tempfile
import zipfile
import shutil
from typing import Callable, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from src.utils.paths import ENGINE_DIR, YTDLP_PATH, is_frozen


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class UpdateError(Exception):
    """Custom exception for update failures"""
    pass


class VersionCheckError(Exception):
    """Exception for version checking failures"""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class VersionInfo:
    """Version information for update checking"""
    version: str
    download_url: str
    release_notes: str = ""
    
    def __bool__(self) -> bool:
        return bool(self.version and self.download_url)


@dataclass
class UpdateResult:
    """Result of an update operation"""
    success: bool
    message: str
    requires_restart: bool = False
    new_version: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# TYPE ALIASES
# ══════════════════════════════════════════════════════════════════════════════

ProgressCallback = Callable[[str, float], None]  # (label, percentage)
LogCallback = Callable[[str, str], None]  # (message, level)


# ══════════════════════════════════════════════════════════════════════════════
# VERSION COMPARISON UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def compare_versions(local: str, remote: str) -> int:
    """
    Compare version strings.
    
    Args:
        local: Local version string
        remote: Remote version string
    
    Returns:
        -1: local < remote (needs update)
         0: local == remote (up to date)
         1: local > remote (local is newer)
    """
    def normalize(v: str) -> list:
        """Convert version string to list of integers for comparison."""
        v = v.strip().lstrip('v').lstrip('V')
        parts = []
        for part in v.replace('-', '.').replace('_', '.').split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        return parts
    
    try:
        local_parts = normalize(local)
        remote_parts = normalize(remote)
        
        # Pad to equal length
        max_len = max(len(local_parts), len(remote_parts))
        local_parts.extend([0] * (max_len - len(local_parts)))
        remote_parts.extend([0] * (max_len - len(remote_parts)))
        
        for l, r in zip(local_parts, remote_parts):
            if l < r:
                return -1
            elif l > r:
                return 1
        return 0
        
    except Exception:
        if local == remote:
            return 0
        return -1 if local < remote else 1


# ══════════════════════════════════════════════════════════════════════════════
# YT-DLP VERSION CHECKING
# ══════════════════════════════════════════════════════════════════════════════

def get_local_ytdlp_version(ytdlp_path: str) -> Optional[str]:
    """
    Get the version of the local yt-dlp binary.
    
    Args:
        ytdlp_path: Path to yt-dlp.exe
    
    Returns:
        str: Version string (e.g., "2023.11.16") or None if not found
    """
    if not os.path.exists(ytdlp_path):
        print(f"[DEBUG] yt-dlp not found at: {ytdlp_path}")
        return None
    
    try:
        result = subprocess.run(
            [ytdlp_path, "--version"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        )
        
        print(f"[DEBUG] yt-dlp --version stdout: '{result.stdout.strip()}'")
        
        if result.returncode == 0:
            version = result.stdout.strip()
            return version if version else None
        else:
            print(f"[DEBUG] yt-dlp --version failed: return code {result.returncode}")
            return None
        
    except subprocess.TimeoutExpired:
        print(f"[DEBUG] yt-dlp --version timed out")
        return None
    except FileNotFoundError:
        print(f"[DEBUG] yt-dlp executable not found")
        return None
    except Exception as e:
        print(f"[DEBUG] Error getting yt-dlp version: {type(e).__name__}: {e}")
        return None


def get_remote_ytdlp_version() -> Optional[VersionInfo]:
    """
    Get the latest yt-dlp version from GitHub API.
    
    Returns:
        VersionInfo or None if check failed
    """
    API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
    
    try:
        response = requests.get(
            API_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=15
        )
        
        # Handle rate limit
        if response.status_code == 403:
            remaining = response.headers.get('X-RateLimit-Remaining', '0')
            if remaining == '0':
                print("⚠️ GitHub API rate limit exceeded")
                return None
        
        response.raise_for_status()
        data = response.json()
        
        version = data.get("tag_name", "").strip()
        
        # Find download URL for Windows exe
        download_url = ""
        for asset in data.get("assets", []):
            if asset.get("name") == "yt-dlp.exe":
                download_url = asset.get("browser_download_url", "")
                break
        
        # Fallback URL
        if not download_url:
            download_url = f"https://github.com/yt-dlp/yt-dlp/releases/download/{version}/yt-dlp.exe"
        
        return VersionInfo(
            version=version,
            download_url=download_url,
            release_notes=data.get("body", "")[:500]
        )
        
    except requests.RequestException:
        return None
    except Exception:
        return None


def check_ytdlp_update(engine_dir: str) -> Tuple[bool, str, str]:
    """
    Check if yt-dlp needs to be updated.
    
    Args:
        engine_dir: Path to engine directory
    
    Returns:
        (needs_update: bool, local_version: str, remote_version: str)
    """
    ytdlp_path = os.path.join(engine_dir, "yt-dlp.exe")
    
    local_ver = get_local_ytdlp_version(ytdlp_path) or "ไม่พบ"
    remote_info = get_remote_ytdlp_version()
    
    if remote_info is None:
        return (False, local_ver, "ไม่สามารถเช็คได้")
    
    remote_ver = remote_info.version
    
    if local_ver == "ไม่พบ":
        return (True, local_ver, remote_ver)
    
    comparison = compare_versions(local_ver, remote_ver)
    needs_update = comparison < 0
    
    return (needs_update, local_ver, remote_ver)


# ══════════════════════════════════════════════════════════════════════════════
# APP VERSION CHECKING (Self-Update)
# ══════════════════════════════════════════════════════════════════════════════

def check_app_update(
    current_version: str,
    version_url: str
) -> Optional[VersionInfo]:
    """
    Check if the application has a new version available.
    
    Args:
        current_version: Current app version (e.g., "3.1.0")
        version_url: URL to version.json
    
    Returns:
        VersionInfo if update available, None if up to date
    """
    try:
        response = requests.get(version_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        remote_version = data.get("version", "")
        if not remote_version:
            return None
        
        comparison = compare_versions(current_version, remote_version)
        
        if comparison < 0:
            return VersionInfo(
                version=remote_version,
                download_url=data.get("download_url", ""),
                release_notes=data.get("release_notes", "")
            )
        
        return None
        
    except Exception:
        return None


def perform_app_update(
    download_url: str,
    app_path: str,
    progress_callback: Optional[ProgressCallback] = None,
    log_callback: Optional[LogCallback] = None
) -> UpdateResult:
    """
    Update the application using Swap & Restart strategy.
    
    Supports both raw .exe files and ZIP packages.
    
    Args:
        download_url: URL to download new version
        app_path: Path to current .exe
        progress_callback: Progress update function
        log_callback: Log message function
    
    Returns:
        UpdateResult with requires_restart=True if successful
    """
    def report_progress(label: str, pct: float) -> None:
        if progress_callback:
            progress_callback(label, pct)
    
    def log(msg: str, level: str = "INFO") -> None:
        if log_callback:
            log_callback(msg, level)
    
    app_dir = os.path.dirname(app_path)
    app_name = os.path.basename(app_path)
    download_temp = os.path.join(app_dir, "_update_download.tmp")
    extract_dir = os.path.join(app_dir, "_update_extract")
    batch_path = os.path.join(app_dir, "update.bat")
    
    try:
        # Download
        log("📥 Downloading new version...", "INFO")
        report_progress("กำลังดาวน์โหลด...", 10.0)
        
        response = requests.get(download_url, stream=True, timeout=120)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(download_temp, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = 10.0 + (downloaded / total_size) * 50.0
                    report_progress(f"ดาวน์โหลด... {downloaded // (1024*1024)} MB", pct)
        
        log(f"✓ Download complete: {downloaded} bytes", "INFO")
        
        # Check file type
        report_progress("ตรวจสอบไฟล์...", 65.0)
        is_zip = zipfile.is_zipfile(download_temp)
        log(f"   • File type: {'ZIP Package' if is_zip else 'Raw EXE'}", "INFO")
        
        if is_zip:
            # ZIP Package mode
            report_progress("แตกไฟล์ ZIP...", 70.0)
            log("📦 Extracting ZIP package...", "INFO")
            
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(download_temp, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find exe in extracted content
            exe_found = None
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith('.exe') and 'infinity' in f.lower():
                        exe_found = os.path.join(root, f)
                        break
                if exe_found:
                    break
            
            if not exe_found:
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.lower().endswith('.exe'):
                            exe_found = os.path.join(root, f)
                            break
                    if exe_found:
                        break
            
            if not exe_found:
                raise UpdateError("ไม่พบไฟล์ .exe ใน ZIP Package")
            
            source_dir = os.path.dirname(exe_found) if os.path.dirname(exe_found) != extract_dir else extract_dir
            log(f"   • Found EXE: {os.path.basename(exe_found)}", "INFO")
            
            # Create batch script for directory merge
            report_progress("เตรียมการติดตั้ง...", 85.0)
            log("📝 Creating update script (Directory Merge)...", "INFO")
            
            batch_content = f'''@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════
echo   Infinity Downloader - Auto Update
echo ══════════════════════════════════════════
echo.

:: Wait for app to close
echo [1/4] รอให้โปรแกรมปิด...
timeout /t 3 /nobreak >nul

:: Try to kill process
taskkill /f /im "{app_name}" 2>nul
timeout /t 2 /nobreak >nul

:: Copy files
echo [2/4] ติดตั้งไฟล์ใหม่...
robocopy "{source_dir}" "{app_dir}" /E /NFL /NDL /NJH /NJS /nc /ns /np 2>nul
if errorlevel 8 (
    xcopy /s /e /y /q "{source_dir}\\*" "{app_dir}\\" 2>nul
)

:: Cleanup
echo [3/4] ทำความสะอาด...
rmdir /s /q "{extract_dir}" 2>nul
del /f /q "{download_temp}" 2>nul

:: Start app
echo [4/4] เปิดโปรแกรม...
if exist "{app_path}" (
    echo.
    echo ════════════════════════════════════════
    echo   ติดตั้งสำเร็จ! กำลังเปิดโปรแกรม...
    echo ════════════════════════════════════════
    timeout /t 2 /nobreak >nul
    start "" "{app_path}" --post-update
) else (
    echo.
    echo เกิดข้อผิดพลาดในการติดตั้ง
    pause
)

:: Delete self
(goto) 2>nul & del "%~f0"
'''
        else:
            # Raw EXE mode
            new_app_path = os.path.join(app_dir, "app.new.exe")
            
            if os.path.exists(new_app_path):
                os.remove(new_app_path)
            os.rename(download_temp, new_app_path)
            
            if os.path.getsize(new_app_path) < 10000:
                raise UpdateError("ไฟล์ที่ดาวน์โหลดเสียหาย")
            
            report_progress("เตรียมการติดตั้ง...", 85.0)
            log("📝 Creating update script (Single EXE)...", "INFO")
            
            batch_content = f'''@echo off
chcp 65001 >nul
echo กำลังอัปเดต... กรุณารอสักครู่
echo.

timeout /t 3 /nobreak >nul

echo ลบไฟล์เก่า...
del /f /q "{app_path}" 2>nul

if exist "{app_path}" (
    echo พยายามปิดโปรแกรม...
    taskkill /f /im "{app_name}" 2>nul
    timeout /t 2 /nobreak >nul
    del /f /q "{app_path}" 2>nul
)

echo ติดตั้งเวอร์ชันใหม่...
move /y "{new_app_path}" "{app_path}"

if exist "{app_path}" (
    echo.
    echo ติดตั้งสำเร็จ! กำลังเปิดโปรแกรม...
    timeout /t 1 /nobreak >nul
    start "" "{app_path}" --post-update
) else (
    echo.
    echo เกิดข้อผิดพลาดในการติดตั้ง
    pause
)

(goto) 2>nul & del "%~f0"
'''
        
        # Write and execute batch
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        report_progress("เริ่มการติดตั้ง...", 95.0)
        log("🚀 Starting update script - app will restart automatically", "INFO")
        
        subprocess.Popen(
            ["cmd", "/c", batch_path],
            shell=False,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=app_dir
        )
        
        report_progress("✅ พร้อมรีสตาร์ท!", 100.0)
        
        return UpdateResult(
            success=True,
            message="กรุณารอสักครู่ โปรแกรมจะเปิดใหม่อัตโนมัติ",
            requires_restart=True,
            new_version=""
        )
        
    except Exception as e:
        log(f"❌ Update failed: {str(e)}", "ERROR")
        report_progress("❌ ล้มเหลว", 0)
        
        # Cleanup
        try:
            if os.path.exists(download_temp):
                os.remove(download_temp)
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            if os.path.exists(batch_path):
                os.remove(batch_path)
        except:
            pass
        
        return UpdateResult(
            success=False,
            message=str(e),
            requires_restart=False
        )


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT UPDATE
# ══════════════════════════════════════════════════════════════════════════════

def update_component(
    download_url: str,
    target_path: str,
    engine_dir: str,
    progress_callback: Optional[ProgressCallback] = None,
    log_callback: Optional[LogCallback] = None,
    timeout: int = 60
) -> bool:
    """Download and update a component with self-healing."""
    
    def report_progress(label: str, pct: float) -> None:
        if progress_callback:
            progress_callback(label, pct)
    
    def log(message: str, level: str = "INFO") -> None:
        if log_callback:
            log_callback(message, level)
    
    filename = os.path.basename(target_path)
    temp_path = os.path.join(engine_dir, f"{os.path.splitext(filename)[0]}.new")
    old_path = os.path.join(engine_dir, f"{os.path.splitext(filename)[0]}.old")
    
    try:
        os.makedirs(engine_dir, exist_ok=True)
        
        log(f"📥 Downloading {filename}...", "INFO")
        report_progress("กำลังดาวน์โหลด...", 5.0)
        
        response = requests.get(download_url, stream=True, timeout=timeout)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = 5.0 + (downloaded / total_size) * 60.0
                    report_progress(f"ดาวน์โหลด... {downloaded // 1024} KB", pct)
        
        log(f"✓ Download complete: {downloaded} bytes", "INFO")
        
        report_progress("ตรวจสอบไฟล์...", 70.0)
        if os.path.getsize(temp_path) < 1000:
            raise UpdateError("ไฟล์เสียหาย")
        
        report_progress("เปลี่ยนไฟล์...", 80.0)
        
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except PermissionError:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", filename],
                        capture_output=True,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                    )
                    os.remove(target_path)
                except:
                    if os.path.exists(old_path):
                        try: os.remove(old_path)
                        except: pass
                    os.rename(target_path, old_path)
        
        report_progress("ติดตั้งไฟล์ใหม่...", 90.0)
        os.rename(temp_path, target_path)
        
        report_progress("✅ อัปเดตสำเร็จ!", 100.0)
        log(f"🎉 {filename} update complete!", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"❌ Error: {str(e)}", "ERROR")
        report_progress("❌ เกิดข้อผิดพลาด", 0)
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# SMART UPDATE FUNCTIONS  
# ══════════════════════════════════════════════════════════════════════════════

def update_ytdlp(
    engine_dir: str,
    progress_callback: Optional[ProgressCallback] = None,
    log_callback: Optional[LogCallback] = None,
    force: bool = False
) -> bool:
    """
    Smart update for yt-dlp - checks version before downloading.
    
    Args:
        engine_dir: Path to engine directory
        progress_callback: Progress update function
        log_callback: Log message function
        force: Force download even if up to date
    
    Returns:
        bool: True if successful (including "already up to date")
    """
    def log(msg: str, level: str = "INFO") -> None:
        if log_callback:
            log_callback(msg, level)
    
    def report(label: str, pct: float) -> None:
        if progress_callback:
            progress_callback(label, pct)
    
    ytdlp_path = os.path.join(engine_dir, "yt-dlp.exe")
    
    # Check version
    report("ตรวจสอบเวอร์ชัน...", 5.0)
    log("🔍 Checking yt-dlp version...", "INFO")
    
    file_exists = os.path.exists(ytdlp_path)
    local_ver = get_local_ytdlp_version(ytdlp_path)
    remote_info = get_remote_ytdlp_version()
    
    if local_ver:
        log(f"   • Local version: {local_ver}", "INFO")
    elif file_exists:
        log("   • ⚠️ File exists but version check failed", "WARNING")
    else:
        log("   • yt-dlp not found locally", "INFO")
    
    if remote_info:
        log(f"   • Latest version: {remote_info.version}", "INFO")
    else:
        log("   • ⚠️ Cannot check latest version (API Error)", "WARNING")
    
    # Decide if update is needed
    needs_update = False
    download_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    
    if not file_exists:
        needs_update = True
        log("   • Must download (file not found)", "INFO")
    elif force:
        needs_update = True
        log("   • Force update requested", "INFO")
    elif not remote_info and file_exists:
        log("   • ✅ Using current version (cannot check for updates)", "SUCCESS")
        report("✅ ใช้เวอร์ชันปัจจุบัน", 100.0)
        return True
    elif not local_ver and file_exists and not force:
        log("   • ✅ Skipping update (version check failed but file exists)", "SUCCESS")
        report("✅ ใช้ไฟล์ปัจจุบัน", 100.0)
        return True
    elif local_ver and remote_info:
        comparison = compare_versions(local_ver, remote_info.version)
        if comparison < 0:
            needs_update = True
            download_url = remote_info.download_url
            log(f"   • 🆕 New version found! {local_ver} → {remote_info.version}", "INFO")
        else:
            log("   • ✅ yt-dlp is up to date", "SUCCESS")
            report("✅ ล่าสุดแล้ว!", 100.0)
            return True
    
    if not needs_update:
        report("✅ ล่าสุดแล้ว!", 100.0)
        return True
    
    # Download and install
    return update_component(
        download_url=download_url,
        target_path=ytdlp_path,
        engine_dir=engine_dir,
        progress_callback=progress_callback,
        log_callback=log_callback,
        timeout=60
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHAINED UPDATE WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════

def run_full_update_routine(
    app_version: str,
    app_version_url: Optional[str],
    app_path: str,
    engine_dir: str,
    progress_callback: Optional[ProgressCallback] = None,
    log_callback: Optional[LogCallback] = None,
    skip_app_update: bool = False
) -> UpdateResult:
    """
    Chained Update Workflow
    
    Workflow:
    1. Check App Update (if enabled)
       - If found -> Download -> Swap & Restart -> STOP
    2. Check yt-dlp Update
       - If found -> Download & Replace
    3. Complete
    
    Args:
        app_version: Current app version
        app_version_url: URL to version.json (None = skip app update)
        app_path: Path to main.exe
        engine_dir: Engine directory path
        progress_callback: Progress update function
        log_callback: Log message function
        skip_app_update: Skip app update entirely
    
    Returns:
        UpdateResult with status and restart requirement
    """
    def log(msg: str, level: str = "INFO") -> None:
        if log_callback:
            log_callback(msg, level)
    
    def report(label: str, pct: float) -> None:
        if progress_callback:
            progress_callback(label, pct)
    
    log("🔄 Starting update check...", "INFO")
    
    # Check App Update
    if not skip_app_update and app_version_url:
        report("ตรวจสอบอัปเดตโปรแกรม...", 5.0)
        log("📱 Checking app version...", "INFO")
        
        app_update = check_app_update(app_version, app_version_url)
        
        if app_update:
            log(f"🆕 New version found: {app_update.version}", "INFO")
            log("   Preparing app update...", "INFO")
            
            result = perform_app_update(
                download_url=app_update.download_url,
                app_path=app_path,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            
            if result.success and result.requires_restart:
                log("📲 App will restart automatically...", "SUCCESS")
                return result
            elif not result.success:
                log("⚠️ App update failed - will try yt-dlp update instead", "WARNING")
        else:
            log("   • App is up to date ✓", "INFO")
    
    # Check yt-dlp Update
    report("ตรวจสอบ yt-dlp...", 40.0)
    
    success = update_ytdlp(
        engine_dir=engine_dir,
        progress_callback=progress_callback,
        log_callback=log_callback
    )
    
    if success:
        return UpdateResult(
            success=True,
            message="อัปเดตเสร็จสมบูรณ์",
            requires_restart=False
        )
    else:
        return UpdateResult(
            success=False,
            message="อัปเดต yt-dlp ล้มเหลว",
            requires_restart=False
        )
