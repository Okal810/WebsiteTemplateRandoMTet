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
    plt.figure(figsize=(12, 5))
    
    # Calculate average delay per hour
    avg_delays = {}
    for h, d in zip(hours, delays):
        if h not in avg_delays:
            avg_delays[h] = []
        avg_delays[h].append(d)
    
    sorted_hours = sorted(avg_delays.keys())
    avg_values = [sum(avg_delays[h])/len(avg_delays[h]) for h in sorted_hours]
    
    plt.subplot(1, 2, 1)
    plt.plot(sorted_hours, avg_values, marker='o', linestyle='-', color='b')
    plt.title('Durchschnittliche Verspaetung pro Stunde')
    plt.xlabel('Uhrzeit (Stunde)')
    plt.ylabel('Verspaetung (Minuten)')
    plt.grid(True)
    plt.xticks(range(min(sorted_hours or [8]), max(sorted_hours or [18]) + 1))

    # --- Plot 2: Punctuality Pie Chart ---
    plt.subplot(1, 2, 2)
    labels = ['Puenktlich (<5min)', 'Verspaetet (>=5min)', 'Ausgefallen']
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
        plt.title('Puenktlichkeit')
    else:
        plt.text(0.5, 0.5, 'Keine Daten', ha='center')

    plt.tight_layout()
    
    # Show plot
    print("Zeige Diagramme...")
    plt.show()

if __name__ == "__main__":
    plot_delays()
