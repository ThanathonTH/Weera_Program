"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    OPTIMIZED DOWNLOAD ENGINE v4.0                            ║
║              High-Performance yt-dlp Wrapper (Decoupled from GUI)            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🚀 Performance Optimizations:                                               ║
║     • --concurrent-fragments 4 (Parallel chunk downloads)                    ║
║     • --resize-buffer (Optimized disk I/O)                                   ║
║     • Optional aria2c external downloader support                            ║
║  🔌 Decoupled: NO GUI imports, uses callbacks for communication             ║
║  🧵 Thread-safe: Designed for background execution                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, List

from src.utils.paths import YTDLP_PATH, ENGINE_DIR


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    message: str
    output_file: Optional[str] = None
    error_code: Optional[int] = None


# Type aliases for callbacks
ProgressCallback = Callable[[str, Optional[float]], None]  # (label, percentage)
LogCallback = Callable[[str, str], None]  # (message, level)


class Downloader:
    """
    High-Performance YouTube to MP3 Downloader
    
    DECOUPLED DESIGN:
    - Does NOT import customtkinter or any GUI library
    - Communicates via callback functions
    - Designed to run in a background thread
    
    PERFORMANCE OPTIMIZATIONS:
    - Concurrent fragment downloads (4x parallel)
    - Resize buffer for optimized disk I/O
    - Optional aria2c external downloader
    
    Usage:
        def on_progress(label: str, pct: Optional[float]):
            print(f"{label}: {pct}%")
        
        def on_log(msg: str, level: str):
            print(f"[{level}] {msg}")
        
        downloader = Downloader(
            output_dir="/path/to/output",
            progress_callback=on_progress,
            log_callback=on_log
        )
        result = downloader.download("https://youtube.com/watch?v=...")
    """
    
    # High-precision regex to capture decimal progress
    PROGRESS_REGEX = re.compile(r'\[download\]\s+(\d+\.?\d*)%')
    
    def __init__(
        self,
        output_dir: str,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
        concurrent_fragments: int = 4,
        use_aria2c: bool = False,
    ):
        """
        Initialize the Downloader.
        
        Args:
            output_dir: Directory to save downloaded MP3 files
            progress_callback: Function to receive progress updates (label, percentage)
            log_callback: Function to receive log messages (message, level)
            concurrent_fragments: Number of parallel fragment downloads (default: 4)
            use_aria2c: Whether to use aria2c as external downloader (if installed)
        """
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.concurrent_fragments = concurrent_fragments
        self.use_aria2c = use_aria2c
        
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
    
    def _report_progress(self, label: str, percentage: Optional[float] = None) -> None:
        """Send progress update via callback."""
        if self.progress_callback:
            self.progress_callback(label, percentage)
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Send log message via callback."""
        if self.log_callback:
            self.log_callback(message, level)
    
    def _build_command(self, url: str) -> List[str]:
        """
        Build the yt-dlp command with optimized arguments.
        
        Args:
            url: YouTube URL to download
            
        Returns:
            List[str]: Command arguments for subprocess
        """
        output_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        
        cmd = [
            YTDLP_PATH,
            "--ffmpeg-location", ENGINE_DIR,
            
            # ═══════════════════════════════════════════════════════════════
            # 🎵 AUDIO SETTINGS
            # ═══════════════════════════════════════════════════════════════
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "320K",  # ✅ Maximum quality CBR
            
            # ═══════════════════════════════════════════════════════════════
            # 📊 METADATA & ARTWORK
            # ═══════════════════════════════════════════════════════════════
            "--add-metadata",           # ✅ Embed Artist, Title, Album
            "--embed-thumbnail",        # ✅ Embed Cover Art
            
            # ═══════════════════════════════════════════════════════════════
            # 🚀 PERFORMANCE OPTIMIZATIONS
            # ═══════════════════════════════════════════════════════════════
            "--concurrent-fragments", str(self.concurrent_fragments),  # ✅ Parallel downloads
            "--resize-buffer",          # ✅ Optimize disk I/O
            "--no-part",                # ✅ Don't use .part files
            
            # ═══════════════════════════════════════════════════════════════
            # 🔒 SAFETY & CONSISTENCY
            # ═══════════════════════════════════════════════════════════════
            "--restrict-filenames",     # ✅ Safe filenames
            "--no-playlist",            # ✅ Single video only
            "--no-mtime",               # ✅ Don't set file modification time
            
            # ═══════════════════════════════════════════════════════════════
            # 📤 OUTPUT SETTINGS
            # ═══════════════════════════════════════════════════════════════
            "--newline",                # ✅ Progress on new lines (for parsing)
            "--output", output_template,
            
            url
        ]
        
        # Optional: Use aria2c as external downloader for even faster downloads
        if self.use_aria2c and self._is_aria2c_available():
            cmd.insert(1, "--external-downloader")
            cmd.insert(2, "aria2c")
            cmd.insert(3, "--external-downloader-args")
            cmd.insert(4, "-x 16 -k 1M")  # 16 connections, 1MB chunks
            self._log("🚀 Using aria2c for accelerated download", "INFO")
        
        return cmd
    
    def _is_aria2c_available(self) -> bool:
        """Check if aria2c is installed and available."""
        try:
            result = subprocess.run(
                ["aria2c", "--version"],
                capture_output=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def download(self, url: str) -> DownloadResult:
        """
        Download a YouTube video as MP3.
        
        This method is BLOCKING and designed to run in a background thread.
        Progress updates are sent via the progress_callback.
        
        Args:
            url: YouTube URL to download
            
        Returns:
            DownloadResult: Result object with success status and message
        """
        self._cancelled = False
        
        # Validate
        if not url:
            return DownloadResult(False, "URL is empty")
        
        if not os.path.exists(YTDLP_PATH):
            return DownloadResult(False, "yt-dlp.exe not found")
        
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir, exist_ok=True)
            except Exception as e:
                return DownloadResult(False, f"Cannot create output directory: {e}")
        
        try:
            self._log(f"🔗 Starting download: {url[:60]}...", "INFO")
            self._report_progress("กำลังเริ่ม...", 0.0)
            
            cmd = self._build_command(url)
            
            # Start subprocess
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='ignore',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            
            output_file = None
            
            # Process output line by line
            for line in self._process.stdout:
                if self._cancelled:
                    self._process.terminate()
                    return DownloadResult(False, "Download cancelled")
                
                line = line.strip()
                if not line:
                    continue
                
                self._log(line, "INFO")
                
                # Parse progress percentage
                match = self.PROGRESS_REGEX.search(line)
                if match:
                    pct = float(match.group(1))
                    self._report_progress("กำลังดาวน์โหลด...", pct)
                
                # Detect conversion phase
                elif "[ExtractAudio]" in line:
                    self._report_progress("แปลงเป็น MP3...", None)
                
                # Detect completion
                elif "Deleting original" in line:
                    self._report_progress("เกือบเสร็จ...", 99.5)
                
                # Capture output filename
                elif "[download] Destination:" in line:
                    output_file = line.split("Destination:")[-1].strip()
            
            # Wait for process to complete
            return_code = self._process.wait()
            self._process = None
            
            if return_code == 0:
                self._report_progress("✅ สำเร็จ!", 100.0)
                self._log("🎉 Download completed successfully!", "SUCCESS")
                return DownloadResult(True, "Download completed", output_file)
            else:
                self._report_progress("❌ ล้มเหลว", 0)
                self._log(f"❌ Download failed with code: {return_code}", "ERROR")
                return DownloadResult(False, f"Failed with code {return_code}", error_code=return_code)
                
        except Exception as e:
            self._log(f"❌ Exception: {str(e)}", "ERROR")
            self._report_progress("❌ Error", 0)
            return DownloadResult(False, str(e))
        finally:
            self._process = None
    
    def cancel(self) -> None:
        """Cancel the current download."""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
                self._log("⏹️ Download cancelled", "WARNING")
            except Exception:
                pass
    
    @property
    def is_running(self) -> bool:
        """Check if a download is currently in progress."""
        return self._process is not None and self._process.poll() is None


# ══════════════════════════════════════════════════════════════════════════════
# 🧵 THREAD-SAFE DECORATOR
# ══════════════════════════════════════════════════════════════════════════════

import threading
from functools import wraps


def run_in_thread(func: Callable) -> Callable:
    """
    Decorator to run a function in a separate daemon thread.
    
    Usage:
        @run_in_thread
        def my_long_running_task():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(
            target=func,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        thread.start()
        return thread
    return wrapper
