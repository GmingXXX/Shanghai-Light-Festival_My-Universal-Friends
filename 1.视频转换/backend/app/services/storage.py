"""
文件存储服务 - 支持本地存储、S3、MinIO
"""
import os
import shutil
from datetime import datetime
from typing import Optional, BinaryIO
from abc import ABC, abstractmethod

import boto3
from minio import Minio
from botocore.exceptions import ClientError

from ..config import Config, ErrorCodes
from ..utils.logger import setup_logger

logger = setup_logger()


class StorageProvider(ABC):
    """存储提供者抽象基类"""
    
    @abstractmethod
    def upload_file(self, file_data: BinaryIO, key: str) -> str:
        """上传文件，返回文件URL或路径"""
        pass
    
    @abstractmethod
    def download_file(self, key: str, local_path: str) -> bool:
        """下载文件到本地路径"""
        pass
    
    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    def get_file_url(self, key: str) -> str:
        """获取文件访问URL"""
        pass


class LocalStorageProvider(StorageProvider):
    """本地存储提供者"""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        os.makedirs(root_path, exist_ok=True)
    
    def _get_full_path(self, key: str) -> str:
        """获取文件完整路径"""
        return os.path.join(self.root_path, key)
    
    def upload_file(self, file_data: BinaryIO, key: str) -> str:
        """上传文件到本地存储"""
        try:
            file_path = self._get_full_path(key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
            
            logger.info("File uploaded to local storage", key=key, path=file_path)
            return file_path
        except Exception as e:
            logger.error("Local upload failed", key=key, error=str(e))
            raise StorageError(f"Failed to upload file: {str(e)}")
    
    def download_file(self, key: str, local_path: str) -> bool:
        """从本地存储下载文件（实际上是复制）"""
        try:
            source_path = self._get_full_path(key)
            if not os.path.exists(source_path):
                return False
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            shutil.copy2(source_path, local_path)
            return True
        except Exception as e:
            logger.error("Local download failed", key=key, error=str(e))
            return False
    
    def delete_file(self, key: str) -> bool:
        """删除本地文件"""
        try:
            file_path = self._get_full_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("File deleted from local storage", key=key)
            return True
        except Exception as e:
            logger.error("Local delete failed", key=key, error=str(e))
            return False
    
    def get_file_url(self, key: str) -> str:
        """获取本地文件路径（作为URL）"""
        return self._get_full_path(key)


class S3StorageProvider(StorageProvider):
    """AWS S3 存储提供者"""
    
    def __init__(self, access_key: str, secret_key: str, region: str, bucket: str):
        self.bucket = bucket
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    
    def upload_file(self, file_data: BinaryIO, key: str) -> str:
        """上传文件到 S3"""
        try:
            self.s3_client.upload_fileobj(file_data, self.bucket, key)
            logger.info("File uploaded to S3", bucket=self.bucket, key=key)
            return f"s3://{self.bucket}/{key}"
        except ClientError as e:
            logger.error("S3 upload failed", bucket=self.bucket, key=key, error=str(e))
            raise StorageError(f"Failed to upload to S3: {str(e)}")
    
    def download_file(self, key: str, local_path: str) -> bool:
        """从 S3 下载文件"""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket, key, local_path)
            return True
        except ClientError as e:
            logger.error("S3 download failed", bucket=self.bucket, key=key, error=str(e))
            return False
    
    def delete_file(self, key: str) -> bool:
        """从 S3 删除文件"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("File deleted from S3", bucket=self.bucket, key=key)
            return True
        except ClientError as e:
            logger.error("S3 delete failed", bucket=self.bucket, key=key, error=str(e))
            return False
    
    def get_file_url(self, key: str) -> str:
        """获取 S3 文件的预签名 URL"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=3600  # 1小时有效期
            )
            return url
        except ClientError as e:
            logger.error("S3 URL generation failed", bucket=self.bucket, key=key, error=str(e))
            return f"s3://{self.bucket}/{key}"


class MinIOStorageProvider(StorageProvider):
    """MinIO 存储提供者"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
        self.bucket = bucket
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # 确保 bucket 存在
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
    
    def upload_file(self, file_data: BinaryIO, key: str) -> str:
        """上传文件到 MinIO"""
        try:
            # 获取文件大小
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            
            self.client.put_object(self.bucket, key, file_data, file_size)
            logger.info("File uploaded to MinIO", bucket=self.bucket, key=key)
            return f"minio://{self.bucket}/{key}"
        except Exception as e:
            logger.error("MinIO upload failed", bucket=self.bucket, key=key, error=str(e))
            raise StorageError(f"Failed to upload to MinIO: {str(e)}")
    
    def download_file(self, key: str, local_path: str) -> bool:
        """从 MinIO 下载文件"""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.fget_object(self.bucket, key, local_path)
            return True
        except Exception as e:
            logger.error("MinIO download failed", bucket=self.bucket, key=key, error=str(e))
            return False
    
    def delete_file(self, key: str) -> bool:
        """从 MinIO 删除文件"""
        try:
            self.client.remove_object(self.bucket, key)
            logger.info("File deleted from MinIO", bucket=self.bucket, key=key)
            return True
        except Exception as e:
            logger.error("MinIO delete failed", bucket=self.bucket, key=key, error=str(e))
            return False
    
    def get_file_url(self, key: str) -> str:
        """获取 MinIO 文件的预签名 URL"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(self.bucket, key, expires=timedelta(hours=1))
            return url
        except Exception as e:
            logger.error("MinIO URL generation failed", bucket=self.bucket, key=key, error=str(e))
            return f"minio://{self.bucket}/{key}"


class StorageError(Exception):
    """存储操作异常"""
    pass


class StorageService:
    """统一存储服务"""
    
    def __init__(self):
        self.provider = self._create_provider()
    
    def _create_provider(self) -> StorageProvider:
        """根据配置创建存储提供者"""
        config = Config.get_storage_config()
        
        if config['provider'] == 's3':
            return S3StorageProvider(
                access_key=config['access_key'],
                secret_key=config['secret_key'],
                region=config['region'],
                bucket=config['bucket']
            )
        elif config['provider'] == 'minio':
            return MinIOStorageProvider(
                endpoint=config['endpoint'],
                access_key=config['access_key'],
                secret_key=config['secret_key'],
                bucket=config['bucket'],
                secure=config['secure']
            )
        else:  # local
            return LocalStorageProvider(config['root_path'])
    
    def generate_file_key(self, file_id: str, filename: str, prefix: str = 'raw') -> str:
        """生成文件存储键"""
        now = datetime.now()
        date_path = now.strftime('%Y/%m/%d')
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        return f"{prefix}/{date_path}/{file_id}.{ext}"
    
    def upload_raw_file(self, file_data: BinaryIO, file_id: str, filename: str) -> str:
        """上传原始文件"""
        key = self.generate_file_key(file_id, filename, 'raw')
        return self.provider.upload_file(file_data, key)
    
    def upload_processed_file(self, file_data: BinaryIO, file_id: str, filename: str = 'output.webm') -> str:
        """上传处理后的文件"""
        key = self.generate_file_key(file_id, filename, 'processed')
        return self.provider.upload_file(file_data, key)
    
    def download_file(self, key: str, local_path: str) -> bool:
        """下载文件到本地"""
        return self.provider.download_file(key, local_path)
    
    def delete_file(self, key: str) -> bool:
        """删除文件"""
        return self.provider.delete_file(key)
    
    def get_file_url(self, key: str) -> str:
        """获取文件访问URL"""
        return self.provider.get_file_url(key)


# 全局存储服务实例
storage_service = StorageService()
