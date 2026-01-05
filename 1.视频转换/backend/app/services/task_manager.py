"""
任务管理服务 - 处理任务状态、元数据存储
"""
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import redis
from ..config import Config, TaskStatus, ErrorCodes
from ..utils.logger import setup_logger

logger = setup_logger()


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(Config.REDIS_URL)
        self.task_prefix = "task:"
        self.file_prefix = "file:"
    
    def create_file_record(self, file_id: str, filename: str, size: int, duration: float = 0) -> dict:
        """
        创建文件记录
        
        Args:
            file_id: 文件ID
            filename: 文件名
            size: 文件大小（字节）
            duration: 视频时长（秒）
            
        Returns:
            文件记录字典
        """
        file_record = {
            'fileId': file_id,
            'name': filename,
            'size': size,
            'duration': duration,
            'uploadedAt': datetime.now().isoformat(),
            'storageKey': None  # 将在上传到存储后设置
        }
        
        # 存储到 Redis
        key = f"{self.file_prefix}{file_id}"
        self.redis_client.setex(
            key, 
            timedelta(hours=Config.FILE_RETENTION_HOURS), 
            json.dumps(file_record)
        )
        
        logger.info("File record created", file_id=file_id, filename=filename)
        return file_record
    
    def get_file_record(self, file_id: str) -> Optional[dict]:
        """获取文件记录"""
        key = f"{self.file_prefix}{file_id}"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def update_file_storage_key(self, file_id: str, storage_key: str) -> bool:
        """更新文件的存储键"""
        file_record = self.get_file_record(file_id)
        if not file_record:
            return False
        
        file_record['storageKey'] = storage_key
        key = f"{self.file_prefix}{file_id}"
        self.redis_client.setex(
            key,
            timedelta(hours=Config.FILE_RETENTION_HOURS),
            json.dumps(file_record)
        )
        return True
    
    def create_task(self, file_id: str, options: dict = None) -> str:
        """
        创建转换任务
        
        Args:
            file_id: 文件ID
            options: 转换选项
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        task_record = {
            'taskId': task_id,
            'fileId': file_id,
            'status': TaskStatus.PENDING,
            'options': options or {},
            'createdAt': datetime.now().isoformat(),
            'startedAt': None,
            'completedAt': None,
            'progress': 0,
            'resultUrl': None,
            'errorCode': None,
            'errorMessage': None
        }
        
        # 存储到 Redis
        key = f"{self.task_prefix}{task_id}"
        self.redis_client.setex(
            key,
            timedelta(hours=Config.FILE_RETENTION_HOURS),
            json.dumps(task_record)
        )
        
        logger.info("Task created", task_id=task_id, file_id=file_id)
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        key = f"{self.task_prefix}{task_id}"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def update_task_status(self, task_id: str, status: str, **kwargs) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            **kwargs: 其他要更新的字段
            
        Returns:
            是否更新成功
        """
        task_record = self.get_task_status(task_id)
        if not task_record:
            return False
        
        # 更新状态
        task_record['status'] = status
        
        # 根据状态更新时间戳
        if status == TaskStatus.RUNNING and not task_record.get('startedAt'):
            task_record['startedAt'] = datetime.now().isoformat()
        elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
            task_record['completedAt'] = datetime.now().isoformat()
        
        # 更新其他字段
        for key, value in kwargs.items():
            task_record[key] = value
        
        # 保存到 Redis
        redis_key = f"{self.task_prefix}{task_id}"
        self.redis_client.setex(
            redis_key,
            timedelta(hours=Config.FILE_RETENTION_HOURS),
            json.dumps(task_record)
        )
        
        logger.info("Task status updated", task_id=task_id, status=status, **kwargs)
        return True
    
    def set_task_running(self, task_id: str, progress: int = 0) -> bool:
        """设置任务为运行中"""
        return self.update_task_status(task_id, TaskStatus.RUNNING, progress=progress)
    
    def set_task_success(self, task_id: str, result_url: str) -> bool:
        """设置任务为成功完成"""
        return self.update_task_status(
            task_id, 
            TaskStatus.SUCCESS, 
            progress=100,
            resultUrl=result_url
        )
    
    def set_task_failed(self, task_id: str, error_code: str, error_message: str) -> bool:
        """设置任务为失败"""
        return self.update_task_status(
            task_id,
            TaskStatus.FAILED,
            errorCode=error_code,
            errorMessage=error_message
        )
    
    def get_tasks_by_status(self, status: str) -> List[dict]:
        """根据状态获取任务列表"""
        tasks = []
        pattern = f"{self.task_prefix}*"
        
        for key in self.redis_client.scan_iter(match=pattern):
            data = self.redis_client.get(key)
            if data:
                task = json.loads(data)
                if task.get('status') == status:
                    tasks.append(task)
        
        return tasks
    
    def cleanup_expired_tasks(self) -> int:
        """清理过期任务（超过保留时间）"""
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=Config.FILE_RETENTION_HOURS)
        
        # 清理任务
        for key in self.redis_client.scan_iter(match=f"{self.task_prefix}*"):
            data = self.redis_client.get(key)
            if data:
                task = json.loads(data)
                created_at = datetime.fromisoformat(task.get('createdAt', ''))
                if created_at < cutoff_time:
                    self.redis_client.delete(key)
                    cleaned_count += 1
        
        # 清理文件记录
        for key in self.redis_client.scan_iter(match=f"{self.file_prefix}*"):
            data = self.redis_client.get(key)
            if data:
                file_record = json.loads(data)
                uploaded_at = datetime.fromisoformat(file_record.get('uploadedAt', ''))
                if uploaded_at < cutoff_time:
                    self.redis_client.delete(key)
                    cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info("Cleaned up expired records", count=cleaned_count)
        
        return cleaned_count
    
    def get_batch_task_status(self, task_ids: List[str]) -> Dict[str, dict]:
        """批量获取任务状态"""
        results = {}
        
        for task_id in task_ids:
            task_status = self.get_task_status(task_id)
            if task_status:
                results[task_id] = task_status
            else:
                results[task_id] = {
                    'taskId': task_id,
                    'status': 'NOT_FOUND',
                    'errorCode': ErrorCodes.TASK_NOT_FOUND,
                    'errorMessage': 'Task not found'
                }
        
        return results


# 全局任务管理器实例
task_manager = TaskManager()
