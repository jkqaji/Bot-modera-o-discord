import sqlite3
import asyncio
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='tickets.db'):
        self.db_name = db_name
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            # Tabela de tickets
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    closed_by INTEGER,
                    reason TEXT
                )
            ''')
            
            # Tabela de mensagens de ticket
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id)
                )
            ''')
            
            # Tabela de moderação
            conn.execute('''
                CREATE TABLE IF NOT EXISTS moderation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    duration TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT true
                )
            ''')
            
            # Tabela de configurações
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id INTEGER PRIMARY KEY,
                    ticket_channel INTEGER,
                    mod_role INTEGER,
                    admin_role INTEGER,
                    log_channel INTEGER
                )
            ''')
    
    # Métodos para tickets
    async def create_ticket(self, ticket_id, user_id, channel_id, category):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO tickets (ticket_id, user_id, channel_id, category)
                VALUES (?, ?, ?, ?)
            ''', (ticket_id, user_id, channel_id, category))
    
    async def close_ticket(self, ticket_id, closed_by, reason=None):
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE tickets 
                SET status = 'closed', closed_at = CURRENT_TIMESTAMP, 
                    closed_by = ?, reason = ?
                WHERE ticket_id = ?
            ''', (closed_by, reason, ticket_id))
    
    async def get_ticket(self, ticket_id):
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM tickets WHERE ticket_id = ?', (ticket_id,))
            return cursor.fetchone()
    
    async def get_user_tickets(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM tickets WHERE user_id = ?', (user_id,))
            return cursor.fetchall()
    
    # Métodos para moderação
    async def add_mod_action(self, case_id, user_id, moderator_id, action, reason, duration=None):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO moderation (case_id, user_id, moderator_id, action, reason, duration)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (case_id, user_id, moderator_id, action, reason, duration))
    
    async def get_user_warnings(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM moderation 
                WHERE user_id = ? AND action = 'warn' AND active = true
            ''', (user_id,))
            return cursor.fetchall()
