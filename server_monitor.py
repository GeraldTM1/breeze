import requests
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import time
import os
from git import Repo

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
        time.sleep(60)
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
    return Repo(repo_path)

def upload_to_github(repo):
    try:
        # Stage the image file
        repo.index.add(['server_population.png'])
        # Commit with timestamp
        repo.index.commit(f"Update graph {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # Push to GitHub
        origin = repo.remote(name='origin')
        origin.push()
        print("Successfully uploaded to GitHub")
    except Exception as e:
        print(f"Error uploading to GitHub: {e}")

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

    plt.figure(figsize=(15, 8))
    plt.plot(df['timestamp'], df['players'], color='blue', linewidth=2, marker='o', markersize=4)
    
    plt.title('Server Population History')
    plt.xlabel('Time')
    plt.ylabel('Number of Players')
    
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig('server_population.png')
    plt.close()
    
    # Upload to GitHub after saving
    repo = setup_git()
    upload_to_github(repo)

def main():
    conn = setup_database()
    
    try:
        while True:
            players = get_server_data()
            if players is not None:
                save_population(conn, players)
                print(f"Saved player count: {players} at {datetime.now()}")
                update_graph()
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        conn.close()
        print("Database connection closed.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        conn.close()

if __name__ == "__main__":
    main()