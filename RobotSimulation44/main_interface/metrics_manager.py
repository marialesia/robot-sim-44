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

        self.sort_total_label = QLabel("Total Sorted: 0")
        self.sort_accuracy_label = QLabel("Accuracy: 0.0%")
        self.sort_efficiency_label = QLabel("Efficiency: 0.0%")
        self.sort_throughput_label = QLabel("Throughput: 0")
        self.sort_errors_label = QLabel("Errors: 0")
        self.sort_error_rate_label = QLabel("Error Rate: 0.0%")
        self.sort_items_per_min_label = QLabel("Items/Min: 0")

        for lbl in [self.sort_total_label, self.sort_accuracy_label, self.sort_efficiency_label,
                    self.sort_throughput_label, self.sort_errors_label,
                    self.sort_error_rate_label, self.sort_items_per_min_label]:
            sorting_layout.addWidget(lbl)

        # User Metrics Sub-Box
        sort_user_metrics_box = QGroupBox("User Metrics")
        sort_user_metrics_layout = QVBoxLayout()

        self.sort_avg_correction_time_label = QLabel("Avg Correction Time: 0.0s")
        self.sort_correction_accuracy_label = QLabel("Correction Accuracy: 0.0%")

        for lbl in [self.sort_avg_correction_time_label, self.sort_correction_accuracy_label]:
            sort_user_metrics_layout.addWidget(lbl)

        sort_user_metrics_box.setLayout(sort_user_metrics_layout)

        # Add the user metrics box below the regular metrics
        sorting_layout.addWidget(sort_user_metrics_box)

        sorting_box.setLayout(sorting_layout)

        # --- Packaging Metrics ---
        packaging_box = QGroupBox("Packaging Metrics")
        packaging_layout = QVBoxLayout()

        self.pack_total_label = QLabel("Total Packed: 0")
        self.pack_accuracy_label = QLabel("Accuracy: 0.0%")
        self.pack_efficiency_label = QLabel("Efficiency: 0.0%")
        self.pack_throughput_label = QLabel("Throughput: 0")
        self.pack_errors_label = QLabel("Errors: 0")
        self.pack_error_rate_label = QLabel("Error Rate: 0.0%")
        self.pack_items_per_min_label = QLabel("Items/Min: 0")

        for lbl in [self.pack_total_label, self.pack_accuracy_label, self.pack_efficiency_label,
                    self.pack_throughput_label, self.pack_errors_label,
                    self.pack_error_rate_label, self.pack_items_per_min_label]:
            packaging_layout.addWidget(lbl)

        # User Metrics Sub-Box
        pack_user_metrics_box = QGroupBox("User Metrics")
        pack_user_metrics_layout = QVBoxLayout()

        self.pack_avg_correction_time_label = QLabel("Avg Correction Time: 0.0s")
        self.pack_correction_accuracy_label = QLabel("Correction Accuracy: 0.0%")

        for lbl in [self.pack_avg_correction_time_label, self.pack_correction_accuracy_label]:
            pack_user_metrics_layout.addWidget(lbl)

        pack_user_metrics_box.setLayout(pack_user_metrics_layout)

        # Add the user metrics box below the regular metrics
        packaging_layout.addWidget(pack_user_metrics_box)

        packaging_box.setLayout(packaging_layout)

        # --- Inspection Metrics ---
        inspection_box = QGroupBox("Inspection Metrics")
        inspection_layout = QVBoxLayout()

        self.insp_total_label = QLabel("Total Inspected: 0")
        self.insp_accuracy_label = QLabel("Accuracy: 0.0%")
        self.insp_efficiency_label = QLabel("Efficiency: 0.0%")
        self.insp_throughput_label = QLabel("Throughput: 0")
        self.insp_defects_missed_label = QLabel("Defects Missed: 0")
        self.insp_error_rate_label = QLabel("Error Rate: 0.0%")
        self.insp_items_per_min_label = QLabel("Items/Min: 0")

        for lbl in [self.insp_total_label, self.insp_accuracy_label, self.insp_efficiency_label,
                    self.insp_throughput_label, self.insp_defects_missed_label,
                    self.insp_error_rate_label, self.insp_items_per_min_label]:
            inspection_layout.addWidget(lbl)

        # User Metrics Sub-Box
        insp_user_metrics_box = QGroupBox("User Metrics")
        insp_user_metrics_layout = QVBoxLayout()

        self.insp_avg_correction_time_label = QLabel("Avg Correction Time: 0.0s")
        self.insp_correction_accuracy_label = QLabel("Correction Accuracy: 0.0%")

        for lbl in [self.insp_avg_correction_time_label, self.insp_correction_accuracy_label]:
            insp_user_metrics_layout.addWidget(lbl)

        insp_user_metrics_box.setLayout(insp_user_metrics_layout)

        # Add the user metrics box below the regular metrics
        inspection_layout.addWidget(insp_user_metrics_box)

        inspection_box.setLayout(inspection_layout)

        # Add all groups to main layout
        main_layout.addWidget(sorting_box)
        main_layout.addWidget(packaging_box)
        main_layout.addWidget(inspection_box)

        self.setLayout(main_layout)

        # --- Internal placeholders ---
        # Sorting
        self.sort_total = 0
        self.sort_accuracy = 0.0
        self.sort_efficiency = 0.0
        self.sort_throughput = 0
        self.sort_errors = 0
        self.sort_error_rate = 0.0
        self.sort_items_per_min = 0
        self.sort_avg_correction_time = 0.0
        self.sort_correction_accuracy = 0.0

        # Packaging
        self.pack_total = 0
        self.pack_accuracy = 0.0
        self.pack_efficiency = 0.0
        self.pack_throughput = 0
        self.pack_errors = 0
        self.pack_error_rate = 0.0
        self.pack_items_per_min = 0
        self.pack_avg_correction_time = 0.0
        self.pack_correction_accuracy = 0.0

        # Inspection
        self.insp_total = 0
        self.insp_accuracy = 0.0
        self.insp_efficiency = 0.0
        self.insp_throughput = 0
        self.insp_defects_missed = 0
        self.insp_error_rate = 0.0
        self.insp_items_per_min = 0
        self.insp_avg_correction_time = 0.0
        self.insp_correction_accuracy = 0.0

    def update_metrics(self, metrics: dict):
        """Update labels with values from a dict of metrics"""

        # Sorting
        self.sort_total = metrics.get("sort_total", self.sort_total)
        self.sort_accuracy = metrics.get("sort_accuracy", self.sort_accuracy)
        self.sort_efficiency = metrics.get("sort_efficiency", self.sort_efficiency)
        self.sort_throughput = metrics.get("sort_throughput", self.sort_throughput)
        self.sort_errors = metrics.get("sort_errors", self.sort_errors)
        self.sort_error_rate = metrics.get("sort_error_rate", self.sort_error_rate)
        self.sort_items_per_min = metrics.get("sort_items_per_min", self.sort_items_per_min)
        self.sort_avg_correction_time = metrics.get("sort_avg_correction_time", self.sort_avg_correction_time)
        self.sort_correction_accuracy = metrics.get("sort_correction_accuracy", self.sort_correction_accuracy)

        self.sort_total_label.setText(f"Total Sorted: {self.sort_total}")
        self.sort_accuracy_label.setText(f"Accuracy: {self.sort_accuracy:.1f}%")
        self.sort_efficiency_label.setText(f"Efficiency: {self.sort_efficiency:.1f}%")
        self.sort_throughput_label.setText(f"Throughput: {self.sort_throughput}")
        self.sort_errors_label.setText(f"Errors: {self.sort_errors}")
        self.sort_error_rate_label.setText(f"Error Rate: {self.sort_error_rate:.1f}%")
        self.sort_items_per_min_label.setText(f"Items/Min: {self.sort_items_per_min}")
        self.sort_avg_correction_time_label.setText(f"Avg Correction Time: {self.sort_avg_correction_time:.1f}s")
        self.sort_correction_accuracy_label.setText(f"Correction Accuracy: {self.sort_correction_accuracy:.1f}%")

        # Packaging
        self.pack_total = metrics.get("pack_total", self.pack_total)
        self.pack_accuracy = metrics.get("pack_accuracy", self.pack_accuracy)
        self.pack_efficiency = metrics.get("pack_efficiency", self.pack_efficiency)
        self.pack_throughput = metrics.get("pack_throughput", self.pack_throughput)
        self.pack_errors = metrics.get("pack_errors", self.pack_errors)
        self.pack_error_rate = metrics.get("pack_error_rate", self.pack_error_rate)
        self.pack_items_per_min = metrics.get("pack_items_per_min", self.pack_items_per_min)
        self.pack_avg_correction_time = metrics.get("pack_avg_correction_time", self.pack_avg_correction_time)
        self.pack_correction_accuracy = metrics.get("pack_correction_accuracy", self.pack_correction_accuracy)

        self.pack_total_label.setText(f"Total Packed: {self.pack_total}")
        self.pack_accuracy_label.setText(f"Accuracy: {self.pack_accuracy:.1f}%")
        self.pack_efficiency_label.setText(f"Efficiency: {self.pack_efficiency:.1f}%")
        self.pack_throughput_label.setText(f"Throughput: {self.pack_throughput}")
        self.pack_errors_label.setText(f"Errors: {self.pack_errors}")
        self.pack_error_rate_label.setText(f"Error Rate: {self.pack_error_rate:.1f}%")
        self.pack_items_per_min_label.setText(f"Items/Min: {self.pack_items_per_min}")
        self.pack_avg_correction_time_label.setText(f"Avg Correction Time: {self.pack_avg_correction_time:.1f}s")
        self.pack_correction_accuracy_label.setText(f"Correction Accuracy: {self.pack_correction_accuracy:.1f}%")

        # Inspection
        self.insp_total = metrics.get("insp_total", self.insp_total)
        self.insp_accuracy = metrics.get("insp_accuracy", self.insp_accuracy)
        self.insp_efficiency = metrics.get("insp_efficiency", self.insp_efficiency)
        self.insp_throughput = metrics.get("insp_throughput", self.insp_throughput)
        self.insp_defects_missed = metrics.get("insp_defects_missed", self.insp_defects_missed)
        self.insp_error_rate = metrics.get("insp_error_rate", self.insp_error_rate)
        self.insp_items_per_min = metrics.get("insp_items_per_min", self.insp_items_per_min)
        self.insp_avg_correction_time = metrics.get("insp_avg_correction_time", self.insp_avg_correction_time)
        self.insp_correction_accuracy = metrics.get("insp_correction_accuracy", self.insp_correction_accuracy)

        self.insp_total_label.setText(f"Total Inspected: {self.insp_total}")
        self.insp_accuracy_label.setText(f"Accuracy: {self.insp_accuracy:.1f}%")
        self.insp_efficiency_label.setText(f"Efficiency: {self.insp_efficiency:.1f}%")
        self.insp_throughput_label.setText(f"Throughput: {self.insp_throughput}")
        self.insp_defects_missed_label.setText(f"Defects Missed: {self.insp_defects_missed}")
        self.insp_error_rate_label.setText(f"Error Rate: {self.insp_error_rate:.1f}%")
        self.insp_items_per_min_label.setText(f"Items/Min: {self.insp_items_per_min}")
        self.insp_avg_correction_time_label.setText(f"Avg Correction Time: {self.insp_avg_correction_time:.1f}s")
        self.insp_correction_accuracy_label.setText(f"Correction Accuracy: {self.insp_correction_accuracy:.1f}%")

    def reset_metrics(self):
        """Reset all metrics to zero and update labels"""
        # Sorting
        self.sort_total = 0
        self.sort_accuracy = 0.0
        self.sort_efficiency = 0.0
        self.sort_throughput = 0
        self.sort_errors = 0
        self.sort_error_rate = 0.0
        self.sort_items_per_min = 0
        self.sort_avg_correction_time = 0.0
        self.sort_correction_accuracy = 0.0

        self.sort_total_label.setText("Total Sorted: 0")
        self.sort_accuracy_label.setText("Accuracy: 0.0%")
        self.sort_efficiency_label.setText("Efficiency: 0.0%")
        self.sort_throughput_label.setText("Throughput: 0")
        self.sort_errors_label.setText("Errors: 0")
        self.sort_error_rate_label.setText("Error Rate: 0.0%")
        self.sort_items_per_min_label.setText("Items/Min: 0")
        self.sort_avg_correction_time_label.setText("Avg Correction Time: 0.0s")
        self.sort_correction_accuracy_label.setText("Correction Accuracy: 0.0%")

        # Packaging
        self.pack_total = 0
        self.pack_accuracy = 0.0
        self.pack_efficiency = 0.0
        self.pack_throughput = 0
        self.pack_errors = 0
        self.pack_error_rate = 0.0
        self.pack_items_per_min = 0
        self.pack_avg_correction_time = 0.0
        self.pack_correction_accuracy = 0.0

        self.pack_total_label.setText("Total Packed: 0")
        self.pack_accuracy_label.setText("Accuracy: 0.0%")
        self.pack_efficiency_label.setText("Efficiency: 0.0%")
        self.pack_throughput_label.setText("Throughput: 0")
        self.pack_errors_label.setText("Errors: 0")
        self.pack_error_rate_label.setText("Error Rate: 0.0%")
        self.pack_items_per_min_label.setText("Items/Min: 0")
        self.pack_avg_correction_time_label.setText("Avg Correction Time: 0.0s")
        self.pack_correction_accuracy_label.setText("Correction Accuracy: 0.0%")

        # Inspection
        self.insp_total = 0
        self.insp_accuracy = 0.0
        self.insp_efficiency = 0.0
        self.insp_throughput = 0
        self.insp_defects_missed = 0
        self.insp_error_rate = 0.0
        self.insp_items_per_min = 0
        self.insp_avg_correction_time = 0.0
        self.insp_correction_accuracy = 0.0

        self.insp_total_label.setText("Total Inspected: 0")
        self.insp_accuracy_label.setText("Accuracy: 0.0%")
        self.insp_efficiency_label.setText("Efficiency: 0.0%")
        self.insp_throughput_label.setText("Throughput: 0")
        self.insp_defects_missed_label.setText("Defects Missed: 0")
        self.insp_error_rate_label.setText("Error Rate: 0.0%")
        self.insp_items_per_min_label.setText("Items/Min: 0")
        self.insp_avg_correction_time_label.setText("Avg Correction Time: 0.0s")
        self.insp_correction_accuracy_label.setText("Correction Accuracy: 0.0%")
