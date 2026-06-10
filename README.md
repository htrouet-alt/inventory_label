# inventory_label

Inventory Labeling System für die Erstellung und den Druck von Inventar-Labels über ZPL-Templates.

## Überblick

Dieses Projekt stellt ein kleines GUI-Tool bereit, mit dem Seriennummern eingegeben und anschließend auf einen Netzwerkdrucker ausgegeben werden können. Die Labels werden über vorhandene ZPL-Dateien gesteuert, die im Ordner zpl/ liegen.

Die Anwendung ist für den Einsatz in einer Inventar- oder Hardware-Umgebung gedacht und unterstützt zusätzlich:

- Auswahl eines ZPL-Templates
- Eingabe einer Seriennummer
- Verbindung zu einem Netzwerkdrucker über IP und Port
- Protokollierung der gedruckten Labels in einer CSV-Datei
- Öffnen der Log-Datei direkt aus der Anwendung

## Voraussetzungen

- Python 3.9 oder höher
- Tkinter (in den meisten Python-Installationen bereits enthalten)
- Ein erreichbarer Zebra-/ZPL-fähiger Netzwerkdrucker

## Schnellstart

1. Konfiguration anpassen
   - Öffne die Datei config.conf im Projektstamm.
   - Trage die Druckeradresse und den Port ein, z. B.:
     - prnt_ip = "192.168.178.157"
     - prnt_port = 9100
     - url = "https://deine-inventar-url/"
     - log = true

2. Templates prüfen
   - Die ZPL-Dateien liegen im Ordner zpl/.
   - Für neue Label-Formate können dort zusätzliche .zpl-Dateien ergänzt werden.

3. Anwendung starten
   - Mit Python:
     python "src/inventory_label_src/Inventory Label.py"

4. Label drucken
   - Template auswählen
   - Seriennummer eingeben
   - Auf „Print“ klicken

## Projektstruktur

- src/inventory_label_src/  - Hauptanwendung und Quellcode
- zpl/                      - ZPL-Labelvorlagen
- config.conf               - Drucker- und URL-Konfiguration
- log.csv                   - Protokoll der Druckvorgänge

## Build als ausführbare Datei

Die Projektdatei src/inventory_label_src/Inventory Label.spec enthält die Konfiguration für PyInstaller.

Beispiel:

pyinstaller --onefile --windowed --icon="icon.ico" --clean "src/inventory_label_src/Inventory Label.py"

## Hinweise

- Die Anwendung nutzt die Datei config.conf für Drucker- und URL-Einstellungen.
- Wenn log = true gesetzt ist, werden alle Druckvorgänge in log.csv gespeichert.
- Die ZPL-Vorlagen bestimmen das Erscheinungsbild der Etiketten; sie können bei Bedarf angepasst werden.
