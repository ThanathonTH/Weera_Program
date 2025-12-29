"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      CUSTOM WIDGETS MODULE                                   ║
║              Context Menu & Smart Keyboard Shortcuts                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📋 Right-Click Context Menu (Cut/Copy/Paste/Select All)                     ║
║  🌐 Hardware Keycode Bindings (Works with Thai/English keyboard)             ║
║  🔧 Language-Independent Shortcuts via Virtual Events                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from typing import Tuple, Any

import customtkinter as ctk


def select_all(entry_widget: Any) -> str:
    """
    Select all text in an entry widget.
    
    Args:
        entry_widget: The tkinter entry widget
        
    Returns:
        str: "break" to prevent default behavior
    """
    try:
        entry_widget.select_range(0, "end")
        entry_widget.icursor("end")
    except Exception:
        pass
    return "break"


def create_context_menu(
    widget: ctk.CTkEntry,
    font: Tuple[str, int] = ("Tahoma", 14)
) -> None:
    """
    Create a right-click context menu for a CTkEntry widget.
    
    Features:
    - Cut/Copy/Paste/Select All with Thai labels
    - Works with any keyboard layout (Thai/English)
    - Hardware keycode-based shortcuts (language independent)
    
    Args:
        widget: The CTkEntry widget to attach the menu to
        font: Font tuple for menu items (family, size)
    
    Example:
        url_entry = ctk.CTkEntry(parent, ...)
        create_context_menu(url_entry, font=("Tahoma", 14))
    """
    # Create the context menu
    context_menu = tk.Menu(widget, tearoff=0, font=font)
    
    # Get the underlying tkinter entry widget from CTkEntry
    try:
        inner_entry = widget._entry  # CTkEntry internal reference
    except AttributeError:
        inner_entry = widget  # Fallback for standard Entry
    
    # Menu commands using virtual events (keyboard layout independent)
    context_menu.add_command(
        label="✂️  ตัด",
        command=lambda: inner_entry.event_generate("<<Cut>>")
    )
    context_menu.add_command(
        label="📄  คัดลอก",
        command=lambda: inner_entry.event_generate("<<Copy>>")
    )
    context_menu.add_command(
        label="📋  วาง",
        command=lambda: inner_entry.event_generate("<<Paste>>")
    )
    context_menu.add_separator()
    context_menu.add_command(
        label="✅  เลือกทั้งหมด",
        command=lambda: select_all(inner_entry)
    )
    
    def show_context_menu(event: tk.Event) -> None:
        """Show context menu at cursor position."""
        try:
            inner_entry.focus_set()
            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(f"⚠️ Context menu error: {e}")
        finally:
            context_menu.grab_release()
    
    # Bind right-click event (Button-3 on Windows/Linux)
    inner_entry.bind("<Button-3>", show_context_menu)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🌐 Smart Keyboard Shortcuts (Keycode-Based, Language Independent)
    # ═══════════════════════════════════════════════════════════════════════════
    # Uses hardware keycodes instead of characters so it works with
    # ANY keyboard layout (Thai, English, Japanese, etc.)
    
    def handle_smart_shortcuts(event: tk.Event) -> str | None:
        """
        Handle Ctrl+Key shortcuts using hardware keycodes.
        Works regardless of keyboard language layout.
        
        Windows Standard Keycodes:
        A=65, C=67, V=86, X=88
        """
        keycode = event.keycode
        
        if keycode == 65:  # A key -> Select All
            select_all(inner_entry)
            return "break"
        elif keycode == 67:  # C key -> Copy
            inner_entry.event_generate("<<Copy>>")
            return "break"
        elif keycode == 86:  # V key -> Paste
            inner_entry.event_generate("<<Paste>>")
            return "break"
        elif keycode == 88:  # X key -> Cut
            inner_entry.event_generate("<<Cut>>")
            return "break"
        
        return None  # Let other keys pass through
    
    # Bind generic Control-Key event to our smart handler
    inner_entry.bind("<Control-Key>", handle_smart_shortcuts)


def create_readonly_entry(
    parent: Any,
    text: str,
    height: int = 40,
    font: Tuple[str, int] = ("Tahoma", 14),
    fg_color: str = "#1e1e2f",
    corner_radius: int = 6
) -> ctk.CTkEntry:
    """
    Create a read-only entry widget for displaying text.
    
    Args:
        parent: Parent widget
        text: Initial text to display
        height: Entry height in pixels
        font: Font tuple
        fg_color: Background color
        corner_radius: Corner radius in pixels
        
    Returns:
        CTkEntry: The configured entry widget
    """
    entry = ctk.CTkEntry(
        parent,
        height=height,
        font=font,
        state="readonly",
        fg_color=fg_color,
        corner_radius=corner_radius
    )
    
    # Set initial text
    entry.configure(state="normal")
    entry.insert(0, text)
    entry.configure(state="readonly")
    
    return entry


def update_readonly_entry(entry: ctk.CTkEntry, text: str) -> None:
    """
    Update the text of a read-only entry widget.
    
    Args:
        entry: The CTkEntry widget
        text: New text to display
    """
    entry.configure(state="normal")
    entry.delete(0, "end")
    entry.insert(0, text)
    entry.configure(state="readonly")
