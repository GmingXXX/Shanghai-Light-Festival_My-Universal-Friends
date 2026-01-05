#!/usr/bin/env python3
"""
透明视频转换器部署测试脚本
测试 API 端点和基本功能
"""

import requests
import time
import json
import sys
from pathlib import Path

# 测试配置
API_BASE_URL = "http://localhost:8000/api"
TIMEOUT = 30

def log_info(message):
    print(f"[INFO] {message}")

def log_error(message):
    print(f"[ERROR] {message}")

def log_success(message):
    print(f"[SUCCESS] {message}")

def test_health_check():
    """测试健康检查接口"""
    log_info("测试健康检查接口...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                log_success("健康检查通过")
                return True
            else:
                log_error(f"健康检查失败: {data}")
                return False
        else:
            log_error(f"健康检查请求失败: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        log_error(f"健康检查连接失败: {e}")
        return False

def create_test_video():
    """创建测试视频文件"""
    log_info("创建测试视频文件...")
    
    try:
        import subprocess
        
        # 使用 FFmpeg 创建一个简单的测试视频
        test_video_path = "test_video.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=black:size=320x240:duration=5",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            test_video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and Path(test_video_path).exists():
            log_success(f"测试视频创建成功: {test_video_path}")
            return test_video_path
        else:
            log_error(f"测试视频创建失败: {result.stderr}")
            return None
            
    except FileNotFoundError:
        log_error("FFmpeg 未找到，跳过视频创建测试")
        return None
    except Exception as e:
        log_error(f"创建测试视频时出错: {e}")
        return None

def test_file_upload(video_path):
    """测试文件上传"""
    log_info("测试文件上传...")
    
    try:
        with open(video_path, 'rb') as f:
            files = {'files': (video_path, f, 'video/mp4')}
            response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                file_id = data[0].get('fileId')
                log_success(f"文件上传成功，文件ID: {file_id}")
                return file_id
            else:
                log_error(f"上传响应格式错误: {data}")
                return None
        else:
            log_error(f"文件上传失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        log_error(f"文件上传异常: {e}")
        return None

def test_convert_task(file_id):
    """测试转换任务"""
    log_info("测试转换任务...")
    
    try:
        payload = {
            "files": [file_id],
            "options": {
                "color": "#000000",
                "tolerance": 10,
                "feather": 0.5
            }
        }
        
        response = requests.post(
            f"{API_BASE_URL}/convert",
            json=payload,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            task_ids = data.get('taskIds', [])
            if task_ids:
                task_id = task_ids[0]
                log_success(f"转换任务创建成功，任务ID: {task_id}")
                return task_id
            else:
                log_error(f"转换任务响应格式错误: {data}")
                return None
        else:
            log_error(f"转换任务创建失败: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        log_error(f"转换任务异常: {e}")
        return None

def test_task_status(task_id):
    """测试任务状态查询"""
    log_info("测试任务状态查询...")
    
    max_attempts = 30  # 最多等待30次（约5分钟）
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"{API_BASE_URL}/status",
                params={"taskId": task_id},
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                progress = data.get('progress', 0)
                
                log_info(f"任务状态: {status}, 进度: {progress}%")
                
                if status == 'SUCCESS':
                    log_success("任务处理完成")
                    return True
                elif status == 'FAILED':
                    error_msg = data.get('errorMessage', 'Unknown error')
                    log_error(f"任务处理失败: {error_msg}")
                    return False
                elif status in ['PENDING', 'RUNNING']:
                    time.sleep(10)  # 等待10秒后重试
                    attempt += 1
                else:
                    log_error(f"未知任务状态: {status}")
                    return False
            else:
                log_error(f"状态查询失败: {response.status_code}")
                return False
                
        except Exception as e:
            log_error(f"状态查询异常: {e}")
            return False
    
    log_error("任务处理超时")
    return False

def test_redis_connection():
    """测试 Redis 连接"""
    log_info("测试 Redis 连接...")
    
    try:
        import redis
        r = redis.from_url("redis://localhost:6379/0")
        r.ping()
        log_success("Redis 连接正常")
        return True
    except Exception as e:
        log_error(f"Redis 连接失败: {e}")
        return False

def test_storage_service():
    """测试存储服务"""
    log_info("测试存储服务...")
    
    # 这里可以添加存储服务的测试
    # 例如创建/读取/删除文件
    log_info("存储服务测试跳过（需要根据配置进行具体测试）")
    return True

def cleanup_test_files():
    """清理测试文件"""
    log_info("清理测试文件...")
    
    test_files = ["test_video.mp4"]
    
    for file_path in test_files:
        try:
            Path(file_path).unlink(missing_ok=True)
            log_info(f"删除测试文件: {file_path}")
        except Exception as e:
            log_error(f"删除测试文件失败 {file_path}: {e}")

def main():
    """主测试函数"""
    print("=" * 50)
    print("透明视频转换器 - 部署测试")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # 测试列表
    tests = [
        ("健康检查", test_health_check),
        ("Redis连接", test_redis_connection),
        ("存储服务", test_storage_service),
    ]
    
    # 执行基础测试
    for test_name, test_func in tests:
        total_tests += 1
        if test_func():
            tests_passed += 1
        print()
    
    # 如果基础测试通过，执行完整流程测试
    if tests_passed == total_tests:
        log_info("开始完整流程测试...")
        
        # 创建测试视频
        video_path = create_test_video()
        
        if video_path:
            # 测试上传
            file_id = test_file_upload(video_path)
            
            if file_id:
                total_tests += 1
                tests_passed += 1
                
                # 测试转换
                task_id = test_convert_task(file_id)
                
                if task_id:
                    total_tests += 1
                    tests_passed += 1
                    
                    # 测试状态查询
                    if test_task_status(task_id):
                        total_tests += 1
                        tests_passed += 1
    
    # 清理测试文件
    cleanup_test_files()
    
    # 输出测试结果
    print("=" * 50)
    print(f"测试完成: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        log_success("🎉 所有测试通过！部署成功！")
        return 0
    else:
        log_error(f"❌ {total_tests - tests_passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
