"""
pytest 配置文件
"""
import os
import tempfile
import pytest
from unittest.mock import Mock

# 设置测试环境变量
os.environ.update({
    'FLASK_ENV': 'testing',
    'REDIS_URL': 'redis://localhost:6379/15',  # 使用测试数据库
    'STORAGE_PROVIDER': 'local',
    'LOCAL_STORAGE_ROOT': tempfile.mkdtemp(),
    'SECRET_KEY': 'test-secret-key',
    'MAX_FILE_SIZE_MB': '50',
    'MAX_FILES_PER_BATCH': '10',
    'MAX_DURATION_SECONDS': '30',
    'ALLOWED_EXTS': 'mp4,mov,webm',
    'FFMPEG_PATH': 'ffmpeg',
})

from app.app import create_app
from app.services.task_manager import task_manager
from app.services.storage import storage_service


@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def mock_task_manager():
    """模拟任务管理器"""
    return Mock(spec=task_manager)


@pytest.fixture
def mock_storage_service():
    """模拟存储服务"""
    return Mock(spec=storage_service)


@pytest.fixture
def sample_file_info():
    """示例文件信息"""
    return {
        'fileId': 'test-file-id',
        'name': 'test-video.mp4',
        'size': 1048576,  # 1MB
        'duration': 10.5
    }


@pytest.fixture
def sample_task_info():
    """示例任务信息"""
    return {
        'taskId': 'test-task-id',
        'fileId': 'test-file-id',
        'status': 'PENDING',
        'options': {
            'color': '#000000',
            'tolerance': 10,
            'feather': 0.5,
            'applyToAll': True
        },
        'progress': 0,
        'resultUrl': None,
        'errorCode': None,
        'errorMessage': None
    }


@pytest.fixture
def cleanup_redis():
    """清理 Redis 测试数据"""
    yield
    # 测试后清理
    try:
        import redis
        r = redis.from_url(os.environ['REDIS_URL'])
        r.flushdb()
    except:
        pass
