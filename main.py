"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  INFINITY MP3 DOWNLOADER v4.0                                ║
║                       Clean Entry Point                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🏗️ Package-Based Architecture                                               ║
║  🚀 High-Performance Download Engine                                          ║
║  🌐 Thai Keyboard Support                                                     ║
║  📦 Modular Design for Easy Maintenance                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Entry Point for Infinity MP3 Downloader.

This is the main entry point that imports and runs the application.
All application logic is organized in the src/ package:

    src/
    ├── utils/       # Helper modules (paths, fonts)
    ├── core/        # Business logic (settings, downloader, updater)
    └── ui/          # GUI components (app, dialogs, widgets)

Usage:
    python main.py
    
    Or as PyInstaller executable:
    InfinityDownloader.exe
"""

import sys


def main() -> None:
    """Application entry point."""
    # Import here to ensure proper module loading after path setup
    from src.ui.app import InfinityMP3Downloader
    
    app = InfinityMP3Downloader()
    app.mainloop()


if __name__ == "__main__":
    # Handle post-update flag (from self-update process)
    if "--post-update" in sys.argv:
        print("✅ Update completed successfully!")
    
    main()
