# audio_manager.py
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import QUrl, QTimer


class AudioManager:
    def __init__(self, base_path="sounds/"):
        # Conveyor belt (looping)
        self.conveyor = QSoundEffect()
        self.conveyor.setSource(QUrl.fromLocalFile(base_path + "conveyor_belt_single.wav"))
        self.conveyor.setLoopCount(QSoundEffect.Infinite)
        self.conveyor.setVolume(1.0)

        # Robotic arm
        self.robotic_arm = QSoundEffect()
        self.robotic_arm.setSource(QUrl.fromLocalFile(base_path + "robot_arm_single.wav"))
        self.robotic_arm.setVolume(1.0)

        # Correct chime
        self.correct_chime = QSoundEffect()
        self.correct_chime.setSource(QUrl.fromLocalFile(base_path + "correct_chime_single.wav"))
        self.correct_chime.setVolume(1.0)

        # Incorrect chime
        self.incorrect_chime = QSoundEffect()
        self.incorrect_chime.setSource(QUrl.fromLocalFile(base_path + "incorrect_chime_single.wav"))
        self.incorrect_chime.setVolume(1.0)

        # Alarm (looping until stopped)
        self.alarm = QSoundEffect()
        self.alarm.setSource(QUrl.fromLocalFile(base_path + "alarm_single.wav"))
        self.alarm.setLoopCount(QSoundEffect.Infinite)
        self.alarm.setVolume(0.9)

        self.conveyor_running = False

    # Conveyor controls
    def start_conveyor(self):
        if not self.conveyor_running:
            self.conveyor.play()
            self.conveyor_running = True

    def stop_conveyor(self):
        if self.conveyor_running:
            self.conveyor.stop()
            self.conveyor_running = False

    # Robotic arm
    def play_robotic_arm(self):
        self.robotic_arm.play()

    # Correct chime
    def play_correct(self):
        self.correct_chime.play()

    # Incorrect chime + alarm (delayed)
    def play_incorrect_with_alarm(self, delay_ms=1200):
        self.incorrect_chime.play()
        QTimer.singleShot(delay_ms, self.start_alarm)

    # Alarm controls
    def start_alarm(self):
        self.alarm.play()

    def stop_alarm(self):
        self.alarm.stop()
