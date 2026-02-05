"""
S-Bahn Verspätung Prediction System
Main CLI Interface

Usage:
    python main.py add "S4 +5 09:30"     # Manuelle Eingabe
    python main.py fetch                  # API Daten holen
    python main.py train                  # Model trainieren
    python main.py predict "S4 09:30"    # Verspätung vorhersagen
    python main.py stats                  # Statistiken anzeigen
    python main.py plot                   # Diagramme anzeigen
"""
import sys
import time
from datetime import datetime

from database import Database, LINES, STATIONS
from data_collector import add_manual_entry, fetch_and_store, parse_input
from model import load_model
from train import train_model


def cmd_add(args: list):
    """Add manual delay entry"""
    if not args:
        print("Usage: python main.py add \"S4 +5 09:30\"")
        return
    
    text = " ".join(args)
    result = add_manual_entry(text)
    
    if result["success"]:
        data = result["data"]
        direction_str = f" Richtung {data['direction']}" if data.get('direction') else ""
        print(f"[OK] Gespeichert: {data['line']} um {data['hour']:02d}:{data['minute']:02d}{direction_str} "
              f"@ {data['station']}, Verspaetung: {data['delay_minutes']:+d} min")
    else:
        print(f"[FEHLER] {result['error']}")


def cmd_fetch():
    """Fetch data from API"""
    print("Hole Daten von der DB API...")
    count = fetch_and_store()
    print(f"[OK] {count} Eintraege gespeichert")


def cmd_monitor(args: list):
    """Run fetch in a loop"""
    interval = 60
    if args and args[0].isdigit():
        interval = int(args[0])
    
    print(f"Starte Monitor (Intervall: {interval}s)")
    print("Druecke Ctrl+C zum Beenden...")
    
    try:
        while True:
            cmd_fetch()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitor beendet.")


def cmd_train():
    """Train the model"""
    print("Starte Training...")
    model = train_model(epochs=100, verbose=True)
    if model:
        print("[OK] Model trainiert und gespeichert")
    else:
        print("[FEHLER] Training fehlgeschlagen (zu wenig Daten?)")


def cmd_predict(args: list):
    """Predict delay"""
    if not args:
        print("Usage: python main.py predict \"S4 09:30\"")
        return
    
    text = " ".join(args)
    parsed = parse_input(text)
    
    if not parsed["line"]:
        print("Keine Linie erkannt (S4 oder S20)")
        return
    if parsed["hour"] is None:
        print("Keine Zeit erkannt (z.B. 09:30)")
        return
    
    # Default values
    station = parsed["station"] or STATIONS[0]
    weekday = datetime.now().weekday()
    
    print(f"Info: Using station '{station}' for prediction...")
    
    model = load_model()
    # Check if model has any gradient or if it's purely random (rudimentary check)
    # Since we can't easily check 'trained-ness' without metadata, we just proceed.
    
    predicted = model.predict(
        line=parsed["line"],
        station=station,
        weekday=weekday,
        hour=parsed["hour"],
        minute=parsed["minute"]
    )
    
    weekday_names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    
    print(f"\n=== Vorhersage fuer {parsed['line']} um {parsed['hour']:02d}:{parsed['minute']:02d} ===")
    print(f"    Station: {station}")
    print(f"    Tag: {weekday_names[weekday]}")
    print(f"    -> Erwartete Verspaetung: {predicted:+.1f} Minuten")


def cmd_stats():
    """Show statistics"""
    db = Database()
    count = db.count()
    data = db.get_all_delays()
    db.close()
    
    print(f"\n=== Statistiken ===")
    print(f"   Gesamt Einträge: {count}")
    
    if data:
        delays = [d["delay_minutes"] for d in data]
        avg_delay = sum(delays) / len(delays)
        max_delay = max(delays)
        
        # Nach Linie
        by_line = {}
        for d in data:
            line = d["line"]
            if line not in by_line:
                by_line[line] = []
            by_line[line].append(d["delay_minutes"])
        
        print(f"    Durchschnitt: {avg_delay:.1f} min")
        print(f"    Maximum: {max_delay} min")
        print(f"\n    Nach Linie:")
        for line, delays in by_line.items():
            avg = sum(delays) / len(delays)
            print(f"      {line}: {len(delays)} Eintraege, Avg {avg:.1f} min")
    
    print(f"\n    Letzte 5 Eintraege:")
    for d in data[:5]:
        direction_str = f" ({d['direction']})" if d.get('direction') else ""
        print(f"      {d['line']} {d['scheduled_time']} @ {d['station']}{direction_str}: "
              f"{d['delay_minutes']:+d} min ({d['source']})")


def cmd_plot():
    """Show delay plots"""
    from visualizer import plot_delays
    plot_delays()


def cmd_help():
    """Show help"""
    print(__doc__)
    print(f"\nLinien: {', '.join(LINES)}")
    print(f"Stationen: {', '.join(STATIONS)}")


def main():
    if len(sys.argv) < 2:
        cmd_help()
        return
    
    command = sys.argv[1].lower()
    args = sys.argv[2:]
    
    commands = {
        "add": lambda: cmd_add(args),
        "fetch": cmd_fetch,
        "monitor": lambda: cmd_monitor(args),
        "train": cmd_train,
        "predict": lambda: cmd_predict(args),
        "stats": cmd_stats,
        "plot": cmd_plot,
        "help": cmd_help,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"Unbekannter Befehl: {command}")
        cmd_help()


if __name__ == "__main__":
    main()
