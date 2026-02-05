from database import Database
db = Database()
rows = db.get_all_delays()[:5]
with open("verification.txt", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(f"Line: {r['line']}, Station: {r['station']}, Scheduled: {r['scheduled_time']}, Direction: '{r['direction']}', Delay: {r['delay_minutes']}\n")
db.close()
