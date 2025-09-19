from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import time


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

        # Graph for Sorting
        self.sort_fig = Figure(figsize=(3, 2), facecolor="#f9f9f9")
        self.sort_canvas = FigureCanvas(self.sort_fig)
        self.sort_ax = self.sort_fig.add_subplot(111)
        self.sort_ax.tick_params(labelsize=8)
        self.sort_ax.set_facecolor("#f9f9f9")
        self.sort_errors_data = []
        self.sort_corrections_data = []
        self.sort_times = []
        self.sort_start_time = None
        self.sort_error_line, = self.sort_ax.plot([], [], color='red', label="Errors Made")
        self.sort_corrections_line, = self.sort_ax.plot([], [], color='green', label="Errors Corrected")
        self.sort_ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.17), ncol=2)
        self.sort_ax.set_ylim(0, 10)
        self.sort_ax.set_xlim(0, 30)
        # Major and minor ticks
        self.sort_ax.yaxis.set_major_locator(MultipleLocator(5))  # 0,5,10
        self.sort_ax.yaxis.set_minor_locator(MultipleLocator(1))  # grid every 1
        self.sort_ax.xaxis.set_major_locator(MultipleLocator(10))
        self.sort_ax.xaxis.set_minor_locator(MultipleLocator(1))
        self.sort_ax.grid(which='minor', linestyle='--', linewidth=0.5, alpha=0.5)
        self.sort_ax.grid(which='major', linestyle='--', linewidth=0.5, alpha=0.7)
        sorting_layout.addWidget(self.sort_canvas)

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

        # Graph for Packaging
        self.pack_fig = Figure(figsize=(3, 2), facecolor="#f9f9f9")
        self.pack_canvas = FigureCanvas(self.pack_fig)
        self.pack_ax = self.pack_fig.add_subplot(111)
        self.pack_ax.tick_params(labelsize=8)
        self.pack_ax.set_facecolor("#f9f9f9")
        self.pack_errors_data = []
        self.pack_corrections_data = []
        self.pack_times = []
        self.pack_start_time = None
        self.pack_error_line, = self.pack_ax.plot([], [], color='red', label="Errors Made")
        self.pack_corrections_line, = self.pack_ax.plot([], [], color='green', label="Errors Corrected")
        self.pack_ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.17), ncol=2)
        self.pack_ax.set_ylim(0, 10)
        self.pack_ax.set_xlim(0, 30)
        # Major and minor ticks
        self.pack_ax.yaxis.set_major_locator(MultipleLocator(5))  # 0,5,10
        self.pack_ax.yaxis.set_minor_locator(MultipleLocator(1))  # grid every 1
        self.pack_ax.xaxis.set_major_locator(MultipleLocator(10))
        self.pack_ax.xaxis.set_minor_locator(MultipleLocator(1))
        self.pack_ax.grid(which='minor', linestyle='--', linewidth=0.5, alpha=0.5)
        self.pack_ax.grid(which='major', linestyle='--', linewidth=0.5, alpha=0.7)
        packaging_layout.addWidget(self.pack_canvas)

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

        # Graph for Inspection
        self.insp_fig = Figure(figsize=(3, 2), facecolor="#f9f9f9")
        self.insp_canvas = FigureCanvas(self.insp_fig)
        self.insp_ax = self.insp_fig.add_subplot(111)
        self.insp_ax.tick_params(labelsize=8)
        self.insp_ax.set_facecolor("#f9f9f9")
        self.insp_errors_data = []
        self.insp_corrections_data = []
        self.insp_times = []
        self.insp_start_time = None
        self.insp_error_line, = self.insp_ax.plot([], [], color='red', label="Errors Made")
        self.insp_corrections_line, = self.insp_ax.plot([], [], color='green', label="Errors Corrected")
        self.insp_ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.17), ncol=2)
        self.insp_ax.set_ylim(0, 10)
        self.insp_ax.set_xlim(0, 30)
        # Major and minor ticks
        self.insp_ax.yaxis.set_major_locator(MultipleLocator(5))  # 0,5,10
        self.insp_ax.yaxis.set_minor_locator(MultipleLocator(1))  # grid every 1
        self.insp_ax.xaxis.set_major_locator(MultipleLocator(10))
        self.insp_ax.xaxis.set_minor_locator(MultipleLocator(1))
        self.insp_ax.grid(which='minor', linestyle='--', linewidth=0.5, alpha=0.5)
        self.insp_ax.grid(which='major', linestyle='--', linewidth=0.5, alpha=0.7)
        inspection_layout.addWidget(self.insp_canvas)

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
        self.sort_corrections = 0
        self.sort_error_rate = 0.0
        self.sort_correction_rate = 0.0

        # Packaging
        self.pack_total = 0
        self.pack_errors = 0
        self.pack_corrections = 0
        self.pack_error_rate = 0.0
        self.pack_correction_rate = 0.0

        # Inspection
        self.insp_total = 0
        self.insp_errors = 0
        self.insp_corrections = 0
        self.insp_error_rate = 0.0
        self.insp_correction_rate = 0.0

    def update_metrics(self, metrics: dict):
        """Update labels with values from a dict of metrics"""
        current_time = time.time()

        # --- Sorting ---
        self.sort_total = metrics.get("sort_total", self.sort_total)
        self.sort_errors = metrics.get("sort_errors", self.sort_errors)
        self.sort_corrections = metrics.get("sort_corrections", self.sort_corrections)
        self.sort_error_rate = metrics.get("sort_error_rate", self.sort_error_rate)
        self.sort_correction_rate = metrics.get("sort_correction_rate", self.sort_correction_rate)

        self.sort_total_label.setText(f"Total Sorted: {self.sort_total}")
        self.sort_errors_label.setText(f"Total Errors: {self.sort_errors}")
        self.sort_error_rate_label.setText(f"Robot Error Rate: {self.sort_error_rate:.1f}%")
        self.sort_correction_rate_label.setText(f"User Correction Rate: {self.sort_correction_rate:.1f}%")

        if "sort_errors" in metrics or "sort_corrections" in metrics:
            if self.sort_start_time is None:
                self.sort_start_time = current_time

            elapsed = current_time - self.sort_start_time
            self.sort_times.append(elapsed)
            self.sort_errors_data.append(self.sort_errors)
            self.sort_corrections_data.append(self.sort_corrections)

            while self.sort_times and (elapsed - self.sort_times[0] > 30):
                self.sort_times.pop(0)
                self.sort_errors_data.pop(0)
                self.sort_corrections_data.pop(0)

            self.sort_error_line.set_data(self.sort_times, self.sort_errors_data)
            self.sort_corrections_line.set_data(self.sort_times, self.sort_corrections_data)

            # --- Dynamic Y axis: last 20 points, multiples of 5 ---
            last_values = (self.sort_errors_data[-20:] + self.sort_corrections_data[-20:])
            if last_values:
                min_y = max(0, min(last_values) // 5 * 5)
                max_y = (int(max(last_values) / 5) + 1) * 5
            else:
                min_y, max_y = 0, 10
            self.sort_ax.set_ylim(min_y, max_y)
            self.sort_ax.yaxis.set_major_locator(MultipleLocator(5))

            min_x = max(0, elapsed - 30)
            self.sort_ax.set_xlim(min_x, min_x + 30)
            self.sort_ax.xaxis.set_major_locator(MultipleLocator(10))

            self.sort_canvas.draw()

        # --- Packaging ---
        self.pack_total = metrics.get("pack_total", self.pack_total)
        self.pack_errors = metrics.get("pack_errors", self.pack_errors)
        self.pack_corrections = metrics.get("pack_corrections", self.pack_corrections)
        self.pack_error_rate = metrics.get("pack_error_rate", self.pack_error_rate)
        self.pack_correction_rate = metrics.get("pack_correction_rate", self.pack_correction_rate)

        self.pack_total_label.setText(f"Total Packed: {self.pack_total}")
        self.pack_errors_label.setText(f"Total Errors: {self.pack_errors}")
        self.pack_error_rate_label.setText(f"Robot Error Rate: {self.pack_error_rate:.1f}%")
        self.pack_correction_rate_label.setText(f"User Correction Rate: {self.pack_correction_rate:.1f}%")

        if "pack_errors" in metrics or "pack_corrections" in metrics:
            if self.pack_start_time is None:
                self.pack_start_time = current_time

            elapsed = current_time - self.pack_start_time
            self.pack_times.append(elapsed)
            self.pack_errors_data.append(self.pack_errors)
            self.pack_corrections_data.append(self.pack_corrections)

            while self.pack_times and (elapsed - self.pack_times[0] > 30):
                self.pack_times.pop(0)
                self.pack_errors_data.pop(0)
                self.pack_corrections_data.pop(0)

            self.pack_error_line.set_data(self.pack_times, self.pack_errors_data)
            self.pack_corrections_line.set_data(self.pack_times, self.pack_corrections_data)

            last_values = (self.pack_errors_data[-20:] + self.pack_corrections_data[-20:])
            if last_values:
                min_y = max(0, min(last_values) // 5 * 5)
                max_y = (int(max(last_values) / 5) + 1) * 5
            else:
                min_y, max_y = 0, 10
            self.pack_ax.set_ylim(min_y, max_y)
            self.pack_ax.yaxis.set_major_locator(MultipleLocator(5))

            min_x = max(0, elapsed - 30)
            self.pack_ax.set_xlim(min_x, min_x + 30)
            self.pack_ax.xaxis.set_major_locator(MultipleLocator(10))

            self.pack_canvas.draw()

        # --- Inspection ---
        self.insp_total = metrics.get("insp_total", self.insp_total)
        self.insp_errors = metrics.get("insp_errors", self.insp_errors)
        self.insp_corrections = metrics.get("insp_corrections", self.insp_corrections)
        self.insp_error_rate = metrics.get("insp_error_rate", self.insp_error_rate)
        self.insp_correction_rate = metrics.get("insp_correction_rate", self.insp_correction_rate)

        self.insp_total_label.setText(f"Total Inspected: {self.insp_total}")
        self.insp_errors_label.setText(f"Total Errors: {self.insp_errors}")
        self.insp_error_rate_label.setText(f"Robot Error Rate: {self.insp_error_rate:.1f}%")
        self.insp_correction_rate_label.setText(f"User Correction Rate: {self.insp_correction_rate:.1f}%")

        if "insp_errors" in metrics or "insp_corrections" in metrics:
            if self.insp_start_time is None:
                self.insp_start_time = current_time

            elapsed = current_time - self.insp_start_time
            self.insp_times.append(elapsed)
            self.insp_errors_data.append(self.insp_errors)
            self.insp_corrections_data.append(self.insp_corrections)

            while self.insp_times and (elapsed - self.insp_times[0] > 30):
                self.insp_times.pop(0)
                self.insp_errors_data.pop(0)
                self.insp_corrections_data.pop(0)

            self.insp_error_line.set_data(self.insp_times, self.insp_errors_data)
            self.insp_corrections_line.set_data(self.insp_times, self.insp_corrections_data)

            last_values = (self.insp_errors_data[-20:] + self.insp_corrections_data[-20:])
            if last_values:
                min_y = max(0, min(last_values) // 5 * 5)
                max_y = (int(max(last_values) / 5) + 1) * 5
            else:
                min_y, max_y = 0, 10
            self.insp_ax.set_ylim(min_y, max_y)
            self.insp_ax.yaxis.set_major_locator(MultipleLocator(5))

            min_x = max(0, elapsed - 30)
            self.insp_ax.set_xlim(min_x, min_x + 30)
            self.insp_ax.xaxis.set_major_locator(MultipleLocator(10))

            self.insp_canvas.draw()

        # --- Inspection ---
        self.insp_total = metrics.get("insp_total", self.insp_total)
        self.insp_errors = metrics.get("insp_errors", self.insp_errors)
        self.insp_corrections = metrics.get("insp_corrections", self.insp_corrections)
        self.insp_error_rate = metrics.get("insp_error_rate", self.insp_error_rate)
        self.insp_correction_rate = metrics.get("insp_correction_rate", self.insp_correction_rate)

        self.insp_total_label.setText(f"Total Inspected: {self.insp_total}")
        self.insp_errors_label.setText(f"Total Errors: {self.insp_errors}")
        self.insp_error_rate_label.setText(f"Robot Error Rate: {self.insp_error_rate:.1f}%")
        self.insp_correction_rate_label.setText(f"User Correction Rate: {self.insp_correction_rate:.1f}%")

        if "insp_errors" in metrics or "insp_corrections" in metrics:
            if self.insp_start_time is None:
                self.insp_start_time = current_time

            elapsed = current_time - self.insp_start_time
            self.insp_times.append(elapsed)
            self.insp_errors_data.append(self.insp_errors)
            self.insp_corrections_data.append(self.insp_corrections)

            while self.insp_times and (elapsed - self.insp_times[0] > 30):
                self.insp_times.pop(0)
                self.insp_errors_data.pop(0)
                self.insp_corrections_data.pop(0)

            self.insp_error_line.set_data(self.insp_times, self.insp_errors_data)
            self.insp_corrections_line.set_data(self.insp_times, self.insp_corrections_data)

            max_y = max(self.insp_errors_data + self.insp_corrections_data + [10]) + 5
            self.insp_ax.set_ylim(0, max_y)
            self.insp_ax.yaxis.set_major_locator(MultipleLocator(5))

            min_x = max(0, elapsed - 30)
            self.insp_ax.set_xlim(min_x, min_x + 30)
            self.insp_ax.xaxis.set_major_locator(MultipleLocator(10))

            self.insp_canvas.draw()

    def reset_metrics(self):
        """Reset all metrics to zero and update labels"""
        current_time = time.time()

        # --- Sorting ---
        self.sort_total = 0
        self.sort_errors = 0
        self.sort_corrections = 0
        self.sort_error_rate = 0.0
        self.sort_correction_rate = 0.0

        self.sort_total_label.setText("Total Sorted: 0")
        self.sort_errors_label.setText("Total Errors: 0")
        self.sort_error_rate_label.setText("Robot Error Rate: 0.0%")
        self.sort_correction_rate_label.setText("User Correction Rate: 0.0%")

        self.sort_errors_data = []
        self.sort_corrections_data = []
        self.sort_times = []
        self.sort_start_time = None
        self.sort_error_line.set_data([], [])
        self.sort_corrections_line.set_data([], [])
        self.sort_ax.set_ylim(0, 10)
        self.sort_ax.set_xlim(0, 30)
        self.sort_ax.yaxis.set_major_locator(MultipleLocator(5))
        self.sort_ax.xaxis.set_major_locator(MultipleLocator(10))
        self.sort_canvas.draw()

        # --- Packaging ---
        self.pack_total = 0
        self.pack_errors = 0
        self.pack_corrections = 0
        self.pack_error_rate = 0.0
        self.pack_correction_rate = 0.0

        self.pack_total_label.setText("Total Packed: 0")
        self.pack_errors_label.setText("Total Errors: 0")
        self.pack_error_rate_label.setText("Robot Error Rate: 0.0%")
        self.pack_correction_rate_label.setText("User Correction Rate: 0.0%")

        self.pack_errors_data = []
        self.pack_corrections_data = []
        self.pack_times = []
        self.pack_start_time = None
        self.pack_error_line.set_data([], [])
        self.pack_corrections_line.set_data([], [])
        self.pack_ax.set_ylim(0, 10)
        self.pack_ax.set_xlim(0, 30)
        self.pack_ax.yaxis.set_major_locator(MultipleLocator(5))
        self.pack_ax.xaxis.set_major_locator(MultipleLocator(10))
        self.pack_canvas.draw()

        # --- Inspection ---
        self.insp_total = 0
        self.insp_errors = 0
        self.insp_corrections = 0
        self.insp_error_rate = 0.0
        self.insp_correction_rate = 0.0

        self.insp_total_label.setText("Total Inspected: 0")
        self.insp_errors_label.setText("Total Errors: 0")
        self.insp_error_rate_label.setText("Robot Error Rate: 0.0%")
        self.insp_correction_rate_label.setText("User Correction Rate: 0.0%")

        self.insp_errors_data = []
        self.insp_corrections_data = []
        self.insp_times = []
        self.insp_start_time = None
        self.insp_error_line.set_data([], [])
        self.insp_corrections_line.set_data([], [])
        self.insp_ax.set_ylim(0, 10)
        self.insp_ax.set_xlim(0, 30)
        self.insp_ax.yaxis.set_major_locator(MultipleLocator(5))
        self.insp_ax.xaxis.set_major_locator(MultipleLocator(10))
        self.insp_canvas.draw()
