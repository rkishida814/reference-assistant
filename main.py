import sys
from PyQt6.QtWidgets import QApplication
from ui.start_screen import StartScreen

def main():
    app = QApplication(sys.argv)
    
    # Initialize the start screen
    start_window = StartScreen()
    start_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
