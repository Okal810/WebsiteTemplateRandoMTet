"""
S-Bahn Verspätung Database Module
SQLite database for storing delay data
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "sbahn_delays.db"

# Vordefinierte Linien und Stationen
LINES = ["S4", "S20"]
STATIONS = [
    "Buchenau", 
    "Fürstenfeldbruck", 
    "Eichenau", 
    "Puchheim", 
    "Aubing", 
    "Pasing", 
    "Grafrath", 
    "Türkenfeld", 
    "Geltendorf"
]


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS delays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line TEXT NOT NULL,
                station TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                delay_minutes INTEGER NOT NULL,
                cancelled INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                weekday INTEGER NOT NULL,
                date TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Schema Migration: Add cancelled column if not exists
        try:
            self.conn.execute("SELECT cancelled FROM delays LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating Database: adding 'cancelled' column...")
            self.conn.execute("ALTER TABLE delays ADD COLUMN cancelled INTEGER DEFAULT 0")

        # Schema Migration: Add date column if not exists
        try:
            self.conn.execute("SELECT date FROM delays LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating Database: adding 'date' column...")
            self.conn.execute("ALTER TABLE delays ADD COLUMN date TEXT DEFAULT ''")
            # Update existing records with today's date (fallback)
            today = datetime.now().strftime("%Y-%m-%d")
            self.conn.execute("UPDATE delays SET date = ? WHERE date = ''", (today,))
        
        # Schema Migration: Add direction column if not exists
        try:
            self.conn.execute("SELECT direction FROM delays LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating Database: adding 'direction' column...")
            self.conn.execute("ALTER TABLE delays ADD COLUMN direction TEXT DEFAULT ''")
        
        # Unique Index for Upsert logic
        # We don't enforce strict unique constraint on DB level to allow manual fixes, 
        # but we use it for lookups using the index
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_unique_train_v2 
            ON delays(line, station, scheduled_time, date, direction)
        """)
        self.conn.commit()

    def add_delay(self, line: str, station: str, scheduled_time: str, 
                  delay_minutes: int, source: str = "manual", cancelled: bool = False,
                  direction: str = "") -> int:
        """
        Add or Update a delay record (Upsert)
        """
        # Ensure delay_minutes is not None
        if delay_minutes is None:
            delay_minutes = 0
        if isinstance(scheduled_time, datetime):
            hour = scheduled_time.hour
            minute = scheduled_time.minute
            weekday = scheduled_time.weekday()
            scheduled_str = scheduled_time.strftime("%H:%M")
            date_str = scheduled_time.strftime("%Y-%m-%d")
        else:
            try:
                parts = scheduled_time.split(":")
                hour = int(parts[0])
                minute = int(parts[1])
            except:
                hour = 0
                minute = 0
            now = datetime.now()
            weekday = now.weekday()
            date_str = now.strftime("%Y-%m-%d")
            scheduled_str = scheduled_time
        
        # Check if exists (including direction if provided)
        # Note: If direction was empty before, we might want to update it.
        # But to keep it simple, we match exactly.
        if direction:
             cursor = self.conn.execute("""
                SELECT id, delay_minutes, cancelled, direction FROM delays 
                WHERE line=? AND station=? AND scheduled_time=? AND date=? AND direction=?
            """, (line.upper(), station, scheduled_str, date_str, direction))
        else:
            # Fallback/Legacy: match without direction if direction not provided
            cursor = self.conn.execute("""
                SELECT id, delay_minutes, cancelled, direction FROM delays 
                WHERE line=? AND station=? AND scheduled_time=? AND date=?
            """, (line.upper(), station, scheduled_str, date_str))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update if changed
            # Also update direction if it was empty
            needs_update = (
                existing['delay_minutes'] != delay_minutes or 
                existing['cancelled'] != (1 if cancelled else 0) or
                (direction and existing['direction'] != direction)
            )
            
            if needs_update:
                print(f"Update: {line} {scheduled_str} ({existing['delay_minutes']} -> {delay_minutes} min)")
                self.conn.execute("""
                    UPDATE delays 
                    SET delay_minutes=?, cancelled=?, source=?, created_at=CURRENT_TIMESTAMP, direction=?
                    WHERE id=?
                """, (delay_minutes, 1 if cancelled else 0, source, direction, existing['id']))
                self.conn.commit()
                return existing['id']
            else:
                return existing['id']
        else:
            # Insert New
            cursor = self.conn.execute("""
                INSERT INTO delays (line, station, scheduled_time, delay_minutes, cancelled,
                                  source, weekday, date, hour, minute, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (line.upper(), station, scheduled_str, delay_minutes, 1 if cancelled else 0,
                  source, weekday, date_str, hour, minute, direction))
            
            self.conn.commit()
            return cursor.lastrowid

    def get_all_delays(self) -> list:
        """Get all delay records"""
        cursor = self.conn.execute("""
            SELECT * FROM delays ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_training_data(self) -> list:
        """Get data formatted for neural network training"""
        cursor = self.conn.execute("""
            SELECT line, station, weekday, hour, minute, delay_minutes
            FROM delays
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_weekday_averages(self) -> dict:
        """Get average delay per weekday"""
        # Weekdays: 0=Mon, 1=Tue, ..., 6=Sun
        cursor = self.conn.execute("""
            SELECT weekday, AVG(delay_minutes) as avg_delay, COUNT(*) as count
            FROM delays
            WHERE cancelled = 0
            GROUP BY weekday
            ORDER BY weekday
        """)
        results = {i: {"avg_delay": 0.0, "count": 0} for i in range(7)}
        for row in cursor.fetchall():
            results[row['weekday']] = {
                "avg_delay": round(row['avg_delay'], 2),
                "count": row['count']
            }
        return results

    def get_daily_summary(self, date_str: str) -> dict:
        """Get statistics for a specific day"""
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN delay_minutes < 5 AND cancelled = 0 THEN 1 ELSE 0 END) as on_time,
                SUM(CASE WHEN delay_minutes >= 5 AND cancelled = 0 THEN 1 ELSE 0 END) as late,
                SUM(cancelled) as cancelled,
                AVG(CASE WHEN cancelled = 0 THEN delay_minutes ELSE NULL END) as avg_delay
            FROM delays
            WHERE date = ?
        """, (date_str,))
        row = cursor.fetchone()
        if not row or row['total'] == 0:
            return None
        
        return {
            "date": date_str,
            "total": row['total'],
            "on_time": row['on_time'],
            "late": row['late'],
            "cancelled": row['cancelled'],
            "avg_delay": round(row['avg_delay'] or 0, 2)
        }

    def get_weekly_summary(self, start_date: str) -> list:
        """Get statistics for a week starting from start_date"""
        # This is a bit simplified, but gets the daily summaries for 7 days
        cursor = self.conn.execute("""
            SELECT 
                date,
                COUNT(*) as total,
                AVG(CASE WHEN cancelled = 0 THEN delay_minutes ELSE NULL END) as avg_delay,
                SUM(cancelled) as cancelled
            FROM delays
            WHERE date >= ?
            GROUP BY date
            ORDER BY date
            LIMIT 7
        """, (start_date,))
        return [dict(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Get total number of records"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM delays")
        return cursor.fetchone()[0]

    def close(self):
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    # Test
    db = Database()
    print(f"Database initialized at {DB_PATH}")
    print(f"Total records: {db.count()}")
    db.close()
