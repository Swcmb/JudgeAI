"""
增强安全模块
提供JWT认证、数据加密、访问控制和审计日志功能
"""

import os
import jwt
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from functools import wraps
import sqlite3
import json
from flask import request, g, current_app
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """用户数据类"""
    id: int
    username: str
    email: str
    role: str
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.last_login:
            data['last_login'] = self.last_login.isoformat()
        return data

@dataclass
class AuditLog:
    """审计日志数据类"""
    id: int
    user_id: int
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class SecurityManager:
    """安全管理器"""
    
    def __init__(self, 
                 secret_key: Optional[str] = None,
                 token_expire_hours: int = 24,
                 db_path: str = "security.db"):
        """
        初始化安全管理器
        
        Args:
            secret_key: JWT密钥，如果为None则自动生成
            token_expire_hours: Token过期时间（小时）
            db_path: 安全数据库路径
        """
        self.db_path = db_path
        self.token_expire_hours = token_expire_hours
        
        # 初始化密钥
        if secret_key:
            self.secret_key = secret_key
        else:
            self.secret_key = self._generate_secret_key()
        
        # 初始化加密器
        self.encryption_key = self._derive_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        # 初始化数据库
        self._init_database()
        
        logger.info("安全管理器已初始化")
    
    def _generate_secret_key(self) -> str:
        """生成安全密钥"""
        return secrets.token_urlsafe(32)
    
    def _derive_encryption_key(self) -> bytes:
        """派生加密密钥"""
        password = self.secret_key.encode()
        salt = b'judge_ai_salt'  # 在生产环境中应该使用随机盐
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _init_database(self):
        """初始化安全数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 用户表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    permissions TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # 审计日志表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    success INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 会话表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                    password.encode('utf-8'), 
                                    salt.encode('utf-8'), 
                                    100000)
        return salt + pwdhash.hex()
    
    def verify_password(self, stored_hash: str, provided_password: str) -> bool:
        """验证密码"""
        salt = stored_hash[:32]
        stored_pwdhash = stored_hash[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                    provided_password.encode('utf-8'), 
                                    salt.encode('utf-8'), 
                                    100000)
        return pwdhash.hex() == stored_pwdhash
    
    def generate_token(self, user: User) -> str:
        """生成JWT Token"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'permissions': user.permissions,
            'exp': datetime.utcnow() + timedelta(hours=self.token_expire_hours),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT Token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError:
            logger.warning("无效Token")
            return None
    
    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        encrypted_data = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher.decrypt(encrypted_bytes)
        return decrypted_data.decode()
    
    def create_user(self, 
                   username: str, 
                   email: str, 
                   password: str, 
                   role: str = 'user',
                   permissions: List[str] = None) -> int:
        """创建用户"""
        if permissions is None:
            permissions = ['read']
        
        password_hash = self.hash_password(password)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO users (username, email, password_hash, role, permissions, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                username, 
                email, 
                password_hash, 
                role, 
                json.dumps(permissions),
                datetime.now().isoformat()
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"用户创建成功: {username} (ID: {user_id})")
            return user_id
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, username, email, password_hash, role, permissions, 
                       created_at, last_login, is_active
                FROM users WHERE username = ? OR email = ?
            ''', (username, username))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user_id, username, email, password_hash, role, permissions_str, \
            created_at_str, last_login_str, is_active = row
            
            if not is_active:
                return None
            
            if not self.verify_password(password_hash, password):
                return None
            
            # 更新最后登录时间
            conn.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.now().isoformat(), user_id))
            conn.commit()
            
            # 创建用户对象
            permissions = json.loads(permissions_str)
            created_at = datetime.fromisoformat(created_at_str)
            last_login = datetime.fromisoformat(last_login_str) if last_login_str else None
            
            return User(
                id=user_id,
                username=username,
                email=email,
                role=role,
                permissions=permissions,
                created_at=created_at,
                last_login=last_login,
                is_active=bool(is_active)
            )
    
    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, username, email, role, permissions, created_at, 
                       last_login, is_active
                FROM users WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user_id, username, email, role, permissions_str, \
            created_at_str, last_login_str, is_active = row
            
            permissions = json.loads(permissions_str)
            created_at = datetime.fromisoformat(created_at_str)
            last_login = datetime.fromisoformat(last_login_str) if last_login_str else None
            
            return User(
                id=user_id,
                username=username,
                email=email,
                role=role,
                permissions=permissions,
                created_at=created_at,
                last_login=last_login,
                is_active=bool(is_active)
            )
    
    def log_audit(self, 
                  user_id: int, 
                  action: str, 
                  resource: str, 
                  details: Dict[str, Any] = None,
                  success: bool = True):
        """记录审计日志"""
        if details is None:
            details = {}
        
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        user_agent = request.headers.get('User-Agent', '')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO audit_logs 
                (user_id, action, resource, details, ip_address, user_agent, timestamp, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                action,
                resource,
                json.dumps(details),
                ip_address,
                user_agent,
                datetime.now().isoformat(),
                success
            ))
            conn.commit()
    
    def get_audit_logs(self, 
                      user_id: Optional[int] = None,
                      action: Optional[str] = None,
                      limit: int = 100) -> List[AuditLog]:
        """获取审计日志"""
        with sqlite3.connect(self.db_path) as conn:
            query = 'SELECT * FROM audit_logs WHERE 1=1'
            params = []
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            
            if action:
                query += ' AND action = ?'
                params.append(action)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                log = AuditLog(
                    id=row[0],
                    user_id=row[1],
                    action=row[2],
                    resource=row[3],
                    details=json.loads(row[4]),
                    ip_address=row[5],
                    user_agent=row[6],
                    timestamp=datetime.fromisoformat(row[7]),
                    success=bool(row[8])
                )
                logs.append(log)
            
            return logs

# 全局安全管理器实例
_security_manager = None

def get_security_manager() -> SecurityManager:
    """获取安全管理器实例"""
    global _security_manager
    if _security_manager is None:
        secret_key = os.getenv('JWT_SECRET_KEY')
        if not secret_key:
            logger.warning("未设置JWT_SECRET_KEY环境变量，使用临时密钥")
            secret_key = None
        
        # 使用固定的数据库路径
        _security_manager = SecurityManager(secret_key=secret_key, db_path="security.db")
    return _security_manager

def init_security_manager(secret_key: Optional[str] = None, **kwargs) -> SecurityManager:
    """初始化安全管理器"""
    global _security_manager
    _security_manager = SecurityManager(secret_key=secret_key, **kwargs)
    return _security_manager

# 装饰器
def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # 从请求头获取Token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return {'success': False, 'error': '无效的认证格式'}, 401
        
        if not token:
            # 从Cookie获取Token
            token = request.cookies.get('auth_token')
        
        if not token:
            return {'success': False, 'error': '缺少认证Token'}, 401
        
        # 验证Token
        security_manager = get_security_manager()
        payload = security_manager.verify_token(token)
        
        if not payload:
            return {'success': False, 'error': '无效或过期的Token'}, 401
        
        # 获取用户信息
        user = security_manager.get_user(payload['user_id'])
        if not user or not user.is_active:
            return {'success': False, 'error': '用户不存在或已被禁用'}, 401
        
        # 设置全局用户信息
        g.current_user = user
        g.user_payload = payload
        
        # 记录审计日志
        security_manager.log_audit(
            user_id=user.id,
            action='access',
            resource=f"{request.method} {request.endpoint}",
            details={'args': args, 'kwargs': kwargs}
        )
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission: str):
    """权限检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return {'success': False, 'error': '用户未认证'}, 401
            
            user = g.current_user
            
            if permission not in user.permissions:
                security_manager = get_security_manager()
                security_manager.log_audit(
                    user_id=user.id,
                    action='permission_denied',
                    resource=f"{request.method} {request.endpoint}",
                    details={'required_permission': permission},
                    success=False
                )
                
                return {'success': False, 'error': f'需要权限: {permission}'}, 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_role(role: str):
    """角色检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return {'success': False, 'error': '用户未认证'}, 401
            
            user = g.current_user
            
            if user.role != role:
                security_manager = get_security_manager()
                security_manager.log_audit(
                    user_id=user.id,
                    action='role_denied',
                    resource=f"{request.method} {request.endpoint}",
                    details={'required_role': role},
                    success=False
                )
                
                return {'success': False, 'error': f'需要角色: {role}'}, 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Flask集成
class FlaskSecurityIntegration:
    """Flask安全集成"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化Flask应用"""
        app.config.setdefault('JWT_SECRET_KEY', os.getenv('JWT_SECRET_KEY'))
        app.config.setdefault('TOKEN_EXPIRE_HOURS', 24)
        
        # 注册安全相关的路由
        self._register_routes(app)
    
    def _register_routes(self, app):
        """注册安全路由"""
        
        @app.route('/api/auth/login', methods=['POST'])
        def login():
            """用户登录"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return {'success': False, 'error': '用户名和密码不能为空'}, 400
            
            security_manager = get_security_manager()
            user = security_manager.authenticate_user(username, password)
            
            if not user:
                security_manager.log_audit(
                    user_id=0,  # 未知用户
                    action='login_failed',
                    resource='auth',
                    details={'username': username},
                    success=False
                )
                return {'success': False, 'error': '用户名或密码错误'}, 401
            
            # 生成Token
            token = security_manager.generate_token(user)
            
            # 记录审计日志
            security_manager.log_audit(
                user_id=user.id,
                action='login_success',
                resource='auth'
            )
            
            return {
                'success': True,
                'token': token,
                'user': user.to_dict()
            }
        
        @app.route('/api/auth/logout', methods=['POST'])
        @require_auth
        def logout():
            """用户登出"""
            user = g.current_user
            security_manager = get_security_manager()
            
            security_manager.log_audit(
                user_id=user.id,
                action='logout',
                resource='auth'
            )
            
            return {'success': True, 'message': '登出成功'}
        
        @app.route('/api/auth/profile')
        @require_auth
        def profile():
            """获取用户资料"""
            user = g.current_user
            return {'success': True, 'user': user.to_dict()}
        
        @app.route('/api/auth/audit_logs')
        @require_permission('admin')
        def audit_logs():
            """获取审计日志"""
            security_manager = get_security_manager()
            logs = security_manager.get_audit_logs(limit=100)
            
            return {
                'success': True,
                'logs': [log.to_dict() for log in logs]
            }
