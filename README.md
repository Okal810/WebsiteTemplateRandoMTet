# Delay Prediction AI for S Bahn Munich.

## Usage

### 1. Daten sammeln
Manuelle Eingabe einer Verspätung (Zeitplangemäße Ankunft, System erkennt Richtung automatisch):
```bash
python main.py add "S4 +5 09:30"
```

Daten von der MVG API abrufen:
```bash
python main.py fetch
```

Oder automatisch alle 60 Sekunden abrufen (Monitor-Modus):
```bash
python main.py monitor
```
(Optional: Intervall in Sekunden angeben, z.B. `python main.py monitor 120`)

### 2. Modell trainieren
Trainiert das Vorhersagemodell mit den gesammelten Daten:
```bash
python main.py train
```

### 3. Vorhersagen
Verspätung für eine bestimmte Linie und Zeit vorhersagen:
```bash
python main.py predict "S4 09:30"
```

### 4. Analyse
Statistiken anzeigen (Durchschnittliche Verspätung, letzte Einträge):
```bash
python main.py stats
```

Diagramme generieren (benötigt `matplotlib`):
```bash
python main.py plot
```

### Hilfe
Alle Befehle anzeigen:
```bash
python main.py help
```
