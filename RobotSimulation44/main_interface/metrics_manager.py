# metrics_manager.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from PyQt5.QtCore import Qt

class MetricsManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QHBoxLayout()   # 3 columns side by side
        main_layout.setAlignment(Qt.AlignTop)

        # --- Sorting Metrics ---
        sorting_box = QGroupBox("Sorting Metrics")
        sorting_layout = QVBoxLayout()

        self.total_label = QLabel("Total Sorted: 0")
        self.correct_label = QLabel("Correct: 0")
        self.errors_label = QLabel("Errors: 0")
        self.accuracy_label = QLabel("Accuracy: 0.0%")
        self.items_per_min_label = QLabel("Items/Min: 0")

        sorting_layout.addWidget(self.total_label)
        sorting_layout.addWidget(self.correct_label)
        sorting_layout.addWidget(self.errors_label)
        sorting_layout.addWidget(self.accuracy_label)
        sorting_layout.addWidget(self.items_per_min_label)
        sorting_box.setLayout(sorting_layout)

        # --- Packaging Metrics ---
        packaging_box = QGroupBox("Packaging Metrics")
        packaging_layout = QVBoxLayout()

        self.packing_efficiency_label = QLabel("Packing Efficiency: 0.0%")
        self.packaging_throughput_label = QLabel("Throughput: 0")
        self.packaging_error_rate_label = QLabel("Error Rate: 0.0%")

        packaging_layout.addWidget(self.packing_efficiency_label)
        packaging_layout.addWidget(self.packaging_throughput_label)
        packaging_layout.addWidget(self.packaging_error_rate_label)
        packaging_box.setLayout(packaging_layout)

        # --- Inspection Metrics ---
        inspection_box = QGroupBox("Inspection Metrics")
        inspection_layout = QVBoxLayout()

        self.inspection_accuracy_label = QLabel("Accuracy: 0.0%")
        self.defects_missed_label = QLabel("Defects Missed: 0")
        self.inspection_throughput_label = QLabel("Throughput: 0")

        inspection_layout.addWidget(self.inspection_accuracy_label)
        inspection_layout.addWidget(self.defects_missed_label)
        inspection_layout.addWidget(self.inspection_throughput_label)
        inspection_box.setLayout(inspection_layout)

        # Add all groups to main layout
        main_layout.addWidget(sorting_box)
        main_layout.addWidget(packaging_box)
        main_layout.addWidget(inspection_box)

        self.setLayout(main_layout)

        # Internal placeholders
        self.total = 0
        self.correct = 0
        self.errors = 0
        self.accuracy = 0.0
        self.items_per_min = 0

        self.packing_efficiency = 0.0
        self.packaging_throughput = 0
        self.packaging_error_rate = 0.0

        self.inspection_accuracy = 0.0
        self.defects_missed = 0
        self.inspection_throughput = 0

    def update_metrics(self, metrics: dict):
        """Update labels with values from a dict of metrics"""

        # Sorting
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

        # Packaging
        self.packing_efficiency = metrics.get("packing_efficiency", self.packing_efficiency)
        self.packaging_throughput = metrics.get("packaging_throughput", self.packaging_throughput)
        self.packaging_error_rate = metrics.get("packaging_error_rate", self.packaging_error_rate)

        self.packing_efficiency_label.setText(f"Packing Efficiency: {self.packing_efficiency:.1f}%")
        self.packaging_throughput_label.setText(f"Throughput: {self.packaging_throughput}")
        self.packaging_error_rate_label.setText(f"Error Rate: {self.packaging_error_rate:.1f}%")

        # Inspection
        self.inspection_accuracy = metrics.get("inspection_accuracy", self.inspection_accuracy)
        self.defects_missed = metrics.get("defects_missed", self.defects_missed)
        self.inspection_throughput = metrics.get("inspection_throughput", self.inspection_throughput)

        self.inspection_accuracy_label.setText(f"Accuracy: {self.inspection_accuracy:.1f}%")
        self.defects_missed_label.setText(f"Defects Missed: {self.defects_missed}")
        self.inspection_throughput_label.setText(f"Throughput: {self.inspection_throughput}")

    def reset_metrics(self):
        # Reset sorting
        self.total = 0
        self.correct = 0
        self.errors = 0
        self.accuracy = 0.0
        self.items_per_min = 0

        self.total_label.setText("Total Sorted: 0")
        self.correct_label.setText("Correct: 0")
        self.errors_label.setText("Errors: 0")
        self.accuracy_label.setText("Accuracy: 0.0%")
        self.items_per_min_label.setText("Items/Min: 0")

        # Reset packaging
        self.packing_efficiency = 0.0
        self.packaging_error_rate = 0.0
        self.packaging_throughput = 0

        self.packing_efficiency_label.setText("Packing Efficiency: 0.0%")
        self.packaging_throughput_label.setText("Throughput: 0")
        self.packaging_error_rate_label.setText("Error Rate: 0.0%")

        # Reset inspection
        self.inspection_accuracy = 0.0
        self.defects_missed = 0
        self.inspection_throughput = 0

        self.inspection_accuracy_label.setText("Accuracy: 0.0%")
        self.defects_missed_label.setText("Defects Missed: 0")
        self.inspection_throughput_label.setText("Throughput: 0")
