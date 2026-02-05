import os
from flask import Flask, render_template, jsonify, request
from database import Database
from report_generator import ReportGenerator
import plotly.express as px
import plotly.utils
import json
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db():
    return Database()

@app.route('/')
def index():
    db = get_db()
    averages = db.get_weekday_averages()
    
    # Prepare data for weekday plot
    weekday_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    data = []
    for i in range(7):
        data.append({
            "Wochentag": weekday_names[i],
            "Durchschnittliche Verspätung": averages[i]["avg_delay"],
            "Anzahl Messungen": averages[i]["count"]
        })
    
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Wochentag", y="Durchschnittliche Verspätung", 
                 title="Durchschnittliche Verspätung nach Wochentag",
                 color="Durchschnittliche Verspätung",
                 color_continuous_scale="Viridis",
                 hover_data=["Anzahl Messungen"])
    
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Get recent reports
    gen = ReportGenerator(db)
    today = datetime.now().strftime("%Y-%m-%d")
    daily_report = gen.generate_daily_report(today)
    weekly_report = gen.generate_weekly_report()
    
    db.close()
    
    return render_template('index.html', 
                           graph_json=graph_json, 
                           daily_report=daily_report, 
                           weekly_report=weekly_report)

@app.route('/api/report/daily')
def daily_api():
    date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    db = get_db()
    gen = ReportGenerator(db)
    report = gen.generate_daily_report(date)
    db.close()
    return jsonify({"report": report})

if __name__ == '__main__':
    # Ensure templates folder exists
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, port=5000)
