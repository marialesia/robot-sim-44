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

        self.sort_total_label = QLabel("Total Sorted: 0")
        self.sort_errors_label = QLabel("Total Errors: 0")
        self.sort_error_rate_label = QLabel("Robot Error Rate: 0.0%")
        self.sort_correction_rate_label = QLabel("User Correction Rate: 0.0%")

        for lbl in [
            self.sort_total_label,
            self.sort_errors_label,
            self.sort_error_rate_label,
            self.sort_correction_rate_label,
        ]:
            sorting_layout.addWidget(lbl)

        sorting_box.setLayout(sorting_layout)

        # --- Packaging Metrics ---
        packaging_box = QGroupBox("Packaging Metrics")
        packaging_layout = QVBoxLayout()

        self.pack_total_label = QLabel("Total Packed: 0")
        self.pack_errors_label = QLabel("Total Errors: 0")
        self.pack_error_rate_label = QLabel("Robot Error Rate: 0.0%")
        self.pack_correction_rate_label = QLabel("User Correction Rate: 0.0%")

        for lbl in [
            self.pack_total_label,
            self.pack_errors_label,
            self.pack_error_rate_label,
            self.pack_correction_rate_label,
        ]:
            packaging_layout.addWidget(lbl)

        packaging_box.setLayout(packaging_layout)

        # --- Inspection Metrics ---
        inspection_box = QGroupBox("Inspection Metrics")
        inspection_layout = QVBoxLayout()

        self.insp_total_label = QLabel("Total Inspected: 0")
        self.insp_errors_label = QLabel("Total Errors: 0")
        self.insp_error_rate_label = QLabel("Robot Error Rate: 0.0%")
        self.insp_correction_rate_label = QLabel("User Correction Rate: 0.0%")

        for lbl in [
            self.insp_total_label,
            self.insp_errors_label,
            self.insp_error_rate_label,
            self.insp_correction_rate_label,
        ]:
            inspection_layout.addWidget(lbl)

        inspection_box.setLayout(inspection_layout)

        # Add all groups to main layout
        main_layout.addWidget(sorting_box)
        main_layout.addWidget(packaging_box)
        main_layout.addWidget(inspection_box)

        self.setLayout(main_layout)

        # --- Internal placeholders ---
        # Sorting
        self.sort_total = 0
        self.sort_errors = 0
        self.sort_error_rate = 0.0
        self.sort_correction_rate = 0.0

        # Packaging
        self.pack_total = 0
        self.pack_errors = 0
        self.pack_error_rate = 0.0
        self.pack_correction_rate = 0.0

        # Inspection
        self.insp_total = 0
        self.insp_errors = 0
        self.insp_error_rate = 0.0
        self.insp_correction_rate = 0.0

    def update_metrics(self, metrics: dict):
        """Update labels with values from a dict of metrics"""

        # Sorting
        self.sort_total = metrics.get("sort_total", self.sort_total)
        self.sort_errors = metrics.get("sort_errors", self.sort_errors)
        self.sort_error_rate = metrics.get("sort_error_rate", self.sort_error_rate)
        self.sort_correction_rate = metrics.get("sort_correction_rate", self.sort_correction_rate)

        self.sort_total_label.setText(f"Total Sorted: {self.sort_total}")
        self.sort_errors_label.setText(f"Total Errors: {self.sort_errors}")
        self.sort_error_rate_label.setText(f"Robot Error Rate: {self.sort_error_rate:.1f}%")
        self.sort_correction_rate_label.setText(f"User Correction Rate: {self.sort_correction_rate:.1f}%")

        # Packaging
        self.pack_total = metrics.get("pack_total", self.pack_total)
        self.pack_errors = metrics.get("pack_errors", self.pack_errors)
        self.pack_error_rate = metrics.get("pack_error_rate", self.pack_error_rate)
        self.pack_correction_rate = metrics.get("pack_correction_rate", self.pack_correction_rate)

        self.pack_total_label.setText(f"Total Packed: {self.pack_total}")
        self.pack_errors_label.setText(f"Total Errors: {self.pack_errors}")
        self.pack_error_rate_label.setText(f"Robot Error Rate: {self.pack_error_rate:.1f}%")
        self.pack_correction_rate_label.setText(f"User Correction Rate: {self.pack_correction_rate:.1f}%")

        # Inspection
        self.insp_total = metrics.get("insp_total", self.insp_total)
        self.insp_errors = metrics.get("insp_errors", self.insp_errors)
        self.insp_error_rate = metrics.get("insp_error_rate", self.insp_error_rate)
        self.insp_correction_rate = metrics.get("insp_correction_rate", self.insp_correction_rate)

        self.insp_total_label.setText(f"Total Inspected: {self.insp_total}")
        self.insp_errors_label.setText(f"Total Errors: {self.insp_errors}")
        self.insp_error_rate_label.setText(f"Robot Error Rate: {self.insp_error_rate:.1f}%")
        self.insp_correction_rate_label.setText(f"User Correction Rate: {self.insp_correction_rate:.1f}%")

    def reset_metrics(self):
        """Reset all metrics to zero and update labels"""
        # Sorting
        self.sort_total = 0
        self.sort_errors = 0
        self.sort_error_rate = 0.0
        self.sort_correction_rate = 0.0

        self.sort_total_label.setText("Total Sorted: 0")
        self.sort_errors_label.setText("Total Errors: 0")
        self.sort_error_rate_label.setText("Robot Error Rate: 0.0%")
        self.sort_correction_rate_label.setText("User Correction Rate: 0.0%")

        # Packaging
        self.pack_total = 0
        self.pack_errors = 0
        self.pack_error_rate = 0.0
        self.pack_correction_rate = 0.0

        self.pack_total_label.setText("Total Packed: 0")
        self.pack_errors_label.setText("Total Errors: 0")
        self.pack_error_rate_label.setText("Robot Error Rate: 0.0%")
        self.pack_correction_rate_label.setText("User Correction Rate: 0.0%")

        # Inspection
        self.insp_total = 0
        self.insp_errors = 0
        self.insp_error_rate = 0.0
        self.insp_correction_rate = 0.0

        self.insp_total_label.setText("Total Inspected: 0")
        self.insp_errors_label.setText("Total Errors: 0")
        self.insp_error_rate_label.setText("Robot Error Rate: 0.0%")
        self.insp_correction_rate_label.setText("User Correction Rate: 0.0%")
