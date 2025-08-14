#!/usr/bin/env python3
"""
YouTube Clip Agent - Main Application Entry Point
"""

from gui.main_window import MainWindow
from utils.logging import setup_logging

def main():
    """Main application entry point"""
    setup_logging()
    app = MainWindow()
    app.run()

if __name__ == '__main__':
    main()
