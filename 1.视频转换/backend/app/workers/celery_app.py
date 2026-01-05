"""
Celery 应用配置
"""
from celery import Celery
from ..config import Config

# 创建 Celery 应用
celery_app = Celery(
    'alphavid_converter',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=['app.workers.video_processor']
)

# 配置 Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10分钟超时
    task_soft_time_limit=540,  # 9分钟软超时
    worker_prefetch_multiplier=1,  # 每次只处理一个任务
    task_acks_late=True,  # 任务完成后才确认
    worker_disable_rate_limits=False,
    task_compression='gzip',
    result_compression='gzip',
)
