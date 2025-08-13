# main.py
import sys
from PyQt5.QtWidgets import QApplication
from main_interface.unified_interface import UnifiedInterface

def main():
    app = QApplication(sys.argv)
    window = UnifiedInterface()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

