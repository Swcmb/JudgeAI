"""
用户权限系统
不同角色的访问控制
"""

import sqlite3
import json
import logging
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import jwt
from functools import wraps

class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"          # 管理员：所有权限
    TEACHER = "teacher"       # 教师：评分、查看结果、管理学生
    VIEWER = "viewer"         # 查看者：只查看结果
    STUDENT = "student"       # 学生：只能查看自己的成绩

class Permission(Enum):
    """权限枚举"""
    # 评分相关
    SCORE_STUDENTS = "score_students"
    BATCH_SCORE = "batch_score"
    VIEW_ALL_RESULTS = "view_all_results"
    VIEW_OWN_RESULTS = "view_own_results"
    
    # 数据管理
    MANAGE_STUDENTS = "manage_students"
    IMPORT_DATA = "import_data"
    EXPORT_DATA = "export_data"
    
    # 系统管理
    MANAGE_USERS = "manage_users"
    MANAGE_CONFIG = "manage_config"
    VIEW_LOGS = "view_logs"
    SYSTEM_SETTINGS = "system_settings"
    
    # 历史记录
    VIEW_HISTORY = "view_history"
    COMPARE_STUDENTS = "compare_students"
    ANALYTICS = "analytics"

@dataclass
class User:
    """用户数据类"""
    id: int
    username: str
    email: str
    role: UserRole
    permissions: List[Permission]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    metadata: Dict[str, Any]

@dataclass
class Session:
    """会话数据类"""
    session_id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str

class UserManagementSystem:
    """用户管理系统"""
    
    # 角色权限映射
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: [
            Permission.SCORE_STUDENTS, Permission.BATCH_SCORE, Permission.VIEW_ALL_RESULTS,
            Permission.MANAGE_STUDENTS, Permission.IMPORT_DATA, Permission.EXPORT_DATA,
            Permission.MANAGE_USERS, Permission.MANAGE_CONFIG, Permission.VIEW_LOGS,
            Permission.SYSTEM_SETTINGS, Permission.VIEW_HISTORY, Permission.COMPARE_STUDENTS,
            Permission.ANALYTICS
        ],
        UserRole.TEACHER: [
            Permission.SCORE_STUDENTS, Permission.BATCH_SCORE, Permission.VIEW_ALL_RESULTS,
            Permission.MANAGE_STUDENTS, Permission.IMPORT_DATA, Permission.EXPORT_DATA,
            Permission.VIEW_HISTORY, Permission.COMPARE_STUDENTS, Permission.ANALYTICS
        ],
        UserRole.VIEWER: [
            Permission.VIEW_ALL_RESULTS, Permission.VIEW_HISTORY, Permission.ANALYTICS
        ],
        UserRole.STUDENT: [
            Permission.VIEW_OWN_RESULTS
        ]
    }
    
    def __init__(self, db_path: str = "user_management.db", jwt_secret: str = None):
        """
        初始化用户管理系统
        
        Args:
            db_path: 数据库路径
            jwt_secret: JWT密钥
        """
        self.db_path = db_path
        self.jwt_secret = jwt_secret or secrets.token_urlsafe(32)
        self.logger = logging.getLogger(__name__)
        self._init_database()
        self._create_default_admin()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                metadata TEXT
            )
        ''')
        
        # 会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 权限日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS permission_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                permission TEXT NOT NULL,
                resource TEXT,
                action TEXT,
                granted BOOLEAN,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 登录日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                success BOOLEAN,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                failure_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _create_default_admin(self):
        """创建默认管理员账户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # 创建默认管理员账户
            default_password = "admin123"
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(default_password, salt)
            
            permissions = json.dumps([perm.value for perm in self.ROLE_PERMISSIONS[UserRole.ADMIN]])
            
            cursor.execute('''
                INSERT INTO users 
                (username, email, password_hash, salt, role, permissions, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                "admin",
                "admin@example.com",
                password_hash,
                salt,
                UserRole.ADMIN.value,
                permissions,
                json.dumps({"is_default": True, "requires_password_change": True})
            ))
            
            conn.commit()
            self.logger.warning("创建了默认管理员账户: admin/admin123")
        
        conn.close()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """密码哈希"""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _verify_password(self, password: str, salt: str, hash_value: str) -> bool:
        """验证密码"""
        return self._hash_password(password, salt) == hash_value
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole, metadata: Dict[str, Any] = None) -> Tuple[bool, str]:
        """创建用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户名和邮箱是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return False, "用户名或邮箱已存在"
            
            # 创建用户
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            permissions = json.dumps([perm.value for perm in self.ROLE_PERMISSIONS[role]])
            
            cursor.execute('''
                INSERT INTO users 
                (username, email, password_hash, salt, role, permissions, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                username, email, password_hash, salt, role.value, permissions,
                json.dumps(metadata or {})
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"创建用户成功: {username} (ID: {user_id})")
            return True, "用户创建成功"
        
        except Exception as e:
            self.logger.error(f"创建用户失败: {e}")
            return False, f"创建用户失败: {str(e)}"
    
    def authenticate(self, username: str, password: str, ip_address: str, 
                   user_agent: str = "") -> Tuple[Optional[User], str]:
        """用户认证"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, role, permissions, 
                       created_at, last_login, is_active, metadata
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            row = cursor.fetchone()
            if not row:
                self._log_login_attempt(None, username, False, ip_address, user_agent, "用户不存在")
                return None, "用户名或密码错误"
            
            user_id, db_username, email, password_hash, salt, role, permissions, \
            created_at, last_login, is_active, metadata = row
            
            if not self._verify_password(password, salt, password_hash):
                self._log_login_attempt(user_id, username, False, ip_address, user_agent, "密码错误")
                return None, "用户名或密码错误"
            
            # 更新最后登录时间
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", 
                          (datetime.now(), user_id))
            
            # 构建用户对象
            user_permissions = [Permission(perm) for perm in json.loads(permissions)]
            user = User(
                id=user_id,
                username=db_username,
                email=email,
                role=UserRole(role),
                permissions=user_permissions,
                created_at=datetime.fromisoformat(created_at),
                last_login=datetime.fromisoformat(last_login) if last_login else None,
                is_active=bool(is_active),
                metadata=json.loads(metadata) if metadata else {}
            )
            
            conn.commit()
            self._log_login_attempt(user_id, username, True, ip_address, user_agent)
            
            return user, "认证成功"
        
        except Exception as e:
            self.logger.error(f"认证失败: {e}")
            return None, f"认证失败: {str(e)}"
        
        finally:
            conn.close()
    
    def _log_login_attempt(self, user_id: Optional[int], username: str, success: bool,
                          ip_address: str, user_agent: str, failure_reason: str = ""):
        """记录登录尝试"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO login_logs 
            (user_id, username, success, ip_address, user_agent, failure_reason)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, success, ip_address, user_agent, failure_reason))
        
        conn.commit()
        conn.close()
    
    def create_session(self, user: User, ip_address: str, 
                     user_agent: str = "", expires_hours: int = 24) -> str:
        """创建会话"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions 
            (session_id, user_id, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, user.id, expires_at, ip_address, user_agent))
        
        conn.commit()
        conn.close()
        
        # 创建JWT令牌
        token_payload = {
            'session_id': session_id,
            'user_id': user.id,
            'username': user.username,
            'role': user.role.value,
            'exp': expires_at.timestamp()
        }
        
        jwt_token = jwt.encode(token_payload, self.jwt_secret, algorithm='HS256')
        return jwt_token
    
    def validate_session(self, token: str, ip_address: str = "") -> Optional[User]:
        """验证会话"""
        try:
            # 解析JWT令牌
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload['session_id']
            user_id = payload['user_id']
            
            # 检查会话是否有效
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.expires_at, s.is_active, u.username, u.email, u.role, u.permissions,
                       u.created_at, u.last_login, u.is_active, u.metadata
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = ? AND s.user_id = ? AND s.is_active = 1
            ''', (session_id, user_id))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            expires_at, session_active, username, email, role, permissions, \
            created_at, last_login, user_active, metadata = row
            
            # 检查会话是否过期
            if datetime.now() > datetime.fromisoformat(expires_at):
                cursor.execute("UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
                conn.commit()
                conn.close()
                return None
            
            # 检查用户是否激活
            if not user_active:
                conn.close()
                return None
            
            conn.close()
            
            # 构建用户对象
            user_permissions = [Permission(perm) for perm in json.loads(permissions)]
            user = User(
                id=user_id,
                username=username,
                email=email,
                role=UserRole(role),
                permissions=user_permissions,
                created_at=datetime.fromisoformat(created_at),
                last_login=datetime.fromisoformat(last_login) if last_login else None,
                is_active=bool(user_active),
                metadata=json.loads(metadata) if metadata else {}
            )
            
            return user
        
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            self.logger.error(f"会话验证失败: {e}")
            return None
    
    def logout(self, token: str) -> bool:
        """用户登出"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload['session_id']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            self.logger.error(f"登出失败: {e}")
            return False
    
    def has_permission(self, user: User, permission: Permission, resource: str = "") -> bool:
        """检查用户权限"""
        granted = permission in user.permissions
        
        # 记录权限检查日志
        self._log_permission_check(user.id, permission.value, resource, "check", granted)
        
        return granted
    
    def _log_permission_check(self, user_id: int, permission: str, resource: str,
                             action: str, granted: bool, ip_address: str = ""):
        """记录权限检查"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO permission_logs 
            (user_id, permission, resource, action, granted, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, permission, resource, action, granted, ip_address))
        
        conn.commit()
        conn.close()
    
    def get_users(self, role: Optional[UserRole] = None, active_only: bool = True) -> List[User]:
        """获取用户列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM users"
        params = []
        
        conditions = []
        if role:
            conditions.append("role = ?")
            params.append(role.value)
        if active_only:
            conditions.append("is_active = 1")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        users = []
        for row in rows:
            permissions = [Permission(perm) for perm in json.loads(row[5])]
            user = User(
                id=row[0],
                username=row[1],
                email=row[2],
                role=UserRole(row[4]),
                permissions=permissions,
                created_at=datetime.fromisoformat(row[6]),
                last_login=datetime.fromisoformat(row[7]) if row[7] else None,
                is_active=bool(row[8]),
                metadata=json.loads(row[9]) if row[9] else {}
            )
            users.append(user)
        
        conn.close()
        return users
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """更新用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            set_clauses = []
            params = []
            
            # 更新基本信息
            if 'email' in updates:
                set_clauses.append("email = ?")
                params.append(updates['email'])
            
            if 'role' in updates:
                new_role = UserRole(updates['role']) if isinstance(updates['role'], str) else updates['role']
                permissions = json.dumps([perm.value for perm in self.ROLE_PERMISSIONS[new_role]])
                set_clauses.append("role = ?")
                params.append(new_role.value)
                set_clauses.append("permissions = ?")
                params.append(permissions)
            
            if 'metadata' in updates:
                set_clauses.append("metadata = ?")
                params.append(json.dumps(updates['metadata']))
            
            if 'is_active' in updates:
                set_clauses.append("is_active = ?")
                params.append(updates['is_active'])
            
            if not set_clauses:
                conn.close()
                return False, "没有要更新的字段"
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            
            return True, "用户更新成功"
        
        except Exception as e:
            self.logger.error(f"更新用户失败: {e}")
            return False, f"更新用户失败: {str(e)}"
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改密码"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False, "用户不存在"
            
            password_hash, salt = row
            
            if not self._verify_password(old_password, salt, password_hash):
                conn.close()
                return False, "原密码错误"
            
            # 更新密码
            new_salt = secrets.token_hex(16)
            new_password_hash = self._hash_password(new_password, new_salt)
            
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ? WHERE id = ?
            ''', (new_password_hash, new_salt, user_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"用户 {user_id} 修改密码成功")
            return True, "密码修改成功"
        
        except Exception as e:
            self.logger.error(f"修改密码失败: {e}")
            return False, f"修改密码失败: {str(e)}"
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """删除用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否为默认管理员
            cursor.execute('SELECT username, metadata FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                metadata = json.loads(row[2]) if row[2] else {}
                if metadata.get('is_default'):
                    conn.close()
                    return False, "不能删除默认管理员账户"
            
            # 删除用户（会级联删除相关会话）
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            conn.commit()
            conn.close()
            
            return True, "用户删除成功"
        
        except Exception as e:
            self.logger.error(f"删除用户失败: {e}")
            return False, f"删除用户失败: {str(e)}"
    
    def get_login_logs(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取登录日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM login_logs WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM login_logs 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        logs = []
        for row in rows:
            log = dict(zip(columns, row))
            logs.append(log)
        
        conn.close()
        return logs
    
    def get_permission_logs(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取权限日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM permission_logs WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM permission_logs 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        logs = []
        for row in rows:
            log = dict(zip(columns, row))
            logs.append(log)
        
        conn.close()
        return logs


# 装饰器用于权限检查
def require_permission(permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 这里需要根据具体的Web框架实现
            # 示例实现，实际使用时需要适配
            token = kwargs.get('token') or args[0] if args else None
            
            if not token:
                return {"error": "需要认证"}, 401
            
            user_manager = UserManagementSystem()
            user = user_manager.validate_session(token)
            
            if not user:
                return {"error": "认证失败"}, 401
            
            if not user_manager.has_permission(user, permission):
                return {"error": "权限不足"}, 403
            
            # 将用户信息传递给函数
            kwargs['current_user'] = user
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def main():
    """测试用户管理系统"""
    import os
    
    # 初始化系统
    user_system = UserManagementSystem()
    
    print("=== 用户管理系统测试 ===")
    
    # 创建测试用户
    success, message = user_system.create_user(
        username="teacher1",
        email="teacher1@example.com",
        password="password123",
        role=UserRole.TEACHER,
        metadata={"department": "计算机学院"}
    )
    print(f"创建教师用户: {'✅' if success else '❌'} {message}")
    
    success, message = user_system.create_user(
        username="student1",
        email="student1@example.com",
        password="password123",
        role=UserRole.STUDENT
    )
    print(f"创建学生用户: {'✅' if success else '❌'} {message}")
    
    # 测试认证
    print("\n=== 测试认证 ===")
    user, message = user_system.authenticate("admin", "admin123", "127.0.0.1")
    if user:
        print(f"管理员认证成功: {user.username}, 角色: {user.role.value}")
        print(f"权限: {[perm.value for perm in user.permissions]}")
        
        # 创建会话
        token = user_system.create_session(user, "127.0.0.1")
        print(f"创建会话成功")
        
        # 验证会话
        validated_user = user_system.validate_session(token)
        print(f"会话验证: {'✅' if validated_user else '❌'}")
        
        # 权限检查
        has_perm = user_system.has_permission(user, Permission.MANAGE_USERS)
        print(f"管理员权限检查: {'✅' if has_perm else '❌'}")
    
    # 测试教师认证
    print("\n=== 测试教师权限 ===")
    teacher_user, message = user_system.authenticate("teacher1", "password123", "127.0.0.1")
    if teacher_user:
        print(f"教师认证成功: {teacher_user.username}")
        
        has_perm = user_system.has_permission(teacher_user, Permission.MANAGE_USERS)
        print(f"教师是否有用户管理权限: {'✅' if has_perm else '❌'}")
        
        has_score_perm = user_system.has_permission(teacher_user, Permission.SCORE_STUDENTS)
        print(f"教师是否有评分权限: {'✅' if has_score_perm else '❌'}")
    
    # 获取用户列表
    print("\n=== 用户列表 ===")
    users = user_system.get_users()
    for user in users:
        print(f"- {user.username} ({user.role.value}): {'活跃' if user.is_active else '未激活'}")
    
    # 获取登录日志
    print("\n=== 登录日志 ===")
    logs = user_system.get_login_logs(limit=5)
    for log in logs:
        status = "成功" if log['success'] else "失败"
        print(f"- {log['username']}: {status} at {log['timestamp']}")


if __name__ == "__main__":
    main()