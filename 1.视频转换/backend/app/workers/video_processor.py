"""
视频处理 Worker - 使用 FFmpeg 进行透明背景转换
"""
import os
import tempfile
import subprocess
import shutil
import time
import threading
from typing import Dict, Any

from celery import current_task
from .celery_app import celery_app
from ..config import Config, TaskStatus, ErrorCodes
from ..services.task_manager import task_manager
from ..services.storage import storage_service
from ..utils.logger import setup_logger

logger = setup_logger()


def build_ffmpeg_command(input_path: str, output_path: str, options: Dict[str, Any]) -> list:
    """
    构建 FFmpeg 命令 - 使用边缘检测和自适应阈值处理
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        options: 转换选项
        
    Returns:
        FFmpeg 命令列表
    """
    # 解析选项
    color = options.get('color', '#000000')
    tolerance = options.get('tolerance', 10)
    feather = options.get('feather', 0.5)
    
    # 新增高级边界处理选项
    edge_enhancement = options.get('edgeEnhancement', True)  # 边缘增强
    edge_threshold_low = options.get('edgeThresholdLow', 0.1)  # 边缘检测低阈值
    edge_threshold_high = options.get('edgeThresholdHigh', 0.4)  # 边缘检测高阈值
    morphology_iterations = options.get('morphologyIterations', 1)  # 形态学处理迭代次数
    
    # 新增：去水印（左上角 ROI）参数（按百分比），默认开启
    remove_watermark = options.get('removeWatermark', True)
    wm_x_percent = float(options.get('wmX', 1.2))
    wm_y_percent = float(options.get('wmY', 1.2))
    wm_w_percent = float(options.get('wmW', 14.0))
    wm_h_percent = float(options.get('wmH', 5.5))
    
    # 转换参数
    # 颜色：#000000 -> black 或 0x000000
    if color == '#000000':
        color_param = 'black'
    else:
        color_param = color.replace('#', '0x')
    
    # 容差：0-100 -> 0.00-1.00
    similarity = tolerance / 100.0
    
    # 边缘平滑：0-10 -> 0.00-1.00
    blend = feather / 10.0
    
    # 构建视频滤镜链
    if edge_enhancement:
        # 方案三：边缘检测 + 自适应阈值处理
        video_filter = _build_enhanced_filter_chain(
            color_param, similarity, blend, 
            edge_threshold_low, edge_threshold_high, morphology_iterations
        )
    else:
        # 传统 colorkey 方法（向后兼容）
        video_filter = f'colorkey=color={color_param}:similarity={similarity:.2f}:blend={blend:.2f}'
    
    # 如启用去水印，则在滤镜链最前增加 delogo 处理
    if remove_watermark:
        # 使用 delogo 进行平滑抹除，并在 ROI 区域叠加全透明遮罩以彻底移除残留
        # 1) delogo：适当增大 t（厚度）以增强去印力度
        delogo_filter = (
            f"delogo=x=iw*{wm_x_percent/100.0:.4f}:"
            f"y=ih*{wm_y_percent/100.0:.4f}:"
            f"w=iw*{wm_w_percent/100.0:.4f}:"
            f"h=ih*{wm_h_percent/100.0:.4f}:"
            f"t=8:show=0"
        )
        # 2) 在滤镜链最前追加 format=rgba + drawbox(alpha=0) 强制将该区域置为完全透明
        transparent_mask = (
            f"format=rgba,drawbox=x=iw*{wm_x_percent/100.0:.4f}:"
            f"y=ih*{wm_y_percent/100.0:.4f}:"
            f"w=iw*{wm_w_percent/100.0:.4f}:"
            f"h=ih*{wm_h_percent/100.0:.4f}:"
            f"color=black@0:t=fill"
        )
        video_filter = f"{delogo_filter},{transparent_mask},{video_filter}"
    
    # 构建 FFmpeg 命令
    cmd = [
        Config.FFMPEG_PATH,
        '-y',  # 覆盖输出文件
        '-i', input_path,  # 输入文件
        '-vf', video_filter,  # 增强的视频滤镜
        '-c:v', 'libvpx-vp9',  # VP9 编码器
        '-pix_fmt', 'yuva420p',  # 支持 Alpha 通道的像素格式
        '-auto-alt-ref', '0',  # VP9 Alpha 必需参数
        '-an',  # 移除音频轨道
        '-loglevel', 'error',  # 只输出错误日志
        output_path  # 输出文件
    ]
    
    return cmd


def _build_enhanced_filter_chain(color_param: str, similarity: float, blend: float, 
                                edge_low: float, edge_high: float, morph_iter: int) -> str:
    """
    构建增强的滤镜链 - 边缘检测 + 自适应阈值处理
    
    Args:
        color_param: 颜色参数
        similarity: 相似度
        blend: 混合度
        edge_low: 边缘检测低阈值
        edge_high: 边缘检测高阈值
        morph_iter: 形态学处理迭代次数
        
    Returns:
        FFmpeg 滤镜链字符串
    """
    # 分支：主要处理 + 边缘检测
    filter_chain = f"split=2[main][edge];"
    
    # 边缘检测分支：使用 Canny 边缘检测
    filter_chain += f"[edge]edgedetect=mode=canny:low={edge_low:.2f}:high={edge_high:.2f}[edges];"
    
    # 主处理分支：双重 colorkey 处理
    # 第一层：移除主要黑色区域
    filter_chain += f"[main]colorkey=color={color_param}:similarity={similarity:.2f}:blend={blend:.2f}[main1];"
    
    # 第二层：处理残留的深灰色/黑色边缘
    dark_similarity = min(similarity + 0.05, 0.95)  # 增加5%容差处理残留
    fine_blend = max(blend * 0.5, 0.01)  # 更精细的混合
    filter_chain += f"[main1]colorkey=color=0x0a0a0a:similarity={dark_similarity:.2f}:blend={fine_blend:.2f}[main2];"
    
    # 形态学处理：去除小的黑色斑点
    if morph_iter > 0:
        filter_chain += f"[main2]erosion=coordinates=1[main3];"
        filter_chain += f"[main3]dilation=coordinates={morph_iter}[main4];"
        main_output = "main4"
    else:
        main_output = "main2"
    
    # 边缘增强：使用边缘检测结果来优化 Alpha 通道
    filter_chain += f"[{main_output}][edges]blend=all_mode=multiply:all_opacity=0.3[enhanced];"
    
    # 最终柔化处理：轻微高斯模糊来平滑边缘
    filter_chain += f"[enhanced]gblur=sigma=0.8:steps=1"
    
    return filter_chain


def _execute_ffmpeg_with_progress(cmd: list, task_id: str, start_progress: int = 40, end_progress: int = 80):
    """
    执行 FFmpeg 命令并模拟进度更新
    
    Args:
        cmd: FFmpeg 命令列表
        task_id: 任务ID
        start_progress: 开始进度百分比
        end_progress: 结束进度百分比
        
    Returns:
        subprocess.CompletedProcess 对象
    """
    # 启动 FFmpeg 进程
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 启动进度更新线程
    progress_thread = threading.Thread(
        target=_update_progress_during_processing,
        args=(task_id, start_progress, end_progress, process),
        daemon=True
    )
    progress_thread.start()
    
    # 等待 FFmpeg 完成
    stdout, stderr = process.communicate(timeout=300)
    
    # 确保进度线程结束
    progress_thread.join(timeout=1)
    
    # 创建 CompletedProcess 对象以保持兼容性
    result = subprocess.CompletedProcess(
        cmd, process.returncode, stdout, stderr
    )
    
    return result


def _update_progress_during_processing(task_id: str, start_progress: int, end_progress: int, process: subprocess.Popen):
    """
    在处理过程中更新进度的后台线程
    
    Args:
        task_id: 任务ID
        start_progress: 开始进度
        end_progress: 结束进度
        process: FFmpeg 进程对象
    """
    current_progress = start_progress
    progress_step = 2  # 每次增加2%
    update_interval = 0.5  # 每0.5秒更新一次
    
    while process.poll() is None:  # 进程还在运行
        if current_progress < end_progress:
            current_progress = min(current_progress + progress_step, end_progress)
            try:
                task_manager.update_task_status(task_id, TaskStatus.RUNNING, progress=current_progress)
                logger.debug("Progress updated", task_id=task_id, progress=current_progress)
            except Exception as e:
                logger.warning("Failed to update progress", task_id=task_id, error=str(e))
        
        time.sleep(update_interval)
    
    # 确保达到结束进度
    if current_progress < end_progress:
        try:
            task_manager.update_task_status(task_id, TaskStatus.RUNNING, progress=end_progress)
        except Exception as e:
            logger.warning("Failed to update final progress", task_id=task_id, error=str(e))


@celery_app.task(bind=True)
def process_video(self, task_id: str, file_id: str, options: Dict[str, Any] = None):
    """
    处理视频任务
    
    Args:
        task_id: 任务ID
        file_id: 文件ID
        options: 转换选项
        
    Returns:
        处理结果
    """
    logger.info("Starting video processing", task_id=task_id, file_id=file_id)
    
    # 设置任务状态为运行中
    task_manager.set_task_running(task_id, progress=10)
    
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. 获取文件记录
            file_record = task_manager.get_file_record(file_id)
            if not file_record:
                raise ProcessingError("File record not found", ErrorCodes.TASK_NOT_FOUND)
            
            storage_key = file_record.get('storageKey')
            if not storage_key:
                raise ProcessingError("File storage key not found", ErrorCodes.STORAGE_ERROR)
            
            # 2. 下载原始文件
            input_path = os.path.join(temp_dir, f"input_{file_id}")
            if not storage_service.download_file(storage_key, input_path):
                raise ProcessingError("Failed to download input file", ErrorCodes.STORAGE_ERROR)
            
            task_manager.update_task_status(task_id, TaskStatus.RUNNING, progress=30)
            
            # 3. 准备输出文件路径
            output_path = os.path.join(temp_dir, f"output_{file_id}.webm")
            
            # 4. 构建并执行 FFmpeg 命令
            cmd = build_ffmpeg_command(input_path, output_path, options or {})
            
            logger.info("Executing FFmpeg command", task_id=task_id, cmd=' '.join(cmd))
            
            # 执行 FFmpeg 并实时更新进度
            task_manager.update_task_status(task_id, TaskStatus.RUNNING, progress=40)
            
            # 使用模拟进度更新来展示处理过程
            result = _execute_ffmpeg_with_progress(cmd, task_id, start_progress=40, end_progress=80)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "FFmpeg processing failed"
                logger.error("FFmpeg failed", task_id=task_id, error=error_msg, returncode=result.returncode)
                raise ProcessingError(f"FFmpeg failed: {error_msg}", ErrorCodes.FFMPEG_FAILED)
            
            # 5. 检查输出文件是否存在
            if not os.path.exists(output_path):
                raise ProcessingError("Output file not created", ErrorCodes.FFMPEG_FAILED)
            
            # 6. 上传处理后的文件
            task_manager.update_task_status(task_id, TaskStatus.RUNNING, progress=85)
            
            with open(output_path, 'rb') as f:
                result_url = storage_service.upload_processed_file(f, file_id, 'output.webm')
            
            task_manager.update_task_status(task_id, TaskStatus.RUNNING, progress=95)
            
            # 7. 设置任务完成
            task_manager.set_task_success(task_id, result_url)
            
            logger.info("Video processing completed", task_id=task_id, file_id=file_id, result_url=result_url)
            
            return {
                'task_id': task_id,
                'file_id': file_id,
                'status': TaskStatus.SUCCESS,
                'result_url': result_url
            }
            
        except ProcessingError as e:
            logger.error("Processing error", task_id=task_id, error_code=e.error_code, error_message=str(e))
            task_manager.set_task_failed(task_id, e.error_code, str(e))
            raise
            
        except subprocess.TimeoutExpired:
            error_msg = "Processing timeout"
            logger.error("Processing timeout", task_id=task_id)
            task_manager.set_task_failed(task_id, ErrorCodes.FFMPEG_FAILED, error_msg)
            raise ProcessingError(error_msg, ErrorCodes.FFMPEG_FAILED)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error("Unexpected processing error", task_id=task_id, error=error_msg)
            task_manager.set_task_failed(task_id, ErrorCodes.INTERNAL_ERROR, error_msg)
            raise ProcessingError(error_msg, ErrorCodes.INTERNAL_ERROR)


class ProcessingError(Exception):
    """视频处理异常"""
    
    def __init__(self, message: str, error_code: str):
        self.error_code = error_code
        super().__init__(message)


@celery_app.task
def cleanup_old_files():
    """清理过期文件的定时任务"""
    logger.info("Starting file cleanup task")
    
    # 清理任务记录
    cleaned_tasks = task_manager.cleanup_expired_tasks()
    
    # TODO: 清理存储中的过期文件
    # 这里可以添加存储清理逻辑
    
    logger.info("File cleanup completed", cleaned_tasks=cleaned_tasks)
    return {'cleaned_tasks': cleaned_tasks}


# 注册定时任务（可选）
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'app.workers.video_processor.cleanup_old_files',
        'schedule': 3600.0,  # 每小时运行一次
    },
}
celery_app.conf.timezone = 'UTC'
