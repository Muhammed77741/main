"""
Trading Bot Manager - Main Application
Phase 1 MVP - Basic GUI without licensing
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui import MainWindow


def main():
    """Main entry point"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Trading Bot Manager")
    app.setOrganizationName("TradingBots")

    # Set style
    app.setStyle('Fusion')

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
