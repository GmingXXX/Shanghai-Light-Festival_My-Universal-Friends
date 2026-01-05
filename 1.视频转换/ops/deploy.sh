#!/bin/bash

# 透明视频转换器部署脚本
# 使用方法: ./deploy.sh [environment]
# environment: dev | staging | production

set -e

ENVIRONMENT=${1:-dev}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🚀 开始部署透明视频转换器 - 环境: $ENVIRONMENT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查部署依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    log_info "依赖检查通过"
}

# 环境配置
setup_environment() {
    log_info "设置环境配置..."
    
    ENV_FILE="$PROJECT_ROOT/.env"
    ENV_EXAMPLE="$PROJECT_ROOT/ops/env.example"
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warn "未找到 .env 文件，从示例创建..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_warn "请编辑 .env 文件配置您的环境变量"
        
        if [ "$ENVIRONMENT" != "dev" ]; then
            log_error "生产环境必须配置正确的环境变量"
            exit 1
        fi
    fi
    
    # 根据环境设置特定配置
    case $ENVIRONMENT in
        "production")
            export FLASK_ENV=production
            export REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
            export STORAGE_PROVIDER=${STORAGE_PROVIDER:-s3}
            ;;
        "staging")
            export FLASK_ENV=staging
            export REDIS_URL=${REDIS_URL:-redis://redis:6379/1}
            export STORAGE_PROVIDER=${STORAGE_PROVIDER:-minio}
            ;;
        *)
            export FLASK_ENV=development
            export REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
            export STORAGE_PROVIDER=${STORAGE_PROVIDER:-minio}
            ;;
    esac
    
    log_info "环境配置完成"
}

# 构建应用
build_application() {
    log_info "构建应用..."
    
    cd "$PROJECT_ROOT"
    
    # 构建后端
    log_info "构建后端镜像..."
    docker build -t alphavid-backend:$TIMESTAMP ./backend
    docker tag alphavid-backend:$TIMESTAMP alphavid-backend:latest
    
    # 构建前端（如果需要）
    if [ -f "./frontend/package.json" ]; then
        log_info "构建前端..."
        cd frontend
        npm ci
        npm run build
        cd ..
    fi
    
    log_info "应用构建完成"
}

# 运行测试
run_tests() {
    log_info "运行测试..."
    
    # 后端测试
    cd "$PROJECT_ROOT/backend"
    if [ -f "requirements.txt" ]; then
        log_info "运行后端测试..."
        docker run --rm \
            -v "$(pwd):/app" \
            -w /app \
            alphavid-backend:latest \
            python -m pytest tests/ -v || {
                log_error "后端测试失败"
                exit 1
            }
    fi
    
    # 前端测试
    cd "$PROJECT_ROOT/frontend"
    if [ -f "package.json" ]; then
        log_info "运行前端测试..."
        npm test || {
            log_error "前端测试失败"
            exit 1
        }
    fi
    
    log_info "测试通过"
}

# 部署服务
deploy_services() {
    log_info "部署服务..."
    
    cd "$PROJECT_ROOT"
    
    # 停止现有服务
    docker-compose -f ops/docker-compose.yml down || true
    
    # 清理旧的容器和镜像
    docker system prune -f
    
    # 启动服务
    docker-compose -f ops/docker-compose.yml up -d --build
    
    log_info "等待服务启动..."
    sleep 30
    
    # 健康检查
    health_check
    
    log_info "服务部署完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
            log_info "健康检查通过"
            return 0
        fi
        
        log_warn "健康检查失败，重试 $attempt/$max_attempts"
        sleep 5
        ((attempt++))
    done
    
    log_error "健康检查失败"
    return 1
}

# 数据库迁移（如果需要）
migrate_database() {
    log_info "执行数据库迁移..."
    
    # 这里可以添加数据库迁移逻辑
    # docker-compose exec api python manage.py migrate
    
    log_info "数据库迁移完成"
}

# 备份（生产环境）
backup_data() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "执行数据备份..."
        
        BACKUP_DIR="/backup/alphavid_$TIMESTAMP"
        mkdir -p "$BACKUP_DIR"
        
        # 备份 Redis 数据
        docker-compose exec redis redis-cli --rdb "$BACKUP_DIR/redis_dump.rdb"
        
        # 备份存储数据（如果使用本地存储）
        if [ "$STORAGE_PROVIDER" = "local" ]; then
            cp -r ./data "$BACKUP_DIR/"
        fi
        
        log_info "数据备份完成: $BACKUP_DIR"
    fi
}

# 回滚
rollback() {
    log_error "部署失败，执行回滚..."
    
    # 停止当前服务
    docker-compose -f ops/docker-compose.yml down
    
    # 恢复到上一个版本
    if docker images | grep -q "alphavid-backend:previous"; then
        docker tag alphavid-backend:previous alphavid-backend:latest
        docker-compose -f ops/docker-compose.yml up -d
        log_info "回滚完成"
    else
        log_error "没有找到可回滚的版本"
    fi
}

# 主部署流程
main() {
    log_info "开始部署流程..."
    
    # 创建备份标签
    if docker images | grep -q "alphavid-backend:latest"; then
        docker tag alphavid-backend:latest alphavid-backend:previous
    fi
    
    # 执行部署步骤
    check_dependencies
    setup_environment
    build_application
    
    # 只在非开发环境运行测试
    if [ "$ENVIRONMENT" != "dev" ]; then
        run_tests
    fi
    
    backup_data
    deploy_services
    
    # 如果健康检查失败，执行回滚
    if ! health_check; then
        rollback
        exit 1
    fi
    
    log_info "🎉 部署成功完成！"
    
    # 显示服务信息
    echo ""
    echo "服务地址:"
    echo "  - API: http://localhost:8000"
    echo "  - 前端: http://localhost:5173"
    echo "  - MinIO: http://localhost:9001"
    echo ""
    echo "查看日志: docker-compose -f ops/docker-compose.yml logs -f"
    echo "停止服务: docker-compose -f ops/docker-compose.yml down"
}

# 信号处理
trap rollback ERR

# 执行主函数
main "$@"
