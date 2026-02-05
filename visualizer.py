"""
S-Bahn Visualization Module
Generates charts for delay statistics using matplotlib
"""
import matplotlib.pyplot as plt
import datetime
from database import Database

def plot_delays():
    """
    Generate and show delay statistics plots
    """
    db = Database()
    data = db.get_all_delays()
    db.close()
    
    if not data:
        print("Keine Daten vorhanden zum Plotten.")
        return

    # Prepare data
    hours = []
    delays = []
    lines = []
    cancelled_count = 0
    on_time_count = 0
    late_count = 0
    
    for d in data:
        lines.append(d['line'])
        
        # Cancellation stats
        if d.get('cancelled') == 1:
            cancelled_count += 1
            continue  # Skip cancelled for delay average calculation? Or treat as high delay?
            # Let's skip for average delay plot, but count for pie chart.
        
        hours.append(d['hour'])
        delays.append(d['delay_minutes'])
        
        if d['delay_minutes'] < 5:
            on_time_count += 1
        else:
            late_count += 1

    # --- Plot 1: Average Delay per Hour ---
    plt.figure(figsize=(15, 6))  # Wider figure for 3 plots
    
    # Calculate average delay per hour
    avg_delays = {}
    for h, d in zip(hours, delays):
        if h not in avg_delays:
            avg_delays[h] = []
        avg_delays[h].append(d)
    
    sorted_hours = sorted(avg_delays.keys())
    avg_values = [sum(avg_delays[h])/len(avg_delays[h]) for h in sorted_hours]
    
    plt.subplot(1, 3, 1)
    plt.plot(sorted_hours, avg_values, marker='o', linestyle='-', color='b')
    plt.title('Durchschnittliche Verspätung pro Stunde')
    plt.xlabel('Uhrzeit (Stunde)')
    plt.ylabel('Verspätung (Minuten)')
    plt.grid(True)
    if sorted_hours:
        plt.xticks(range(min(sorted_hours), max(sorted_hours) + 1))

    # --- Plot 2: Punctuality Pie Chart ---
    plt.subplot(1, 3, 2)
    labels = ['Pünktlich (<5min)', 'Verspätet (>=5min)', 'Ausgefallen']
    sizes = [on_time_count, late_count, cancelled_count]
    colors = ['#66b3ff', '#ff9999', '#999999']
    explode = (0.1, 0, 0)  # explode 1st slice

    # Filter out zero values to avoid messy chart
    final_labels = []
    final_sizes = []
    final_colors = []
    final_explode = []
    
    for i, size in enumerate(sizes):
        if size > 0:
            final_labels.append(labels[i])
            final_sizes.append(size)
            final_colors.append(colors[i])
            final_explode.append(explode[i])

    if final_sizes:
        plt.pie(final_sizes, explode=final_explode, labels=final_labels, colors=final_colors,
                autopct='%1.1f%%', shadow=True, startangle=140)
        plt.title('Pünktlichkeit')
    else:
        plt.text(0.5, 0.5, 'Keine Daten', ha='center')

    # --- Plot 3: Average Delay per Station ---
    plt.subplot(1, 3, 3)
    
    station_delays = {}
    for d in data:
        s = d['station']
        if s not in station_delays:
            station_delays[s] = []
        station_delays[s].append(d['delay_minutes'])
    
    stations = list(station_delays.keys())
    avg_station_delays = [sum(station_delays[s])/len(station_delays[s]) for s in stations]
    
    plt.bar(stations, avg_station_delays, color=['#4daf4a', '#377eb8', '#e41a1c', '#984ea3'][:len(stations)])
    plt.title('Durchschnitt pro Station')
    plt.ylabel('Minuten')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.5)

    plt.tight_layout()
    
    # Show plot
    print("Zeige Diagramme...")
    plt.show()

if __name__ == "__main__":
    plot_delays()
