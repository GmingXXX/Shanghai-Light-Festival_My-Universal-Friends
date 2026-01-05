"""
API 集成测试
"""
import pytest
import json
import tempfile
from unittest.mock import patch, Mock
from io import BytesIO

from app.config import ErrorCodes


class TestUploadAPI:
    """测试文件上传 API"""
    
    def test_upload_success(self, client):
        """测试成功上传文件"""
        # 创建模拟视频文件
        file_data = BytesIO(b'fake video data')
        
        with patch('app.api.routes.get_file_info') as mock_get_info, \
             patch('app.api.routes.validate_video_duration') as mock_validate_duration, \
             patch('app.api.routes.task_manager') as mock_task_manager, \
             patch('app.api.routes.storage_service') as mock_storage:
            
            # 配置模拟
            mock_get_info.return_value = {
                'name': 'test.mp4',
                'size': 1048576,
                'duration': 10.0
            }
            mock_validate_duration.return_value = (True, 10.0)
            mock_task_manager.create_file_record.return_value = {
                'fileId': 'test-file-id',
                'name': 'test.mp4',
                'size': 1048576,
                'duration': 10.0
            }
            mock_storage.upload_raw_file.return_value = 'storage-url'
            mock_storage.generate_file_key.return_value = 'raw/2025/09/16/test-file-id.mp4'
            
            response = client.post('/api/upload', data={
                'files': (file_data, 'test.mp4')
            }, content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['fileId'] == 'test-file-id'
        assert data[0]['name'] == 'test.mp4'
    
    def test_upload_no_files(self, client):
        """测试没有文件的上传请求"""
        response = client.post('/api/upload', data={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.INVALID_FILE
    
    def test_upload_invalid_extension(self, client):
        """测试无效扩展名的文件上传"""
        file_data = BytesIO(b'fake data')
        
        response = client.post('/api/upload', data={
            'files': (file_data, 'test.avi')
        }, content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.UNSUPPORTED_FORMAT


class TestConvertAPI:
    """测试转换 API"""
    
    def test_convert_success(self, client):
        """测试成功启动转换"""
        with patch('app.api.routes.task_manager') as mock_task_manager, \
             patch('app.api.routes.process_video') as mock_process_video:
            
            # 配置模拟
            mock_task_manager.get_file_record.return_value = {
                'fileId': 'test-file-id',
                'name': 'test.mp4'
            }
            mock_task_manager.create_task.return_value = 'test-task-id'
            mock_process_video.delay.return_value = Mock()
            
            response = client.post('/api/convert', 
                json={
                    'files': ['test-file-id'],
                    'options': {
                        'color': '#000000',
                        'tolerance': 10,
                        'feather': 0.5
                    }
                })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['taskIds'] == ['test-task-id']
    
    def test_convert_no_files(self, client):
        """测试没有文件ID的转换请求"""
        response = client.post('/api/convert', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.INVALID_FILE
    
    def test_convert_file_not_found(self, client):
        """测试文件不存在的转换请求"""
        with patch('app.api.routes.task_manager') as mock_task_manager:
            mock_task_manager.get_file_record.return_value = None
            
            response = client.post('/api/convert', 
                json={'files': ['non-existent-id']})
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.TASK_NOT_FOUND
    
    def test_convert_invalid_options(self, client):
        """测试无效转换选项"""
        with patch('app.api.routes.task_manager') as mock_task_manager:
            mock_task_manager.get_file_record.return_value = {
                'fileId': 'test-file-id'
            }
            
            response = client.post('/api/convert', 
                json={
                    'files': ['test-file-id'],
                    'options': {
                        'tolerance': 150  # 超出范围
                    }
                })
        
        assert response.status_code == 400


class TestStatusAPI:
    """测试状态查询 API"""
    
    def test_get_status_success(self, client):
        """测试成功获取任务状态"""
        with patch('app.api.routes.task_manager') as mock_task_manager:
            mock_task_manager.get_task_status.return_value = {
                'taskId': 'test-task-id',
                'status': 'SUCCESS',
                'progress': 100,
                'resultUrl': 'http://example.com/result.webm'
            }
            
            response = client.get('/api/status?taskId=test-task-id')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['taskId'] == 'test-task-id'
        assert data['status'] == 'SUCCESS'
        assert data['resultUrl'] == 'http://example.com/result.webm'
    
    def test_get_status_no_task_id(self, client):
        """测试没有任务ID的状态查询"""
        response = client.get('/api/status')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.INVALID_FILE
    
    def test_get_status_not_found(self, client):
        """测试任务不存在的状态查询"""
        with patch('app.api.routes.task_manager') as mock_task_manager:
            mock_task_manager.get_task_status.return_value = None
            
            response = client.get('/api/status?taskId=non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.TASK_NOT_FOUND


class TestDownloadAPI:
    """测试下载 API"""
    
    def test_download_success(self, client):
        """测试成功下载文件"""
        with patch('app.api.routes.storage_service') as mock_storage, \
             patch('app.api.routes.tempfile.NamedTemporaryFile') as mock_temp:
            
            # 配置模拟
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.webm'
            mock_storage.download_file.return_value = True
            
            response = client.get('/api/download?fileId=test-file-id')
        
        # 由于 send_file 在测试环境中的行为，我们主要检查是否调用了存储服务
        mock_storage.download_file.assert_called_once()
    
    def test_download_no_file_id(self, client):
        """测试没有文件ID的下载请求"""
        response = client.get('/api/download')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.INVALID_FILE
    
    def test_download_file_not_found(self, client):
        """测试文件不存在的下载请求"""
        with patch('app.api.routes.storage_service') as mock_storage, \
             patch('app.api.routes.tempfile.NamedTemporaryFile') as mock_temp:
            
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.webm'
            mock_storage.download_file.return_value = False
            
            response = client.get('/api/download?fileId=non-existent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error']['code'] == ErrorCodes.TASK_NOT_FOUND


class TestHealthAPI:
    """测试健康检查 API"""
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'alphavid-converter'
