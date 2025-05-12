import requests
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import time
import os
from git import Repo
# Replace matplotlib import with plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def setup_database():
    conn = sqlite3.connect('server_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_population (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            players INTEGER,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    return conn

def get_server_data():
    url = "https://servers-frontend.fivem.net/api/servers/single/vvgvgx"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://servers.fivem.net',
        'Referer': 'https://servers.fivem.net/',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('Data', {}).get('clients', 0)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching server data: {e}")
        time.sleep(30)  # Changed from 60 to 30
        return None

def save_population(conn, players):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO server_population (players, timestamp) VALUES (?, ?)",
        (players, datetime.now())
    )
    conn.commit()

def setup_git():
    repo_path = os.path.dirname(os.path.abspath(__file__))
    repo = Repo(repo_path)
    # Configure auto push
    if 'origin' in repo.remotes:
        origin = repo.remotes.origin
        origin.pull()  # Pull latest changes first
    return repo

def update_graph():
    conn = sqlite3.connect('server_stats.db')
    query = """
    SELECT players, timestamp 
    FROM server_population 
    ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    conn.close()

    # Create TradingView-style plot
    fig = go.Figure()
    
    # Add main line
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['players'],
        mode='lines',
        name='Players',
        line=dict(color='#2962FF', width=2),
        fill='tozeroy',
        fillcolor='rgba(41, 98, 255, 0.1)'
    ))
    
    # Layout configuration
    fig.update_layout(
        title='Server Population History',
        xaxis=dict(
            title='Time',
            showgrid=True,
            gridcolor='#2B2B2B',
            rangeslider=dict(visible=True),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1h", step="hour", stepmode="backward"),
                    dict(count=6, label="6h", step="hour", stepmode="backward"),
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(step="all")
                ])
            )
        ),
        yaxis=dict(
            title='Number of Players',
            showgrid=True,
            gridcolor='#2B2B2B'
        ),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(color='#FFFFFF'),
        margin=dict(l=50, r=50, b=50, t=50, pad=4),
        hovermode='x unified',
        showlegend=False
    )
    
    # Save as HTML
    fig.write_html('server_population.html')
    
    # Upload to GitHub after saving
    repo = setup_git()
    upload_to_github(repo)

def upload_to_github(repo):
    try:
        # Create HTML file with update time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content = f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; }}
                .update-time {{ color: green; font-size: 18px; margin: 20px; }}
                iframe {{ width: 100%; height: 90vh; border: none; }}
            </style>
        </head>
        <body>
            <div class="update-time">Last Updated: {current_time}</div>
            <iframe src="server_population.html"></iframe>
        </body>
        </html>
        """
        with open('index.html', 'w') as f:
            f.write(html_content)

        # Stage both files
        repo.index.add(['server_population.html', 'index.html'])
        repo.index.commit(f"Update graph {current_time}")
        
        # Stage and commit with force
        repo.git.add('--all')
        repo.git.commit('-m', f"Update graph {current_time}", '--allow-empty')
        
        # Force push to ensure updates
        origin = repo.remote(name='origin')
        origin.push(force=True)
        print("✅ Graph is live on the website!")
    except Exception as e:
        print(f"❌ Failed to update website: {e}")

def main():
    conn = setup_database()
    
    try:
        while True:
            players = get_server_data()
            if players is not None:
                save_population(conn, players)
                print(f"Saved player count: {players} at {datetime.now()}")
                update_graph()
            time.sleep(30)  # Changed from 15 to 30
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        conn.close()
        print("Database connection closed.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        conn.close()

if __name__ == "__main__":
    main()