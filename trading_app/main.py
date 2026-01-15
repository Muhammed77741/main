"""
Trading Bot Manager - Main Application
Production version with licensing system
"""
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from gui import MainWindow
from gui.activation_dialog import ActivationDialog
from licensing import LicenseManager


def main():
    """Main entry point"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Trading Bot Manager")
    app.setOrganizationName("TradingBots")
    app.setApplicationVersion("1.0.0")

    # Set style
    app.setStyle('Fusion')

    # Initialize license manager
    license_manager = LicenseManager()
    
    # Check license status
    license_status = license_manager.check_license()
    
    # Handle first run - show welcome and start trial or activate
    if license_status.get('is_first_run'):
        # Show activation dialog for first run
        activation_dialog = ActivationDialog(license_manager)
        if activation_dialog.exec() != activation_dialog.Accepted:
            # User cancelled - exit application
            return 0
        
        # Re-check license after activation/trial start
        license_status = license_manager.check_license()
    
    # Check if activation is required
    if license_status['requires_activation']:
        # Trial expired or no valid license
        activation_dialog = ActivationDialog(license_manager)
        
        # Show message about trial expiration
        if not license_status.get('is_first_run'):
            QMessageBox.warning(
                None,
                "Trial Expired",
                "Your trial period has expired.\n\n"
                "Please activate with a license key to continue using the application."
            )
        
        if activation_dialog.exec() != activation_dialog.Accepted:
            # User cancelled - exit application
            QMessageBox.information(
                None,
                "Activation Required",
                "The application requires activation to continue."
            )
            return 0
        
        # Re-check license after activation
        license_status = license_manager.check_license()
    
    # Verify we have a valid license or trial
    if not license_status['is_valid']:
        QMessageBox.critical(
            None,
            "License Error",
            f"License validation failed: {license_status['message']}\n\n"
            "Please contact support."
        )
        return 1
    
    # Show license/trial info
    if license_status.get('is_trial'):
        days = license_status['days_remaining']
        if days <= 2:
            QMessageBox.warning(
                None,
                "Trial Expiring Soon",
                f"Your trial expires in {days} day(s).\n\n"
                "Please purchase a license to continue using the application after trial expires."
            )
    
    # Create and show main window with license manager
    window = MainWindow(license_manager=license_manager)
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
