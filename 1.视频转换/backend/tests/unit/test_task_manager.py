"""
测试任务管理器
"""
import pytest
import json
from unittest.mock import Mock, patch

from app.services.task_manager import TaskManager
from app.config import TaskStatus


class TestTaskManager:
    """测试任务管理器"""
    
    @pytest.fixture
    def task_manager(self):
        """创建任务管理器实例"""
        with patch('app.services.task_manager.redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            tm = TaskManager()
            tm.redis_client = mock_client
            return tm
    
    def test_create_file_record(self, task_manager):
        """测试创建文件记录"""
        file_id = 'test-file-id'
        filename = 'test.mp4'
        size = 1048576
        duration = 10.5
        
        result = task_manager.create_file_record(file_id, filename, size, duration)
        
        # 检查返回结果
        assert result['fileId'] == file_id
        assert result['name'] == filename
        assert result['size'] == size
        assert result['duration'] == duration
        assert 'uploadedAt' in result
        assert result['storageKey'] is None
        
        # 检查 Redis 调用
        task_manager.redis_client.setex.assert_called_once()
        args = task_manager.redis_client.setex.call_args[0]
        assert args[0] == f"file:{file_id}"
        
        # 检查存储的数据
        stored_data = json.loads(args[2])
        assert stored_data['fileId'] == file_id
    
    def test_get_file_record(self, task_manager):
        """测试获取文件记录"""
        file_id = 'test-file-id'
        expected_data = {
            'fileId': file_id,
            'name': 'test.mp4',
            'size': 1048576,
            'duration': 10.5
        }
        
        # 模拟 Redis 返回数据
        task_manager.redis_client.get.return_value = json.dumps(expected_data)
        
        result = task_manager.get_file_record(file_id)
        
        assert result == expected_data
        task_manager.redis_client.get.assert_called_once_with(f"file:{file_id}")
    
    def test_get_file_record_not_found(self, task_manager):
        """测试获取不存在的文件记录"""
        file_id = 'non-existent-id'
        
        # 模拟 Redis 返回 None
        task_manager.redis_client.get.return_value = None
        
        result = task_manager.get_file_record(file_id)
        
        assert result is None
    
    def test_create_task(self, task_manager):
        """测试创建任务"""
        file_id = 'test-file-id'
        options = {
            'color': '#000000',
            'tolerance': 10,
            'feather': 0.5
        }
        
        with patch('app.services.task_manager.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = 'test-task-id'
            mock_uuid.return_value.__str__ = lambda x: 'test-task-id'
            
            task_id = task_manager.create_task(file_id, options)
        
        assert task_id == 'test-task-id'
        
        # 检查 Redis 调用
        task_manager.redis_client.setex.assert_called_once()
        args = task_manager.redis_client.setex.call_args[0]
        assert args[0] == f"task:test-task-id"
        
        # 检查存储的数据
        stored_data = json.loads(args[2])
        assert stored_data['taskId'] == 'test-task-id'
        assert stored_data['fileId'] == file_id
        assert stored_data['status'] == TaskStatus.PENDING
        assert stored_data['options'] == options
    
    def test_update_task_status(self, task_manager):
        """测试更新任务状态"""
        task_id = 'test-task-id'
        existing_task = {
            'taskId': task_id,
            'status': TaskStatus.PENDING,
            'progress': 0,
            'startedAt': None
        }
        
        # 模拟获取现有任务
        task_manager.redis_client.get.return_value = json.dumps(existing_task)
        
        result = task_manager.update_task_status(
            task_id, 
            TaskStatus.RUNNING, 
            progress=50
        )
        
        assert result == True
        
        # 检查更新调用
        task_manager.redis_client.setex.assert_called()
        args = task_manager.redis_client.setex.call_args[0]
        updated_data = json.loads(args[2])
        
        assert updated_data['status'] == TaskStatus.RUNNING
        assert updated_data['progress'] == 50
        assert updated_data['startedAt'] is not None  # 应该设置开始时间
    
    def test_set_task_success(self, task_manager):
        """测试设置任务成功"""
        task_id = 'test-task-id'
        result_url = 'http://example.com/result.webm'
        
        existing_task = {
            'taskId': task_id,
            'status': TaskStatus.RUNNING,
            'progress': 50
        }
        
        task_manager.redis_client.get.return_value = json.dumps(existing_task)
        
        result = task_manager.set_task_success(task_id, result_url)
        
        assert result == True
        
        # 检查更新
        args = task_manager.redis_client.setex.call_args[0]
        updated_data = json.loads(args[2])
        
        assert updated_data['status'] == TaskStatus.SUCCESS
        assert updated_data['progress'] == 100
        assert updated_data['resultUrl'] == result_url
        assert updated_data['completedAt'] is not None
    
    def test_set_task_failed(self, task_manager):
        """测试设置任务失败"""
        task_id = 'test-task-id'
        error_code = 'FFMPEG_FAILED'
        error_message = 'FFmpeg processing failed'
        
        existing_task = {
            'taskId': task_id,
            'status': TaskStatus.RUNNING,
            'progress': 30
        }
        
        task_manager.redis_client.get.return_value = json.dumps(existing_task)
        
        result = task_manager.set_task_failed(task_id, error_code, error_message)
        
        assert result == True
        
        # 检查更新
        args = task_manager.redis_client.setex.call_args[0]
        updated_data = json.loads(args[2])
        
        assert updated_data['status'] == TaskStatus.FAILED
        assert updated_data['errorCode'] == error_code
        assert updated_data['errorMessage'] == error_message
        assert updated_data['completedAt'] is not None
    
    def test_get_batch_task_status(self, task_manager):
        """测试批量获取任务状态"""
        task_ids = ['task-1', 'task-2', 'non-existent']
        
        # 模拟 Redis 返回
        def mock_get(key):
            if key == 'task:task-1':
                return json.dumps({'taskId': 'task-1', 'status': 'SUCCESS'})
            elif key == 'task:task-2':
                return json.dumps({'taskId': 'task-2', 'status': 'RUNNING'})
            else:
                return None
        
        task_manager.redis_client.get.side_effect = mock_get
        
        results = task_manager.get_batch_task_status(task_ids)
        
        assert len(results) == 3
        assert results['task-1']['status'] == 'SUCCESS'
        assert results['task-2']['status'] == 'RUNNING'
        assert results['non-existent']['status'] == 'NOT_FOUND'
