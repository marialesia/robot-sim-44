# metrics_manager.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class MetricsManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # Placeholder labels for metrics
        self.total_label = QLabel("Total Sorted: 0")
        self.correct_label = QLabel("Correct: 0")
        self.errors_label = QLabel("Errors: 0")
        self.accuracy_label = QLabel("Accuracy: 0.0%")
        self.items_per_min_label = QLabel("Items/Min: 0")

        # Add to layout
        layout.addWidget(self.total_label)
        layout.addWidget(self.correct_label)
        layout.addWidget(self.errors_label)
        layout.addWidget(self.accuracy_label)
        layout.addWidget(self.items_per_min_label)

        self.setLayout(layout)

        # Internal placeholders
        self.total = 0
        self.correct = 0
        self.errors = 0
        self.accuracy = 0.0
        self.items_per_min = 0

    def update_metrics(self, metrics: dict):
        """Update labels with values from a dict of metrics"""
        self.total = metrics.get("total", self.total)
        self.correct = metrics.get("correct", self.correct)
        self.errors = metrics.get("errors", self.errors)
        self.accuracy = metrics.get("accuracy", self.accuracy)
        self.items_per_min = metrics.get("items_per_min", self.items_per_min)

        # Refresh text
        self.total_label.setText(f"Total Sorted: {self.total}")
        self.correct_label.setText(f"Correct: {self.correct}")
        self.errors_label.setText(f"Errors: {self.errors}")
        self.accuracy_label.setText(f"Accuracy: {self.accuracy:.1f}%")
        self.items_per_min_label.setText(f"Items/Min: {self.items_per_min}")

    def reset_metrics(self):
        self.total_sorted_label.setText("Total Sorted: 0")
        self.correct_label.setText("Correct: 0")
        self.errors_label.setText("Errors: 0")
        self.accuracy_label.setText("Accuracy: 0%")
        self.items_per_min_label.setText("Items/Min: 0")
        self.spawn_rate_avg_label.setText("Spawn Rate Avg: 0")

