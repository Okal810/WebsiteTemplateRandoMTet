p6"""
S-Bahn Report Generator
Formats database statistics into human-readable reports
"""
from database import Database
from datetime import datetime, timedelta

class ReportGenerator:
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def generate_daily_report(self, date_str: str = None) -> str:
        """Generate a text-based daily report"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        summary = self.db.get_daily_summary(date_str)
        if not summary:
            return f"Keine Daten für den {date_str} gefunden."
            
        report = [
            f"=== TAGESBERICHT: {date_str} ===",
            f"Gesamtanzahl Züge: {summary['total']}",
            f"Pünktlich (<5min): {summary['on_time']} ({round(summary['on_time']/summary['total']*100, 1)}%)",
            f"Verspätet (>=5min): {summary['late']} ({round(summary['late']/summary['total']*100, 1)}%)",
            f"Ausgefallen: {summary['cancelled']} ({round(summary['cancelled']/summary['total']*100, 1)}%)",
            f"Durchschnittliche Verspätung: {summary['avg_delay']} Minuten",
            "================================"
        ]
        return "\n".join(report)

    def generate_weekly_report(self, start_date: str = None) -> str:
        """Generate a text-based weekly report"""
        if not start_date:
            # Default to last 7 days
            start_date = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
            
        summaries = self.db.get_weekly_summary(start_date)
        if not summaries:
            return f"Keine Daten ab dem {start_date} gefunden."
            
        report = [f"=== WOCHENBERICHT ab {start_date} ==="]
        
        total_trains = 0
        total_delay = 0
        total_cancelled = 0
        days_with_data = 0
        
        for s in summaries:
            report.append(f"{s['date']}: {s['total']} Züge, Ø {round(s['avg_delay'], 1)}min Versp., {s['cancelled']} Ausfälle")
            total_trains += s['total']
            total_delay += s['avg_delay'] * s['total']
            total_cancelled += s['cancelled']
            days_with_data += 1
            
        if days_with_data > 0:
            avg_week_delay = round(total_delay / total_trains if total_trains > 0 else 0, 2)
            report.append("----------------------------")
            report.append(f"Gesamt Woche: {total_trains} Züge")
            report.append(f"Durchschnittliche Verspätung: {avg_week_delay} Minuten")
            report.append(f"Gesamt Ausfälle: {total_cancelled}")
            
        report.append("================================")
        return "\n".join(report)

    def get_weekday_summary_text(self) -> str:
        """Get text summary of weekday averages"""
        averages = self.db.get_weekday_averages()
        names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        
        report = ["=== WOCHENTAG DURCHSCHNITT ==="]
        for i in range(7):
            avg = averages[i]
            report.append(f"{names[i]}: {avg['avg_delay']} min ({avg['count']} Messungen)")
        report.append("==============================")
        return "\n".join(report)

if __name__ == "__main__":
    gen = ReportGenerator()
    print(gen.get_weekday_summary_text())
    print("\n")
    # Use actual current date to test
    today = datetime.now().strftime("%Y-%m-%d")
    print(gen.generate_daily_report(today))
