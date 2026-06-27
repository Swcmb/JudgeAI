# JudgeAI API 完整文档

## 概述

JudgeAI 提供了完整的算法竞赛团队AI评分系统的REST API接口，支持第三方系统集成和自动化评分任务。项目包含Flask版本和Next.js版本，两者API设计略有差异但功能对等。

### 版本对比

| 特性 | Flask版本 | Next.js版本 |
|------|-----------|-------------|
| 基础URL | `http://localhost:5000/api/v1` | `http://localhost:3000/api/v1` |
| 认证方式 | JWT Bearer Token | NextAuth.js JWT Session |
| 数据格式 | JSON | JSON |
| 字符编码 | UTF-8 | UTF-8 |
| 实时通信 | WebSocket | Server-Sent Events (SSE) |

### 基础信息

#### Flask版本
- **API版本**: v1
- **基础URL**: `http://localhost:5000/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

#### Next.js版本
- **API版本**: v1
- **基础URL**: `http://localhost:3000/api/v1`
- **认证方式**: NextAuth.js Session Token
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证

### Flask版本认证

所有API请求（除了登录和API信息）都需要在请求头中包含JWT Token：

```
Authorization: Bearer <your_jwt_token>
```

### Next.js版本认证

Next.js版本使用NextAuth.js进行会话管理，认证方式分为客户端和服务端：

#### 客户端认证
使用NextAuth.js的客户端方法：
```javascript
import { signIn, signOut, useSession, getSession } from "next-auth/react";

// 登录
await signIn('credentials', {
  username: 'admin',
  password: 'password',
  redirect: false
});

// 获取会话
const { data: session } = useSession();
```

#### 服务端API认证
在服务端API路由中检查会话：
```typescript
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";

export async function GET() {
  const session = await getServerSession(authOptions);
  
  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  
  // API逻辑
}
```

#### 外部API调用认证
外部系统调用需要提供有效的会话令牌：
```
Authorization: Bearer <nextauth_jwt_token>
```

## API端点

## API端点

### 1. 系统信息

#### Flask版本 - 获取API信息

```http
GET /api/v1/info
```

**响应示例**:
```json
{
  "name": "JudgeAI API",
  "version": "1.0.0",
  "description": "算法竞赛团队AI评分系统API",
  "endpoints": {
    "authentication": "/api/v1/auth/*",
    "scoring": "/api/v1/scoring/*",
    "config": "/api/v1/config/*",
    "tasks": "/api/v1/tasks/*",
    "files": "/api/v1/files/*"
  },
  "documentation": "/api/v1/docs"
}
```

#### Next.js版本 - 获取API信息

```http
GET /api/v1/info
```

**响应示例**:
```json
{
  "name": "JudgeAI Next.js API",
  "version": "2.0.0",
  "description": "算法竞赛团队AI评分系统Next.js API",
  "framework": "Next.js 14",
  "endpoints": {
    "authentication": "/api/auth/*",
    "tasks": "/api/v1/tasks/*",
    "templates": "/api/v1/templates/*",
    "knowledge": "/api/v1/knowledge/*",
    "users": "/api/v1/users/*",
    "scoring": "/api/v1/scoring/*"
  },
  "features": ["RAG", "Vector Storage", "Multi-model AI", "Real-time Updates"]
}
```

### 2. 认证

#### 用户登录

```http
POST /api/v1/auth/login
```

**请求体**:
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin",
      "permissions": ["read", "write", "admin"],
      "created_at": "2024-01-01T00:00:00",
      "last_login": "2024-01-01T12:00:00",
      "is_active": true
    },
    "expires_in": 86400
  }
}
```

**错误响应**:
```json
{
  "success": false,
  "error": "用户名或密码错误",
  "error_code": "INVALID_CREDENTIALS"
}
```

### 3. 评分

#### 提交评分任务

```http
POST /api/v1/scoring/submit
```

**请求体**:
```json
{
  "students": [
    {
      "id": "001",
      "name": "张三",
      "content": "我是一名计算机专业的学生，对算法竞赛很感兴趣...",
      "template_id": "tpl_20240101_120000_default_template"
    }
  ],
  "template_id": "tpl_20240101_120000_default_template",
  "async": true
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_20240101_120000_abcdef123456",
    "status": "submitted",
    "total_students": 1,
    "async": true
  }
}
```

#### 评分单个学生

```http
POST /api/v1/scoring/student
```

**请求体**:
```json
{
  "student": {
    "id": "001",
    "name": "张三",
    "content": "我是一名计算机专业的学生，对算法竞赛很感兴趣..."
  },
  "template_id": "tpl_20240101_120000_default_template"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "result": {
      "思考过程": "该学生表现出强烈的学习意愿...",
      "学习态度": {
        "分数": 23,
        "理由": "积极主动，有强烈的学习意愿"
      },
      "自学能力": {
        "分数": 20,
        "理由": "具备一定的自学能力"
      },
      "算法基础": {
        "分数": 18,
        "理由": "有基础但需要加强"
      },
      "团队合作能力": {
        "分数": 22,
        "理由": "能够有效合作"
      },
      "总分": 83,
      "综合评价": "该学生具有较好的潜力，建议培养"
    }
  }
}
```

### 4. 配置管理

#### 获取评分模板列表

```http
GET /api/v1/config/templates
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "templates": [
      {
        "id": "tpl_20240101_120000_default_template",
        "name": "默认评分模板",
        "description": "包含四个基础维度的标准评分模板",
        "dimensions": ["learning_attitude", "self_study", "algorithm", "teamwork"],
        "is_default": true,
        "is_active": true,
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
        "created_by": "system"
      }
    ]
  }
}
```

#### 获取单个评分模板

```http
GET /api/v1/config/templates/{template_id}
```

#### 获取评分维度列表

```http
GET /api/v1/config/dimensions
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "dimensions": [
      {
        "id": "learning_attitude",
        "name": "学习态度",
        "weight": 0.25,
        "max_score": 25,
        "description": "评估学生的学习积极性和态度",
        "scoring_criteria": [
          {
            "range": "20-25",
            "description": "积极主动，有强烈学习意愿"
          },
          {
            "range": "10-19",
            "description": "态度一般，需要督促"
          },
          {
            "range": "0-9",
            "description": "态度消极，缺乏动力"
          }
        ],
        "is_active": true,
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
        "created_by": "system"
      }
    ]
  }
}
```

### 5. 任务管理

#### 获取任务状态

```http
GET /api/v1/tasks/{task_id}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task": {
      "task_id": "task_20240101_120000_abcdef123456",
      "task_type": "batch_scoring",
      "status": "completed",
      "priority": "normal",
      "created_at": "2024-01-01T12:00:00",
      "started_at": "2024-01-01T12:00:05",
      "completed_at": "2024-01-01T12:05:30",
      "progress": {
        "current": 10,
        "total": 10,
        "percentage": 100.0,
        "message": "已评分 10/10 个学生",
        "estimated_remaining": 0
      },
      "result": {
        "success": true,
        "data": {
          "total_students": 10,
          "successful_count": 10,
          "failed_count": 0,
          "results": [...]
        },
        "execution_time": 325.5,
        "created_files": ["results/batch_20240101_120500/scores.csv"]
      }
    }
  }
}
```

#### 获取任务列表

```http
GET /api/v1/tasks?status=completed&limit=20
```

**查询参数**:
- `status` (可选): 任务状态过滤 (`pending`, `running`, `completed`, `failed`, `cancelled`)
- `limit` (可选): 返回数量限制，默认20

### 6. 文件处理

#### 文件上传

```http
POST /api/v1/files/upload
Content-Type: multipart/form-data
```

**请求参数**:
- `file`: 文件对象（支持CSV, Excel, JSON, TXT格式）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "file_id": "file_20240101_120000_abcdef123456",
    "filename": "students.xlsx",
    "total_records": 50,
    "valid_records": 48,
    "preview": [
      {
        "id": "001",
        "name": "张三",
        "content": "我是一名计算机专业的学生..."
      }
    ]
  }
}
```

### 7. 统计信息

#### 获取系统统计

```http
GET /api/v1/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "api_stats": {
      "total_requests": 1250,
      "cache_hits": 890,
      "cache_misses": 360,
      "batch_requests": 45,
      "errors": 12,
      "cache_hit_rate": 71.2
    },
    "task_stats": {
      "total_tasks": 156,
      "completed_tasks": 142,
      "running_tasks": 3,
      "failed_tasks": 11
    },
    "config_stats": {
      "total_templates": 5,
      "total_dimensions": 8
    },
    "system_info": {
      "version": "1.0.0",
      "uptime": "N/A",
      "timestamp": "2024-01-01T12:00:00"
    }
  }
}
```

### 8. Webhook

#### 评分完成通知

```http
POST /api/v1/webhook/scoring-complete
```

**请求体**:
```json
{
  "task_id": "task_20240101_120000_abcdef123456",
  "status": "completed",
  "results": [...]
}
```

## 错误处理

### 标准错误响应格式

```json
{
  "success": false,
  "error": "错误描述",
  "error_code": "ERROR_CODE",
  "details": "详细错误信息（可选）"
}
```

### 常见错误码

| 错误码 | HTTP状态码 | 描述 |
|--------|------------|------|
| `MISSING_CREDENTIALS` | 400 | 缺少认证信息 |
| `INVALID_CREDENTIALS` | 401 | 用户名或密码错误 |
| `INVALID_TOKEN` | 401 | Token无效或过期 |
| `INSUFFICIENT_PERMISSIONS` | 403 | 权限不足 |
| `MISSING_STUDENTS` | 400 | 缺少学生数据 |
| `INVALID_STUDENT_FORMAT` | 400 | 学生数据格式错误 |
| `TEMPLATE_NOT_FOUND` | 404 | 模板不存在 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `UNSUPPORTED_FILE_TYPE` | 400 | 不支持的文件格式 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

## 限制和配额

### 请求限制

- **认证Token有效期**: 24小时
- **文件上传大小限制**: 16MB
- **批量评分最大学生数**: 1000
- **API请求频率**: 无限制（建议合理使用）

### 数据格式限制

- **学生姓名**: 最大100字符
- **学生内容**: 最大10000字符
- **自定义维度数量**: 最大10个
- **评分模板数量**: 最大50个

## SDK和示例代码

### Python SDK示例

```python
import requests
import json

class JudgeAIClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.token = self._login(username, password)
    
    def _login(self, username, password):
        response = requests.post(f"{self.base_url}/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        
        if response.json()['success']:
            return response.json()['data']['token']
        else:
            raise Exception("登录失败")
    
    def _request(self, method, endpoint, data=None):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/api/v1{endpoint}"
        response = requests.request(method, url, headers=headers, json=data)
        
        return response.json()
    
    def submit_scoring(self, students, template_id=None, async=True):
        return self._request("POST", "/scoring/submit", {
            "students": students,
            "template_id": template_id,
            "async": async
        })
    
    def get_task_status(self, task_id):
        return self._request("GET", f"/tasks/{task_id}")
    
    def get_templates(self):
        return self._request("GET", "/config/templates")

# 使用示例
client = JudgeAIClient("http://localhost:5000", "admin", "password123")

# 提交评分任务
result = client.submit_scoring([
    {
        "id": "001",
        "name": "张三",
        "content": "我是一名计算机专业的学生..."
    }
])

if result['success']:
    task_id = result['data']['task_id']
    print(f"任务已提交: {task_id}")
    
    # 查询任务状态
    status = client.get_task_status(task_id)
    print(f"任务状态: {status['data']['task']['status']}")
```

### JavaScript SDK示例

```javascript
class JudgeAIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const result = await response.json();
        if (result.success) {
            this.token = result.data.token;
            return result;
        } else {
            throw new Error(result.error);
        }
    }
    
    async request(method, endpoint, data = null) {
        const response = await fetch(`${this.baseUrl}/api/v1${endpoint}`, {
            method,
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: data ? JSON.stringify(data) : null
        });
        
        return await response.json();
    }
    
    async submitScoring(students, templateId = null, async = true) {
        return this.request('POST', '/scoring/submit', {
            students,
            template_id: templateId,
            async
        });
    }
    
    async getTaskStatus(taskId) {
        return this.request('GET', `/tasks/${taskId}`);
    }
}

// 使用示例
const client = new JudgeAIClient('http://localhost:5000');

await client.login('admin', 'password123');

const result = await client.submitScoring([
    {
        id: '001',
        name: '张三',
        content: '我是一名计算机专业的学生...'
    }
]);

if (result.success) {
    console.log('任务已提交:', result.data.task_id);
}
```

## Next.js版本特有API

### 9. 知识库管理 (Next.js版本特有)

#### 获取知识库文档列表

```http
GET /api/v1/knowledge/documents
```

**查询参数**:
- `search` (可选): 搜索关键词
- `category` (可选): 文档分类
- `limit` (可选): 返回数量限制，默认20

**响应示例**:
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "id": "doc_20240101_120000_abcdef123456",
        "title": "算法竞赛评分标准",
        "content": "详细的评分标准说明...",
        "category": "scoring_criteria",
        "tags": ["算法", "评分", "标准"],
        "embeddings_count": 156,
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
        "created_by": "admin"
      }
    ],
    "total": 1,
    "page": 1,
    "totalPages": 1
  }
}
```

#### 上传知识库文档

```http
POST /api/v1/knowledge/upload
Content-Type: multipart/form-data
```

**请求参数**:
- `file`: 文件对象（支持TXT, PDF, DOC, MD格式）
- `title`: 文档标题
- `category`: 文档分类
- `tags`: 文档标签（JSON数组）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "document": {
      "id": "doc_20240101_120000_new123456",
      "title": "新的评分文档",
      "category": "scoring_criteria",
      "tags": ["评分", "新文档"],
      "status": "processing",
      "embeddings_count": 0
    },
    "processing_status": "queued_for_embedding"
  }
}
```

#### 搜索知识库

```http
POST /api/v1/knowledge/search
```

**请求体**:
```json
{
  "query": "如何评估学生的算法能力",
  "limit": 5,
  "threshold": 0.7
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "document_id": "doc_20240101_120000_abcdef123456",
        "title": "算法竞赛评分标准",
        "snippet": "算法基础维度的评估应该包括...",
        "score": 0.89,
        "metadata": {
          "category": "scoring_criteria",
          "tags": ["算法", "评分"]
        }
      }
    ],
    "query": "如何评估学生的算法能力",
    "total_results": 1
  }
}
```

### 10. 模板管理 (Next.js版本特有)

#### 创建评分模板

```http
POST /api/v1/templates
```

**请求体**:
```json
{
  "name": "高级算法竞赛模板",
  "description": "适用于高级算法竞赛选拔的评分模板",
  "dimensions": [
    {
      "name": "算法思维",
      "weight": 0.3,
      "max_score": 30,
      "criteria": [
        {"range": "25-30", "description": "优秀的算法思维能力"},
        {"range": "15-24", "description": "良好的算法思维能力"},
        {"range": "0-14", "description": "算法思维能力有待提升"}
      ]
    },
    {
      "name": "代码实现",
      "weight": 0.3,
      "max_score": 30,
      "criteria": [
        {"range": "25-30", "description": "代码能力强，bug少"},
        {"range": "15-24", "description": "代码能力一般"},
        {"range": "0-14", "description": "代码实现能力较弱"}
      ]
    }
  ],
  "is_default": false
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "template": {
      "id": "tpl_20240101_120000_advanced123",
      "name": "高级算法竞赛模板",
      "description": "适用于高级算法竞赛选拔的评分模板",
      "dimensions_count": 2,
      "total_score": 60,
      "is_default": false,
      "is_active": true,
      "created_at": "2024-01-01T12:00:00",
      "created_by": "admin"
    }
  }
}
```

#### 获取模板详情

```http
GET /api/v1/templates/{template_id}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "template": {
      "id": "tpl_20240101_120000_advanced123",
      "name": "高级算法竞赛模板",
      "description": "适用于高级算法竞赛选拔的评分模板",
      "dimensions": [
        {
          "id": "dim_algorithm_thinking",
          "name": "算法思维",
          "weight": 0.3,
          "max_score": 30,
          "criteria": [...]
        }
      ],
      "is_default": false,
      "is_active": true,
      "usage_count": 15,
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:00:00",
      "created_by": "admin"
    }
  }
}
```

### 11. 用户管理 (Next.js版本特有)

#### 获取用户列表

```http
GET /api/v1/users
```

**查询参数**:
- `role` (可选): 用户角色过滤 (`admin`, `teacher`, `viewer`)
- `status` (可选): 用户状态过滤 (`active`, `inactive`)
- `limit` (可选): 返回数量限制，默认20

**响应示例**:
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "user_20240101_120000_admin123",
        "username": "admin",
        "email": "admin@judgeai.com",
        "name": "系统管理员",
        "role": "admin",
        "status": "active",
        "avatar": "/avatars/admin.png",
        "created_at": "2024-01-01T12:00:00",
        "last_login": "2024-01-01T15:30:00"
      }
    ],
    "total": 1,
    "page": 1,
    "totalPages": 1
  }
}
```

#### 创建用户

```http
POST /api/v1/users
```

**请求体**:
```json
{
  "username": "teacher1",
  "email": "teacher1@school.com",
  "name": "张老师",
  "password": "securePassword123",
  "role": "teacher",
  "profile": {
    "department": "计算机科学系",
    "title": "副教授"
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user_20240101_120000_teacher123",
      "username": "teacher1",
      "email": "teacher1@school.com",
      "name": "张老师",
      "role": "teacher",
      "status": "active",
      "created_at": "2024-01-01T12:00:00",
      "profile": {
        "department": "计算机科学系",
        "title": "副教授"
      }
    }
  }
}
```

### 12. 实时事件 (Next.js版本特有)

#### Server-Sent Events (SSE)

Next.js版本支持实时事件推送：

```http
GET /api/v1/events/stream
```

**客户端连接示例**:
```javascript
const eventSource = new EventSource('/api/v1/events/stream');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'task_update':
      console.log('任务更新:', data.payload);
      break;
    case 'scoring_progress':
      console.log('评分进度:', data.payload);
      break;
    case 'system_notification':
      console.log('系统通知:', data.payload);
      break;
  }
};

eventSource.onerror = function(err) {
  console.error('SSE连接错误:', err);
};
```

**事件格式**:
```json
{
  "type": "task_update|scoring_progress|system_notification",
  "timestamp": "2024-01-01T12:00:00",
  "payload": {
    // 事件特定数据
  }
}
```

### 13. 数据导出 (Next.js版本特有)

#### 导出评分结果

```http
POST /api/v1/export/scores
```

**请求体**:
```json
{
  "task_ids": ["task_20240101_120000_abcdef123456"],
  "format": "excel",
  "include_details": true,
  "template": "standard_report"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "export_id": "export_20240101_120000_xyz789",
    "status": "processing",
    "format": "excel",
    "download_url": null,
    "estimated_completion": "2024-01-01T12:02:00"
  }
}
```

#### 获取导出状态

```http
GET /api/v1/export/{export_id}/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "export": {
      "id": "export_20240101_120000_xyz789",
      "status": "completed",
      "format": "excel",
      "file_size": 2048576,
      "download_url": "/api/v1/export/export_20240101_120000_xyz789/download",
      "expires_at": "2024-01-08T12:00:00"
    }
  }
}
```

#### 下载导出文件

```http
GET /api/v1/export/{export_id}/download
```

返回文件流或重定向到下载URL。

## 更新日志

### v2.0.0 (Next.js版本, 2024-01-01)
- 全新的Next.js架构
- 集成RAG（检索增强生成）功能
- 支持向量数据库（Chroma/FAISS）
- 实时事件推送（SSE）
- 增强的用户管理系统
- 模板管理系统重构
- 数据导出功能
- 知识库管理
- 多模型AI支持
- 审计日志系统

### v1.0.0 (Flask版本, 2024-01-01)
- 初始API版本发布
- 支持用户认证和授权
- 提供完整的评分功能
- 支持异步任务处理
- 提供配置管理接口
- 支持文件上传和处理
- 提供系统统计信息
- 支持Webhook通知

## SDK和示例代码

### Next.js版本 TypeScript SDK

```typescript
interface JudgeAIConfig {
  baseUrl: string;
  timeout?: number;
}

interface User {
  id: string;
  username: string;
  email: string;
  name: string;
  role: 'admin' | 'teacher' | 'viewer';
}

interface Template {
  id: string;
  name: string;
  description: string;
  dimensions: Dimension[];
}

interface ScoringTask {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  results?: ScoringResult[];
}

class JudgeAINextJSClient {
  private config: JudgeAIConfig;
  private session?: any;

  constructor(config: JudgeAIConfig) {
    this.config = config;
  }

  // 认证
  async login(username: string, password: string): Promise<boolean> {
    const response = await fetch(`${this.config.baseUrl}/api/auth/callback/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, csrfToken: 'your-csrf-token' })
    });

    return response.ok;
  }

  // 模板管理
  async getTemplates(): Promise<Template[]> {
    const response = await this.authenticatedFetch('/api/v1/templates');
    const result = await response.json();
    return result.data.templates;
  }

  async createTemplate(template: Partial<Template>): Promise<Template> {
    const response = await this.authenticatedFetch('/api/v1/templates', {
      method: 'POST',
      body: JSON.stringify(template)
    });
    const result = await response.json();
    return result.data.template;
  }

  // 任务管理
  async getTasks(): Promise<ScoringTask[]> {
    const response = await this.authenticatedFetch('/api/v1/tasks');
    const result = await response.json();
    return result.data.tasks;
  }

  async createTask(students: any[], templateId: string): Promise<ScoringTask> {
    const response = await this.authenticatedFetch('/api/v1/tasks', {
      method: 'POST',
      body: JSON.stringify({ students, templateId })
    });
    const result = await response.json();
    return result.data.task;
  }

  // 知识库
  async searchKnowledge(query: string): Promise<any[]> {
    const response = await this.authenticatedFetch('/api/v1/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query })
    });
    const result = await response.json();
    return result.data.results;
  }

  // 实时事件
  subscribeToEvents(callback: (event: any) => void): EventSource {
    const eventSource = new EventSource(`${this.config.baseUrl}/api/v1/events/stream`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      callback(data);
    };
    return eventSource;
  }

  private async authenticatedFetch(endpoint: string, options?: RequestInit): Promise<Response> {
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        // NextAuth.js会自动处理session cookie
      },
      credentials: 'include',
      ...options
    };

    return fetch(`${this.config.baseUrl}${endpoint}`, defaultOptions);
  }
}

// 使用示例
const client = new JudgeAINextJSClient({
  baseUrl: 'http://localhost:3000',
  timeout: 10000
});

// 登录
await client.login('admin', 'password123');

// 获取模板列表
const templates = await client.getTemplates();

// 创建评分任务
const task = await client.createTask(
  [{ id: '001', name: '张三', content: '...' }],
  templates[0].id
);

// 订阅实时事件
client.subscribeToEvents((event) => {
  console.log('实时事件:', event);
});
```

## 支持和反馈

如有任何问题或建议，请联系技术支持团队：

- **Flask版本支持**:
  - 邮箱: flask-support@judgeai.com
  - 文档: https://docs.judgeai.com/flask
  - GitHub: https://github.com/JudgeAI/flask-api

- **Next.js版本支持**:
  - 邮箱: nextjs-support@judgeai.com
  - 文档: https://docs.judgeai.com/nextjs
  - GitHub: https://github.com/JudgeAI/nextjs-api

- **通用支持**:
  - 官网: https://judgeai.com
  - 社区论坛: https://community.judgeai.com
  - 技术博客: https://blog.judgeai.com