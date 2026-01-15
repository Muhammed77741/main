"""
License Key Generator Tool
Standalone tool for generating license keys
"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Add parent directory to path to import licensing module
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from licensing.keygen import generate_license_key
from licensing.hwid import get_hardware_id


class LicenseKeyGeneratorWindow(QMainWindow):
    """Main window for license key generator"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Trading Bot Manager - License Key Generator")
        self.setGeometry(100, 100, 700, 500)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Title
        title = QLabel("License Key Generator")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Hardware ID input group
        hwid_group = QGroupBox("Hardware ID")
        hwid_layout = QVBoxLayout()
        
        info_label = QLabel("Enter the customer's Hardware ID:")
        hwid_layout.addWidget(info_label)
        
        hwid_input_layout = QHBoxLayout()
        self.hwid_input = QLineEdit()
        self.hwid_input.setPlaceholderText("Paste Hardware ID here...")
        self.hwid_input.setFont(QFont("Courier", 10))
        hwid_input_layout.addWidget(self.hwid_input)
        
        use_current_btn = QPushButton("Use Current Machine")
        use_current_btn.clicked.connect(self.use_current_hwid)
        hwid_input_layout.addWidget(use_current_btn)
        
        hwid_layout.addLayout(hwid_input_layout)
        hwid_group.setLayout(hwid_layout)
        layout.addWidget(hwid_group)
        
        # License options group
        options_group = QGroupBox("License Options")
        options_layout = QVBoxLayout()
        
        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration:"))
        
        self.duration_combo = QComboBox()
        self.duration_combo.addItems([
            "7 days (Trial)",
            "30 days",
            "90 days",
            "180 days",
            "365 days (1 year)",
            "730 days (2 years)",
            "1095 days (3 years)",
            "Lifetime"
        ])
        self.duration_combo.setCurrentIndex(4)  # Default to 1 year
        duration_layout.addWidget(self.duration_combo)
        duration_layout.addStretch()
        
        options_layout.addLayout(duration_layout)
        
        # Features
        features_layout = QHBoxLayout()
        features_layout.addWidget(QLabel("Features:"))
        
        self.features_combo = QComboBox()
        self.features_combo.addItems([
            "ALL (Full Access)",
            "BTC Only",
            "ETH Only",
            "XAUUSD Only"
        ])
        features_layout.addWidget(self.features_combo)
        features_layout.addStretch()
        
        options_layout.addLayout(features_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Generate button
        generate_btn = QPushButton("Generate License Key")
        generate_btn.setMinimumHeight(40)
        generate_btn.clicked.connect(self.generate_key)
        layout.addWidget(generate_btn)
        
        # Output group
        output_group = QGroupBox("Generated License Key")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier", 10))
        self.output_text.setMinimumHeight(150)
        output_layout.addWidget(self.output_text)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        output_layout.addWidget(copy_btn)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        layout.addStretch()
    
    def use_current_hwid(self):
        """Use current machine's hardware ID"""
        hwid = get_hardware_id()
        self.hwid_input.setText(hwid)
        QMessageBox.information(
            self,
            "Hardware ID",
            f"Using current machine's Hardware ID:\n\n{hwid}"
        )
    
    def generate_key(self):
        """Generate license key"""
        hwid = self.hwid_input.text().strip()
        
        if not hwid:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter a Hardware ID."
            )
            return
        
        # Parse duration
        duration_text = self.duration_combo.currentText()
        if "Lifetime" in duration_text:
            days = 0
        else:
            days = int(duration_text.split()[0])
        
        # Parse features
        features_text = self.features_combo.currentText()
        if "ALL" in features_text:
            features = "ALL"
        elif "BTC Only" in features_text:
            features = "BTC"
        elif "ETH Only" in features_text:
            features = "ETH"
        elif "XAUUSD Only" in features_text:
            features = "XAUUSD"
        else:
            features = "ALL"
        
        # Generate key
        try:
            license_key = generate_license_key(hwid, days, features)
            
            # Format output
            from datetime import datetime
            output = f"""
{'='*60}
Trading Bot Manager - License Key
{'='*60}

Hardware ID:
{hwid}

License Key:
{license_key}

Duration: {duration_text}
Features: {features_text}

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{'='*60}

IMPORTANT:
- This license is bound to the above Hardware ID
- Customer must enter this exact key in the application
- Keep this information secure and confidential

{'='*60}
"""
            
            self.output_text.setPlainText(output)
            
            QMessageBox.information(
                self,
                "Success",
                "License key generated successfully!"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate license key:\n\n{str(e)}"
            )
    
    def copy_to_clipboard(self):
        """Copy generated key to clipboard"""
        text = self.output_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(
                self,
                "Copied",
                "License information copied to clipboard!"
            )
        else:
            QMessageBox.warning(
                self,
                "Nothing to Copy",
                "Please generate a license key first."
            )


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("License Key Generator")
    app.setStyle('Fusion')
    
    window = LicenseKeyGeneratorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
