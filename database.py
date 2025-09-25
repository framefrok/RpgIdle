import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 0,
            artifact_parts INTEGER DEFAULT 0,
            magic_dust INTEGER DEFAULT 0,
            guns INTEGER DEFAULT 0,
            ether_currency INTEGER DEFAULT 0,
            strength INTEGER DEFAULT 10,
            cunning INTEGER DEFAULT 10,
            intellect INTEGER DEFAULT 10,
            artifact_levels TEXT DEFAULT '[0,0,0,0,0,0,0,0]',
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_player(user_id, username):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO players (user_id, username, created_at)
        VALUES (?, ?, ?)
    ''', (user_id, username, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def update_player(user_id, **kwargs):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    fields = ', '.join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [user_id]
    c.execute(f"UPDATE players SET {fields} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def update_resources(user_id, coins=0, artifact_parts=0, magic_dust=0, guns=0):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''
        UPDATE players
        SET coins = MAX(0, coins + ?),
            artifact_parts = MAX(0, artifact_parts + ?),
            magic_dust = MAX(0, magic_dust + ?),
            guns = MAX(0, guns + ?)
        WHERE user_id = ?
    ''', (int(coins), int(artifact_parts), int(magic_dust), int(guns), user_id))
    conn.commit()
    conn.close()
