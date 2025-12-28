"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     INFINITY MP3 DOWNLOADER v3.1                             ║
║                    Decoupled Wrapper Architecture                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🐛 FIX: Font loading after root window creation                             ║
║  � FIX: Checkbox state persistence sync with settings.json                  ║
║  🎯 High-Precision Progress (Floating Point)                                ║
║  📁 World-Class Path Management with Intelligent State Sync                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import customtkinter as ctk
import threading
import subprocess
import requests
import zipfile
import os
import shutil
import re
import io
import sys
import json
from tkinter import filedialog, messagebox
from typing import Optional, Callable
from datetime import datetime

# Import decoupled updater module (Chained Update System)
from updater import run_full_update_routine

# ══════════════════════════════════════════════════════════════════════════════
# ⚙️ PATH CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.join(BASE_DIR, "engine")
FONT_DIR = os.path.join(BASE_DIR, "font")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

YTDLP_PATH = os.path.join(ENGINE_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(ENGINE_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(ENGINE_DIR, "ffprobe.exe")

# Download URLs
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# 🔄 APP VERSION & UPDATE CONFIGURATION
APP_VERSION = "3.1.0"
UPDATE_JSON_URL = "https://raw.githubusercontent.com/ThanathonTH/Weera_Program/main/version.json"

# UI Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ══════════════════════════════════════════════════════════════════════════════
# 💾 SETTINGS MANAGER (Persistent Configuration)
# ══════════════════════════════════════════════════════════════════════════════

class SettingsManager:
    """จัดการการบันทึกและโหลดการตั้งค่าแบบ Persistent"""
    
    _cache: dict = None  # Cache เพื่อลด I/O
    
    DEFAULT_SETTINGS = {
        "download_path": "",
        "first_run_complete": False,
    }
    
    @classmethod
    def load(cls) -> dict:
        """โหลดการตั้งค่าจากไฟล์ (ใช้ cache)"""
        if cls._cache is not None:
            return cls._cache
        
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    cls._cache = {**cls.DEFAULT_SETTINGS, **settings}
                    print(f"✓ โหลดการตั้งค่าจาก: {SETTINGS_FILE}")
                    return cls._cache
        except Exception as e:
            print(f"⚠️ ไม่สามารถโหลดการตั้งค่า: {e}")
        
        cls._cache = cls.DEFAULT_SETTINGS.copy()
        return cls._cache
    
    @classmethod
    def save(cls, settings: dict) -> bool:
        """บันทึกการตั้งค่าลงไฟล์"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            cls._cache = settings  # Update cache
            print(f"✓ บันทึกการตั้งค่าไปที่: {SETTINGS_FILE}")
            return True
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกการตั้งค่า: {e}")
            return False
    
    @classmethod
    def clear_path(cls) -> bool:
        """ลบ download_path ออกจาก settings (ทำให้เป็น session-only)"""
        settings = cls.load()
        settings["download_path"] = ""
        return cls.save(settings)
    
    @classmethod
    def save_path(cls, path: str) -> bool:
        """บันทึก download_path"""
        settings = cls.load()
        settings["download_path"] = path
        settings["first_run_complete"] = True
        return cls.save(settings)
    
    @classmethod
    def has_saved_path(cls) -> bool:
        """ตรวจสอบว่ามี path บันทึกไว้หรือไม่"""
        settings = cls.load()
        return bool(settings.get("download_path", ""))
    
    @classmethod
    def is_first_run(cls) -> bool:
        """ตรวจสอบว่าเป็นการเปิดครั้งแรกหรือไม่"""
        settings = cls.load()
        return not settings.get("first_run_complete", False)


# ══════════════════════════════════════════════════════════════════════════════
# 🔤 FONT LOADER (Deferred - โหลดหลังสร้าง Root Window)
# ══════════════════════════════════════════════════════════════════════════════

class FontLoader:
    """
    ระบบโหลดฟอนต์แบบ Deferred
    
    CRITICAL FIX: ต้องโหลดหลังจาก Root Window ถูกสร้างแล้ว
    ไม่งั้นจะ error "Too early to use font: no default root window"
    """
    
    SAFE_THAI_FONTS = ["Tahoma", "Microsoft Sans Serif", "Arial"]
    _loaded = False
    _font_family = "Tahoma"
    _is_custom = False
    
    @classmethod
    def load(cls) -> tuple:
        """
        โหลดฟอนต์ - ต้องเรียกหลัง root window ถูกสร้าง
        
        Returns:
            tuple: (font_family, is_custom_font)
        """
        if cls._loaded:
            return (cls._font_family, cls._is_custom)
        
        print("\n🔤 === Font Health Check ===")
        
        # Step 1: ลองโหลด Custom Font
        if os.path.exists(FONT_DIR):
            font_files = [
                ("THSarabunNew.ttf", "Regular"),
                ("THSarabunNew Bold.ttf", "Bold"),
            ]
            
            loaded = 0
            for filename, variant in font_files:
                filepath = os.path.join(FONT_DIR, filename)
                if os.path.exists(filepath):
                    try:
                        ctk.FontManager.load_font(filepath)
                        loaded += 1
                        print(f"✓ โหลด {variant}: {filename}")
                    except Exception as e:
                        print(f"⚠️ โหลดไม่ได้ {filename}: {e}")
            
            if loaded > 0:
                # ทดสอบว่าฟอนต์ใช้ได้จริง
                try:
                    test = ctk.CTkFont(family="TH Sarabun New", size=14)
                    if test:
                        cls._font_family = "TH Sarabun New"
                        cls._is_custom = True
                        cls._loaded = True
                        print("✅ ใช้ฟอนต์: TH Sarabun New")
                        print("=" * 35 + "\n")
                        return (cls._font_family, cls._is_custom)
                except Exception as e:
                    print(f"⚠️ ฟอนต์โหลดแล้วแต่ใช้ไม่ได้: {e}")
        
        # Step 2: ใช้ Fallback
        for font_name in cls.SAFE_THAI_FONTS:
            try:
                test = ctk.CTkFont(family=font_name, size=14)
                if test:
                    cls._font_family = font_name
                    cls._is_custom = False
                    cls._loaded = True
                    print(f"🔄 ใช้ฟอนต์ Fallback: {font_name}")
                    print("=" * 35 + "\n")
                    return (cls._font_family, cls._is_custom)
            except:
                continue
        
        cls._loaded = True
        print("⚠️ ใช้ฟอนต์ Default: Tahoma")
        print("=" * 35 + "\n")
        return ("Tahoma", False)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: THREAD-SAFE DECORATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_in_thread(func: Callable) -> Callable:
    """Decorator สำหรับรันฟังก์ชันใน Thread แยก"""
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# 📁 FIRST-RUN PATH SELECTION DIALOG (Mandatory - No Cancel)
# ══════════════════════════════════════════════════════════════════════════════

class FirstRunPathDialog(ctk.CTkToplevel):
    """Modal Dialog บังคับเลือก Download Path - ปิด = ปิดโปรแกรม"""
    
    def __init__(self, parent, font_family: str, is_custom: bool, on_complete: Callable):
        super().__init__(parent)
        self.on_complete = on_complete
        self.selected_path = None
        
        # Font settings
        self.font_family = font_family
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
        
        # Window config
        self.title("เลือกโฟลเดอร์ปลายทาง")
        self.geometry("550x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 550) // 2
        y = (self.winfo_screenheight() - 320) // 2
        self.geometry(f"550x320+{x}+{y}")
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._build_ui()
    
    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=25)
        
        # Header
        header = ctk.CTkLabel(container, text="📁 ยินดีต้อนรับ!", font=self.FONT_HEADER)
        header.pack(pady=(0, 5))
        
        subtitle = ctk.CTkLabel(
            container,
            text="กรุณาเลือกโฟลเดอร์สำหรับเก็บไฟล์ MP3",
            font=self.FONT_NORMAL,
            text_color="#AAAAAA"
        )
        subtitle.pack(pady=(0, 20))
        
        # Path Frame
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
            path_frame, text="📂 เลือก", command=self._browse,
            width=100, height=45, font=self.FONT_BOLD
        )
        browse_btn.pack(side="right", padx=(0, 15), pady=15)
        
        # Confirm Button
        self.confirm_btn = ctk.CTkButton(
            container, text="✓ ยืนยันและเริ่มใช้งาน", command=self._confirm,
            height=50, font=self.FONT_BOLD,
            fg_color="#22C55E", hover_color="#16A34A", state="disabled"
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
    
    def _browse(self):
        default = os.path.join(os.path.expanduser("~"), "Music")
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง", initialdir=default)
        if folder:
            self.selected_path = folder
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.path_entry.configure(state="readonly")
            self.confirm_btn.configure(state="normal")
    
    def _confirm(self):
        if self.selected_path:
            # บันทึกทันที (first run)
            SettingsManager.save_path(self.selected_path)
            self.destroy()
            self.on_complete(self.selected_path)
    
    def _on_cancel(self):
        if messagebox.askyesno("ปิดโปรแกรม?", "ต้องเลือกโฟลเดอร์ก่อน\nต้องการปิดโปรแกรมหรือไม่?"):
            self.destroy()
            os._exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# 🚫 DEPENDENCY SETUP DIALOG (No Cancel)
# ══════════════════════════════════════════════════════════════════════════════

class DependencySetupDialog(ctk.CTkToplevel):
    """ติดตั้ง Dependencies - บังคับรอ"""
    
    def __init__(self, parent, font_family: str, is_custom: bool, on_complete: Callable):
        super().__init__(parent)
        self.on_complete = on_complete
        self.cancelled = False
        
        # Font settings
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
        
        self.title("กำลังติดตั้งระบบ...")
        self.geometry("520x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 280) // 2
        self.geometry(f"520x280+{x}+{y}")
        
        self.protocol("WM_DELETE_WINDOW", self._on_force_close)
        self._build_ui()
        self.after(100, self._start_setup)
    
    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=30)
        
        header = ctk.CTkLabel(container, text="🚀 กำลังเตรียมระบบ", font=self.FONT_HEADER)
        header.pack(pady=(0, 10))
        
        subtitle = ctk.CTkLabel(
            container, text="กรุณารอสักครู่ (ประมาณ 1-2 นาที)",
            font=self.FONT_SUBTITLE, text_color="#888888"
        )
        subtitle.pack(pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(container, text="เริ่มต้น...", font=self.FONT_NORMAL)
        self.status_label.pack(pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(container, width=450, height=16)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        self.detail_label = ctk.CTkLabel(
            container, text="", font=self.FONT_SMALL, text_color="#777777"
        )
        self.detail_label.pack(pady=10)
    
    def _update_status(self, status: str, detail: str = "", progress: float = None):
        self.after(0, lambda: self.status_label.configure(text=status))
        self.after(0, lambda: self.detail_label.configure(text=detail))
        if progress is not None:
            self.after(0, lambda: self.progress_bar.set(progress))
    
    def _on_force_close(self):
        if messagebox.askyesno("ปิดโปรแกรม?", "การติดตั้งยังไม่เสร็จ\nต้องการปิดหรือไม่?"):
            self.cancelled = True
            self.destroy()
            os._exit(0)
    
    @run_in_thread
    def _start_setup(self):
        try:
            os.makedirs(ENGINE_DIR, exist_ok=True)
            
            if not os.path.exists(YTDLP_PATH):
                self._update_status("📥 ดาวน์โหลด yt-dlp.exe...", "จาก GitHub", 0.05)
                if not self._download_file(YTDLP_DOWNLOAD_URL, YTDLP_PATH, "yt-dlp"):
                    return
            self._update_status("✅ yt-dlp.exe พร้อม", "", 0.4)
            if self.cancelled: return
            
            if not os.path.exists(FFMPEG_PATH):
                self._update_status("📥 ดาวน์โหลด FFmpeg...", "~80MB", 0.45)
                if not self._download_and_extract_ffmpeg():
                    return
            self._update_status("✅ ffmpeg.exe พร้อม", "", 0.95)
            if self.cancelled: return
            
            self._update_status("🎉 ติดตั้งสำเร็จ!", "พร้อมใช้งาน", 1.0)
            self.after(1200, lambda: self._finish(True))
            
        except Exception as e:
            self._update_status(f"❌ Error: {str(e)}", "", 0)
            self.after(4000, lambda: self._finish(False))
    
    def _download_file(self, url: str, dest: str, name: str) -> bool:
        try:
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    if self.cancelled: return False
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
        try:
            resp = requests.get(FFMPEG_DOWNLOAD_URL, stream=True, timeout=180)
            resp.raise_for_status()
            total = int(resp.headers.get('content-length', 0))
            downloaded = 0
            chunks = []
            
            for chunk in resp.iter_content(65536):
                if self.cancelled: return False
                chunks.append(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total
                    self._update_status(
                        f"📥 FFmpeg...", f"{downloaded//(1024*1024)} MB",
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
    
    def _finish(self, success: bool):
        self.destroy()
        self.on_complete(success)


# ══════════════════════════════════════════════════════════════════════════════
# 🎨 MAIN APPLICATION v3.1
# ══════════════════════════════════════════════════════════════════════════════

class InfinityMP3Downloader(ctk.CTk):
    """
    Infinity MP3 Downloader v3.1
    
    🐛 FIXES:
    - Font loading after root window creation
    - Checkbox state persistence sync with settings.json
    
    Features:
    - High-Precision Progress Bar (Floating Point: 45.5%)
    - Intelligent Path Management with State Sync
    - Collapsible Log Console
    """
    
    def __init__(self):
        super().__init__()
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 1: โหลดฟอนต์หลังสร้าง Root Window
        # ═══════════════════════════════════════════════════════════════════
        self.font_family, self.is_custom_font = FontLoader.load()
        self._setup_fonts()
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 2: โหลด Settings และ Sync Checkbox State
        # ═══════════════════════════════════════════════════════════════════
        settings = SettingsManager.load()
        self.output_dir = settings.get("download_path", "")
        
        # CRITICAL: ถ้ามี path บันทึกไว้ -> checkbox = True
        self._path_is_saved = bool(self.output_dir)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 3: Window Config
        # ═══════════════════════════════════════════════════════════════════
        self.title("∞ Infinity MP3 Downloader v3.1")
        self.geometry("780x550")
        self.minsize(720, 450)
        
        # ═══════════════════════════════════════════════════════════════════
        # STEP 4: App Icon (Visual Identity)
        # ═══════════════════════════════════════════════════════════════════
        ICON_PATH = os.path.join(BASE_DIR, "icon", "weeraOwner.ico")
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
                print(f"✅ App icon loaded: {ICON_PATH}")
            except Exception as e:
                print(f"⚠️ Failed to load icon: {e}")
        else:
            print(f"⚠️ Icon not found: {ICON_PATH}")
        
        # State
        self.is_downloading = False
        self.is_updating = False
        self.current_process: Optional[subprocess.Popen] = None
        self.log_visible = False
        
        self._build_ui()
        self.after(200, self._startup_sequence)
    
    def _setup_fonts(self):
        """ตั้งค่าฟอนต์ตาม Font Family ที่โหลดได้"""
        ff = self.font_family
        if self.is_custom_font:
            self.FONT_NORMAL = (ff, 18)
            self.FONT_BOLD = (ff, 18, "bold")
            self.FONT_HEADER = (ff, 26, "bold")
            self.FONT_SUBTITLE = (ff, 15)
            self.FONT_SMALL = (ff, 14)
        else:
            self.FONT_NORMAL = (ff, 14)
            self.FONT_BOLD = (ff, 14, "bold")
            self.FONT_HEADER = (ff, 22, "bold")
            self.FONT_SUBTITLE = (ff, 12)
            self.FONT_SMALL = (ff, 11)
        self.FONT_LOG = ("Consolas", 12)
    
    def _build_ui(self):
        """สร้าง UI"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)
        
        # ══════════════════════════════════════════════════════════════════════
        # 1. HEADER
        # ══════════════════════════════════════════════════════════════════════
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=25, pady=(20, 15), sticky="ew")
        
        title = ctk.CTkLabel(
            header, text="∞ Infinity MP3 Downloader",
            font=ctk.CTkFont(family=self.font_family, size=26, weight="bold")
        )
        title.pack(anchor="w")
        
        version = ctk.CTkLabel(
            header, text="v3.1 • ระบบแปลง YouTube เป็น MP3",
            font=self.FONT_SMALL, text_color="#777777"
        )
        version.pack(anchor="w")
        
        # ══════════════════════════════════════════════════════════════════════
        # 2. INPUT SECTION (URL + Buttons)
        # ══════════════════════════════════════════════════════════════════════
        input_section = ctk.CTkFrame(self)
        input_section.grid(row=1, column=0, padx=25, pady=10, sticky="ew")
        input_section.grid_columnconfigure(0, weight=1)
        
        url_label = ctk.CTkLabel(input_section, text="🔗 ลิงก์ YouTube:", font=self.FONT_BOLD)
        url_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            input_section, placeholder_text="https://www.youtube.com/watch?v=...",
            height=48, font=self.FONT_NORMAL, corner_radius=8
        )
        self.url_entry.grid(row=1, column=0, padx=15, sticky="ew")
        
        # Buttons
        btn_row = ctk.CTkFrame(input_section, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=10, pady=15, sticky="ew")
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.download_btn = ctk.CTkButton(
            btn_row, text="⬇️  ดาวน์โหลด MP3", command=self._on_download,
            height=52, font=self.FONT_BOLD,
            fg_color="#22C55E", hover_color="#16A34A", corner_radius=10
        )
        self.download_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.update_btn = ctk.CTkButton(
            btn_row, text="🔄 อัปเดต", command=self._on_update,
            height=52, font=self.FONT_NORMAL,
            fg_color="#3B82F6", hover_color="#2563EB", corner_radius=10
        )
        self.update_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            btn_row, text="⏹️ หยุด", command=self._on_stop,
            height=52, font=self.FONT_NORMAL,
            fg_color="#DC2626", hover_color="#B91C1C", corner_radius=10, state="disabled"
        )
        self.stop_btn.grid(row=0, column=2, padx=5, sticky="ew")
        
        # ══════════════════════════════════════════════════════════════════════
        # 3. CONFIG SECTION (Path + Save Checkbox)
        # ══════════════════════════════════════════════════════════════════════
        config_section = ctk.CTkFrame(self)
        config_section.grid(row=2, column=0, padx=25, pady=(5, 10), sticky="ew")
        config_section.grid_columnconfigure(1, weight=1)
        
        path_label = ctk.CTkLabel(config_section, text="📁 โฟลเดอร์:", font=self.FONT_BOLD)
        path_label.grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        # Read-only Path Display
        self.path_display = ctk.CTkEntry(
            config_section, height=40, font=self.FONT_NORMAL,
            state="readonly", fg_color="#1e1e2f", corner_radius=6
        )
        self.path_display.grid(row=0, column=1, padx=(0, 10), pady=12, sticky="ew")
        
        # Browse Button
        browse_btn = ctk.CTkButton(
            config_section, text="เปลี่ยน", command=self._browse_folder,
            width=80, height=40, font=self.FONT_SMALL,
            fg_color="transparent", hover_color="#374151", border_width=1, corner_radius=6
        )
        browse_btn.grid(row=0, column=2, padx=(0, 10), pady=12)
        
        # Save Checkbox - CRITICAL: ตั้งค่าเริ่มต้นตาม _path_is_saved
        self.save_default_var = ctk.BooleanVar(value=self._path_is_saved)
        self.save_checkbox = ctk.CTkCheckBox(
            config_section, text="💾 บันทึกเป็นค่าเริ่มต้น",
            variable=self.save_default_var, font=self.FONT_SMALL,
            command=self._on_save_checkbox_toggle
        )
        self.save_checkbox.grid(row=0, column=3, padx=(5, 15), pady=12)
        
        # ══════════════════════════════════════════════════════════════════════
        # 4. PROGRESS SECTION (Ghost)
        # ══════════════════════════════════════════════════════════════════════
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="พร้อมทำงาน", font=self.FONT_BOLD
        )
        self.progress_label.pack(side="left", padx=(0, 15))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=14, corner_radius=7)
        self.progress_bar.pack(side="left", expand=True, fill="x", padx=(0, 15))
        self.progress_bar.set(0)
        
        # High-Precision Percentage
        self.progress_pct = ctk.CTkLabel(
            self.progress_frame, text="", font=self.FONT_BOLD,
            text_color="#22C55E", width=70
        )
        self.progress_pct.pack(side="right")
        
        # ══════════════════════════════════════════════════════════════════════
        # 5. LOG SECTION (Collapsible)
        # ══════════════════════════════════════════════════════════════════════
        self.log_container = ctk.CTkFrame(self)
        
        log_header = ctk.CTkFrame(self.log_container, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(12, 5))
        
        log_title = ctk.CTkLabel(log_header, text="📋 บันทึกการทำงาน", font=self.FONT_BOLD)
        log_title.pack(side="left")
        
        self.log_textbox = ctk.CTkTextbox(
            self.log_container, font=self.FONT_LOG, wrap="word", corner_radius=8
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # ══════════════════════════════════════════════════════════════════════
        # 6. STATUS BAR
        # ══════════════════════════════════════════════════════════════════════
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=5, column=0, padx=25, pady=(5, 15), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame, text="พร้อมทำงาน", font=self.FONT_SMALL, text_color="#666666"
        )
        self.status_label.pack(side="left")
        
        self.toggle_log_btn = ctk.CTkButton(
            status_frame, text="📝 แสดง Log", command=self._toggle_log,
            height=28, width=100, font=self.FONT_SMALL,
            fg_color="transparent", hover_color="#374151", border_width=1, corner_radius=6
        )
        self.toggle_log_btn.pack(side="right")
    
    # ══════════════════════════════════════════════════════════════════════════
    # STARTUP SEQUENCE
    # ══════════════════════════════════════════════════════════════════════════
    
    def _startup_sequence(self):
        """ลำดับการเริ่มต้น"""
        # Update path display
        self._update_path_display()
        
        # First Run: ต้องเลือก Path ก่อน
        if SettingsManager.is_first_run() or not self.output_dir:
            self.log("🆕 ครั้งแรก - กรุณาเลือกโฟลเดอร์", "INFO")
            FirstRunPathDialog(self, self.font_family, self.is_custom_font, self._on_path_selected)
            return
        
        # Check Dependencies
        self._check_dependencies()
    
    def _on_path_selected(self, path: str):
        """Callback หลังเลือก Path"""
        self.output_dir = path
        self._path_is_saved = True
        self.save_default_var.set(True)  # Sync checkbox
        self._update_path_display()
        self.log(f"✅ ตั้งโฟลเดอร์: {path}", "SUCCESS")
        self._check_dependencies()
    
    def _check_dependencies(self):
        """ตรวจสอบ Dependencies"""
        if not os.path.exists(YTDLP_PATH) or not os.path.exists(FFMPEG_PATH):
            self.log("⚠️ ติดตั้งระบบ...", "WARNING")
            DependencySetupDialog(self, self.font_family, self.is_custom_font, self._on_deps_complete)
        else:
            self.log("✅ ระบบพร้อมทำงาน", "SUCCESS")
    
    def _on_deps_complete(self, success: bool):
        if success:
            self.log("🎉 ติดตั้งสำเร็จ!", "SUCCESS")
        else:
            self.log("❌ ติดตั้งล้มเหลว", "ERROR")
    
    # ══════════════════════════════════════════════════════════════════════════
    # PATH MANAGEMENT (Intelligent State Sync)
    # ══════════════════════════════════════════════════════════════════════════
    
    def _update_path_display(self):
        """อัปเดต Path Display"""
        self.path_display.configure(state="normal")
        self.path_display.delete(0, "end")
        self.path_display.insert(0, self.output_dir or "(ยังไม่ได้เลือก)")
        self.path_display.configure(state="readonly")
    
    def _browse_folder(self):
        """เลือกโฟลเดอร์ใหม่"""
        folder = filedialog.askdirectory(
            title="เลือกโฟลเดอร์ปลายทาง",
            initialdir=self.output_dir or os.path.expanduser("~")
        )
        if folder:
            self.output_dir = folder
            self._update_path_display()
            self.log(f"📂 เปลี่ยนโฟลเดอร์: {folder}", "INFO")
            
            # ถ้า checkbox ติ๊กอยู่ -> บันทึกทันที
            if self.save_default_var.get():
                SettingsManager.save_path(folder)
                self.log("💾 บันทึกเป็นค่าเริ่มต้นแล้ว", "SUCCESS")
    
    def _on_save_checkbox_toggle(self):
        """
        CRITICAL: Logic เมื่อ Checkbox ถูก Toggle
        
        - Toggle ON (Check): บันทึก path ลง settings.json ทันที
        - Toggle OFF (Uncheck): ลบ path ออกจาก settings.json (session-only)
        """
        if self.save_default_var.get():
            # Checked: บันทึก
            if self.output_dir:
                SettingsManager.save_path(self.output_dir)
                self._path_is_saved = True
                self.log("💾 บันทึกโฟลเดอร์เป็นค่าเริ่มต้นแล้ว", "SUCCESS")
            else:
                self.log("⚠️ กรุณาเลือกโฟลเดอร์ก่อน", "WARNING")
                self.save_default_var.set(False)
        else:
            # Unchecked: ลบจาก settings (session-only mode)
            SettingsManager.clear_path()
            self._path_is_saved = False
            self.log("🔄 โฟลเดอร์จะใช้เฉพาะรอบนี้ (ไม่บันทึก)", "INFO")
    
    # ══════════════════════════════════════════════════════════════════════════
    # UI STATE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    
    def _show_progress(self):
        def _show():
            self.progress_frame.grid(row=3, column=0, padx=25, pady=10, sticky="ew")
            self.progress_bar.set(0)
        self.after(0, _show)
    
    def _hide_progress(self, delay_ms: int = 2000):
        def _hide():
            self.progress_frame.grid_forget()
            self.progress_bar.set(0)
            self.progress_pct.configure(text="")
        self.after(delay_ms, _hide)
    
    def _toggle_log(self):
        if self.log_visible:
            self.log_container.grid_forget()
            self.toggle_log_btn.configure(text="📝 แสดง Log")
            self.geometry("780x550")
            self.log_visible = False
        else:
            self.log_container.grid(row=4, column=0, padx=25, pady=(0, 10), sticky="nsew")
            self.toggle_log_btn.configure(text="📝 ซ่อน Log")
            self.geometry("780x700")
            self.log_visible = True
    
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "•")
        formatted = f"[{timestamp}] {prefix} {message}\n"
        
        def _update():
            self.log_textbox.insert("end", formatted)
            self.log_textbox.see("end")
        self.after(0, _update)
    
    def update_progress(self, label: str, percentage: float = None):
        """High-Precision Progress Update (1 decimal place)"""
        def _update():
            self.progress_label.configure(text=label)
            if percentage is not None:
                self.progress_bar.set(percentage / 100.0)
                self.progress_pct.configure(text=f"{percentage:.1f}%")
            else:
                self.progress_pct.configure(text="")
        self.after(0, _update)
    
    def set_buttons_state(self, busy: bool = False):
        def _update():
            state = "disabled" if busy else "normal"
            self.download_btn.configure(state=state)
            self.update_btn.configure(state=state)
            self.stop_btn.configure(state="normal" if busy else "disabled")
        self.after(0, _update)
    
    # ══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _on_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("ไม่พบลิงก์", "กรุณาวาง URL")
            return
        if not self.output_dir:
            messagebox.showwarning("ไม่พบโฟลเดอร์", "กรุณาเลือกโฟลเดอร์ก่อน")
            return
        if not os.path.exists(YTDLP_PATH):
            messagebox.showerror("ไม่พบระบบ", "กรุณากด 'อัปเดต'")
            return
        
        self.is_downloading = True
        self.set_buttons_state(busy=True)
        self._show_progress()
        self._start_download(url)
    
    def _on_update(self):
        if messagebox.askyesno("อัปเดต?", "ดาวน์โหลด yt-dlp ล่าสุด?"):
            self.is_updating = True
            self.set_buttons_state(busy=True)
            self._show_progress()
            self._start_update()
    
    def _on_stop(self):
        if self.current_process:
            self.log("⏹️ หยุด...", "WARNING")
            try:
                self.current_process.terminate()
                self.current_process = None
            except: pass
        self.is_downloading = False
        self.is_updating = False
        self.set_buttons_state(busy=False)
        self.update_progress("หยุดแล้ว", 0)
        self._hide_progress(1000)
    
    # ══════════════════════════════════════════════════════════════════════════
    # DOWNLOAD LOGIC (High-Precision Progress)
    # ══════════════════════════════════════════════════════════════════════════
    
    @run_in_thread
    def _start_download(self, url: str):
        try:
            self.log(f"🔗 เริ่มดาวน์โหลด: {url[:50]}...", "INFO")
            self.update_progress("กำลังเริ่ม...", 0.0)
            
            cmd = [
                YTDLP_PATH,
                "--ffmpeg-location", ENGINE_DIR,
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "320K",  # ✅ CBR 320kbps (Maximum Quality)
                "--add-metadata",           # ✅ Embed Artist, Title, etc.
                "--embed-thumbnail",        # ✅ Embed Cover Art
                "--restrict-filenames",
                "--no-playlist",
                "--newline",
                "--output", os.path.join(self.output_dir, "%(title)s.%(ext)s"),
                url
            ]
            
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # High-Precision Regex (captures decimals)
            progress_re = re.compile(r'\[download\]\s+(\d+\.?\d*)%')
            
            for line in self.current_process.stdout:
                line = line.strip()
                if not line: continue
                self.log(line)
                
                match = progress_re.search(line)
                if match:
                    pct = float(match.group(1))  # Floating point!
                    self.update_progress("กำลังดาวน์โหลด...", pct)
                elif "[ExtractAudio]" in line:
                    self.update_progress("แปลงเป็น MP3...", None)
                elif "Deleting original" in line:
                    self.update_progress("เกือบเสร็จ...", 99.5)
            
            return_code = self.current_process.wait()
            self.current_process = None
            
            if return_code == 0:
                self.update_progress("✅ สำเร็จ!", 100.0)
                self.log("🎉 ดาวน์โหลดเสร็จ!", "SUCCESS")
                self.after(0, lambda: messagebox.showinfo("สำเร็จ", "ดาวน์โหลดเรียบร้อย!"))
            else:
                self.update_progress("❌ ล้มเหลว", 0)
                self.log(f"❌ Error: {return_code}", "ERROR")
            
            self._hide_progress()
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            self.update_progress("❌ Error", 0)
            self._hide_progress()
        finally:
            self.is_downloading = False
            self.set_buttons_state(busy=False)
    
    @run_in_thread
    def _start_update(self):
        """
        🔗 Chained Update System
        
        ลำดับการทำงาน:
        1. ตรวจสอบ App Update (version.json) - ถ้ามี จะ Swap & Restart
        2. ตรวจสอบ yt-dlp Update - Smart Version Check ก่อนดาวน์โหลด
        """
        try:
            # ═══════════════════════════════════════════════════════════════
            # Detect Running Mode
            # ═══════════════════════════════════════════════════════════════
            is_frozen = getattr(sys, 'frozen', False)
            
            if is_frozen:
                # Production Mode (.exe)
                app_path = sys.executable
                skip_app_update = False
                self.log("🏭 Production Mode: Running as compiled .exe", "INFO")
            else:
                # Developer Mode (.py)
                app_path = os.path.join(BASE_DIR, "main.exe")
                skip_app_update = True
                self.log("━" * 50, "INFO")
                self.log("🛠️ DEV MODE: Skipping App Self-Update (Safety Protocol)", "WARNING")
                self.log("   • รันจากซอร์สโค้ด .py", "INFO")
                self.log("   • ข้าม App Self-Update เพื่อป้องกันไฟล์เสียหาย", "INFO")
                self.log("   • จะตรวจสอบเฉพาะ yt-dlp เท่านั้น", "INFO")
                self.log("━" * 50, "INFO")
                # Small delay so user can read the message
                import time
                time.sleep(1)
            
            self.log(f"📌 App Version: {APP_VERSION}", "INFO")
            
            # เรียกใช้ Chained Update Routine
            result = run_full_update_routine(
                app_version=APP_VERSION,
                app_version_url=UPDATE_JSON_URL,
                app_path=app_path,
                engine_dir=ENGINE_DIR,
                progress_callback=self.update_progress,
                log_callback=self.log,
                skip_app_update=skip_app_update
            )
            
            # ตรวจสอบผลลัพธ์
            if result.requires_restart:
                # App update ต้องการ restart
                self.log("🔄 โปรแกรมจะปิดและเปิดใหม่อัตโนมัติ...", "SUCCESS")
                self.after(0, lambda: messagebox.showinfo(
                    "กำลังอัปเดต",
                    "โปรแกรมจะปิดและเปิดใหม่อัตโนมัติเพื่อติดตั้งเวอร์ชันใหม่"
                ))
                # รอ 1 วินาทีแล้วปิดโปรแกรม (ให้ batch script ทำงาน)
                self.after(1500, lambda: sys.exit(0))
                return
            
            if result.success:
                self.after(0, lambda: messagebox.showinfo("สำเร็จ", result.message))
            else:
                self.after(0, lambda: messagebox.showwarning("แจ้งเตือน", result.message))
            
            self._hide_progress()
            
        except Exception as e:
            self.log(f"❌ อัปเดตล้มเหลว: {str(e)}", "ERROR")
            self.update_progress("❌ ล้มเหลว", 0)
            self._hide_progress()
        finally:
            self.is_updating = False
            self.set_buttons_state(busy=False)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = InfinityMP3Downloader()
    app.mainloop()
