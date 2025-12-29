"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        FONT LOADER MODULE                                     ║
║              Deferred Font Loading for CustomTkinter                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🔤 Custom Thai Font Support (TH Sarabun New)                                 ║
║  🔄 Fallback to System Fonts (Tahoma, Arial)                                  ║
║  ⚠️ MUST be called AFTER root window is created                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from typing import Tuple, List

import customtkinter as ctk

from .paths import FONT_DIR


class FontLoader:
    """
    Deferred Font Loading System
    
    CRITICAL: Must call load() AFTER creating the root CTk window,
    otherwise you'll get "Too early to use font: no default root window" error.
    
    Usage:
        app = ctk.CTk()  # Create window first
        font_family, is_custom = FontLoader.load()  # Then load fonts
    """
    
    # Thai-compatible fallback fonts (in priority order)
    SAFE_THAI_FONTS: List[str] = ["Tahoma", "Microsoft Sans Serif", "Arial"]
    
    # Class-level cache
    _loaded: bool = False
    _font_family: str = "Tahoma"
    _is_custom: bool = False
    
    @classmethod
    def load(cls) -> Tuple[str, bool]:
        """
        Load fonts - MUST be called after root window is created.
        
        Returns:
            Tuple[str, bool]: (font_family_name, is_custom_font)
        """
        if cls._loaded:
            return (cls._font_family, cls._is_custom)
        
        print("\n🔤 === Font Health Check ===")
        
        # Step 1: Try to load Custom Font
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
                        print(f"✓ Loaded {variant}: {filename}")
                    except Exception as e:
                        print(f"⚠️ Failed to load {filename}: {e}")
            
            if loaded > 0:
                # Test if the font is actually usable
                try:
                    test = ctk.CTkFont(family="TH Sarabun New", size=14)
                    if test:
                        cls._font_family = "TH Sarabun New"
                        cls._is_custom = True
                        cls._loaded = True
                        print("✅ Using font: TH Sarabun New")
                        print("=" * 35 + "\n")
                        return (cls._font_family, cls._is_custom)
                except Exception as e:
                    print(f"⚠️ Font loaded but not usable: {e}")
        
        # Step 2: Use Fallback Fonts
        for font_name in cls.SAFE_THAI_FONTS:
            try:
                test = ctk.CTkFont(family=font_name, size=14)
                if test:
                    cls._font_family = font_name
                    cls._is_custom = False
                    cls._loaded = True
                    print(f"🔄 Using fallback font: {font_name}")
                    print("=" * 35 + "\n")
                    return (cls._font_family, cls._is_custom)
            except Exception:
                continue
        
        # Step 3: Default fallback
        cls._loaded = True
        print("⚠️ Using default font: Tahoma")
        print("=" * 35 + "\n")
        return ("Tahoma", False)
    
    @classmethod
    def get_font_sizes(cls, is_custom: bool) -> dict:
        """
        Get appropriate font sizes based on font type.
        
        Custom fonts (TH Sarabun New) need larger sizes due to their design.
        System fonts work well at standard sizes.
        
        Args:
            is_custom: Whether using custom font
            
        Returns:
            dict: Font size configuration
        """
        if is_custom:
            return {
                "normal": 18,
                "bold": 18,
                "header": 26,
                "subtitle": 15,
                "small": 14,
            }
        else:
            return {
                "normal": 14,
                "bold": 14,
                "header": 22,
                "subtitle": 12,
                "small": 11,
            }
    
    @classmethod
    def reset(cls) -> None:
        """Reset the loader state (useful for testing)."""
        cls._loaded = False
        cls._font_family = "Tahoma"
        cls._is_custom = False
