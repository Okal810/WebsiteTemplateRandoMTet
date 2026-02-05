"""
S-Bahn Data Collector Module
Manuelle Eingabe + API Integration
"""
import re
import requests
from datetime import datetime
from database import Database, LINES, STATIONS

# API endpoint für Deutsche Bahn
DB_API_BASE = "https://v6.db.transport.rest"

# Station IDs für die API (HAFAS IDs)
STATION_IDS = {
    "Buchenau": "8001156",
    "Fürstenfeldbruck": "8002073"
}

# Statischer Fahrplan (Minuten der Abfahrt)
SCHEDULE = {
    "S4": {
        "Buchenau": {
            "München": [8, 28, 48],
            "Geltendorf": [11, 31, 51]
        },
        "Fürstenfeldbruck": {
            "München": [11, 31, 51],
            "Geltendorf": [7, 27, 47]
        }
    },
    "S20": {
         # S20 hat eingeschränkten Fahrplan, hier Platzhalter/Default
        "Buchenau": { "München": [], "Geltendorf": [] },
        "Fürstenfeldbruck": { "München": [], "Geltendorf": [] }
    }
}

def get_direction_from_schedule(line: str, station: str, minute: int) -> str:
    """Bestimme Richtung basierend auf Fahrplan-Minute"""
    if line not in SCHEDULE or station not in SCHEDULE[line]:
        return ""
    
    sched = SCHEDULE[line][station]
    
    if minute in sched["München"]:
        return "München"
    if minute in sched["Geltendorf"]:
        return "Geltendorf"
    return ""  # Keine genaue Übereinstimmung


def parse_input(text: str) -> dict:
    """
    Parse user input to extract delay information
    
    Supported formats:
    - "S4 +5 09:30"
    - "S20 Buchenau +3 10:15"
    - "s4 buchenau 5min 09:00"
    - "+2 S4 09:45"
    
    Returns:
        dict with keys: line, station, delay_minutes, hour, minute, direction
    """
    text = text.strip().upper()
    result = {
        "line": None,
        "station": None,
        "delay_minutes": 0,
        "hour": None,
        "minute": None,
        "direction": ""
    }
    
    # Finde Linie (S4, S20)
    for line in LINES:
        if line.upper() in text:
            result["line"] = line
            break
    
    # Finde Station
    for station in STATIONS:
        if station.upper() in text:
            result["station"] = station
            break
    
    # Finde Verspätung (+5, -3, 5min, 5 min)
    # Regex: Look for number that is EITHER:
    # 1. preceded by + or - (e.g. +5, -2)
    # 2. followed by 'min' (e.g. 5min)
    # 3. separate word (e.g. S4 5 09:30 -> 5) - risk of confusion with time
    # Safer: require +/- OR 'min' OR position check?
    # Let's use: (?:^|\s)([+\-]\d+|\d+\s*min)(?:\s|$)
    delay_match = re.search(r'(?:^|\s)([+\-]\d+|\d+\s*min)(?:\s|$)', text)
    
    if delay_match:
        delay_str = delay_match.group(1)
        delay_val = int(re.search(r'\d+', delay_str).group())
        if '-' in delay_str:
            delay_val = -delay_val
        result["delay_minutes"] = delay_val
    else:
        # Fallback: check for standalone number if it's clearly not time or line
        # Simple parsing is tricky. Let's rely on explicit +/- or min for now to avoid S4/S20 confusion.
        pass
    
    # Finde Zeit (09:30, 9:30)
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        result["hour"] = int(time_match.group(1))
        result["minute"] = int(time_match.group(2))
        
        # Versuche Richtung zu bestimmen wenn alles da ist
        if result["line"] and result["station"]:
            result["direction"] = get_direction_from_schedule(
                result["line"], result["station"], result["minute"]
            )
    
    return result


def add_manual_entry(text: str, db: Database = None) -> dict:
    """
    Add a manual delay entry from parsed text
    
    Returns:
        dict with parsed data and success status
    """
    parsed = parse_input(text)
    
    # Validierung
    if not parsed["line"]:
        return {"success": False, "error": "Keine Linie erkannt (S4 oder S20)"}
    if parsed["hour"] is None:
        return {"success": False, "error": "Keine Zeit erkannt (z.B. 09:30)"}
    
    # Default Station wenn nicht angegeben
    if not parsed["station"]:
        parsed["station"] = STATIONS[0]  # Default: Buchenau
        
        # Erneuter Versuch Richtung zu bestimmen nun mit Station
        if not parsed["direction"]:
            parsed["direction"] = get_direction_from_schedule(
                parsed["line"], parsed["station"], parsed["minute"]
            )
    
    # In DB speichern
    if db is None:
        db = Database()
        close_db = True
    else:
        close_db = False
    
    scheduled_time = f"{parsed['hour']:02d}:{parsed['minute']:02d}"
    record_id = db.add_delay(
        line=parsed["line"],
        station=parsed["station"],
        scheduled_time=scheduled_time,
        delay_minutes=parsed["delay_minutes"],
        source="manual",
        direction=parsed["direction"]
    )
    
    if close_db:
        db.close()
    
    return {
        "success": True,
        "id": record_id,
        "data": parsed
    }


from mvg import MvgApi

def fetch_from_api(station: str = None) -> list:
    """
    Fetch current departures and delays from MVG API
    
    Args:
        station: Station name or None for all stations
    
    Returns:
        list of delay records
    """
    stations_to_fetch = [station] if station else STATIONS
    results = []
    
    for station_name in stations_to_fetch:
        try:
            # 1. Station ID finden
            station_obj = MvgApi.station(station_name)
            if not station_obj:
                print(f"Station nicht gefunden: {station_name}")
                continue
            
            s_id = station_obj['id']
            
            # 2. Abfahrten holen
            api = MvgApi(s_id)
            departures = api.departures()
            
            for dep in departures:
                # Filter: Nur S-Bahn (Type 'S-Bahn' oder Line starts with S)
                if dep.get('type') != 'S-Bahn' and not dep.get('line', '').startswith('S'):
                    continue
                
                line_name = dep.get('line', '')
                
                # Nur S4 und S20 (oder alle S-Bahnen wenn gewuenscht, aber wir filtern hier strikt wie vorher)
                if line_name not in LINES:
                    continue
                
                # Verspaetung
                delay_minutes = dep.get('delay', 0) or 0
                cancelled = dep.get('cancelled', False)
                dest = dep.get('destination', '')
                
                # Richtung bestimmen
                direction = ""
                if "München" in dest or "Ostbahnhof" in dest or "Ebersberg" in dest or "Trudering" in dest:
                    direction = "München"
                elif "Geltendorf" in dest or "Grafrath" in dest:
                    direction = "Geltendorf"
                
                
                # Fahrplanzeit (planned is unix timestamp)
                planned_ts = dep.get('planned')
                if planned_ts:
                    dt = datetime.fromtimestamp(planned_ts)
                    scheduled_time = dt.strftime("%H:%M")
                    minute = dt.minute
                else:
                    scheduled_time = "00:00"
                    minute = 0
                
                # Fallback direction from schedule if not clear from destination
                if not direction:
                    direction = get_direction_from_schedule(line_name, station_name, minute)

                results.append({
                    "line": line_name,
                    "station": station_name,
                    "scheduled_time": scheduled_time,
                    "delay_minutes": delay_minutes,
                    "cancelled": cancelled,
                    "source": "api",
                    "direction": direction
                })
                
        except Exception as e:
            print(f"API Error fuer {station_name}: {e}")
    
    return results


def fetch_and_store(db: Database = None) -> int:
    """
    Fetch from API and store in database
    
    Returns:
        Number of records added
    """
    if db is None:
        db = Database()
        close_db = True
    else:
        close_db = False
    
    delays = fetch_from_api()
    count = 0
    
    for delay in delays:
        db.add_delay(
            line=delay["line"],
            station=delay["station"],
            scheduled_time=delay["scheduled_time"],
            delay_minutes=delay["delay_minutes"],
            source="api",
            cancelled=delay.get("cancelled", False),
            direction=delay.get("direction", "")
        )
        count += 1
    
    if close_db:
        db.close()
    
    return count


if __name__ == "__main__":
    # Test parsing
    test_inputs = [
        "S4 +5 09:30",
        "S20 Buchenau +3 10:15",
        "s4 -2 08:00",
        "+7 S4 Fürstenfeldbruck 09:45",
        "S4 15:48"  # Should be München
    ]
    
    print("=== Parser Test ===")
    for inp in test_inputs:
        print(f"{inp} -> {parse_input(inp)}")
    
    # Test Direction
    print("\n=== Direction Test ===")
    print(f"S4 Buchenau 15:48 -> {get_direction_from_schedule('S4', 'Buchenau', 48)}")
    print(f"S4 Buchenau 15:51 -> {get_direction_from_schedule('S4', 'Buchenau', 51)}")
    print(f"S4 Buchenau 15:00 -> {get_direction_from_schedule('S4', 'Buchenau', 0)}")
    
    # print("\n=== API Test ===")
    # delays = fetch_from_api("Buchenau")
    # print(f"Gefunden: {len(delays)} Abfahrten")
    # for d in delays[:3]:
    #     print(f"  {d['line']} um {d['scheduled_time']} ({d['direction']}): +{d['delay_minutes']} min")
