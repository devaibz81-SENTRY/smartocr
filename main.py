"""
SmartOCR - Real-time Scoreboard OCR with Field Tracking
Main entry point
"""
import sys
from PySide6.QtWidgets import QApplication
from src.core.app import SmartOCRApp

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SmartOCR")
    app.setApplicationVersion("1.0.0")
    
    window = SmartOCRApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
