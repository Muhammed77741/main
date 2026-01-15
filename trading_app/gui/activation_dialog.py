"""
License Activation Dialog
UI for entering and activating license keys
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QGroupBox, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QClipboard


# License key format configuration
LICENSE_KEY_GROUP_SIZE = 5  # Characters per group (e.g., XXXXX-XXXXX)


class ActivationDialog(QDialog):
    """Dialog for license activation"""
    
    activation_successful = Signal(dict)
    
    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("License Activation - Trading Bot Manager")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Make dialog modal
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("License Activation Required")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status message
        self.status_label = QLabel("Please enter your license key to activate the application.")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addSpacing(20)
        
        # Hardware ID Group
        hwid_group = QGroupBox("Hardware ID")
        hwid_layout = QVBoxLayout()
        
        info_label = QLabel("Your Hardware ID (needed for license generation):")
        info_label.setWordWrap(True)
        hwid_layout.addWidget(info_label)
        
        hwid_container = QHBoxLayout()
        self.hwid_display = QLineEdit()
        self.hwid_display.setReadOnly(True)
        hwid = self.license_manager.get_hardware_id()
        self.hwid_display.setText(hwid)
        self.hwid_display.setFont(QFont("Courier", 9))
        hwid_container.addWidget(self.hwid_display)
        
        copy_hwid_btn = QPushButton("Copy")
        copy_hwid_btn.setMaximumWidth(80)
        copy_hwid_btn.clicked.connect(self.copy_hardware_id)
        hwid_container.addWidget(copy_hwid_btn)
        
        hwid_layout.addLayout(hwid_container)
        hwid_group.setLayout(hwid_layout)
        layout.addWidget(hwid_group)
        
        layout.addSpacing(20)
        
        # License Key Group
        license_group = QGroupBox("License Key")
        license_layout = QVBoxLayout()
        
        key_label = QLabel("Enter your license key:")
        license_layout.addWidget(key_label)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.license_input.setFont(QFont("Courier", 11))
        self.license_input.textChanged.connect(self.format_license_key)
        license_layout.addWidget(self.license_input)
        
        license_group.setLayout(license_layout)
        layout.addWidget(license_group)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.activate_btn = QPushButton("Activate License")
        self.activate_btn.clicked.connect(self.activate_license)
        self.activate_btn.setMinimumHeight(35)
        button_layout.addWidget(self.activate_btn)
        
        # Start trial button (only if trial not expired)
        license_status = self.license_manager.check_license()
        if license_status.get('is_first_run'):
            self.trial_btn = QPushButton(f"Start {self.license_manager.trial_manager.TRIAL_DAYS}-Day Trial")
            self.trial_btn.clicked.connect(self.start_trial)
            self.trial_btn.setMinimumHeight(35)
            button_layout.addWidget(self.trial_btn)
        
        cancel_btn = QPushButton("Exit")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        layout.addSpacing(10)
        
        # Help text
        help_text = QLabel(
            "Don't have a license? Contact support to purchase.\n"
            "Trial version is fully functional for 7 days."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray; font-size: 10px;")
        help_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(help_text)
        
        self.setLayout(layout)
    
    def format_license_key(self, text):
        """Auto-format license key with dashes"""
        # Remove all non-alphanumeric characters
        clean = ''.join(c for c in text.upper() if c.isalnum())
        
        # Format with dashes every LICENSE_KEY_GROUP_SIZE characters
        formatted = '-'.join([clean[i:i+LICENSE_KEY_GROUP_SIZE] 
                             for i in range(0, len(clean), LICENSE_KEY_GROUP_SIZE)])
        
        # Update only if different (to avoid infinite loop)
        if formatted != text:
            cursor_pos = self.license_input.cursorPosition()
            self.license_input.setText(formatted)
            # Restore cursor position
            self.license_input.setCursorPosition(min(cursor_pos, len(formatted)))
    
    def copy_hardware_id(self):
        """Copy hardware ID to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hwid_display.text())
        
        QMessageBox.information(
            self,
            "Copied",
            "Hardware ID copied to clipboard!"
        )
    
    def activate_license(self):
        """Activate license with entered key"""
        license_key = self.license_input.text().strip()
        
        if not license_key:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter a license key."
            )
            return
        
        # Disable button during activation
        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("Activating...")
        
        # Attempt activation
        result = self.license_manager.activate_license(license_key)
        
        # Re-enable button
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("Activate License")
        
        if result['success']:
            QMessageBox.information(
                self,
                "Activation Successful",
                f"{result['message']}\n\nThe application will now start."
            )
            self.activation_successful.emit(result['license_info'])
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Activation Failed",
                f"{result['message']}\n\nPlease check your license key and try again."
            )
    
    def start_trial(self):
        """Start trial period"""
        reply = QMessageBox.question(
            self,
            "Start Trial",
            f"Start {self.license_manager.trial_manager.TRIAL_DAYS}-day trial?\n\n"
            "You can purchase a license at any time during or after the trial.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            trial_info = self.license_manager.start_trial()
            
            QMessageBox.information(
                self,
                "Trial Started",
                f"Trial started successfully!\n\n"
                f"Days remaining: {trial_info['days_remaining']}\n"
                f"Expires: {trial_info['expires_at'].strftime('%Y-%m-%d')}\n\n"
                "The application will now start."
            )
            self.accept()


class TrialStatusWidget(QLabel):
    """Widget to display trial/license status in main window"""
    
    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.update_status()
    
    def update_status(self):
        """Update status display"""
        status_msg = self.license_manager.get_status_message()
        status = self.license_manager.check_license()
        
        # Color coding
        if status['is_valid']:
            if status.get('is_licensed'):
                color = "green"
                icon = "✓"
            else:
                # Trial
                days = status['days_remaining']
                if days <= 2:
                    color = "red"
                    icon = "⚠"
                elif days <= 5:
                    color = "orange"
                    icon = "⚠"
                else:
                    color = "blue"
                    icon = "ℹ"
        else:
            color = "red"
            icon = "✗"
        
        self.setText(f"{icon} {status_msg}")
        self.setStyleSheet(f"color: {color}; font-weight: bold; padding: 5px;")


if __name__ == '__main__':
    # Test activation dialog
    import sys
    from licensing import LicenseManager
    
    app = QApplication(sys.argv)
    
    lm = LicenseManager()
    dialog = ActivationDialog(lm)
    
    if dialog.exec() == QDialog.Accepted:
        print("Activation successful!")
    else:
        print("Activation cancelled or failed")
    
    sys.exit(0)
