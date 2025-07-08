# 🌡️ Temperaturlogger (Python GUI)

Ein grafisches Tool zur Temperaturerfassung über einen Arduino (mit MAX31865-Sensor) per USB, basierend auf PyQt5 und Matplotlib.

## 📦 Voraussetzungen

### Python-Pakete
Installiere die benötigten Abhängigkeiten mit:
```bash
pip install pyqt5 pyserial matplotlib
```

## 🚀 Verwendung

1. **Arduino vorbereiten**: Stelle sicher, dass das Arduino-Skript (`main.cpp`) auf dem Board installiert ist und Temperaturdaten via Serial bereitstellt.
2. **Script starten**:
```bash
python Temperaturlogger.py
```
3. **In der GUI**:
   - USB-Port auswählen
   - Auf „Verbinden“ klicken
   - Intervall festlegen (z. B. 1 Sekunde)
   - „Messung starten“ drücken
   - Temperaturverlauf wird aufgezeichnet und geplottet

## 📁 CSV-Dateiformat

Jede Messung wird automatisch als `.csv` gespeichert:

```csv
# Datum: YYYY-MM-DD; Uhrzeit: HH:MM:SS
# Uhrzeit (HH:MM:SS), t (min), T (°C), Markierung
14:30:01, 0.0000, 25.300,
14:30:03, 0.0333, 25.500, Start
```

## ⌨️ Tastenkürzel

- `M`: aktuelle Messung manuell markieren (wird im Plot und CSV hervorgehoben)

## 🧪 Testgeräte

- Arduino Uno / Nano
- MAX31865 mit PT1000-Fühler
- OLED-Anzeige (z. B. SSD1306)

## 👨‍💻 Autoren

- Julius Zimmermann
- Ludwig Gabler
- Ergänzt durch ChatGPT (Dokumentation & Kommentare)

---
Lizenz: MIT – Nutzung frei mit Namensnennung