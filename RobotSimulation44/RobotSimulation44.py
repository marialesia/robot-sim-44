import sys
import PyQt5
import matplotlib
import pandas
import numpy
from PyQt5.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
window = QLabel("Hello World!")
print("All imports successful!")
window.show()
sys.exit(app.exec_())

