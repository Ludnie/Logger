#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 13:11:17 2025

v0.2.0

@author: Julius Zimmermann & Ludwig Gabler
"""

import sys
import time
import csv
from datetime import timedelta, datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QPushButton, QLCDNumber, QStyle, QFileDialog,
    QComboBox, QLabel, QMessageBox, QDoubleSpinBox,
    QInputDialog
)
from PyQt5 import QtCore
import serial
import serial.tools.list_ports
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
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

        # Schon hier für Hover-Tooltip initialisieren
        self.t = []
        self.T = []

        self.marked_annotations ={}

        self.setWindowTitle("Temperaturlogger v0.2.0")
        self.setStyleSheet("QPushButton { padding: 6px; font-size: 14px; } QLabel { font-weight: bold; }")

        self.ser = None
        self.fileName = None
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.getnewdata)

        layout = QGridLayout()
        
        self.left_widget = QWidget()
        self.left_layout = QGridLayout(self.left_widget)

        # Port-Auswahl
        self.cb_ports = QComboBox()
        self.update_ports()
        self.left_layout.addWidget(QLabel("USB-Port auswählen:"), 0, 0, 1, 2)
        self.left_layout.addWidget(self.cb_ports, 1, 0, 1, 2)

        self.bt_refresh_ports = QPushButton("Ports aktualisieren")
        self.bt_refresh_ports.clicked.connect(self.update_ports)
        self.left_layout.addWidget(self.bt_refresh_ports, 2, 0, 1, 2)

        self.bt_connect = QPushButton("Verbinden")
        self.bt_connect.setIcon(self.style().standardIcon(QStyle.SP_CommandLink))
        self.bt_connect.clicked.connect(self.connect_device)
        self.left_layout.addWidget(self.bt_connect, 3, 0, 1, 2)

        self.bt_disconnect = QPushButton("Verbindung trennen")
        self.bt_disconnect.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.bt_disconnect.setEnabled(False)
        self.bt_disconnect.pressed.connect(self.disconnect_serial)
        self.left_layout.addWidget(self.bt_disconnect, 4, 0, 1, 2)

        # Info-Anzeige (Firmware, Seriennummer, Sensortyp)
        self.label_info_compact = QLabel("Firmware: - | SN: - | Sensor: -")
        self.left_layout.addWidget(self.label_info_compact, 5, 0, 1, 2)

        # LCD-Anzeige
        self.lcd_T = QLCDNumber()
        self.lcd_T.setSegmentStyle(QLCDNumber.Flat)
        self.left_layout.addWidget(self.lcd_T, 6, 0, 1, 2)

        # Intervall-Einstellung
        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0.1, 60.0)  # Min: 100 ms, Max: 60 s
        self.spin_interval.setSingleStep(0.1)
        self.spin_interval.setValue(1.0)
        self.spin_interval.setSuffix(" s")
        self.left_layout.addWidget(QLabel("Messintervall:"), 8, 0)
        self.left_layout.addWidget(self.spin_interval, 8, 1)
        self.spin_interval.valueChanged.connect(self.update_timer_interval)

        # Start-/Stop-Knöpfe
        self.bt_start = QPushButton("Messung starten")
        self.bt_start.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.bt_start.setEnabled(False) # erst aktivieren, wenn ein Gerät verbunden ist
        self.bt_start.pressed.connect(self.start)
        self.left_layout.addWidget(self.bt_start, 9, 0, 1, 2)

        self.bt_stop = QPushButton("Messung stoppen")
        self.bt_stop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.bt_stop.setEnabled(False)
        self.bt_stop.pressed.connect(self.stop)
        self.left_layout.addWidget(self.bt_stop, 10, 0, 1, 2)

        self.left_widget.setFixedWidth(300)

        main_layout = QGridLayout()
        main_layout.addWidget(self.left_widget, 0, 0)

        # Plot + Toolbar
        self.line = None
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout = QGridLayout()
        plot_layout.addWidget(self.toolbar, 0, 0)
        plot_layout.addWidget(self.canvas, 1, 0)

        # Tooltip für den Plot
        self.annot = self.canvas.axes.annotate(
            "", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->")
        )
        self.annot.set_visible(False)

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)


        plot_widget = QWidget()
        plot_widget.setLayout(plot_layout)
        main_layout.addWidget(plot_widget, 0, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()

        self.canvas.keyPressEvent = self.keyPressEvent

    def update_ports(self):
        self.cb_ports.clear()
        ports = serial.tools.list_ports.comports()
        usb_ports = [p for p in ports if "USB" in p.description.upper() or "SERIAL" in p.description.upper()]
        for port in usb_ports:
            self.cb_ports.addItem(f"{port.device} - {port.description}", port.device)
        if not usb_ports:
            self.cb_ports.addItem("Keine USB-Ports gefunden", None)

    def connect_device(self):
        selected_port = self.cb_ports.currentData()
        if not selected_port:
            QMessageBox.critical(self, "Fehler", "Bitte wähle einen gültigen USB-Port aus.")
            return

        try:
            self.ser = serial.Serial(selected_port, 115200, timeout=2)
            time.sleep(1.5)  # Warten wegen Reset
            self.read_device_info()
            self.bt_start.setEnabled(True)
            QMessageBox.information(self, "Verbunden", f"Verbindung zu {selected_port} erfolgreich.")
            self.bt_disconnect.setEnabled(True)
            self.bt_connect.setEnabled(False)
            self.bt_start.setEnabled(True)
        except serial.SerialException as e:
            QMessageBox.critical(self, "Verbindungsfehler", f"Serieller Port konnte nicht geöffnet werden:\n{e}")

    def disconnect_serial(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            QMessageBox.information(self, "Verbindung getrennt", "Die serielle Verbindung wurde getrennt.")
        self.bt_disconnect.setEnabled(False)
        self.bt_connect.setEnabled(True)
        self.bt_start.setEnabled(False)

    def read_device_info(self):
        fw = sn = st = "-"
        try:
            self.ser.write(b"i\n")
            time.sleep(0.5)
            info_lines = []
            while self.ser.in_waiting:
                line = self.ser.readline().decode("utf-8").strip()
                info_lines.append(line)

            for line in info_lines:
                if "Firmware" in line:
                    fw = line.split(":")[1].strip()
                elif "Seriennummer" in line:
                    sn = line.split(":")[1].strip()
                elif "Sensor-Typ" in line:
                    st = line.split(":")[1].strip()

        except Exception as e:
            print(f"Fehler beim Abrufen der Geräteinformationen: {e}")

        self.label_info_compact.setText(f"{fw} | {sn} | {st}")
        self.setWindowTitle(f"Temperaturlogger – {sn} | {fw} | {st}")


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
        if not self.ser or not self.ser.is_open:
            QMessageBox.critical(self, "Fehler", "Bitte stelle zuerst eine Verbindung her.")
            return

        self.saveFileDialog()
        if not self.fileName:
            QMessageBox.information(self, "Abgebrochen", "Keine Datei ausgewählt. Messung wird nicht gestartet.")
            self.ser.close()
            return

        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        self.starttime = time.perf_counter()

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        try:
            with open(f"{self.fileName}.csv", "a", newline='') as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow([f"# Datum: {current_date}; Uhrzeit: {current_time}"])
                writer.writerow(["# Uhrzeit (HH:MM:SS)", "t (min)", "T (°C)", "Markierung"])
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

        self.bt_disconnect.setEnabled(True)

    def getnewdata(self):
        try:
            self.ser.write(b"1\n")
            raw = self.ser.readline().decode("utf-8").strip()

            if not raw:
                print("Keine Antwort erhalten.")
                return

            Tval = float(raw)
            print(f"Messwert: {Tval:.3f}")

            duration = timedelta(seconds=time.perf_counter() - self.starttime)
            duration_in_min = round(duration.total_seconds(), 3) / 60

            self.t.append(duration_in_min)
            self.T.append(Tval)

            with open(f"{self.fileName}.csv", "a", newline='') as f:
                writer = csv.writer(f, delimiter=",")
                idx = len(self.t)
                mark = ""  # standardmäßig leer
                writer.writerow([
                    datetime.now().strftime("%H:%M:%S"),
                    f"{duration_in_min:.4f}",
                    f"{Tval:.3f}",
                    mark
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
        # Linie beim ersten Mal erstellen
        if self.line is None:
            self.line, = self.canvas.axes.plot([], [], 'r')
            self.canvas.axes.set_xlabel("t in min")
            self.canvas.axes.set_ylabel("T in °C")

        # Daten aktualisieren
        self.line.set_data(self.t, self.T)

        # Nur sichtbare Daten für Min/Max
        x_start, x_end = self.canvas.axes.get_xlim()
        visible_points = [(t, T) for t, T in zip(self.t, self.T) if x_start <= t <= x_end]
        if not visible_points:
            self.canvas.draw()
            return

        visible_t, visible_T = zip(*visible_points)
        min_T = min(visible_T)
        max_T = max(visible_T)
        xmin = min(visible_t)

        # Alte Min/Max-Linien entfernen (falls vorhanden)
        for line in getattr(self, "minmax_lines", []):
            line.remove()
        for text in getattr(self, "minmax_texts", []):
            text.remove()

        # Neue Linien + Texte zeichnen
        self.minmax_lines = [
            self.canvas.axes.axhline(min_T, color='blue', linestyle='--', linewidth=1),
            self.canvas.axes.axhline(max_T, color='green', linestyle='--', linewidth=1),
        ]
        self.minmax_texts = [
            self.canvas.axes.text(xmin, min_T, f"Min: {min_T:.2f} °C", color='blue',
                                va='bottom', ha='left', fontsize=8, backgroundcolor='white'),
            self.canvas.axes.text(xmin, max_T, f"Max: {max_T:.2f} °C", color='green',
                                va='top', ha='left', fontsize=8, backgroundcolor='white'),
        ]

        self.canvas.axes.relim()

        # Automatische Skalierung abhängig vom Toolbar-Modus
        if self.toolbar.mode == '':
            # Nichts aktiv: automatisch X- und Y-Achse anpassen
            self.canvas.axes.autoscale_view()
        else:
            # Zoom oder Pan aktiv: nur Y-Achse neu skalieren
            self.canvas.axes.autoscale_view(scalex=False)

        self.canvas.draw_idle()

    def on_hover(self, event):
        if not hasattr(self, "line") or self.line is None:
            return
        if event.inaxes != self.canvas.axes:
            self.annot.set_visible(False)
            self.canvas.draw_idle()
            return

        xdata = self.line.get_xdata()
        ydata = self.line.get_ydata()

        if len(xdata) == 0:
            return

        # Finde nächsten Punkt
        distances = [(event.xdata - x)**2 + (event.ydata - y)**2 for x, y in zip(xdata, ydata)]
        index = distances.index(min(distances))
        x, y = xdata[index], ydata[index]

        # Wenn Maus nah genug
        if abs(event.xdata - x) < 0.2 and abs(event.ydata - y) < 1.0:
            self.annot.xy = (x, y)
            self.annot.set_text(f"t: {x:.2f} min\nT: {y:.2f} °C")
            self.annot.set_visible(True)
            self.canvas.draw_idle()
        else:
            self.annot.set_visible(False)
            self.canvas.draw_idle()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_M:
            self.mark_current_point()
    
    def mark_current_point(self):
        if not self.t:
            return

        idx = len(self.t) - 1
        t_val = self.t[idx]

        # Dialog zur Eingabe eines Markierungsnamens
        text, ok = QInputDialog.getText(self, "Markierung setzen", "Markierungsname:")
        if not ok or not text.strip():
            return  # Abbruch oder leer

        self.marked_annotations[idx] = text.strip()

        # Vertikale Linie und Text zeichnen
        self.canvas.axes.axvline(t_val, color='orange', linestyle='--', linewidth=1)
        self.canvas.axes.text(t_val, max(self.T), text.strip(), rotation=90, color='orange',
                            va='top', ha='center', fontsize=8, backgroundcolor='white')

        self.canvas.draw_idle()

        self.append_marking_to_csv(idx, text.strip())

    def append_marking_to_csv(self, idx, name):
        # Versuch, zuletzt beschriebene Zeile zu ersetzen
        try:
            with open(f"{self.fileName}.csv", "r", newline='') as f:
                rows = list(csv.reader(f))

            # Finde Datenzeile (überspringe Kopfzeilen)
            data_lines = [i for i, row in enumerate(rows) if not row[0].startswith("#")]
            if idx < len(data_lines):
                data_idx = data_lines[idx]
                if len(rows[data_idx]) == 3:
                    rows[data_idx].append(name)
                else:
                    rows[data_idx][3] = name

                # Datei überschreiben
                with open(f"{self.fileName}.csv", "w", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
        except Exception as e:
            print(f"Fehler beim Aktualisieren der CSV-Datei: {e}")

    def stop(self):
        self.timer.stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.bt_start.setEnabled(True)
        self.bt_stop.setEnabled(False)
        self.bt_disconnect.setEnabled(False)
        self.bt_connect.setEnabled(True)

    def closeEvent(self, event):
        self.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
