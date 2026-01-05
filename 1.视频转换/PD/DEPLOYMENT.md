# 透明视频转换器 - 部署指南

## 快速开始

### 开发环境部署

1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd alphavid-converter
   ```

2. **配置环境变量**
   ```bash
   cp ops/env.example .env
   # 编辑 .env 文件配置您的环境
   ```

3. **使用 Docker Compose 启动**
   ```bash
   docker-compose -f ops/docker-compose.yml up -d --build
   ```

4. **访问应用**
   - 前端：http://localhost:5173
   - API：http://localhost:8000
   - MinIO 控制台：http://localhost:9001

### 生产环境部署

#### 方案一：Docker Compose（推荐）

1. **准备服务器**
   - Ubuntu 20.04+ 或 CentOS 7+
   - 至少 4GB RAM，2 CPU 核心
   - 安装 Docker 和 Docker Compose

2. **配置环境**
   ```bash
   # 创建生产环境配置
   cp ops/env.example .env
   
   # 编辑关键配置
   FLASK_ENV=production
   SECRET_KEY=your-production-secret-key
   STORAGE_PROVIDER=s3
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   S3_BUCKET=your-bucket-name
   ```

3. **部署**
   ```bash
   ./ops/deploy.sh production
   ```

4. **配置反向代理（Nginx）**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5173;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           client_max_body_size 500M;
       }
   }
   ```

#### 方案二：云服务分离部署

1. **前端部署（Vercel/Netlify）**
   ```bash
   cd frontend
   npm run build
   # 将 dist 目录部署到静态托管服务
   ```

2. **后端部署（Render/Heroku）**
   ```dockerfile
   # 使用 backend/Dockerfile
   # 配置环境变量
   # 部署到容器平台
   ```

3. **存储配置（AWS S3）**
   - 创建 S3 存储桶
   - 配置生命周期规则（24小时自动删除）
   - 设置 CORS 策略

## 环境变量说明

### 必需配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `SECRET_KEY` | Flask 密钥 | `your-secret-key` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `STORAGE_PROVIDER` | 存储类型 | `s3` / `minio` / `local` |

### S3 配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `AWS_ACCESS_KEY_ID` | AWS 访问密钥 | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS 密钥 | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `S3_REGION` | S3 区域 | `us-east-1` |
| `S3_BUCKET` | S3 存储桶 | `alphavid-converter` |

### 业务配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MAX_FILE_SIZE_MB` | 最大文件大小(MB) | `50` |
| `MAX_FILES_PER_BATCH` | 批量文件数限制 | `10` |
| `MAX_DURATION_SECONDS` | 视频时长限制(秒) | `30` |
| `FILE_RETENTION_HOURS` | 文件保留时间(小时) | `24` |

## 监控与维护

### 健康检查

```bash
curl http://localhost:8000/api/health
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f ops/docker-compose.yml logs -f

# 查看特定服务日志
docker-compose -f ops/docker-compose.yml logs -f api
docker-compose -f ops/docker-compose.yml logs -f worker
```

### 性能监控

1. **系统资源监控**
   - CPU 使用率
   - 内存使用率
   - 磁盘空间
   - 网络带宽

2. **应用指标监控**
   - 请求响应时间
   - 任务处理时长
   - 错误率
   - 队列长度

### 备份策略

1. **Redis 数据备份**
   ```bash
   docker-compose exec redis redis-cli --rdb /backup/redis_dump.rdb
   ```

2. **配置文件备份**
   ```bash
   tar -czf config_backup.tar.gz .env ops/
   ```

3. **日志备份**
   ```bash
   docker-compose logs > logs_backup.txt
   ```

## 故障排除

### 常见问题

1. **FFmpeg 处理失败**
   - 检查视频文件格式是否支持
   - 验证 FFmpeg 是否正确安装
   - 查看 worker 日志获取详细错误

2. **存储连接失败**
   - 验证 S3/MinIO 连接配置
   - 检查网络连接
   - 确认存储桶权限

3. **内存不足**
   - 增加服务器内存
   - 调整 worker 并发数
   - 优化 FFmpeg 参数

4. **Redis 连接失败**
   - 检查 Redis 服务状态
   - 验证连接字符串
   - 检查防火墙设置

### 日志分析

```bash
# 查找错误日志
docker-compose logs | grep -i error

# 查找特定任务日志
docker-compose logs | grep "task_id:your-task-id"

# 监控实时日志
docker-compose logs -f --tail=100
```

## 扩展部署

### 水平扩展

1. **增加 Worker 实例**
   ```yaml
   worker:
     deploy:
       replicas: 4
   ```

2. **负载均衡**
   ```nginx
   upstream api_backend {
       server localhost:8000;
       server localhost:8001;
       server localhost:8002;
   }
   ```

### 高可用部署

1. **Redis 主从配置**
2. **多区域部署**
3. **故障转移策略**

## 安全配置

### HTTPS 配置

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
}
```

### 防火墙设置

```bash
# 只开放必要端口
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### 访问限制

```nginx
# API 访问频率限制
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api {
    limit_req zone=api burst=20 nodelay;
}
```

## 性能优化

### 缓存配置

```nginx
# 静态资源缓存
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 压缩配置

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

## 更新部署

### 滚动更新

```bash
# 拉取最新代码
git pull origin main

# 重新部署
./ops/deploy.sh production
```

### 回滚

```bash
# 查看部署历史
docker images | grep alphavid-backend

# 回滚到上一版本
docker tag alphavid-backend:previous alphavid-backend:latest
docker-compose up -d
```
