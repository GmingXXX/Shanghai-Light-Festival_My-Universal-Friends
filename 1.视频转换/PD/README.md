# 透明视频转换器 (AlphaVid Converter)

将黑底（或纯色）视频一键转为带 Alpha 通道的透明视频，支持批量上传与下载，输出 WebM（VP8/VP9）等网页友好格式。适合设计师、运营与开发者快速制作透明动效。

## 🚀 快速启动

### 离线版本（最简单）

直接打开 `alphavid-converter-standalone.html` 文件即可使用，无需安装任何软件。

**特点：**
- 🌟 完全离线运行，数据不上传云端
- 🚀 单文件HTML，打开即用
- 💻 支持现代浏览器（Chrome、Firefox、Safari、Edge）
- 📱 响应式设计，支持移动端

**使用方法：**
1. 下载或克隆项目
2. 双击打开 `alphavid-converter-standalone.html`
3. 选择或拖拽视频文件
4. 调整参数（可选）
5. 点击转换并下载结果

**最近更新：**
- ✅ **关键修复**: 彻底解决单文件HTML进度条闪烁问题，确保实时平滑更新
- ✅ **离线版进度优化**: 完全重构单文件HTML的进度显示机制，支持详细处理阶段
- ✅ **进度同步修复**: 将进度回调移至video.onseeked事件，确保与实际处理同步
- ✅ **UI优化**: 改进待处理状态显示，使用动态进度条替代静态标签
- ✅ **重大更新**: 新增边缘检测优化算法，显著改善主体边界黑色残留问题
- ✅ 添加高级边界处理选项，支持边缘检测灵敏度和形态学处理调节
- ✅ 优化 FFmpeg 滤镜链，使用双重 colorkey + 边缘检测 + 自适应阈值处理
- ✅ 增强进度条动画效果，提升用户交互体验
- ✅ 实现多线程进度更新机制，每0.5秒更新一次处理进度
- ✅ 单文件HTML支持6个处理阶段的详细进度显示和预计剩余时间

### 使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd alphavid-converter

# 2. 配置环境变量
cp ops/env.example .env

# 3. 启动所有服务
docker-compose -f ops/docker-compose.yml up -d --build

# 4. 访问应用
# 前端: http://localhost:5173
# API: http://localhost:8000
# MinIO 控制台: http://localhost:9001 (minioadmin/minioadmin)
```

### 本地开发

#### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动 Redis (需要单独安装)
redis-server

# 启动 API 服务
python -m app.app

# 启动 Worker (新终端)
celery -A app.workers.celery_app worker --loglevel=info
```

#### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 📋 功能特性

- ✅ **多格式支持**: MP4, MOV, WebM 视频格式
- ✅ **批量处理**: 最多同时处理 10 个文件
- ✅ **实时预览**: 棋盘格背景预览透明效果
- ✅ **参数调节**: 颜色、容差、边缘平滑可调
- 🎯 **边界优化**: 边缘检测 + 自适应阈值处理，完美去除黑色残留
- ✅ **高级选项**: 边缘检测灵敏度、形态学处理等专业参数
- ✅ **去水印（新）**: 一键去除左上角水印（可调整 ROI 比例）
- ✅ **高质量输出**: VP9 编码，支持 Alpha 通道
- ✅ **自动清理**: 24小时后自动删除文件
- ✅ **批量下载**: ZIP 打包批量下载
- ✅ **响应式设计**: 支持桌面和移动端
- ✅ **离线版本**: 单文件HTML，无需安装，打开即用

## 🛠 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design
- **后端**: Python 3.11 + Flask + Celery + Redis
- **视频处理**: FFmpeg (VP9 + Alpha 通道)
- **存储**: S3/MinIO/本地存储
- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

---

## 一、总体架构与技术选型

- 前端：React（或 Vue）+ Ant Design / MUI
  - 负责文件上传、任务创建、状态轮询、结果预览（棋盘格背景）与下载/打包下载
- 后端：Python + Flask（或 FastAPI）
  - 提供上传、任务状态查询、单文件/打包下载、参数校验、鉴权（可选）
- 异步队列：Celery + Redis
  - 将视频转码工作从 Web 请求中解耦，提升并发与稳定性
- 视频处理：FFmpeg
  - 使用 colorkey/chromakey 滤镜抠除纯色背景，导出带 Alpha 的 VP9（yuva420p）
- 存储：S3 兼容对象存储（生产）/ 本地磁盘（开发）
  - 原始上传与处理结果分区存放，配置 24h 生命周期自动清理
- 部署：
  - 方案 A：Docker Compose（api、worker、redis、minio）
  - 方案 B：前端 Vercel/Netlify，后端 Render/Heroku，文件存 S3
- 监控与日志：
  - 统一结构化日志（JSON），接入 Sentry/云日志；健康检查与基础指标（处理时长、失败率）

---

## 二、目录结构（建议）

```
/（repo root）
  README.md
  frontend/
    src/
    package.json
  backend/
    app/
      api/               # 路由：upload/status/download/batch-download
      services/          # 业务：任务创建、参数校验、S3、压缩打包
      workers/           # Celery 任务：FFmpeg 转码
      utils/             # 工具：日志、异常、校验
      config.py
      app.py
    requirements.txt
    Dockerfile
  ops/
    docker-compose.yml   # api、worker、redis、minio（dev）
    env.example
  .github/workflows/
    ci.yml               # Lint/Test/Build 基础流水线
```

---

## 三、数据流与队列状态机

- 用户上传 → 后端存储原始文件，返回 `fileId`
- 用户点击“开始转换” → 为每个文件创建 `taskId`，入队 Celery 任务
- Worker 消费任务 → 拉取原始文件 → 执行 FFmpeg → 产出结果文件 → 回写存储与任务元数据
- 前端轮询 `/api/status?taskId=...` → 更新卡片状态与进度
- 用户下载单个或批量下载 Zip

任务状态机（TaskStatus）：
- PENDING（已创建，未开始）
- RUNNING（处理中）
- SUCCESS（完成，含 resultUrl、预览 URL）
- FAILED（失败，含失败原因 code/message）

---

## 四、API 设计（V1.0）

- POST `/api/upload`
  - 表单：`files[]`（最多 10 个）
  - 返回：`[{ fileId, name, size, duration }...]`
- POST `/api/convert`
  - 入参（JSON）：
    - `files: string[]`（fileId 列表，≤10）
    - `options`（可选，高级参数，默认隐藏）：
      - `color: string`（默认 `#000000`）
      - `tolerance: number`（0-100，默认 10 → similarity 映射）
      - `feather: number`（0-10，默认 0.5 → blend 映射）
      - `applyToAll: boolean`（默认 true）
  - 返回：`{ taskIds: string[] }`
- GET `/api/status?taskId=...`
  - 返回：`{ taskId, status, progress?, errorCode?, errorMessage?, resultUrl? }`
- GET `/api/download?fileId=...`
  - 鉴权（可选），返回处理后的 WebM 二进制流
- POST `/api/batch-download`
  - 入参：`{ taskIds: string[] }`
  - 返回：Zip 文件流（仅对 SUCCESS 状态的结果打包）

错误码（示例）：
- `LIMIT_EXCEEDED_SIZE`、`LIMIT_EXCEEDED_COUNT`、`LIMIT_EXCEEDED_DURATION`
- `UNSUPPORTED_FORMAT`、`FFMPEG_FAILED`、`STORAGE_ERROR`

---

## 五、参数映射与 FFmpeg 命令

- 颜色：`color` → colorkey 颜色，例如 `black` 或 `0x000000`
- 容差：`tolerance`（0-100）→ `similarity`（0.00-1.00），建议 `similarity = tolerance / 100`
- 边缘平滑：`feather`（0-10）→ `blend`（0.00-1.00），建议 `blend = feather / 10`

### 传统模式（向后兼容）：

```bash
ffmpeg -y -i input.mp4 \
  -vf "colorkey=color=black:similarity=0.10:blend=0.05" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -an output.webm
```

### 🎯 边界优化模式（推荐）：

```bash
ffmpeg -y -i input.mp4 \
  -vf "delogo=x=iw*0.0120:y=ih*0.0120:w=iw*0.1400:h=ih*0.0550:show=0,split=2[main][edge];
       [edge]edgedetect=mode=canny:low=0.10:high=0.40[edges];
       [main]colorkey=color=black:similarity=0.10:blend=0.05[main1];
       [main1]colorkey=color=0x0a0a0a:similarity=0.15:blend=0.025[main2];
       [main2]erosion=coordinates=1[main3];
       [main3]dilation=coordinates=1[main4];
       [main4][edges]blend=all_mode=multiply:all_opacity=0.3[enhanced];
       [enhanced]gblur=sigma=0.8:steps=1" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -an output.webm
```

**边界优化技术说明：**
- 🔍 **边缘检测**: 使用 Canny 算法精确识别主体边界
- 🎯 **双重抠像**: 先处理主要黑色区域，再处理残留深色边缘
- 🧹 **形态学处理**: 去除小的黑色斑点和噪点
- 🌟 **边缘增强**: 结合边缘检测结果优化 Alpha 通道
- 💫 **柔化处理**: 轻微高斯模糊平滑边缘

### 去水印（左上角）

- 默认开启，使用 FFmpeg `delogo` 于滤镜链最前。
- 默认 ROI 比例：x=1.2%、y=1.2%、w=14%、h=5.5%。
- 可通过选项覆盖：`removeWatermark`、`wmX`、`wmY`、`wmW`、`wmH`（百分比 0-100）。

示例（等价于默认值）：

```bash
ffmpeg -y -i input.mp4 \
  -vf "delogo=x=iw*0.012:y=ih*0.012:w=iw*0.14:h=ih*0.055:show=0, ...其余滤镜..." \
  -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -an output.webm
```

说明：
- `-pix_fmt yuva420p` 与 `-auto-alt-ref 0` 是 VP9 Alpha 的关键
- 边界优化模式特别适用于发光效果、烟雾、头发丝等复杂边界
- 结果用于网页预览/使用；V1.5 可追加 `.mov`（ProRes 4444）等

---

## 六、限制与校验（与 PRD 对齐）

- 单文件大小 ≤ 50MB
- 单次最多 10 个文件
- 单个视频时长 ≤ 30 秒
- 支持格式：`.mp4` `.mov` `.webm`
- 后端在 `upload` 与 `convert` 双重校验，失败返回可读错误信息

---

## 七、存储与生命周期

- 目录布局（S3 示例）：
  - `raw/{yyyy}/{mm}/{dd}/{uuid}.ext` 原始上传
  - `processed/{yyyy}/{mm}/{dd}/{uuid}.webm` 结果
  - `temp/` 批量打包临时产物（可选，建议流式打包避免落盘）
- 生命周期：
  - 原始与结果默认 24h 自动删除（生产用存储策略；开发用定时清理）

---

## 八、环境变量（示例）

- `FLASK_ENV=development|production`
- `SECRET_KEY=...`
- `REDIS_URL=redis://redis:6379/0`
- `STORAGE_PROVIDER=s3|local`
- （S3）`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`S3_REGION`、`S3_BUCKET`
- （本地）`LOCAL_STORAGE_ROOT=/data`
- `MAX_FILE_SIZE_MB=50`、`MAX_FILES_PER_BATCH=10`、`MAX_DURATION_SECONDS=30`
- `FFMPEG_PATH=/usr/bin/ffmpeg`（或使用系统 PATH）
- `ALLOWED_EXTS=mp4,mov,webm`
- `CORS_ORIGINS=*`（生产请收敛）

---

## 九、本地开发指引

### 方案 A：Docker Compose（推荐）

- 依赖：Docker Desktop、Git
- 启动：

```bash
# 1. 复制环境变量
cp ops/env.example .env

# 2. 启动
docker compose -f ops/docker-compose.yml up -d --build

# 3. 访问
# 前端：http://localhost:5173  (若使用 Vite)
# 后端：http://localhost:8000
```

### 方案 B：裸机开发（Windows/macOS/Linux）

- 安装 FFmpeg：
  - Windows：推荐下载静态编译包并加入 PATH
  - macOS：`brew install ffmpeg`
  - Ubuntu：`sudo apt-get install -y ffmpeg`
- 启动后端：

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export FLASK_ENV=development
export REDIS_URL=redis://localhost:6379/0
python app/app.py
```

- 启动队列 Worker：

```bash
cd backend
celery -A app.workers.celery_app worker --concurrency=2 --loglevel=INFO
```

- 启动前端（以 React+Vite 为例）：

```bash
cd frontend
npm i
npm run dev
```

---

## 十、部署方案

### 方案 A：一体化（Docker Compose）
- 组件：api、worker、redis、nginx（可选静态托管）、对象存储（生产用 S3，开发用 minio）
- 优点：环境一致、可控性强；缺点：需自管主机与安全

### 方案 B：前后端分离 + 托管
- 前端：Vercel/Netlify 静态托管
- 后端：Render/Heroku 提供长期运行容器
- 文件：AWS S3（配置生命周期）
- 优点：省运维、弹性扩展；缺点：带宽与外部依赖受限

---

## 十一、CI/CD 与质量保障

- GitHub Actions：
  - 后端：lint（flake8/ruff）、单测（pytest）、安全扫描（bandit）
  - 前端：lint（eslint）、单测（vitest/jest）、构建
- 构建产物：前端静态文件、后端镜像
- 基准指标：
  - 10 秒、720p 视频目标 30 秒内处理完成（单个任务）
  - 失败率 < 1%，可重试 2 次

---

## 十二、日志、监控与告警

- 结构化日志：traceId、taskId、fileId、时长、失败原因
- 监控：处理时长 P50/P95、并发任务数、队列堆积、错误比率
- 告警：队列堆积阈值、FFmpeg 失败率、存储失败率

---

## 十三、测试计划（V1.0）

- 单元测试：
  - 参数校验、任务创建、状态机转换、FFmpeg 命令构建
- 集成测试：
  - 端到端：上传 → 转码 → 预览 → 下载/打包
  - 边界：超限、错误格式、损坏文件、超时重试
- 性能测试：
  - 并发 5/10/20，文件大小与时长维度下的时延统计
- 回归测试：
  - 关键路径与历史缺陷用例覆盖

---

## 十四、里程碑与排期（示例）

- M1（第1周）：项目脚手架、上传与存储、基础 UI、队列打通
- M2（第2周）：FFmpeg 转码 Alpha、状态轮询与预览、单文件下载
- M3（第3周）：批量打包下载、错误处理与重试、日志与监控
- M4（第4周）：性能优化、跨浏览器验证、发布与文档完善

---

## 十五、风险与应对

- FFmpeg Alpha 兼容性：
  - 采用 VP9 `yuva420p`，提供兼容性检测与降级提示
- 大视频/高并发：
  - 后端限流与队列隔离，超时/重试与熔断策略
- 存储成本与清理：
  - 生命周期 24h 清理，后台定时核查漏删
- 浏览器预览兼容：
  - 提供回退提示与静态占位，Safari/移动端专项验证

---

## 十六、隐私与合规

- 明示隐私政策与数据保留（默认 24h 内自动删除）
- 加密传输（HTTPS），访问控制（私有存储 + 临时签名 URL）
- 日志脱敏（仅保留必要元数据）

---

## 十七、后续迭代（与 PRD 路线图一致）

- V1.1：更多输入/输出格式（GIF/APNG）、移动端体验优化、前后对比预览
- V1.2：绿幕/蓝幕 `chromakey` 优化、尺寸裁剪与简单编辑
- V2.0：用户体系、付费与加速通道、开放 API

---

## 附录：返回结构示例

- 上传：
```json
[
  { "fileId": "f_123", "name": "a.mp4", "size": 10485760, "duration": 9.8 },
  { "fileId": "f_124", "name": "b.mov", "size": 20480000, "duration": 12.3 }
]
```

- 转换：
```json
{ "taskIds": ["t_501", "t_502"] }
```

- 状态：
```json
{
  "taskId": "t_501",
  "status": "SUCCESS",
  "resultUrl": "https://.../processed/2025/09/16/uuid.webm"
}
```
