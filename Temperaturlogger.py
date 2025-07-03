#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 13:11:17 2025

@author: Julius Zimmermann & Ludwig Gabler
"""

import sys
import time
import csv
from datetime import timedelta, datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QPushButton, QLCDNumber, QStyle, QFileDialog,
    QComboBox, QLabel, QMessageBox, QDoubleSpinBox
)
from PyQt5 import QtCore
import serial
import serial.tools.list_ports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.set_xlabel("t in min")
        self.axes.set_ylabel("T in °C")
        super().__init__(fig)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Temperaturlogger")
        self.setStyleSheet("QPushButton { padding: 6px; font-size: 14px; } QLabel { font-weight: bold; }")

        self.ser = None
        self.fileName = None
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.getnewdata)

        layout = QGridLayout()

        # Port-Auswahl
        self.cb_ports = QComboBox()
        self.update_ports()
        layout.addWidget(QLabel("USB-Port auswählen:"), 0, 0, 1, 2)
        layout.addWidget(self.cb_ports, 1, 0, 1, 2)

        self.bt_refresh_ports = QPushButton("Ports aktualisieren")
        self.bt_refresh_ports.clicked.connect(self.update_ports)
        layout.addWidget(self.bt_refresh_ports, 2, 0, 1, 2)

        # Intervall-Einstellung
        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0.1, 60.0)  # Min: 100 ms, Max: 60 s
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setValue(1.0)
        self.spin_interval.setSuffix(" s")
        layout.addWidget(QLabel("Messintervall:"), 4, 0)
        layout.addWidget(self.spin_interval, 4, 1)
        self.spin_interval.valueChanged.connect(self.update_timer_interval)

        # Start-/Stop-Knöpfe
        self.bt_start = QPushButton("Messung starten")
        self.bt_start.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.bt_start.pressed.connect(self.start)
        layout.addWidget(self.bt_start, 5, 0, 1, 2)

        self.bt_stop = QPushButton("Messung stoppen")
        self.bt_stop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.bt_stop.setEnabled(False)
        self.bt_stop.pressed.connect(self.stop)
        layout.addWidget(self.bt_stop, 6, 0, 1, 2)

        # LCD-Anzeige
        self.lcd_T = QLCDNumber()
        self.lcd_T.setSegmentStyle(QLCDNumber.Flat)
        layout.addWidget(self.lcd_T, 3, 0, 1, 2)

        # Plot
        self.canvas = MplCanvas(self)
        layout.addWidget(self.canvas, 0, 3, 10, 4)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def update_ports(self):
        self.cb_ports.clear()
        ports = serial.tools.list_ports.comports()
        usb_ports = [p for p in ports if "USB" in p.description.upper() or "SERIAL" in p.description.upper()]
        for port in usb_ports:
            self.cb_ports.addItem(f"{port.device} - {port.description}", port.device)
        if not usb_ports:
            self.cb_ports.addItem("Keine USB-Ports gefunden", None)

    def saveFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        self.fileName, _ = QFileDialog.getSaveFileName(
            self,
            "Speichern",
            "",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
            "CSV-Dateien (*.csv)",
            options=options
        )
        if self.fileName:
            self.fileName = self.fileName.rstrip(".csv")

    def update_timer_interval(self):
        if self.timer.isActive():
            interval_ms = int(self.spin_interval.value() * 1000)
            self.timer.setInterval(interval_ms)
            print(f"Messintervall aktualisiert: {self.spin_interval.value():.2f} s")

    
    def start(self):
        selected_port = self.cb_ports.currentData()
        if not selected_port:
            QMessageBox.critical(self, "Fehler", "Bitte wähle einen gültigen USB-Port aus.")
            return

        try:
            self.ser = serial.Serial(selected_port, 115200, timeout=2)
        except serial.SerialException as e:
            QMessageBox.critical(self, "Verbindungsfehler", f"Serieller Port konnte nicht geöffnet werden:\n{e}")
            return

        self.saveFileDialog()
        if not self.fileName:
            QMessageBox.information(self, "Abgebrochen", "Keine Datei ausgewählt. Messung wird nicht gestartet.")
            self.ser.close()
            return

        self.t = []
        self.T = []
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        self.starttime = time.perf_counter()

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        try:
            with open(f"{self.fileName}.csv", "a") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow([f"# Datum: {current_date}; Uhrzeit: {current_time}"])
                writer.writerow(["# Uhrzeit (HH:MM:SS)", "t (min)", "T (°C)"])
        except Exception as e:
            QMessageBox.critical(self, "Dateifehler", f"Fehler beim Schreiben der CSV-Datei:\n{e}")
            self.ser.close()
            return

        self.canvas.axes.clear()
        self.canvas.axes.set_xlabel("t in min")
        self.canvas.axes.set_ylabel("T in °C")
        self.canvas.draw()

        interval_ms = int(self.spin_interval.value() * 1000)
        self.timer.setInterval(interval_ms)
        self.timer.start()
        self.bt_start.setEnabled(False)
        self.bt_stop.setEnabled(True)

    def getnewdata(self):
        try:
            self.ser.write(b"1\n")
            raw = self.ser.readline().decode("utf-8").strip()

            if not raw:
                print("Keine Antwort erhalten.")
                return

            Tval = float(raw)
            print(f"Messwert: {Tval}")

            duration = timedelta(seconds=time.perf_counter() - self.starttime)
            duration_in_min = round(duration.total_seconds(), 3) / 60

            self.t.append(duration_in_min)
            self.T.append(Tval)

            with open(f"{self.fileName}.csv", "a") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    f"{duration_in_min:.4f}",
                    Tval
                ])

            self.update_plot()
            self.lcd_T.display(Tval)

        except ValueError:
            print("Ungültiger Messwert empfangen.")
        except serial.SerialException as e:
            QMessageBox.critical(self, "Serieller Fehler", f"Fehler beim Lesen vom Gerät:\n{e}")
            self.stop()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Ein unerwarteter Fehler ist aufgetreten:\n{e}")
            self.stop()

    def update_plot(self):
        self.canvas.axes.plot(self.t, self.T, 'r')
        self.canvas.draw()

    def stop(self):
        self.timer.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.bt_start.setEnabled(True)
        self.bt_stop.setEnabled(False)

    def closeEvent(self, event):
        self.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
