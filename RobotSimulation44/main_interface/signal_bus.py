# signal_bus.py
from PyQt5.QtCore import QObject, pyqtSignal

class SignalBus(QObject):
    tasks_changed = pyqtSignal(list)
    start_pressed = pyqtSignal()
    pause_pressed = pyqtSignal()
