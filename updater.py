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
from typing import Callable, Optional, Dict, Any, Tuple
from dataclasses import dataclass


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
    
    def __bool__(self):
        return bool(self.version and self.download_url)


@dataclass
class UpdateResult:
    """Result of an update operation"""
    success: bool
    message: str
    requires_restart: bool = False
    new_version: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# VERSION COMPARISON UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def compare_versions(local: str, remote: str) -> int:
    """
    เปรียบเทียบเวอร์ชัน
    
    Args:
        local: เวอร์ชันในเครื่อง
        remote: เวอร์ชันจาก server
    
    Returns:
        -1: local < remote (ต้องอัปเดต)
         0: local == remote (ล่าสุดแล้ว)
         1: local > remote (ในเครื่องใหม่กว่า?!)
    """
    def normalize(v: str) -> list:
        """แปลงเป็น list ของตัวเลขเพื่อเปรียบเทียบ"""
        # รองรับทั้ง "2023.11.16" และ "1.0.0" format
        v = v.strip().lstrip('v').lstrip('V')
        parts = []
        for part in v.replace('-', '.').replace('_', '.').split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                # ถ้าเป็น string เช่น "beta" ให้ใช้ 0
                parts.append(0)
        return parts
    
    try:
        local_parts = normalize(local)
        remote_parts = normalize(remote)
        
        # Pad ให้ยาวเท่ากัน
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
        # ถ้าเปรียบเทียบไม่ได้ ให้ใช้ string comparison
        if local == remote:
            return 0
        return -1 if local < remote else 1


# ══════════════════════════════════════════════════════════════════════════════
# YT-DLP VERSION CHECKING
# ══════════════════════════════════════════════════════════════════════════════

def get_local_ytdlp_version(ytdlp_path: str) -> Optional[str]:
    """
    ดึงเวอร์ชันของ yt-dlp จาก binary ในเครื่อง
    
    Args:
        ytdlp_path: Path ไปยัง yt-dlp.exe
    
    Returns:
        str: เวอร์ชัน (e.g., "2023.11.16") หรือ None ถ้าไม่พบ/เช็คไม่ได้
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
            errors='ignore',  # ✅ Ignore encoding errors for non-English systems
            timeout=15,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        )
        
        # Debug: show raw output
        print(f"[DEBUG] yt-dlp --version stdout: '{result.stdout.strip()}'")
        
        if result.returncode == 0:
            version = result.stdout.strip()
            if version:
                return version
            else:
                print(f"[DEBUG] yt-dlp returned empty version")
                return None
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
    ดึงข้อมูลเวอร์ชันล่าสุดของ yt-dlp จาก GitHub API
    
    Returns:
        VersionInfo หรือ None ถ้าเช็คไม่ได้
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
        
        # หา download URL สำหรับ Windows exe
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
            release_notes=data.get("body", "")[:500]  # Truncate
        )
        
    except requests.RequestException:
        return None
    except Exception:
        return None


def check_ytdlp_update(engine_dir: str) -> Tuple[bool, str, str]:
    """
    ตรวจสอบว่า yt-dlp ต้องอัปเดตหรือไม่
    
    Args:
        engine_dir: โฟลเดอร์ engine
    
    Returns:
        (needs_update: bool, local_version: str, remote_version: str)
    """
    ytdlp_path = os.path.join(engine_dir, "yt-dlp.exe")
    
    local_ver = get_local_ytdlp_version(ytdlp_path) or "ไม่พบ"
    remote_info = get_remote_ytdlp_version()
    
    if remote_info is None:
        # API fail - ไม่สามารถเช็คได้
        return (False, local_ver, "ไม่สามารถเช็คได้")
    
    remote_ver = remote_info.version
    
    if local_ver == "ไม่พบ":
        # ยังไม่มี - ต้องโหลด
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
    ตรวจสอบว่าแอปพลิเคชันมีเวอร์ชันใหม่หรือไม่
    
    Args:
        current_version: เวอร์ชันปัจจุบันของแอป (e.g., "3.1.0")
        version_url: URL ไปยัง version.json
    
    Returns:
        VersionInfo ถ้ามีอัปเดต, None ถ้าล่าสุดแล้ว
    
    Expected version.json format:
    {
        "version": "3.2.0",
        "download_url": "https://example.com/app.exe",
        "release_notes": "Bug fixes..."
    }
    """
    try:
        response = requests.get(version_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        remote_version = data.get("version", "")
        if not remote_version:
            return None
        
        comparison = compare_versions(current_version, remote_version)
        
        if comparison < 0:  # Remote is newer
            return VersionInfo(
                version=remote_version,
                download_url=data.get("download_url", ""),
                release_notes=data.get("release_notes", "")
            )
        
        return None  # Up to date
        
    except Exception:
        return None


def perform_app_update(
    download_url: str,
    app_path: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    log_callback: Optional[Callable[[str, str], None]] = None
) -> UpdateResult:
    """
    อัปเดตแอปพลิเคชันโดยใช้ Swap & Restart Strategy
    
    Windows ไม่อนุญาตให้ลบ/เขียนทับไฟล์ .exe ที่กำลังทำงาน
    ดังนั้นต้องใช้ batch script ที่จะ:
    1. รอให้แอปปิด
    2. เปลี่ยนชื่อ/ลบไฟล์เก่า
    3. ย้ายไฟล์ใหม่มาแทน
    4. เปิดแอปใหม่
    5. ลบ batch script ตัวเอง
    
    Args:
        download_url: URL สำหรับดาวน์โหลด .exe ใหม่
        app_path: Path ของ .exe ปัจจุบัน
        progress_callback: func(label, pct)
        log_callback: func(message, level)
    
    Returns:
        UpdateResult ที่มี requires_restart=True ถ้าสำเร็จ
    """
    def report_progress(label: str, pct: float):
        if progress_callback:
            progress_callback(label, pct)
    
    def log(msg: str, level: str = "INFO"):
        if log_callback:
            log_callback(msg, level)
    
    app_dir = os.path.dirname(app_path)
    app_name = os.path.basename(app_path)
    new_app_path = os.path.join(app_dir, "app.new.exe")
    batch_path = os.path.join(app_dir, "update.bat")
    
    try:
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: ดาวน์โหลดไฟล์ใหม่
        # ═══════════════════════════════════════════════════════════════════
        log("📥 กำลังดาวน์โหลดเวอร์ชันใหม่...", "INFO")
        report_progress("กำลังดาวน์โหลด...", 10.0)
        
        response = requests.get(download_url, stream=True, timeout=120)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(new_app_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = 10.0 + (downloaded / total_size) * 60.0
                    report_progress(f"ดาวน์โหลด... {downloaded // (1024*1024)} MB", pct)
        
        log(f"✓ ดาวน์โหลดเสร็จ: {downloaded} bytes", "INFO")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: ตรวจสอบไฟล์
        # ═══════════════════════════════════════════════════════════════════
        report_progress("ตรวจสอบไฟล์...", 75.0)
        
        if os.path.getsize(new_app_path) < 10000:
            raise UpdateError("ไฟล์ที่ดาวน์โหลดเสียหาย")
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: สร้าง Batch Script สำหรับ Swap
        # ═══════════════════════════════════════════════════════════════════
        report_progress("เตรียมการติดตั้ง...", 85.0)
        log("📝 สร้าง update script...", "INFO")
        
        # Batch script content
        batch_content = f'''@echo off
chcp 65001 >nul
echo กำลังอัปเดต... กรุณารอสักครู่
echo.

:: รอให้แอปเดิมปิด (3 วินาที)
timeout /t 3 /nobreak >nul

:: พยายามลบไฟล์เก่า
echo ลบไฟล์เก่า...
del /f /q "{app_path}" 2>nul

:: ถ้าลบไม่ได้ ลอง taskkill
if exist "{app_path}" (
    echo พยายามปิดโปรแกรม...
    taskkill /f /im "{app_name}" 2>nul
    timeout /t 2 /nobreak >nul
    del /f /q "{app_path}" 2>nul
)

:: ย้ายไฟล์ใหม่มาแทน
echo ติดตั้งเวอร์ชันใหม่...
move /y "{new_app_path}" "{app_path}"

:: ตรวจสอบว่าย้ายสำเร็จ
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

:: ลบ batch script ตัวเอง
(goto) 2>nul & del "%~f0"
'''
        
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: Execute Batch Script
        # ═══════════════════════════════════════════════════════════════════
        report_progress("เริ่มการติดตั้ง...", 95.0)
        log("🚀 เริ่ม update script - โปรแกรมจะปิดและเปิดใหม่อัตโนมัติ", "INFO")
        
        # Start batch script (detached from this process)
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
        log(f"❌ อัปเดตล้มเหลว: {str(e)}", "ERROR")
        report_progress("❌ ล้มเหลว", 0)
        
        # Cleanup
        try:
            if os.path.exists(new_app_path):
                os.remove(new_app_path)
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
# COMPONENT UPDATE (Original Logic - Now with Verification)
# ══════════════════════════════════════════════════════════════════════════════

def update_component(
    download_url: str,
    target_path: str,
    engine_dir: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    log_callback: Optional[Callable[[str, str], None]] = None,
    timeout: int = 60
) -> bool:
    """ดาวน์โหลดและอัปเดต Component แบบ Self-Healing (Original)"""
    
    def report_progress(label: str, pct: float):
        if progress_callback:
            progress_callback(label, pct)
    
    def log(message: str, level: str = "INFO"):
        if log_callback:
            log_callback(message, level)
    
    filename = os.path.basename(target_path)
    temp_path = os.path.join(engine_dir, f"{os.path.splitext(filename)[0]}.new")
    old_path = os.path.join(engine_dir, f"{os.path.splitext(filename)[0]}.old")
    
    try:
        os.makedirs(engine_dir, exist_ok=True)
        
        log(f"📥 กำลังดาวน์โหลด {filename}...", "INFO")
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
        
        log(f"✓ ดาวน์โหลดเสร็จ: {downloaded} bytes", "INFO")
        
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
        log(f"🎉 อัปเดต {filename} เสร็จสมบูรณ์!", "SUCCESS")
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
    progress_callback: Optional[Callable[[str, float], None]] = None,
    log_callback: Optional[Callable[[str, str], None]] = None,
    force: bool = False
) -> bool:
    """
    Smart Update สำหรับ yt-dlp - เช็คเวอร์ชันก่อนดาวน์โหลด
    
    Args:
        engine_dir: โฟลเดอร์ engine
        progress_callback: func(label, pct)
        log_callback: func(message, level)
        force: บังคับดาวน์โหลดแม้ว่าจะล่าสุดแล้ว
    
    Returns:
        bool: True ถ้าสำเร็จ (รวมถึงกรณี "ล่าสุดแล้ว")
    """
    def log(msg: str, level: str = "INFO"):
        if log_callback:
            log_callback(msg, level)
    
    def report(label: str, pct: float):
        if progress_callback:
            progress_callback(label, pct)
    
    ytdlp_path = os.path.join(engine_dir, "yt-dlp.exe")
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: ตรวจสอบเวอร์ชัน
    # ═══════════════════════════════════════════════════════════════════════
    report("ตรวจสอบเวอร์ชัน...", 5.0)
    log("🔍 กำลังตรวจสอบเวอร์ชัน yt-dlp...", "INFO")
    
    # Check file existence FIRST (separate from version check)
    file_exists = os.path.exists(ytdlp_path)
    local_ver = get_local_ytdlp_version(ytdlp_path)
    remote_info = get_remote_ytdlp_version()
    
    # Log local status
    if local_ver:
        log(f"   • เวอร์ชันในเครื่อง: {local_ver}", "INFO")
    elif file_exists:
        log("   • ⚠️ ไฟล์มีอยู่แต่เช็คเวอร์ชันไม่ได้ (สมมติว่าใช้งานได้)", "WARNING")
    else:
        log("   • ยังไม่มี yt-dlp ในเครื่อง", "INFO")
    
    # Log remote status
    if remote_info:
        log(f"   • เวอร์ชันล่าสุด: {remote_info.version}", "INFO")
    else:
        log("   • ⚠️ ไม่สามารถเช็คเวอร์ชันล่าสุดได้ (API Error/Rate Limit)", "WARNING")
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: ตัดสินใจว่าต้อง update หรือไม่
    # ═══════════════════════════════════════════════════════════════════════
    needs_update = False
    download_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    
    # Case 1: No file at all -> Must download
    if not file_exists:
        needs_update = True
        log("   • ต้องดาวน์โหลด (ไม่มีไฟล์)", "INFO")
    
    # Case 2: Force update requested
    elif force:
        needs_update = True
        log("   • บังคับอัปเดตตามที่ร้องขอ", "INFO")
    
    # Case 3: API failed but file exists -> KEEP existing (NO blind update)
    elif not remote_info and file_exists:
        log("   • ✅ ใช้เวอร์ชันปัจจุบัน (ไม่สามารถเช็ค update ได้)", "SUCCESS")
        report("✅ ใช้เวอร์ชันปัจจุบัน", 100.0)
        return True
    
    # Case 4: Version check failed but file exists -> Assume valid (NO blind update)
    elif not local_ver and file_exists and not force:
        log("   • ✅ ข้าม update (เช็คเวอร์ชันไม่ได้แต่ไฟล์มีอยู่)", "SUCCESS")
        report("✅ ใช้ไฟล์ปัจจุบัน", 100.0)
        return True
    
    # Case 5: Have both versions -> Compare
    elif local_ver and remote_info:
        comparison = compare_versions(local_ver, remote_info.version)
        if comparison < 0:
            needs_update = True
            download_url = remote_info.download_url
            log(f"   • 🆕 พบเวอร์ชันใหม่! {local_ver} → {remote_info.version}", "INFO")
        else:
            log("   • ✅ yt-dlp เป็นเวอร์ชันล่าสุดแล้ว", "SUCCESS")
            report("✅ ล่าสุดแล้ว!", 100.0)
            return True
    
    if not needs_update:
        report("✅ ล่าสุดแล้ว!", 100.0)
        return True
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: ดาวน์โหลดและติดตั้ง
    # ═══════════════════════════════════════════════════════════════════════
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
    progress_callback: Optional[Callable[[str, float], None]] = None,
    log_callback: Optional[Callable[[str, str], None]] = None,
    skip_app_update: bool = False
) -> UpdateResult:
    """
    🔗 Chained Update Workflow
    
    ลำดับการทำงาน:
    1. ตรวจสอบ App Update (ถ้าเปิดใช้)
       - ถ้ามี -> Download -> Swap & Restart -> STOP
    2. ตรวจสอบ yt-dlp Update
       - ถ้ามี -> Download & Replace
    3. เสร็จสิ้น
    
    Args:
        app_version: เวอร์ชันปัจจุบันของแอป
        app_version_url: URL ไปยัง version.json (None = ข้าม app update)
        app_path: Path ของ main.exe
        engine_dir: โฟลเดอร์ engine
        progress_callback: func(label, pct)
        log_callback: func(message, level)
        skip_app_update: ข้าม app update ไปเลย
    
    Returns:
        UpdateResult ที่บอกสถานะและว่าต้อง restart หรือไม่
    """
    def log(msg: str, level: str = "INFO"):
        if log_callback:
            log_callback(msg, level)
    
    def report(label: str, pct: float):
        if progress_callback:
            progress_callback(label, pct)
    
    log("🔄 เริ่มตรวจสอบการอัปเดต...", "INFO")
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: Check App Update
    # ═══════════════════════════════════════════════════════════════════════
    if not skip_app_update and app_version_url:
        report("ตรวจสอบอัปเดตโปรแกรม...", 5.0)
        log("📱 ตรวจสอบเวอร์ชันโปรแกรม...", "INFO")
        
        app_update = check_app_update(app_version, app_version_url)
        
        if app_update:
            log(f"🆕 พบเวอร์ชันใหม่: {app_update.version}", "INFO")
            log(f"   กำลังเตรียมอัปเดตโปรแกรม...", "INFO")
            
            result = perform_app_update(
                download_url=app_update.download_url,
                app_path=app_path,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            
            if result.success and result.requires_restart:
                log("📲 โปรแกรมจะรีสตาร์ทอัตโนมัติ...", "SUCCESS")
                return result
            elif not result.success:
                log("⚠️ อัปเดตโปรแกรมล้มเหลว - จะลองอัปเดต yt-dlp แทน", "WARNING")
        else:
            log("   • โปรแกรมเป็นเวอร์ชันล่าสุดแล้ว ✓", "INFO")
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: Check yt-dlp Update
    # ═══════════════════════════════════════════════════════════════════════
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
