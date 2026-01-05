"""
文件与参数校验工具
"""
import os
from typing import List, Optional, Tuple
from werkzeug.datastructures import FileStorage
from moviepy.editor import VideoFileClip

from ..config import Config, ErrorCodes


def validate_file_extension(filename: str) -> bool:
    """
    校验文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        是否为支持的格式
    """
    if not filename:
        return False
        
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in Config.ALLOWED_EXTENSIONS


def validate_file_size(file_storage: FileStorage) -> bool:
    """
    校验文件大小
    
    Args:
        file_storage: Flask 文件对象
        
    Returns:
        是否在大小限制内
    """
    # 获取文件大小（字节）
    file_storage.seek(0, 2)  # 移到文件末尾
    file_size = file_storage.tell()
    file_storage.seek(0)  # 重置到开头
    
    max_size_bytes = Config.MAX_FILE_SIZE_MB * 1024 * 1024
    return file_size <= max_size_bytes


def validate_video_duration(file_path: str) -> Tuple[bool, Optional[float]]:
    """
    校验视频时长
    
    Args:
        file_path: 视频文件路径
        
    Returns:
        (是否在时长限制内, 视频时长秒数)
    """
    try:
        with VideoFileClip(file_path) as clip:
            duration = clip.duration
            is_valid = duration <= Config.MAX_DURATION_SECONDS
            return is_valid, duration
    except Exception:
        return False, None


def validate_batch_size(files: List[FileStorage]) -> bool:
    """
    校验批量文件数量
    
    Args:
        files: 文件列表
        
    Returns:
        是否在数量限制内
    """
    return len(files) <= Config.MAX_FILES_PER_BATCH


def validate_convert_options(options: dict) -> Tuple[bool, Optional[str]]:
    """
    校验转换参数
    
    Args:
        options: 转换选项字典
        
    Returns:
        (是否有效, 错误信息)
    """
    if not options:
        return True, None
        
    # 校验颜色格式
    color = options.get('color', '#000000')
    if not isinstance(color, str) or not color.startswith('#'):
        return False, "Invalid color format, expected #RRGGBB"
    
    # 校验容差范围
    tolerance = options.get('tolerance', 10)
    if not isinstance(tolerance, (int, float)) or not (0 <= tolerance <= 100):
        return False, "Tolerance must be between 0 and 100"
    
    # 校验边缘平滑范围
    feather = options.get('feather', 0.5)
    if not isinstance(feather, (int, float)) or not (0 <= feather <= 10):
        return False, "Feather must be between 0 and 10"
    
    # 校验边缘增强选项
    edge_enhancement = options.get('edgeEnhancement', True)
    if not isinstance(edge_enhancement, bool):
        return False, "Edge enhancement must be boolean"
    
    # 校验边缘检测阈值
    edge_threshold_low = options.get('edgeThresholdLow', 0.1)
    if not isinstance(edge_threshold_low, (int, float)) or not (0.01 <= edge_threshold_low <= 0.5):
        return False, "Edge threshold low must be between 0.01 and 0.5"
    
    edge_threshold_high = options.get('edgeThresholdHigh', 0.4)
    if not isinstance(edge_threshold_high, (int, float)) or not (0.1 <= edge_threshold_high <= 1.0):
        return False, "Edge threshold high must be between 0.1 and 1.0"
    
    # 确保高阈值大于低阈值
    if edge_threshold_high <= edge_threshold_low:
        return False, "Edge threshold high must be greater than edge threshold low"
    
    # 校验形态学处理迭代次数
    morphology_iterations = options.get('morphologyIterations', 1)
    if not isinstance(morphology_iterations, int) or not (0 <= morphology_iterations <= 5):
        return False, "Morphology iterations must be integer between 0 and 5"
    
    # 去水印：开关与 ROI 百分比（0-100），默认开启
    remove_watermark = options.get('removeWatermark', True)
    if not isinstance(remove_watermark, bool):
        return False, "removeWatermark must be boolean"
    
    # 仅在开启时校验 ROI
    if remove_watermark:
        wm_defaults = {
            'wmX': 1.2,
            'wmY': 1.2,
            'wmW': 14.0,
            'wmH': 5.5,
        }
        for key, default_val in wm_defaults.items():
            val = options.get(key, default_val)
            if not isinstance(val, (int, float)):
                return False, f"{key} must be a number representing percentage"
            # 允许 0-100 的百分比，宽高需大于 0
            if key in ('wmW', 'wmH'):
                if not (0.1 <= float(val) <= 100.0):
                    return False, f"{key} must be within 0.1 to 100"
            else:
                if not (0.0 <= float(val) <= 100.0):
                    return False, f"{key} must be within 0 to 100"
    
    return True, None


def get_file_info(file_storage: FileStorage, file_path: str) -> dict:
    """
    获取文件基本信息
    
    Args:
        file_storage: Flask 文件对象
        file_path: 文件保存路径
        
    Returns:
        文件信息字典
    """
    # 获取文件大小
    file_storage.seek(0, 2)
    file_size = file_storage.tell()
    file_storage.seek(0)
    
    # 获取视频时长
    try:
        with VideoFileClip(file_path) as clip:
            duration = clip.duration
    except Exception:
        duration = 0
    
    return {
        'name': file_storage.filename,
        'size': file_size,
        'duration': duration
    }


class ValidationError(Exception):
    """校验错误异常"""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def validate_upload_files(files: List[FileStorage]) -> None:
    """
    校验上传文件列表，失败时抛出 ValidationError
    
    Args:
        files: 文件列表
        
    Raises:
        ValidationError: 校验失败时抛出
    """
    # 校验文件数量
    if not validate_batch_size(files):
        raise ValidationError(
            ErrorCodes.LIMIT_EXCEEDED_COUNT,
            f"Maximum {Config.MAX_FILES_PER_BATCH} files allowed per batch"
        )
    
    for file_storage in files:
        # 校验文件名
        if not file_storage.filename:
            raise ValidationError(
                ErrorCodes.INVALID_FILE,
                "Empty filename"
            )
        
        # 校验扩展名
        if not validate_file_extension(file_storage.filename):
            raise ValidationError(
                ErrorCodes.UNSUPPORTED_FORMAT,
                f"Unsupported file format. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
            )
        
        # 校验文件大小
        if not validate_file_size(file_storage):
            raise ValidationError(
                ErrorCodes.LIMIT_EXCEEDED_SIZE,
                f"File size exceeds {Config.MAX_FILE_SIZE_MB}MB limit"
            )
