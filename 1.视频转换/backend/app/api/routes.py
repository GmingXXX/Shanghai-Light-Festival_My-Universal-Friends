"""
API 路由 - 处理上传、转换、状态查询、下载
"""
import os
import uuid
import tempfile
import zipfile
from io import BytesIO
from typing import List

from flask import Blueprint, request, jsonify, send_file
from werkzeug.datastructures import FileStorage

from ..config import Config, ErrorCodes
from ..services.task_manager import task_manager
from ..services.storage import storage_service
from ..workers.video_processor import process_video
from ..utils.validators import validate_upload_files, validate_convert_options, get_file_info, ValidationError
from ..utils.logger import setup_logger

logger = setup_logger()

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'service': 'alphavid-converter',
        'version': '1.0.0'
    })


@api_bp.route('/upload', methods=['POST'])
def upload_files():
    """
    文件上传接口
    
    接收多个视频文件，进行校验并存储
    返回文件信息列表
    """
    try:
        # 获取上传的文件
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'No files provided'
                }
            }), 400
        
        # 校验文件
        validate_upload_files(files)
        
        results = []
        
        for file_storage in files:
            try:
                # 生成文件ID
                file_id = str(uuid.uuid4())
                
                # 创建临时文件来获取视频信息
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_storage.filename.rsplit('.', 1)[-1]}") as temp_file:
                    file_storage.save(temp_file.name)
                    
                    # 获取文件信息
                    file_info = get_file_info(file_storage, temp_file.name)
                    
                    # 校验视频时长
                    from ..utils.validators import validate_video_duration
                    duration_valid, duration = validate_video_duration(temp_file.name)
                    if not duration_valid:
                        raise ValidationError(
                            ErrorCodes.LIMIT_EXCEEDED_DURATION,
                            f"Video duration exceeds {Config.MAX_DURATION_SECONDS} seconds limit"
                        )
                    
                    file_info['duration'] = duration or 0
                    
                    # 创建文件记录
                    file_record = task_manager.create_file_record(
                        file_id=file_id,
                        filename=file_storage.filename,
                        size=file_info['size'],
                        duration=file_info['duration']
                    )
                    
                    # 上传到存储
                    file_storage.seek(0)  # 重置文件指针
                    storage_url = storage_service.upload_raw_file(
                        file_storage.stream,
                        file_id,
                        file_storage.filename
                    )
                    
                    # 更新存储键
                    storage_key = storage_service.generate_file_key(file_id, file_storage.filename, 'raw')
                    task_manager.update_file_storage_key(file_id, storage_key)
                    
                    # 清理临时文件
                    os.unlink(temp_file.name)
                    
                    results.append({
                        'fileId': file_id,
                        'name': file_storage.filename,
                        'size': file_info['size'],
                        'duration': file_info['duration']
                    })
                    
                    logger.info("File uploaded successfully", file_id=file_id, filename=file_storage.filename)
                    
            except ValidationError as e:
                logger.error("File validation failed", filename=file_storage.filename, error=str(e))
                return jsonify({
                    'error': {
                        'code': e.error_code,
                        'message': e.message
                    }
                }), 400
                
            except Exception as e:
                logger.error("File upload failed", filename=file_storage.filename, error=str(e))
                return jsonify({
                    'error': {
                        'code': ErrorCodes.STORAGE_ERROR,
                        'message': f"Failed to upload file: {str(e)}"
                    }
                }), 500
        
        return jsonify(results)
        
    except ValidationError as e:
        logger.error("Upload validation failed", error=str(e))
        return jsonify({
            'error': {
                'code': e.error_code,
                'message': e.message
            }
        }), 400
        
    except Exception as e:
        logger.error("Upload failed", error=str(e))
        return jsonify({
            'error': {
                'code': ErrorCodes.INTERNAL_ERROR,
                'message': 'Internal server error'
            }
        }), 500


@api_bp.route('/convert', methods=['POST'])
def convert_files():
    """
    开始转换任务
    
    接收文件ID列表和转换选项，创建处理任务
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'No data provided'
                }
            }), 400
        
        file_ids = data.get('files', [])
        options = data.get('options', {})
        
        if not file_ids:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'No file IDs provided'
                }
            }), 400
        
        if len(file_ids) > Config.MAX_FILES_PER_BATCH:
            return jsonify({
                'error': {
                    'code': ErrorCodes.LIMIT_EXCEEDED_COUNT,
                    'message': f'Maximum {Config.MAX_FILES_PER_BATCH} files allowed per batch'
                }
            }), 400
        
        # 校验转换选项
        options_valid, options_error = validate_convert_options(options)
        if not options_valid:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': options_error
                }
            }), 400
        
        task_ids = []
        
        for file_id in file_ids:
            # 检查文件是否存在
            file_record = task_manager.get_file_record(file_id)
            if not file_record:
                return jsonify({
                    'error': {
                        'code': ErrorCodes.TASK_NOT_FOUND,
                        'message': f'File {file_id} not found'
                    }
                }), 404
            
            # 创建任务
            task_id = task_manager.create_task(file_id, options)
            task_ids.append(task_id)
            
            # 提交到 Celery 队列
            process_video.delay(task_id, file_id, options)
            
            logger.info("Convert task created", task_id=task_id, file_id=file_id)
        
        return jsonify({'taskIds': task_ids})
        
    except Exception as e:
        logger.error("Convert failed", error=str(e))
        return jsonify({
            'error': {
                'code': ErrorCodes.INTERNAL_ERROR,
                'message': 'Internal server error'
            }
        }), 500


@api_bp.route('/status', methods=['GET'])
def get_task_status():
    """获取任务状态"""
    try:
        task_id = request.args.get('taskId')
        if not task_id:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'Task ID is required'
                }
            }), 400
        
        task_status = task_manager.get_task_status(task_id)
        if not task_status:
            return jsonify({
                'error': {
                    'code': ErrorCodes.TASK_NOT_FOUND,
                    'message': 'Task not found'
                }
            }), 404
        
        # 构建响应
        response = {
            'taskId': task_status['taskId'],
            'status': task_status['status'],
            'progress': task_status.get('progress', 0)
        }
        
        # 添加结果URL（如果成功）
        if task_status['status'] == 'SUCCESS' and task_status.get('resultUrl'):
            response['resultUrl'] = task_status['resultUrl']
        
        # 添加错误信息（如果失败）
        if task_status['status'] == 'FAILED':
            response['errorCode'] = task_status.get('errorCode')
            response['errorMessage'] = task_status.get('errorMessage')
        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Status check failed", error=str(e))
        return jsonify({
            'error': {
                'code': ErrorCodes.INTERNAL_ERROR,
                'message': 'Internal server error'
            }
        }), 500


@api_bp.route('/download', methods=['GET'])
def download_file():
    """下载处理后的文件"""
    try:
        file_id = request.args.get('fileId')
        if not file_id:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'File ID is required'
                }
            }), 400
        
        # 生成处理后文件的存储键
        storage_key = storage_service.generate_file_key(file_id, 'output.webm', 'processed')
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            if not storage_service.download_file(storage_key, temp_file.name):
                return jsonify({
                    'error': {
                        'code': ErrorCodes.TASK_NOT_FOUND,
                        'message': 'Processed file not found'
                    }
                }), 404
            
            # 发送文件
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'transparent_{file_id}.webm',
                mimetype='video/webm'
            )
        
    except Exception as e:
        logger.error("Download failed", file_id=file_id, error=str(e))
        return jsonify({
            'error': {
                'code': ErrorCodes.INTERNAL_ERROR,
                'message': 'Internal server error'
            }
        }), 500


@api_bp.route('/batch-download', methods=['POST'])
def batch_download():
    """批量下载处理后的文件（打包为ZIP）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'No data provided'
                }
            }), 400
        
        task_ids = data.get('taskIds', [])
        if not task_ids:
            return jsonify({
                'error': {
                    'code': ErrorCodes.INVALID_FILE,
                    'message': 'No task IDs provided'
                }
            }), 400
        
        # 创建内存中的ZIP文件
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            successful_files = 0
            
            for task_id in task_ids:
                try:
                    # 获取任务状态
                    task_status = task_manager.get_task_status(task_id)
                    if not task_status or task_status['status'] != 'SUCCESS':
                        continue
                    
                    file_id = task_status['fileId']
                    
                    # 获取文件记录以获取原始文件名
                    file_record = task_manager.get_file_record(file_id)
                    original_name = file_record['name'] if file_record else 'unknown'
                    base_name = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
                    
                    # 生成处理后文件的存储键
                    storage_key = storage_service.generate_file_key(file_id, 'output.webm', 'processed')
                    
                    # 下载到临时文件
                    with tempfile.NamedTemporaryFile() as temp_file:
                        if storage_service.download_file(storage_key, temp_file.name):
                            # 添加到ZIP
                            zip_file.write(temp_file.name, f'{base_name}_transparent.webm')
                            successful_files += 1
                            logger.info("File added to ZIP", task_id=task_id, file_id=file_id)
                        
                except Exception as e:
                    logger.error("Failed to add file to ZIP", task_id=task_id, error=str(e))
                    continue
        
        if successful_files == 0:
            return jsonify({
                'error': {
                    'code': ErrorCodes.TASK_NOT_FOUND,
                    'message': 'No processed files found'
                }
            }), 404
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='transparent_videos.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        logger.error("Batch download failed", error=str(e))
        return jsonify({
            'error': {
                'code': ErrorCodes.INTERNAL_ERROR,
                'message': 'Internal server error'
            }
        }), 500


# 错误处理
@api_bp.errorhandler(413)
def file_too_large(error):
    """文件过大错误处理"""
    return jsonify({
        'error': {
            'code': ErrorCodes.LIMIT_EXCEEDED_SIZE,
            'message': f'File size exceeds {Config.MAX_FILE_SIZE_MB}MB limit'
        }
    }), 413


@api_bp.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'error': {
            'code': ErrorCodes.TASK_NOT_FOUND,
            'message': 'Resource not found'
        }
    }), 404


@api_bp.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error("Internal server error", error=str(error))
    return jsonify({
        'error': {
            'code': ErrorCodes.INTERNAL_ERROR,
            'message': 'Internal server error'
        }
    }), 500
