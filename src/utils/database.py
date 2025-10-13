import sqlite3
from datetime import datetime

class SummaryDatabase:
    def __init__(self, db_path="data/summaries.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()
    
    def create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                summary TEXT NOT NULL,
                confidence REAL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def save_summary(self, query, summary, confidence, sources):
        self.conn.execute(
            "INSERT INTO summaries (query, summary, confidence, sources) VALUES (?, ?, ?, ?)",
            (query, summary, confidence, str(sources))
        )
        self.conn.commit()
    
    def get_recent_summaries(self, limit=10):
        cursor = self.conn.execute(
            "SELECT query, summary, created_at FROM summaries ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()