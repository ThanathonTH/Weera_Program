"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        DIALOG COMPONENTS                                      ║
║              First-Run Path Selection & Dependency Setup                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📁 FirstRunPathDialog - Mandatory folder selection on first run             ║
║  🚀 DependencySetupDialog - yt-dlp & FFmpeg installation                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import io
import shutil
import zipfile
import requests
from typing import Callable, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox

from src.utils.paths import (
    ENGINE_DIR,
    YTDLP_PATH,
    FFMPEG_PATH,
    FFPROBE_PATH,
    YTDLP_DOWNLOAD_URL,
    FFMPEG_DOWNLOAD_URL,
)
from src.core.settings import SettingsManager
from src.core.downloader import run_in_thread


class FirstRunPathDialog(ctk.CTkToplevel):
    """
    Modal dialog for first-run folder selection.
    
    User MUST select a download folder before using the app.
    Closing the dialog without selecting will exit the application.
    """
    
    def __init__(
        self,
        parent: ctk.CTk,
        font_family: str,
        is_custom: bool,
        on_complete: Callable[[str], None]
    ):
        """
        Initialize the first-run path dialog.
        
        Args:
            parent: Parent window
            font_family: Font family name
            is_custom: Whether using custom font (affects sizes)
            on_complete: Callback function with selected path
        """
        super().__init__(parent)
        
        self.on_complete = on_complete
        self.selected_path: str | None = None
        self.font_family = font_family
        
        # Font configuration
        if is_custom:
            self.FONT_NORMAL = (font_family, 18)
            self.FONT_BOLD = (font_family, 18, "bold")
            self.FONT_HEADER = (font_family, 28, "bold")
            self.FONT_SMALL = (font_family, 14)
        else:
            self.FONT_NORMAL = (font_family, 14)
            self.FONT_BOLD = (font_family, 14, "bold")
            self.FONT_HEADER = (font_family, 22, "bold")
            self.FONT_SMALL = (font_family, 11)
        
        # Window configuration
        self.title("เลือกโฟลเดอร์ปลายทาง")
        self.geometry("550x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 550) // 2
        y = (self.winfo_screenheight() - 320) // 2
        self.geometry(f"550x320+{x}+{y}")
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the dialog UI."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=25)
        
        # Header
        header = ctk.CTkLabel(
            container,
            text="📁 ยินดีต้อนรับ!",
            font=self.FONT_HEADER
        )
        header.pack(pady=(0, 5))
        
        subtitle = ctk.CTkLabel(
            container,
            text="กรุณาเลือกโฟลเดอร์สำหรับเก็บไฟล์ MP3",
            font=self.FONT_NORMAL,
            text_color="#AAAAAA"
        )
        subtitle.pack(pady=(0, 20))
        
        # Path selection frame
        path_frame = ctk.CTkFrame(container)
        path_frame.pack(fill="x", pady=10)
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="(ยังไม่ได้เลือก)",
            height=45,
            font=self.FONT_NORMAL,
            state="readonly",
            fg_color="#1a1a2e"
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=15)
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="📂 เลือก",
            command=self._browse,
            width=100,
            height=45,
            font=self.FONT_BOLD
        )
        browse_btn.pack(side="right", padx=(0, 15), pady=15)
        
        # Confirm button
        self.confirm_btn = ctk.CTkButton(
            container,
            text="✓ ยืนยันและเริ่มใช้งาน",
            command=self._confirm,
            height=50,
            font=self.FONT_BOLD,
            fg_color="#22C55E",
            hover_color="#16A34A",
            state="disabled"
        )
        self.confirm_btn.pack(pady=(20, 10), fill="x")
        
        # Note
        note = ctk.CTkLabel(
            container,
            text="💡 คุณสามารถเปลี่ยนโฟลเดอร์ได้ภายหลัง",
            font=self.FONT_SMALL,
            text_color="#666666"
        )
        note.pack(pady=(5, 0))
    
    def _browse(self) -> None:
        """Open folder selection dialog."""
        default = os.path.join(os.path.expanduser("~"), "Music")
        folder = filedialog.askdirectory(
            title="เลือกโฟลเดอร์ปลายทาง",
            initialdir=default
        )
        if folder:
            self.selected_path = folder
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.path_entry.configure(state="readonly")
            self.confirm_btn.configure(state="normal")
    
    def _confirm(self) -> None:
        """Confirm selection and save to settings."""
        if self.selected_path:
            SettingsManager.save_path(self.selected_path)
            self.destroy()
            self.on_complete(self.selected_path)
    
    def _on_cancel(self) -> None:
        """Handle dialog close attempt."""
        if messagebox.askyesno(
            "ปิดโปรแกรม?",
            "ต้องเลือกโฟลเดอร์ก่อน\nต้องการปิดโปรแกรมหรือไม่?"
        ):
            self.destroy()
            os._exit(0)


class DependencySetupDialog(ctk.CTkToplevel):
    """
    Modal dialog for installing dependencies (yt-dlp & FFmpeg).
    
    Automatically downloads and installs required binaries.
    User cannot cancel during installation.
    """
    
    def __init__(
        self,
        parent: ctk.CTk,
        font_family: str,
        is_custom: bool,
        on_complete: Callable[[bool], None]
    ):
        """
        Initialize the dependency setup dialog.
        
        Args:
            parent: Parent window
            font_family: Font family name
            is_custom: Whether using custom font
            on_complete: Callback with success status
        """
        super().__init__(parent)
        
        self.on_complete = on_complete
        self.cancelled = False
        
        # Font configuration
        if is_custom:
            self.FONT_NORMAL = (font_family, 18)
            self.FONT_HEADER = (font_family, 28, "bold")
            self.FONT_SUBTITLE = (font_family, 15)
            self.FONT_SMALL = (font_family, 14)
        else:
            self.FONT_NORMAL = (font_family, 14)
            self.FONT_HEADER = (font_family, 22, "bold")
            self.FONT_SUBTITLE = (font_family, 12)
            self.FONT_SMALL = (font_family, 11)
        
        # Window configuration
        self.title("กำลังติดตั้งระบบ...")
        self.geometry("520x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 280) // 2
        self.geometry(f"520x280+{x}+{y}")
        
        self.protocol("WM_DELETE_WINDOW", self._on_force_close)
        self._build_ui()
        self.after(100, self._start_setup)
    
    def _build_ui(self) -> None:
        """Build the dialog UI."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=30)
        
        header = ctk.CTkLabel(
            container,
            text="🚀 กำลังเตรียมระบบ",
            font=self.FONT_HEADER
        )
        header.pack(pady=(0, 10))
        
        subtitle = ctk.CTkLabel(
            container,
            text="กรุณารอสักครู่ (ประมาณ 1-2 นาที)",
            font=self.FONT_SUBTITLE,
            text_color="#888888"
        )
        subtitle.pack(pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(
            container,
            text="เริ่มต้น...",
            font=self.FONT_NORMAL
        )
        self.status_label.pack(pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(container, width=450, height=16)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        self.detail_label = ctk.CTkLabel(
            container,
            text="",
            font=self.FONT_SMALL,
            text_color="#777777"
        )
        self.detail_label.pack(pady=10)
    
    def _update_status(
        self,
        status: str,
        detail: str = "",
        progress: float | None = None
    ) -> None:
        """Update status display (thread-safe)."""
        self.after(0, lambda: self.status_label.configure(text=status))
        self.after(0, lambda: self.detail_label.configure(text=detail))
        if progress is not None:
            self.after(0, lambda: self.progress_bar.set(progress))
    
    def _on_force_close(self) -> None:
        """Handle force close attempt."""
        if messagebox.askyesno(
            "ปิดโปรแกรม?",
            "การติดตั้งยังไม่เสร็จ\nต้องการปิดหรือไม่?"
        ):
            self.cancelled = True
            self.destroy()
            os._exit(0)
    
    @run_in_thread
    def _start_setup(self) -> None:
        """Start the setup process in background thread."""
        try:
            os.makedirs(ENGINE_DIR, exist_ok=True)
            
            # Download yt-dlp
            if not os.path.exists(YTDLP_PATH):
                self._update_status("📥 ดาวน์โหลด yt-dlp.exe...", "จาก GitHub", 0.05)
                if not self._download_file(YTDLP_DOWNLOAD_URL, YTDLP_PATH, "yt-dlp"):
                    return
            self._update_status("✅ yt-dlp.exe พร้อม", "", 0.4)
            
            if self.cancelled:
                return
            
            # Download FFmpeg
            if not os.path.exists(FFMPEG_PATH):
                self._update_status("📥 ดาวน์โหลด FFmpeg...", "~80MB", 0.45)
                if not self._download_and_extract_ffmpeg():
                    return
            self._update_status("✅ ffmpeg.exe พร้อม", "", 0.95)
            
            if self.cancelled:
                return
            
            self._update_status("🎉 ติดตั้งสำเร็จ!", "พร้อมใช้งาน", 1.0)
            self.after(1200, lambda: self._finish(True))
            
        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", "", 0)
            self.after(4000, lambda: self._finish(False))
    
    def _download_file(self, url: str, dest: str, name: str) -> bool:
        """Download a file with progress updates."""
        try:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    if self.cancelled:
                        return False
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        mb = downloaded / (1024*1024)
                        self._update_status(f"📥 {name}...", f"{mb:.1f} MB")
            return True
            
        except Exception as e:
            self._update_status(f"❌ ล้มเหลว: {e}", "", 0)
            return False
    
    def _download_and_extract_ffmpeg(self) -> bool:
        """Download and extract FFmpeg from ZIP."""
        try:
            resp = requests.get(FFMPEG_DOWNLOAD_URL, stream=True, timeout=180)
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            chunks = []
            
            for chunk in resp.iter_content(65536):
                if self.cancelled:
                    return False
                chunks.append(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total
                    self._update_status(
                        "📥 FFmpeg...",
                        f"{downloaded//(1024*1024)} MB",
                        0.45 + (pct * 0.4)
                    )
            
            self._update_status("📦 แตกไฟล์...", "", 0.88)
            zip_data = b''.join(chunks)
            
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                for name in zf.namelist():
                    nl = name.lower()
                    if nl.endswith('ffmpeg.exe'):
                        with zf.open(name) as s, open(FFMPEG_PATH, 'wb') as d:
                            shutil.copyfileobj(s, d)
                    elif nl.endswith('ffprobe.exe'):
                        with zf.open(name) as s, open(FFPROBE_PATH, 'wb') as d:
                            shutil.copyfileobj(s, d)
            
            return os.path.exists(FFMPEG_PATH)
            
        except Exception as e:
            self._update_status(f"❌ FFmpeg ล้มเหลว: {e}", "", 0)
            return False
    
    def _finish(self, success: bool) -> None:
        """Complete the setup process."""
        self.destroy()
        self.on_complete(success)
