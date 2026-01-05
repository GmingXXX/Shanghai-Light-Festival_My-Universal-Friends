"""
测试校验器模块
"""
import pytest
from unittest.mock import Mock, patch
from werkzeug.datastructures import FileStorage
from io import BytesIO

from app.utils.validators import (
    validate_file_extension,
    validate_file_size,
    validate_batch_size,
    validate_convert_options,
    validate_upload_files,
    ValidationError
)
from app.config import ErrorCodes


class TestFileExtensionValidation:
    """测试文件扩展名校验"""
    
    def test_valid_extensions(self):
        """测试有效的扩展名"""
        assert validate_file_extension('video.mp4') == True
        assert validate_file_extension('video.mov') == True
        assert validate_file_extension('video.webm') == True
        assert validate_file_extension('VIDEO.MP4') == True  # 大小写不敏感
    
    def test_invalid_extensions(self):
        """测试无效的扩展名"""
        assert validate_file_extension('video.avi') == False
        assert validate_file_extension('video.mkv') == False
        assert validate_file_extension('document.pdf') == False
        assert validate_file_extension('image.jpg') == False
    
    def test_no_extension(self):
        """测试没有扩展名的文件"""
        assert validate_file_extension('video') == False
        assert validate_file_extension('') == False
        assert validate_file_extension(None) == False


class TestFileSizeValidation:
    """测试文件大小校验"""
    
    def test_valid_file_size(self):
        """测试有效的文件大小"""
        # 创建 1MB 的模拟文件
        file_data = BytesIO(b'0' * 1024 * 1024)
        file_storage = FileStorage(file_data, filename='test.mp4')
        
        assert validate_file_size(file_storage) == True
    
    def test_oversized_file(self):
        """测试超大文件"""
        # 创建 60MB 的模拟文件（超过 50MB 限制）
        file_data = BytesIO(b'0' * 60 * 1024 * 1024)
        file_storage = FileStorage(file_data, filename='test.mp4')
        
        assert validate_file_size(file_storage) == False


class TestBatchSizeValidation:
    """测试批量文件数量校验"""
    
    def test_valid_batch_size(self):
        """测试有效的批量大小"""
        files = [Mock() for _ in range(5)]  # 5个文件
        assert validate_batch_size(files) == True
        
        files = [Mock() for _ in range(10)]  # 10个文件（边界值）
        assert validate_batch_size(files) == True
    
    def test_oversized_batch(self):
        """测试超出限制的批量大小"""
        files = [Mock() for _ in range(11)]  # 11个文件（超过限制）
        assert validate_batch_size(files) == False


class TestConvertOptionsValidation:
    """测试转换选项校验"""
    
    def test_valid_options(self):
        """测试有效的转换选项"""
        options = {
            'color': '#000000',
            'tolerance': 10,
            'feather': 0.5,
            'applyToAll': True
        }
        valid, error = validate_convert_options(options)
        assert valid == True
        assert error is None
    
    def test_empty_options(self):
        """测试空选项"""
        valid, error = validate_convert_options({})
        assert valid == True
        assert error is None
        
        valid, error = validate_convert_options(None)
        assert valid == True
        assert error is None
    
    def test_invalid_color(self):
        """测试无效的颜色格式"""
        options = {'color': 'invalid-color'}
        valid, error = validate_convert_options(options)
        assert valid == False
        assert 'color format' in error
    
    def test_invalid_tolerance(self):
        """测试无效的容差值"""
        options = {'tolerance': 150}  # 超出范围
        valid, error = validate_convert_options(options)
        assert valid == False
        assert 'Tolerance must be between' in error
        
        options = {'tolerance': -10}  # 负值
        valid, error = validate_convert_options(options)
        assert valid == False
        assert 'Tolerance must be between' in error
    
    def test_invalid_feather(self):
        """测试无效的边缘平滑值"""
        options = {'feather': 15}  # 超出范围
        valid, error = validate_convert_options(options)
        assert valid == False
        assert 'Feather must be between' in error


class TestUploadFilesValidation:
    """测试文件上传校验"""
    
    def test_valid_upload(self):
        """测试有效的上传文件"""
        file_data = BytesIO(b'0' * 1024 * 1024)  # 1MB
        file_storage = FileStorage(file_data, filename='test.mp4')
        files = [file_storage]
        
        # 应该不抛出异常
        validate_upload_files(files)
    
    def test_too_many_files(self):
        """测试文件数量超限"""
        files = []
        for i in range(11):  # 11个文件
            file_data = BytesIO(b'0' * 1024)
            file_storage = FileStorage(file_data, filename=f'test{i}.mp4')
            files.append(file_storage)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_files(files)
        
        assert exc_info.value.error_code == ErrorCodes.LIMIT_EXCEEDED_COUNT
    
    def test_invalid_file_extension(self):
        """测试无效文件扩展名"""
        file_data = BytesIO(b'0' * 1024)
        file_storage = FileStorage(file_data, filename='test.avi')
        files = [file_storage]
        
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_files(files)
        
        assert exc_info.value.error_code == ErrorCodes.UNSUPPORTED_FORMAT
    
    def test_empty_filename(self):
        """测试空文件名"""
        file_data = BytesIO(b'0' * 1024)
        file_storage = FileStorage(file_data, filename='')
        files = [file_storage]
        
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_files(files)
        
        assert exc_info.value.error_code == ErrorCodes.INVALID_FILE
    
    @patch('app.utils.validators.validate_file_size')
    def test_oversized_file(self, mock_validate_size):
        """测试超大文件"""
        mock_validate_size.return_value = False
        
        file_data = BytesIO(b'0' * 1024)
        file_storage = FileStorage(file_data, filename='test.mp4')
        files = [file_storage]
        
        with pytest.raises(ValidationError) as exc_info:
            validate_upload_files(files)
        
        assert exc_info.value.error_code == ErrorCodes.LIMIT_EXCEEDED_SIZE
