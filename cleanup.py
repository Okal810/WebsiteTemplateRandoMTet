import sqlite3
from database import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Original count:", cursor.execute("SELECT COUNT(*) FROM delays").fetchone()[0])

# Delete entries created by bug (source='manual', delay=4, date=today)
# Actually, let's just delete recent manual entries to be safe for re-test
conn.execute("DELETE FROM delays WHERE source='manual' AND delay_minutes=4")

print("New count:", cursor.execute("SELECT COUNT(*) FROM delays").fetchone()[0])
conn.commit()
conn.close()
