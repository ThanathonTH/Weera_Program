"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  INFINITY MP3 DOWNLOADER v4.0                                ║
║                 Main Application (CustomTkinter GUI)                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🚀 Package-Based Architecture                                                ║
║  🔌 Decoupled Download Engine with Performance Optimizations                  ║
║  🌐 Thai Keyboard Support (Hardware Keycode Bindings)                         ║
║  🎨 High-Precision Progress Bar (Floating Point)                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import ctypes
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from src.utils.paths import (
    BASE_DIR,
    ENGINE_DIR,
    YTDLP_PATH,
    FFMPEG_PATH,
    APP_VERSION,
    UPDATE_JSON_URL,
    is_frozen,
    get_icon_path,
)
from src.utils.fonts import FontLoader
from src.core.settings import SettingsManager
from src.core.downloader import Downloader, run_in_thread
from src.core.updater import run_full_update_routine
from src.ui.dialogs import FirstRunPathDialog, DependencySetupDialog
from src.ui.widgets import create_context_menu


# Set UI Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class InfinityMP3Downloader(ctk.CTk):
    """
    Infinity MP3 Downloader v4.0
    
    Main application window with modular architecture.
    
    Features:
    - High-Performance Download Engine (concurrent fragments)
    - Decoupled GUI/Logic design
    - Thai keyboard support
    - Intelligent path management
    """
    
    def __init__(self):
        super().__init__()
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 1: Load fonts after root window creation
        # ═══════════════════════════════════════════════════════════════════════
        self.font_family, self.is_custom_font = FontLoader.load()
        self._setup_fonts()
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 2: Load settings and sync checkbox state
        # ═══════════════════════════════════════════════════════════════════════
        settings = SettingsManager.load()
        self.output_dir: str = settings.get("download_path", "")
        self._path_is_saved: bool = bool(self.output_dir)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 3: Window configuration
        # ═══════════════════════════════════════════════════════════════════════
        self.title(f"∞ Infinity MP3 Downloader v{APP_VERSION}")
        self.geometry("780x550")
        self.minsize(720, 450)
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 4: App Icon (Taskbar Fix for Windows)
        # ═══════════════════════════════════════════════════════════════════════
        try:
            myappid = f'weera.infinity.downloader.v{APP_VERSION}'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            print(f"✅ Taskbar ID set: {myappid}")
        except Exception as e:
            print(f"⚠️ Failed to set taskbar ID: {e}")
        
        icon_path = get_icon_path()
        if icon_path:
            try:
                self.iconbitmap(icon_path)
                print(f"✅ App icon loaded: {icon_path}")
            except Exception as e:
                print(f"⚠️ Failed to load icon: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # STEP 5: State variables
        # ═══════════════════════════════════════════════════════════════════════
        self.is_downloading: bool = False
        self.is_updating: bool = False
        self.downloader: Optional[Downloader] = None
        self.log_visible: bool = False
        
        # Build UI and start
        self._build_ui()
        self.after(200, self._startup_sequence)
    
    def _setup_fonts(self) -> None:
        """Configure font tuples based on loaded font family."""
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
    
    def _build_ui(self) -> None:
        """Build the main application UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)
        
        # ══════════════════════════════════════════════════════════════════════
        # 1. HEADER
        # ══════════════════════════════════════════════════════════════════════
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=25, pady=(20, 15), sticky="ew")
        
        title = ctk.CTkLabel(
            header,
            text="∞ Infinity MP3 Downloader",
            font=ctk.CTkFont(family=self.font_family, size=26, weight="bold")
        )
        title.pack(anchor="w")
        
        version = ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION} • ระบบแปลง YouTube เป็น MP3 (Optimized)",
            font=self.FONT_SMALL,
            text_color="#777777"
        )
        version.pack(anchor="w")
        
        # ══════════════════════════════════════════════════════════════════════
        # 2. INPUT SECTION (URL + Buttons)
        # ══════════════════════════════════════════════════════════════════════
        input_section = ctk.CTkFrame(self)
        input_section.grid(row=1, column=0, padx=25, pady=10, sticky="ew")
        input_section.grid_columnconfigure(0, weight=1)
        
        url_label = ctk.CTkLabel(
            input_section,
            text="🔗 ลิงก์ YouTube:",
            font=self.FONT_BOLD
        )
        url_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.url_entry = ctk.CTkEntry(
            input_section,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=48,
            font=self.FONT_NORMAL,
            corner_radius=8
        )
        self.url_entry.grid(row=1, column=0, padx=15, sticky="ew")
        
        # Add context menu with Thai keyboard support
        create_context_menu(self.url_entry, font=self.FONT_NORMAL)
        
        # Buttons row
        btn_row = ctk.CTkFrame(input_section, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=10, pady=15, sticky="ew")
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.download_btn = ctk.CTkButton(
            btn_row,
            text="⬇️  ดาวน์โหลด MP3",
            command=self._on_download,
            height=52,
            font=self.FONT_BOLD,
            fg_color="#22C55E",
            hover_color="#16A34A",
            corner_radius=10
        )
        self.download_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.update_btn = ctk.CTkButton(
            btn_row,
            text="🔄 อัปเดต",
            command=self._on_update,
            height=52,
            font=self.FONT_NORMAL,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            corner_radius=10
        )
        self.update_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            btn_row,
            text="⏹️ หยุด",
            command=self._on_stop,
            height=52,
            font=self.FONT_NORMAL,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            corner_radius=10,
            state="disabled"
        )
        self.stop_btn.grid(row=0, column=2, padx=5, sticky="ew")
        
        # ══════════════════════════════════════════════════════════════════════
        # 3. CONFIG SECTION (Path + Save Checkbox)
        # ══════════════════════════════════════════════════════════════════════
        config_section = ctk.CTkFrame(self)
        config_section.grid(row=2, column=0, padx=25, pady=(5, 10), sticky="ew")
        config_section.grid_columnconfigure(1, weight=1)
        
        path_label = ctk.CTkLabel(
            config_section,
            text="📁 โฟลเดอร์:",
            font=self.FONT_BOLD
        )
        path_label.grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        self.path_display = ctk.CTkEntry(
            config_section,
            height=40,
            font=self.FONT_NORMAL,
            state="readonly",
            fg_color="#1e1e2f",
            corner_radius=6
        )
        self.path_display.grid(row=0, column=1, padx=(0, 10), pady=12, sticky="ew")
        
        browse_btn = ctk.CTkButton(
            config_section,
            text="เปลี่ยน",
            command=self._browse_folder,
            width=80,
            height=40,
            font=self.FONT_SMALL,
            fg_color="transparent",
            hover_color="#374151",
            border_width=1,
            corner_radius=6
        )
        browse_btn.grid(row=0, column=2, padx=(0, 10), pady=12)
        
        # Save checkbox - synced with _path_is_saved
        self.save_default_var = ctk.BooleanVar(value=self._path_is_saved)
        self.save_checkbox = ctk.CTkCheckBox(
            config_section,
            text="💾 บันทึกเป็นค่าเริ่มต้น",
            variable=self.save_default_var,
            font=self.FONT_SMALL,
            command=self._on_save_checkbox_toggle
        )
        self.save_checkbox.grid(row=0, column=3, padx=(5, 15), pady=12)
        
        # ══════════════════════════════════════════════════════════════════════
        # 4. PROGRESS SECTION (Initially hidden)
        # ══════════════════════════════════════════════════════════════════════
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="พร้อมทำงาน",
            font=self.FONT_BOLD
        )
        self.progress_label.pack(side="left", padx=(0, 15))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=14,
            corner_radius=7
        )
        self.progress_bar.pack(side="left", expand=True, fill="x", padx=(0, 15))
        self.progress_bar.set(0)
        
        self.progress_pct = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=self.FONT_BOLD,
            text_color="#22C55E",
            width=70
        )
        self.progress_pct.pack(side="right")
        
        # ══════════════════════════════════════════════════════════════════════
        # 5. LOG SECTION (Collapsible)
        # ══════════════════════════════════════════════════════════════════════
        self.log_container = ctk.CTkFrame(self)
        
        log_header = ctk.CTkFrame(self.log_container, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(12, 5))
        
        log_title = ctk.CTkLabel(
            log_header,
            text="📋 บันทึกการทำงาน",
            font=self.FONT_BOLD
        )
        log_title.pack(side="left")
        
        self.log_textbox = ctk.CTkTextbox(
            self.log_container,
            font=self.FONT_LOG,
            wrap="word",
            corner_radius=8
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # ══════════════════════════════════════════════════════════════════════
        # 6. STATUS BAR
        # ══════════════════════════════════════════════════════════════════════
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=5, column=0, padx=25, pady=(5, 15), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="พร้อมทำงาน",
            font=self.FONT_SMALL,
            text_color="#666666"
        )
        self.status_label.pack(side="left")
        
        self.toggle_log_btn = ctk.CTkButton(
            status_frame,
            text="📝 แสดง Log",
            command=self._toggle_log,
            height=28,
            width=100,
            font=self.FONT_SMALL,
            fg_color="transparent",
            hover_color="#374151",
            border_width=1,
            corner_radius=6
        )
        self.toggle_log_btn.pack(side="right")
    
    # ══════════════════════════════════════════════════════════════════════════
    # STARTUP SEQUENCE
    # ══════════════════════════════════════════════════════════════════════════
    
    def _startup_sequence(self) -> None:
        """Application startup sequence."""
        self._update_path_display()
        
        # First run: must select path
        if SettingsManager.is_first_run() or not self.output_dir:
            self.log("🆕 ครั้งแรก - กรุณาเลือกโฟลเดอร์", "INFO")
            FirstRunPathDialog(
                self,
                self.font_family,
                self.is_custom_font,
                self._on_path_selected
            )
            return
        
        # Check dependencies
        self._check_dependencies()
    
    def _on_path_selected(self, path: str) -> None:
        """Callback after path selection."""
        self.output_dir = path
        self._path_is_saved = True
        self.save_default_var.set(True)
        self._update_path_display()
        self.log(f"✅ ตั้งโฟลเดอร์: {path}", "SUCCESS")
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if dependencies are installed."""
        if not os.path.exists(YTDLP_PATH) or not os.path.exists(FFMPEG_PATH):
            self.log("⚠️ ติดตั้งระบบ...", "WARNING")
            DependencySetupDialog(
                self,
                self.font_family,
                self.is_custom_font,
                self._on_deps_complete
            )
        else:
            self.log("✅ ระบบพร้อมทำงาน", "SUCCESS")
    
    def _on_deps_complete(self, success: bool) -> None:
        """Callback after dependency installation."""
        if success:
            self.log("🎉 ติดตั้งสำเร็จ!", "SUCCESS")
        else:
            self.log("❌ ติดตั้งล้มเหลว", "ERROR")
    
    # ══════════════════════════════════════════════════════════════════════════
    # PATH MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    
    def _update_path_display(self) -> None:
        """Update the path display entry."""
        self.path_display.configure(state="normal")
        self.path_display.delete(0, "end")
        self.path_display.insert(0, self.output_dir or "(ยังไม่ได้เลือก)")
        self.path_display.configure(state="readonly")
    
    def _browse_folder(self) -> None:
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(
            title="เลือกโฟลเดอร์ปลายทาง",
            initialdir=self.output_dir or os.path.expanduser("~")
        )
        if folder:
            self.output_dir = folder
            self._update_path_display()
            self.log(f"📂 เปลี่ยนโฟลเดอร์: {folder}", "INFO")
            
            if self.save_default_var.get():
                SettingsManager.save_path(folder)
                self.log("💾 บันทึกเป็นค่าเริ่มต้นแล้ว", "SUCCESS")
    
    def _on_save_checkbox_toggle(self) -> None:
        """Handle save checkbox state change."""
        if self.save_default_var.get():
            if self.output_dir:
                SettingsManager.save_path(self.output_dir)
                self._path_is_saved = True
                self.log("💾 บันทึกโฟลเดอร์เป็นค่าเริ่มต้นแล้ว", "SUCCESS")
            else:
                self.log("⚠️ กรุณาเลือกโฟลเดอร์ก่อน", "WARNING")
                self.save_default_var.set(False)
        else:
            SettingsManager.clear_path()
            self._path_is_saved = False
            self.log("🔄 โฟลเดอร์จะใช้เฉพาะรอบนี้ (ไม่บันทึก)", "INFO")
    
    # ══════════════════════════════════════════════════════════════════════════
    # UI STATE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    
    def _show_progress(self) -> None:
        """Show the progress bar."""
        def _show():
            self.progress_frame.grid(row=3, column=0, padx=25, pady=10, sticky="ew")
            self.progress_bar.set(0)
        self.after(0, _show)
    
    def _hide_progress(self, delay_ms: int = 2000) -> None:
        """Hide the progress bar after delay."""
        def _hide():
            self.progress_frame.grid_forget()
            self.progress_bar.set(0)
            self.progress_pct.configure(text="")
        self.after(delay_ms, _hide)
    
    def _toggle_log(self) -> None:
        """Toggle log visibility."""
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
    
    def log(self, message: str, level: str = "INFO") -> None:
        """Add a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "•")
        formatted = f"[{timestamp}] {prefix} {message}\n"
        
        def _update():
            self.log_textbox.insert("end", formatted)
            self.log_textbox.see("end")
        self.after(0, _update)
    
    def update_progress(self, label: str, percentage: Optional[float] = None) -> None:
        """Update progress display (thread-safe)."""
        def _update():
            self.progress_label.configure(text=label)
            if percentage is not None:
                self.progress_bar.set(percentage / 100.0)
                self.progress_pct.configure(text=f"{percentage:.1f}%")
            else:
                self.progress_pct.configure(text="")
        self.after(0, _update)
    
    def set_buttons_state(self, busy: bool = False) -> None:
        """Set button states based on busy status."""
        def _update():
            state = "disabled" if busy else "normal"
            self.download_btn.configure(state=state)
            self.update_btn.configure(state=state)
            self.stop_btn.configure(state="normal" if busy else "disabled")
        self.after(0, _update)
    
    # ══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _on_download(self) -> None:
        """Handle download button click."""
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
    
    def _on_update(self) -> None:
        """Handle update button click."""
        if messagebox.askyesno("อัปเดต?", "ดาวน์โหลด yt-dlp ล่าสุด?"):
            self.is_updating = True
            self.set_buttons_state(busy=True)
            self._show_progress()
            self._start_update()
    
    def _on_stop(self) -> None:
        """Handle stop button click."""
        if self.downloader:
            self.downloader.cancel()
            self.log("⏹️ หยุด...", "WARNING")
        
        self.is_downloading = False
        self.is_updating = False
        self.set_buttons_state(busy=False)
        self.update_progress("หยุดแล้ว", 0)
        self._hide_progress(1000)
    
    # ══════════════════════════════════════════════════════════════════════════
    # DOWNLOAD LOGIC (Using Optimized Downloader)
    # ══════════════════════════════════════════════════════════════════════════
    
    @run_in_thread
    def _start_download(self, url: str) -> None:
        """Start download in background thread."""
        try:
            # Create optimized downloader with callbacks
            self.downloader = Downloader(
                output_dir=self.output_dir,
                progress_callback=self.update_progress,
                log_callback=self.log,
                concurrent_fragments=4,  # 🚀 Parallel downloads
                use_aria2c=False  # Set to True if user has aria2c
            )
            
            result = self.downloader.download(url)
            
            if result.success:
                self.after(0, lambda: messagebox.showinfo("สำเร็จ", "ดาวน์โหลดเรียบร้อย!"))
            else:
                self.after(0, lambda: messagebox.showerror("ล้มเหลว", result.message))
            
            self._hide_progress()
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            self.update_progress("❌ Error", 0)
            self._hide_progress()
        finally:
            self.is_downloading = False
            self.downloader = None
            self.set_buttons_state(busy=False)
    
    @run_in_thread
    def _start_update(self) -> None:
        """Start update routine in background thread."""
        try:
            # Detect running mode
            if is_frozen():
                app_path = sys.executable
                skip_app_update = False
                self.log("🏭 Production Mode: Running as compiled .exe", "INFO")
            else:
                app_path = os.path.join(BASE_DIR, "main.exe")
                skip_app_update = True
                self.log("━" * 50, "INFO")
                self.log("🛠️ DEV MODE: Skipping App Self-Update", "WARNING")
                self.log("   • รันจากซอร์สโค้ด .py", "INFO")
                self.log("   • จะตรวจสอบเฉพาะ yt-dlp เท่านั้น", "INFO")
                self.log("━" * 50, "INFO")
                import time
                time.sleep(1)
            
            self.log(f"📌 App Version: {APP_VERSION}", "INFO")
            
            result = run_full_update_routine(
                app_version=APP_VERSION,
                app_version_url=UPDATE_JSON_URL,
                app_path=app_path,
                engine_dir=ENGINE_DIR,
                progress_callback=self.update_progress,
                log_callback=self.log,
                skip_app_update=skip_app_update
            )
            
            if result.requires_restart:
                self.log("🔄 โปรแกรมจะปิดและเปิดใหม่อัตโนมัติ...", "SUCCESS")
                self.after(0, lambda: messagebox.showinfo(
                    "กำลังอัปเดต",
                    "โปรแกรมจะปิดและเปิดใหม่อัตโนมัติเพื่อติดตั้งเวอร์ชันใหม่"
                ))
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
