# 📘 Visuelle Dokumentation – Temperaturlogger.py

Diese Dokumentation beschreibt die wichtigsten Komponenten, Abläufe und das Zusammenspiel im Python-Skript `Temperaturlogger.py`, das eine grafische Benutzeroberfläche (GUI) zur Temperaturüberwachung bietet.

---

## 🔧 Hauptfunktionen

| Funktion | Beschreibung |
|----------|--------------|
| `update_ports()` | Listet verfügbare serielle USB-Ports auf. |
| `connect_device()` | Baut die Verbindung zum Mikrocontroller auf. |
| `read_device_info()` | Liest Firmware-, Seriennummer- und Sensortyp-Infos aus. |
| `start()` | Startet die Temperaturmessung und erzeugt die CSV-Datei. |
| `getnewdata()` | Holt jede Sekunde einen Temperaturwert vom Gerät. |
| `update_plot()` | Zeichnet die Temperaturkurve inklusive Min/Max-Linien. |
| `mark_current_point()` | Setzt Markierungen im Plot und CSV. |
| `stop()` | Beendet die Messung. |

---

## 🧱 GUI-Komponenten (PyQt5)

````plaintext
MainWindow
|-- QComboBox (Port-Auswahl)
|-- QPushButton (Verbinden / Trennen)
|-- QLCDNumber (Temperaturanzeige)
|-- QDoubleSpinBox (Messintervall)
|-- QPushButton (Start / Stopp)
|-- QLabel (Geräteinfo)
|-- Matplotlib Canvas (Plot)
|-- NavigationToolbar
````

---
## 🔄 Datenfluss

````plaintext
User klickt „Start“
    ↓
→ Verbindung prüfen
    ↓
→ CSV-Datei anlegen
    ↓
→ Timer starten (z. B. alle 1 Sekunde)
    ↓
→ Gerät via seriellem Port nach Temperatur fragen
    ↓
→ Antwort empfangen & als Float interpretieren
    ↓
→ Wert anzeigen (LCD) + in CSV speichern
    ↓
→ Plot aktualisieren
````

---
## 📂 Dateiaufbau (CSV)

```csv
# Datum: 2025-07-08; Uhrzeit: 14:30:00
# Uhrzeit (HH:MM:SS), t (min), T (°C), Markierung
14:30:01, 0.0000, 25.300,
14:30:02, 0.0167, 25.400,
14:30:03, 0.0333, 25.500, Start
```

---
## 🧠 Hinweise für Entwickler

- Gerät muss bei Start korrekt verbunden sein.
- Bei Änderung des Intervalls während Messung: Timer wird angepasst.
- Fehler (kein Port, falsche Werte, etc.) werden mit QMessageBox angezeigt.
- Markierungen lassen sich manuell setzen und werden persistent in der CSV gespeichert.

---
© Julius Zimmermann & Ludwig Gabler – erweitert mit Kommentaren und Visualisierung durch ChatGPT