"""Authentication database models and management."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    """User model."""
    id: Optional[int] = None
    username: str
    password_hash: str
    email: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class APIKey(BaseModel):
    """API Key model."""
    id: Optional[int] = None
    user_id: int
    key: str
    name: str
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


class RefreshToken(BaseModel):
    """Refresh token model."""
    id: Optional[int] = None
    user_id: int
    token: str
    expires_at: datetime
    created_at: Optional[datetime] = None
    is_revoked: bool = False


class BlacklistedToken(BaseModel):
    """Blacklisted token model."""
    id: Optional[int] = None
    token: str
    blacklisted_at: Optional[datetime] = None
    reason: str = "revoked"


class AuthDatabase:
    """Authentication database manager."""
    
    def __init__(self, db_path: str = "./storage/auth.db"):
        """Initialize database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # API Keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Refresh tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_revoked BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Blacklisted tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT DEFAULT 'revoked'
            )
        """)
        
        # Commit table creation first
        conn.commit()
        
        # Create indexes after tables exist
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklisted_tokens_token ON blacklisted_tokens(token)")
        
        conn.commit()
        conn.close()
    
    # User operations
    def create_user(self, username: str, password_hash: str, email: str) -> int:
        """Create a new user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row["id"],
                username=row["username"],
                password_hash=row["password_hash"],
                email=row["email"],
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None
            )
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row["id"],
                username=row["username"],
                password_hash=row["password_hash"],
                email=row["email"],
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None
            )
        return None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    
    # API Key operations
    def create_api_key(self, user_id: int, name: str, expires_days: Optional[int] = None) -> str:
        """Create a new API key."""
        key = f"sk_{secrets.token_urlsafe(32)}"
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_keys (user_id, key, name, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, key, name, expires_at)
        )
        conn.commit()
        conn.close()
        return key
    
    def get_api_key(self, key: str) -> Optional[APIKey]:
        """Get API key details."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return APIKey(
                id=row["id"],
                user_id=row["user_id"],
                key=row["key"],
                name=row["name"],
                is_active=bool(row["is_active"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None
            )
        return None
    
    def get_user_api_keys(self, user_id: int) -> list[APIKey]:
        """Get all API keys for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        keys = []
        for row in rows:
            keys.append(APIKey(
                id=row["id"],
                user_id=row["user_id"],
                key=row["key"],
                name=row["name"],
                is_active=bool(row["is_active"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None
            ))
        return keys
    
    def update_api_key_usage(self, key: str):
        """Update API key last used timestamp."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE key = ?",
            (key,)
        )
        conn.commit()
        conn.close()
    
    def revoke_api_key(self, key: str):
        """Revoke an API key."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key = ?",
            (key,)
        )
        # Add to blacklist
        cursor.execute(
            "INSERT OR IGNORE INTO blacklisted_tokens (token, reason) VALUES (?, 'api_key_revoked')",
            (key,)
        )
        conn.commit()
        conn.close()
    
    def revoke_api_key_by_id(self, key_id: int, user_id: int):
        """Revoke an API key by ID (with user verification)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE api_keys SET is_active = 0 WHERE id = ? AND user_id = ?",
            (key_id, user_id)
        )
        # Get key to blacklist
        cursor.execute("SELECT key FROM api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT OR IGNORE INTO blacklisted_tokens (token, reason) VALUES (?, 'api_key_revoked')",
                (row["key"],)
            )
        conn.commit()
        conn.close()
    
    # Refresh token operations
    def create_refresh_token(self, user_id: int, expires_days: int = 30) -> str:
        """Create a new refresh token."""
        token = secrets.token_urlsafe(64)
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at)
        )
        conn.commit()
        conn.close()
        return token
    
    def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token details."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refresh_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return RefreshToken(
                id=row["id"],
                user_id=row["user_id"],
                token=row["token"],
                expires_at=datetime.fromisoformat(row["expires_at"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                is_revoked=bool(row["is_revoked"])
            )
        return None
    
    def revoke_refresh_token(self, token: str):
        """Revoke a refresh token."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE refresh_tokens SET is_revoked = 1 WHERE token = ?",
            (token,)
        )
        # Add to blacklist
        cursor.execute(
            "INSERT OR IGNORE INTO blacklisted_tokens (token, reason) VALUES (?, 'refresh_token_revoked')",
            (token,)
        )
        conn.commit()
        conn.close()
    
    def revoke_user_refresh_tokens(self, user_id: int):
        """Revoke all refresh tokens for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        # Get all tokens
        cursor.execute("SELECT token FROM refresh_tokens WHERE user_id = ? AND is_revoked = 0", (user_id,))
        tokens = [row["token"] for row in cursor.fetchall()]
        
        # Revoke them
        cursor.execute(
            "UPDATE refresh_tokens SET is_revoked = 1 WHERE user_id = ?",
            (user_id,)
        )
        
        # Blacklist them
        for token in tokens:
            cursor.execute(
                "INSERT OR IGNORE INTO blacklisted_tokens (token, reason) VALUES (?, 'user_logout')",
                (token,)
            )
        
        conn.commit()
        conn.close()
    
    # Blacklist operations
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM blacklisted_tokens WHERE token = ?", (token,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def blacklist_token(self, token: str, reason: str = "revoked"):
        """Add token to blacklist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO blacklisted_tokens (token, reason) VALUES (?, ?)",
            (token, reason)
        )
        conn.commit()
        conn.close()
    
    # Cleanup operations
    def cleanup_expired_tokens(self):
        """Remove expired tokens and API keys."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete expired refresh tokens
        cursor.execute(
            "DELETE FROM refresh_tokens WHERE expires_at < datetime('now')"
        )
        
        # Deactivate expired API keys
        cursor.execute(
            "UPDATE api_keys SET is_active = 0 WHERE expires_at IS NOT NULL AND expires_at < datetime('now')"
        )
        
        # Clean up old blacklisted tokens (older than 30 days)
        cursor.execute(
            "DELETE FROM blacklisted_tokens WHERE blacklisted_at < datetime('now', '-30 days')"
        )
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected


# Global database instance
auth_db = AuthDatabase()
