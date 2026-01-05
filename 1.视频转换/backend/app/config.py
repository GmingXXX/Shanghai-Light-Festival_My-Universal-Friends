"""
配置文件 - 环境变量与常量
"""
import os
from typing import Optional


class Config:
    """基础配置类"""
    
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # Redis 配置
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Celery 配置
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # 存储配置
    STORAGE_PROVIDER = os.getenv('STORAGE_PROVIDER', 'local')  # 'local' | 's3' | 'minio'
    LOCAL_STORAGE_ROOT = os.getenv('LOCAL_STORAGE_ROOT', './data')
    
    # S3 配置
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    S3_REGION = os.getenv('S3_REGION', 'us-east-1')
    S3_BUCKET = os.getenv('S3_BUCKET', 'alphavid-converter')
    
    # MinIO 配置（开发环境）
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
    
    # 业务限制（与 PRD 对齐）
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
    MAX_FILES_PER_BATCH = int(os.getenv('MAX_FILES_PER_BATCH', '10'))
    MAX_DURATION_SECONDS = int(os.getenv('MAX_DURATION_SECONDS', '30'))
    
    # 支持的文件格式
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTS', 'mp4,mov,webm').split(','))
    
    # FFmpeg 配置
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')  # 使用 PATH 中的 ffmpeg
    
    # CORS 配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # 文件生命周期（小时）
    FILE_RETENTION_HOURS = int(os.getenv('FILE_RETENTION_HOURS', '24'))
    
    @classmethod
    def get_storage_config(cls) -> dict:
        """获取存储配置"""
        if cls.STORAGE_PROVIDER == 's3':
            return {
                'provider': 's3',
                'access_key': cls.AWS_ACCESS_KEY_ID,
                'secret_key': cls.AWS_SECRET_ACCESS_KEY,
                'region': cls.S3_REGION,
                'bucket': cls.S3_BUCKET
            }
        elif cls.STORAGE_PROVIDER == 'minio':
            return {
                'provider': 'minio',
                'endpoint': cls.MINIO_ENDPOINT,
                'access_key': cls.MINIO_ACCESS_KEY,
                'secret_key': cls.MINIO_SECRET_KEY,
                'secure': cls.MINIO_SECURE,
                'bucket': cls.S3_BUCKET
            }
        else:  # local
            return {
                'provider': 'local',
                'root_path': cls.LOCAL_STORAGE_ROOT
            }


# 错误码常量
class ErrorCodes:
    """错误码定义"""
    
    # 文件限制
    LIMIT_EXCEEDED_SIZE = 'LIMIT_EXCEEDED_SIZE'
    LIMIT_EXCEEDED_COUNT = 'LIMIT_EXCEEDED_COUNT' 
    LIMIT_EXCEEDED_DURATION = 'LIMIT_EXCEEDED_DURATION'
    
    # 格式问题
    UNSUPPORTED_FORMAT = 'UNSUPPORTED_FORMAT'
    INVALID_FILE = 'INVALID_FILE'
    
    # 处理错误
    FFMPEG_FAILED = 'FFMPEG_FAILED'
    STORAGE_ERROR = 'STORAGE_ERROR'
    TASK_NOT_FOUND = 'TASK_NOT_FOUND'
    
    # 系统错误
    INTERNAL_ERROR = 'INTERNAL_ERROR'


# 任务状态
class TaskStatus:
    """任务状态常量"""
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
